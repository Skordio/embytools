from datetime import datetime
from pathlib import Path

import typer

from ..envelope import read_export, write_export
from ..output import print_json, print_table
from ..session import emby_session

channels_app = typer.Typer(help="Live TV channel commands.")

EXPORT_TYPE = "livetv-favorite-channels"
NUMBER_TYPE = "livetv-channel-numbers"


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


# --- Channel numbering -------------------------------------------------------

numbers_app = typer.Typer(help="Assign and back up Live TV channel numbers.")


def _even_fill(names: list[str], lo: int, hi: int) -> list[tuple[str, str]]:
    """Spread names across the band [lo, hi], maximizing even gaps.

    Channel i gets number lo + i*step, where step packs the band as loosely as
    it can while keeping every channel inside it. Numbers are returned as strings
    (Emby's channel-number field is a string).
    """
    n = len(names)
    if n == 0:
        return []
    capacity = hi - lo + 1
    if n > capacity:
        raise ValueError(
            f"{n} channels can't fit in band {lo}-{hi} ({capacity} slots); widen the band."
        )
    step = max(1, capacity // n)
    return [(name, str(lo + i * step)) for i, name in enumerate(names)]


def _assign_numbers(
    channels: list[dict],
    favorite_names: set[str],
    fav_band: tuple[int, int],
    other_band: tuple[int, int],
) -> list[dict]:
    """Build an ordered, name-keyed numbering: favorites low, others high.

    ``channels`` is the management list (already in sort-index / alphabetical
    order); that order is preserved within each band.
    """
    fav_order = [c["Name"] for c in channels if c["Name"] in favorite_names]
    other_order = [c["Name"] for c in channels if c["Name"] not in favorite_names]
    assigned = _even_fill(fav_order, *fav_band) + _even_fill(other_order, *other_band)
    return [{"Name": name, "Number": number} for name, number in assigned]


def _first_user_id(emby) -> str:
    """Any user id, used only as the context for fetching editable item DTOs."""
    users = emby.users.list()
    if not users:
        typer.echo("No users found on the server.", err=True)
        raise typer.Exit(1)
    return users[0]["Id"]


def _current_numbers(channels: list[dict]) -> list[dict]:
    """Name-keyed list of channels that currently have a number."""
    return [
        {"Name": c["Name"], "Number": str(c["ChannelNumber"])}
        for c in channels
        if c.get("ChannelNumber")
    ]


def _snapshot_numbers(emby, export_dir: Path, channels: list[dict]) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = export_dir / f"channel-numbers-{ts}.json"
    data = _current_numbers(channels)
    write_export(path, NUMBER_TYPE, emby.base_url, data)
    typer.echo(f"Snapshotted {len(data)} channel number(s) -> {path}")


def _write_numbers(emby, plan: list[tuple[dict, str]]) -> None:
    """Apply (channel, number) pairs, reporting partial progress on failure."""
    user_id = _first_user_id(emby)
    done = 0
    try:
        for channel, number in plan:
            emby.livetv.set_channel_number(user_id, channel["Id"], number)
            done += 1
    except Exception:
        typer.echo(f"Aborted partway: changed {done}/{len(plan)} before the error.", err=True)
        raise
    typer.echo(f"Done. Set numbers on {done} channel(s).")


def _apply_numbers(emby, desired: list[dict], dry_run: bool, yes: bool, snapshot: bool, export_dir: Path) -> None:
    """Set channel numbers from a desired list, matching channels by name."""
    channels, _ = emby.livetv.manage_channels()
    by_name: dict[str, list[dict]] = {}
    for c in channels:
        by_name.setdefault(c["Name"], []).append(c)

    plan: list[tuple[dict, str]] = []
    missing: list[str] = []
    ambiguous: list[str] = []
    for entry in desired:
        name, number = entry["Name"], str(entry["Number"])
        matches = by_name.get(name, [])
        if len(matches) == 1:
            current = str(matches[0].get("ChannelNumber") or "")
            if current != number:
                plan.append((matches[0], number))
        elif not matches:
            missing.append(name)
        else:
            ambiguous.append(name)

    typer.echo(
        f"{len(desired)} entries; {len(plan)} channel(s) to change "
        f"({len(missing)} missing, {len(ambiguous)} ambiguous by name)."
    )
    for channel, number in plan[:50]:
        typer.echo(f"  {channel['Name']}: {channel.get('ChannelNumber') or '—'} -> {number}")
    if len(plan) > 50:
        typer.echo(f"  … and {len(plan) - 50} more")
    for name in missing:
        typer.echo(f"  missing (no channel named this): {name}", err=True)
    for name in ambiguous:
        typer.echo(f"  ambiguous (multiple channels, skipped): {name}", err=True)

    if not plan:
        typer.echo("Already in sync.")
        return
    if dry_run:
        typer.echo("Dry run — no changes made.")
        return
    if snapshot:
        _snapshot_numbers(emby, export_dir, channels)
    if not yes:
        typer.confirm(f"Set numbers on {len(plan)} channel(s)?", abort=True)
    _write_numbers(emby, plan)


@numbers_app.command("generate")
def numbers_generate(
    favorites_user: str = typer.Argument(..., help="User whose favorites get the low band."),
    file: Path = typer.Argument(..., help="Destination JSON file."),
    fav_start: int = typer.Option(1, "--fav-start", help="Favorites band start."),
    fav_end: int = typer.Option(999, "--fav-end", help="Favorites band end."),
    other_start: int = typer.Option(1000, "--other-start", help="Others band start."),
    other_end: int = typer.Option(9999, "--other-end", help="Others band end."),
):
    """Generate a proposed channel numbering (favorites low, others high)."""
    with emby_session() as emby:
        u = _resolve_user(emby, favorites_user)
        fav_names = {c["Name"] for c in emby.livetv.favorite_channels(u["Id"])}
        channels, _ = emby.livetv.manage_channels()
        try:
            data = _assign_numbers(
                channels, fav_names, (fav_start, fav_end), (other_start, other_end)
            )
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1)
        write_export(file, NUMBER_TYPE, emby.base_url, data)
        favs = sum(1 for d in data if d["Name"] in fav_names)
        typer.echo(f"Wrote numbering for {len(data)} channels ({favs} favorites) -> {file}")


@numbers_app.command("export")
def numbers_export(file: Path = typer.Argument(..., help="Destination JSON file.")):
    """Back up current channel numbers (name-keyed) to a file."""
    with emby_session() as emby:
        channels, _ = emby.livetv.manage_channels()
        data = _current_numbers(channels)
        write_export(file, NUMBER_TYPE, emby.base_url, data)
        typer.echo(f"Exported {len(data)} channel number(s) -> {file}")


@numbers_app.command("apply")
def numbers_apply(
    file: Path = typer.Argument(..., help="Numbering JSON file (from generate or export)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    snapshot: bool = typer.Option(
        True, "--snapshot/--no-snapshot", help="Back up current numbers first."
    ),
    export_dir: Path = typer.Option(
        Path("snapshots"), "--export-dir", help="Directory for the pre-apply snapshot."
    ),
):
    """Apply channel numbers from a file, matching channels by name."""
    try:
        desired = read_export(file, NUMBER_TYPE)
    except (ValueError, KeyError, OSError) as e:
        typer.echo(f"Could not read numbering file: {e}", err=True)
        raise typer.Exit(1)
    with emby_session() as emby:
        _apply_numbers(emby, desired, dry_run, yes, snapshot, export_dir)


@numbers_app.command("clear")
def numbers_clear(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    snapshot: bool = typer.Option(
        True, "--snapshot/--no-snapshot", help="Back up current numbers first."
    ),
    export_dir: Path = typer.Option(
        Path("snapshots"), "--export-dir", help="Directory for the pre-clear snapshot."
    ),
):
    """Clear the number on every channel that has one (sets empty string)."""
    with emby_session() as emby:
        channels, _ = emby.livetv.manage_channels()
        numbered = [c for c in channels if c.get("ChannelNumber")]
        typer.echo(f"{len(numbered)} channel(s) have a number to clear.")
        for c in numbered[:50]:
            typer.echo(f"  {c['Name']}: {c['ChannelNumber']} -> (cleared)")
        if not numbered:
            return
        if dry_run:
            typer.echo("Dry run — no changes made.")
            return
        if snapshot:
            _snapshot_numbers(emby, export_dir, channels)
        if not yes:
            typer.confirm(f"Clear numbers on {len(numbered)} channel(s)?", abort=True)
        _write_numbers(emby, [(c, "") for c in numbered])


channels_app.add_typer(numbers_app, name="numbers")
