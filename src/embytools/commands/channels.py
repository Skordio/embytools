from datetime import datetime
from pathlib import Path

import typer

from ..envelope import read_export, write_export
from ..output import print_json, print_table
from ..session import emby_session

channels_app = typer.Typer(help="Live TV channel commands.")

EXPORT_TYPE = "livetv-favorite-channels"


def _slim(channels: list[dict]) -> list[dict]:
    """Reduce channel objects to the fields worth saving/copying."""
    return [{"Id": c["Id"], "Name": c["Name"]} for c in channels]


def _safe_filename(name: str) -> str:
    """Make a user name safe to use as a filename component."""
    return "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name)


def _snapshot_favorites(emby, export_dir: Path, users: list[tuple[dict, list[dict]]]) -> None:
    """Write a timestamped favorites snapshot per user into export_dir."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for user, favorites in users:
        path = export_dir / f"{_safe_filename(user['Name'])}-favorite-channels-{ts}.json"
        write_export(path, EXPORT_TYPE, emby.base_url, favorites)
        typer.echo(f"Snapshotted {len(favorites)} channel(s) for {user['Name']} -> {path}")


def _resolve_user(emby, name: str) -> dict:
    user = emby.users.find(name)
    if user is None:
        typer.echo(f"No user named {name!r}.", err=True)
        raise typer.Exit(1)
    return user


def _apply_favorites(
    emby,
    target: dict,
    items: list[dict],
    dry_run: bool,
    yes: bool,
    replace: bool = False,
    existing_channels: list[dict] | None = None,
) -> None:
    """Bring the target user's favorite channels in line with ``items``.

    Shared by ``copy`` and ``import``: previews the plan, then confirms before
    writing. Always adds items not yet favorited. When ``replace`` is set, also
    removes the target's existing favorites that aren't in ``items`` (exact
    sync); otherwise removals are left alone (additive). Idempotent and
    accurate — existing favorites are skipped so the preview matches reality.

    Pass ``existing_channels`` to reuse an already-fetched favorites list and
    avoid a redundant request.
    """
    if existing_channels is None:
        existing_channels = emby.livetv.favorite_channels(target["Id"])
    existing = {c["Id"]: c["Name"] for c in existing_channels}
    desired = {i["Id"] for i in items}
    to_add = [i for i in items if i["Id"] not in existing]
    to_remove = (
        [{"Id": cid, "Name": name} for cid, name in existing.items() if cid not in desired]
        if replace
        else []
    )

    typer.echo(
        f"{target['Name']}: {len(to_add)} to add, {len(to_remove)} to remove "
        f"({len(items) - len(to_add)} already favorited)."
    )
    for i in to_add:
        typer.echo(f"  + {i['Name']} ({i['Id']})")
    for i in to_remove:
        typer.echo(f"  - {i['Name']} ({i['Id']})")

    if not to_add and not to_remove:
        typer.echo("Already in sync." if replace else "Nothing to copy.")
        return
    if dry_run:
        typer.echo("Dry run — no changes made.")
        return
    if not yes:
        plan = f"Add {len(to_add)}"
        if to_remove:
            plan += f" and remove {len(to_remove)}"
        typer.confirm(f"{plan} favorite channel(s) for {target['Name']}?", abort=True)

    added = removed = 0
    try:
        for i in to_add:
            emby.favorites.add(target["Id"], i["Id"])
            added += 1
        for i in to_remove:
            emby.favorites.remove(target["Id"], i["Id"])
            removed += 1
    except Exception:
        typer.echo(
            f"Aborted partway for {target['Name']}: added {added}/{len(to_add)}, "
            f"removed {removed}/{len(to_remove)} before the error.",
            err=True,
        )
        raise

    done = f"Added {added}"
    if replace:
        done += f", removed {removed}"
    typer.echo(f"Done. {done} favorite channel(s) for {target['Name']}.")


@channels_app.command("list")
def channels_list(
    user: str = typer.Argument(..., help="User name."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
):
    """List a user's favorite Live TV channels."""
    with emby_session() as emby:
        u = _resolve_user(emby, user)
        channels = emby.livetv.favorite_channels(u["Id"])
        if not channels:
            typer.echo("No favorite channels." if not as_json else "[]")
            return
        rows = _slim(channels)
        if as_json:
            print_json(rows)
        else:
            print_table(rows, [("Name", 30), ("Id", 0)])


@channels_app.command("all")
def channels_all(as_json: bool = typer.Option(False, "--json", help="Emit JSON.")):
    """List all Live TV channels with their sort index and channel number."""
    with emby_session() as emby:
        channels, total = emby.livetv.manage_channels()
        if total > len(channels):
            typer.echo(
                f"Warning: showing {len(channels)} of {total} channels "
                "(raise the limit to see all).",
                err=True,
            )
        rows = [
            {
                "SortIndex": c.get("SortIndexNumber", 0),
                "Number": c.get("ChannelNumber") or "",
                "Name": c["Name"],
                "Id": c["Id"],
            }
            for c in channels
        ]
        if as_json:
            print_json(rows)
        else:
            print_table(rows, [("SortIndex", 9), ("Number", 7), ("Name", 34), ("Id", 0)])


@channels_app.command("copy")
def channels_copy(
    source: str = typer.Argument(..., help="Source user name."),
    target: str = typer.Argument(..., help="Target user name."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Make the target's favorites exactly match the source (also removes extras).",
    ),
    export: bool = typer.Option(
        False,
        "--export",
        help="Snapshot both users' favorites (pre-copy) to --export-dir before copying.",
    ),
    export_dir: Path = typer.Option(
        Path("snapshots"), "--export-dir", help="Directory for --export snapshots."
    ),
):
    """Copy a user's favorite Live TV channels onto another user."""
    with emby_session() as emby:
        src = _resolve_user(emby, source)
        tgt = _resolve_user(emby, target)
        channels = _slim(emby.livetv.favorite_channels(src["Id"]))

        # Fetch the target's current favorites once; reused for both the
        # snapshot and the add/remove plan below.
        target_existing = emby.livetv.favorite_channels(tgt["Id"])

        if export:
            if dry_run:
                typer.echo("Dry run — skipping snapshots.")
            else:
                _snapshot_favorites(
                    emby,
                    export_dir,
                    [(src, channels), (tgt, _slim(target_existing))],
                )

        _apply_favorites(
            emby, tgt, channels, dry_run, yes, replace=replace, existing_channels=target_existing
        )


@channels_app.command("export")
def channels_export(
    user: str = typer.Argument(..., help="User name."),
    file: Path = typer.Argument(..., help="Destination JSON file."),
):
    """Export a user's favorite Live TV channels to a JSON file."""
    with emby_session() as emby:
        u = _resolve_user(emby, user)
        channels = _slim(emby.livetv.favorite_channels(u["Id"]))
        write_export(file, EXPORT_TYPE, emby.base_url, channels)
        typer.echo(f"Exported {len(channels)} channel(s) to {file}.")


@channels_app.command("import")
def channels_import(
    target: str = typer.Argument(..., help="Target user name."),
    file: Path = typer.Argument(..., help="Exported JSON file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    replace: bool = typer.Option(
        False,
        "--replace",
        help="Make the target's favorites exactly match the file (also removes extras).",
    ),
):
    """Apply favorite Live TV channels from an export file to a user."""
    try:
        items = read_export(file, EXPORT_TYPE)
    except (ValueError, KeyError, OSError) as e:
        typer.echo(f"Could not read export: {e}", err=True)
        raise typer.Exit(1)
    with emby_session() as emby:
        tgt = _resolve_user(emby, target)
        _apply_favorites(emby, tgt, items, dry_run, yes, replace=replace)
