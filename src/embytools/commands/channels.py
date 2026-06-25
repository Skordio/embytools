from datetime import datetime
from pathlib import Path

import typer

from ..envelope import read_export, write_export
from ..numbering import SCHEMES, SchemeContext, get_scheme, load_plugin
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
    name_to_id: dict[str, str] | None = None,
    snapshot_cb=None,
) -> None:
    """Bring the target user's favorite channels in line with ``items``.

    Channels are matched by **name**, not id. ``items`` may come from an export
    file whose ids are stale (Emby regenerates channel ids when the upstream M3U
    source changes domain), so each desired channel is resolved to the target's
    *current* id via ``name_to_id``. When ``name_to_id`` is omitted the ids
    carried by ``items`` are used — correct for live ``copy``, where source and
    target share one server snapshot.

    Shared by ``copy`` and ``import``: previews the plan, runs ``snapshot_cb``
    (if given) and confirms before writing. Always adds items not yet favorited
    (by name). When ``replace`` is set, also removes the target's existing
    favorites whose names aren't in ``items`` (exact sync); otherwise removals
    are left alone (additive). Idempotent and accurate — favorites already
    present by name are skipped so the preview matches reality.

    Pass ``existing_channels`` to reuse an already-fetched favorites list and
    avoid a redundant request.
    """
    if existing_channels is None:
        existing_channels = emby.livetv.favorite_channels(target["Id"])
    if name_to_id is None:
        name_to_id = {i["Name"]: i["Id"] for i in items}

    existing_names = {c["Name"] for c in existing_channels}
    desired_names = {i["Name"] for i in items}

    to_add: list[tuple[str, str]] = []  # (name, current id)
    unresolved: list[str] = []  # desired names with no channel on the server
    seen: set[str] = set()
    for i in items:
        name = i["Name"]
        if name in existing_names or name in seen:
            continue
        seen.add(name)
        cid = name_to_id.get(name)
        if cid is None:
            unresolved.append(name)
        else:
            to_add.append((name, cid))
    to_remove = (
        [(c["Name"], c["Id"]) for c in existing_channels if c["Name"] not in desired_names]
        if replace
        else []
    )

    typer.echo(
        f"{target['Name']}: {len(to_add)} to add, {len(to_remove)} to remove "
        f"({len(desired_names & existing_names)} already favorited)."
    )
    for name, cid in to_add:
        typer.echo(f"  + {name} ({cid})")
    for name, cid in to_remove:
        typer.echo(f"  - {name} ({cid})")
    for name in unresolved:
        typer.echo(f"  ! no channel named {name!r} on the server, skipped.", err=True)

    if not to_add and not to_remove:
        typer.echo("Already in sync." if replace else "Nothing to copy.")
        return
    if dry_run:
        typer.echo("Dry run — no changes made.")
        return
    if snapshot_cb:
        snapshot_cb()
    if not yes:
        plan = f"Add {len(to_add)}"
        if to_remove:
            plan += f" and remove {len(to_remove)}"
        typer.confirm(f"{plan} favorite channel(s) for {target['Name']}?", abort=True)

    added = removed = 0
    try:
        for name, cid in to_add:
            emby.favorites.add(target["Id"], cid)
            added += 1
        for name, cid in to_remove:
            emby.favorites.remove(target["Id"], cid)
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

        # --export snapshots both users up front. Otherwise, a --replace copy
        # is a destructive write, so snapshot the target as a safety net (fired
        # by _apply_favorites only when there's actually something to change).
        cb = None
        if export:
            if dry_run:
                typer.echo("Dry run — skipping snapshots.")
            else:
                _snapshot_favorites(
                    emby,
                    export_dir,
                    [(src, channels), (tgt, _slim(target_existing))],
                )
        elif replace:
            cb = lambda: _snapshot_favorites(emby, export_dir, [(tgt, _slim(target_existing))])

        _apply_favorites(
            emby,
            tgt,
            channels,
            dry_run,
            yes,
            replace=replace,
            existing_channels=target_existing,
            snapshot_cb=cb,
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
    snapshot: bool = typer.Option(
        True, "--snapshot/--no-snapshot", help="Back up the target's current favorites first."
    ),
    export_dir: Path = typer.Option(
        Path("snapshots"), "--export-dir", help="Directory for the pre-import snapshot."
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
        existing = emby.livetv.favorite_channels(tgt["Id"])
        # Resolve the file's channel names to the target's current channel ids,
        # so favorites survive an upstream id regeneration (match by name).
        name_to_id = {c["Name"]: c["Id"] for c in emby.livetv.all_channels(tgt["Id"])}
        cb = (
            (lambda: _snapshot_favorites(emby, export_dir, [(tgt, _slim(existing))]))
            if snapshot
            else None
        )
        _apply_favorites(
            emby,
            tgt,
            items,
            dry_run,
            yes,
            replace=replace,
            existing_channels=existing,
            name_to_id=name_to_id,
            snapshot_cb=cb,
        )


# --- Channel numbering -------------------------------------------------------

numbers_app = typer.Typer(help="Assign and back up Live TV channel numbers.")


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


def _parse_opts(opts: list[str]) -> dict[str, str]:
    parsed = {}
    for item in opts or []:
        if "=" not in item:
            typer.echo(f"--opt must be key=value, got {item!r}.", err=True)
            raise typer.Exit(1)
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


def _load_plugins(plugins: list[Path]) -> None:
    for path in plugins or []:
        try:
            load_plugin(path)
        except Exception as e:  # surface any plugin error as a friendly message
            typer.echo(f"Could not load plugin {path}: {e}", err=True)
            raise typer.Exit(1)


@numbers_app.command("generate")
def numbers_generate(
    scheme_name: str = typer.Argument(..., help="Scheme name (see `channels numbers schemes`)."),
    file: Path = typer.Argument(..., help="Destination JSON file."),
    opt: list[str] = typer.Option(
        None, "--opt", help="Scheme option as key=value (repeatable), e.g. --opt user=Steve."
    ),
    plugin: list[Path] = typer.Option(
        None, "--plugin", help="Load scheme(s) from a .py file (repeatable)."
    ),
):
    """Generate a channel numbering using a scheme from a --plugin file."""
    if not plugin:
        typer.echo(
            "generate requires at least one --plugin <file.py> providing the scheme "
            "(e.g. schemes/favorites_bands.py). See `channels numbers schemes --plugin ...`.",
            err=True,
        )
        raise typer.Exit(1)
    _load_plugins(plugin)
    try:
        fn = get_scheme(scheme_name)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    options = _parse_opts(opt)
    with emby_session() as emby:
        channels, _ = emby.livetv.manage_channels()
        ctx = SchemeContext(emby=emby, channels=channels, options=options)
        try:
            data = fn(ctx)
        except (ValueError, KeyError) as e:
            typer.echo(f"Scheme {scheme_name!r} failed: {e}", err=True)
            raise typer.Exit(1)
        if not isinstance(data, list) or not all(
            isinstance(d, dict) and "Name" in d and "Number" in d for d in data
        ):
            typer.echo(
                f"Scheme {scheme_name!r} must return a list of {{'Name','Number'}} dicts.",
                err=True,
            )
            raise typer.Exit(1)
        data = [{"Name": d["Name"], "Number": str(d["Number"])} for d in data]
        write_export(file, NUMBER_TYPE, emby.base_url, data)
        typer.echo(f"Wrote numbering for {len(data)} channels -> {file}")


@numbers_app.command("schemes")
def numbers_schemes(
    plugin: list[Path] = typer.Option(
        None, "--plugin", help="Also load scheme(s) from a .py file (repeatable)."
    ),
):
    """List available numbering schemes."""
    _load_plugins(plugin)
    if not SCHEMES:
        typer.echo("No schemes registered.")
        return
    for name in sorted(SCHEMES):
        doc = (SCHEMES[name].__doc__ or "").strip().splitlines()
        summary = doc[0] if doc else ""
        typer.echo(f"{name:<18} {summary}")


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


# --- Channel tags -----------------------------------------------------------

tags_app = typer.Typer(help="Manage Live TV channel tags.")

TAGS_TYPE = "livetv-channel-tags"


def _tag_names(channel: dict) -> list[str]:
    """A channel's tag names, read from its TagItems."""
    return [t["Name"] for t in (channel.get("TagItems") or [])]


def _channels_by_name(channels: list[dict]) -> dict[str, list[dict]]:
    by_name: dict[str, list[dict]] = {}
    for c in channels:
        by_name.setdefault(c["Name"], []).append(c)
    return by_name


def _resolve_channels(by_name: dict, names: list[str]) -> list[dict]:
    """Resolve channel names to single channels, reporting missing/ambiguous."""
    resolved = []
    for name in names:
        matches = by_name.get(name, [])
        if len(matches) == 1:
            resolved.append(matches[0])
        elif not matches:
            typer.echo(f"  missing (no channel named this): {name}", err=True)
        else:
            typer.echo(f"  ambiguous (multiple channels, skipped): {name}", err=True)
    return resolved


def _snapshot_tags(emby, export_dir: Path, channels: list[dict]) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = export_dir / f"channel-tags-{ts}.json"
    data = [{"Name": c["Name"], "Tags": _tag_names(c)} for c in channels if _tag_names(c)]
    write_export(path, TAGS_TYPE, emby.base_url, data)
    typer.echo(f"Snapshotted tags for {len(data)} channel(s) -> {path}")


def _apply_tag_changes(emby, plan, dry_run: bool, yes: bool, snapshot_cb=None) -> None:
    """plan: list of (channel, to_add:set, to_remove:set). Preview, confirm, apply."""
    plan = [(c, add, rem) for (c, add, rem) in plan if add or rem]
    total_add = sum(len(a) for _, a, _ in plan)
    total_rem = sum(len(r) for _, _, r in plan)
    typer.echo(f"{len(plan)} channel(s) to change: +{total_add} tag(s), -{total_rem} tag(s).")
    for c, add, rem in plan[:50]:
        bits = [f"+{t}" for t in sorted(add)] + [f"-{t}" for t in sorted(rem)]
        typer.echo(f"  {c['Name']}: {' '.join(bits)}")
    if len(plan) > 50:
        typer.echo(f"  … and {len(plan) - 50} more")

    if not plan:
        typer.echo("Nothing to change.")
        return
    if dry_run:
        typer.echo("Dry run — no changes made.")
        return
    if snapshot_cb:
        snapshot_cb()
    if not yes:
        typer.confirm(f"Apply tag changes to {len(plan)} channel(s)?", abort=True)

    done = 0
    try:
        for c, add, rem in plan:
            if add:
                emby.livetv.add_tags(c["Id"], sorted(add))
            if rem:
                emby.livetv.remove_tags(c["Id"], sorted(rem))
            done += 1
    except Exception:
        typer.echo(f"Aborted partway: changed {done}/{len(plan)} before the error.", err=True)
        raise
    typer.echo(f"Done. Updated tags on {done} channel(s).")


@tags_app.command("list")
def tags_list(as_json: bool = typer.Option(False, "--json", help="Emit JSON.")):
    """List all channel tags and how many channels carry each."""
    with emby_session() as emby:
        channels = emby.livetv.channels_with_tags(_first_user_id(emby))
        counts: dict[str, int] = {}
        for c in channels:
            for t in _tag_names(c):
                counts[t] = counts.get(t, 0) + 1
        rows = [{"Tag": t, "Channels": n} for t, n in sorted(counts.items())]
        if not rows:
            typer.echo("No tags." if not as_json else "[]")
            return
        if as_json:
            print_json(rows)
        else:
            print_table(rows, [("Tag", 32), ("Channels", 0)])


@tags_app.command("channels")
def tags_channels(
    tag: str = typer.Argument(..., help="Tag name."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
):
    """List channels that have a given tag."""
    with emby_session() as emby:
        channels = emby.livetv.channels_by_tag(_first_user_id(emby), tag)
        rows = [{"Name": c["Name"], "Id": c["Id"]} for c in channels]
        if not rows:
            typer.echo(f"No channels with tag {tag!r}." if not as_json else "[]")
            return
        if as_json:
            print_json(rows)
        else:
            print_table(rows, [("Name", 34), ("Id", 0)])


@tags_app.command("show")
def tags_show(
    channel: str = typer.Argument(..., help="Channel name."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
):
    """Show a channel's tags."""
    with emby_session() as emby:
        by_name = _channels_by_name(emby.livetv.channels_with_tags(_first_user_id(emby)))
        resolved = _resolve_channels(by_name, [channel])
        if not resolved:
            raise typer.Exit(1)
        tags = sorted(_tag_names(resolved[0]))
        if as_json:
            print_json(tags)
        else:
            typer.echo(", ".join(tags) if tags else "(no tags)")


@tags_app.command("add")
def tags_add(
    tag: str = typer.Argument(..., help="Tag to add."),
    channels: list[str] = typer.Argument(..., help="Channel name(s)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Add a tag to one or more channels."""
    with emby_session() as emby:
        by_name = _channels_by_name(emby.livetv.channels_with_tags(_first_user_id(emby)))
        resolved = _resolve_channels(by_name, channels)
        plan = [(c, {tag} - set(_tag_names(c)), set()) for c in resolved]
        _apply_tag_changes(emby, plan, dry_run, yes)


@tags_app.command("remove")
def tags_remove(
    tag: str = typer.Argument(..., help="Tag to remove."),
    channels: list[str] = typer.Argument(..., help="Channel name(s)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Remove a tag from one or more channels."""
    with emby_session() as emby:
        by_name = _channels_by_name(emby.livetv.channels_with_tags(_first_user_id(emby)))
        resolved = _resolve_channels(by_name, channels)
        plan = [(c, set(), {tag} & set(_tag_names(c))) for c in resolved]
        _apply_tag_changes(emby, plan, dry_run, yes)


@tags_app.command("set")
def tags_set(
    channel: str = typer.Argument(..., help="Channel name."),
    tags: list[str] = typer.Argument(..., help="The exact tag set for the channel."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Set a channel's tags exactly — adds missing and removes the rest."""
    with emby_session() as emby:
        by_name = _channels_by_name(emby.livetv.channels_with_tags(_first_user_id(emby)))
        resolved = _resolve_channels(by_name, [channel])
        if not resolved:
            raise typer.Exit(1)
        c = resolved[0]
        desired, current = set(tags), set(_tag_names(c))
        plan = [(c, desired - current, current - desired)]
        _apply_tag_changes(emby, plan, dry_run, yes)


@tags_app.command("export")
def tags_export(
    file: Path = typer.Argument(..., help="Destination JSON file."),
    tag: str = typer.Option(None, "--tag", help="Only export channels having this tag."),
):
    """Export channel tags (name-keyed) to a file."""
    with emby_session() as emby:
        channels = emby.livetv.channels_with_tags(_first_user_id(emby))
        if tag:
            data = [{"Name": c["Name"], "Tags": [tag]} for c in channels if tag in _tag_names(c)]
        else:
            data = [{"Name": c["Name"], "Tags": _tag_names(c)} for c in channels if _tag_names(c)]
        write_export(file, TAGS_TYPE, emby.base_url, data)
        typer.echo(f"Exported tags for {len(data)} channel(s) -> {file}")


@tags_app.command("import")
def tags_import(
    file: Path = typer.Argument(..., help="Tag export file."),
    replace: bool = typer.Option(
        False, "--replace", help="Make each channel's tags exactly match the file."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    snapshot: bool = typer.Option(
        True, "--snapshot/--no-snapshot", help="Back up current tags first."
    ),
    export_dir: Path = typer.Option(
        Path("snapshots"), "--export-dir", help="Directory for the pre-import snapshot."
    ),
):
    """Apply channel tags from a file, matching channels by name."""
    try:
        desired = read_export(file, TAGS_TYPE)
    except (ValueError, KeyError, OSError) as e:
        typer.echo(f"Could not read tag file: {e}", err=True)
        raise typer.Exit(1)
    with emby_session() as emby:
        channels = emby.livetv.channels_with_tags(_first_user_id(emby))
        by_name = _channels_by_name(channels)
        desired_by_name = {d["Name"]: set(d.get("Tags") or []) for d in desired}
        resolved = _resolve_channels(by_name, [d["Name"] for d in desired])
        plan = []
        for c in resolved:
            want = desired_by_name.get(c["Name"], set())
            current = set(_tag_names(c))
            to_remove = (current - want) if replace else set()
            plan.append((c, want - current, to_remove))
        cb = (lambda: _snapshot_tags(emby, export_dir, channels)) if snapshot else None
        _apply_tag_changes(emby, plan, dry_run, yes, snapshot_cb=cb)


channels_app.add_typer(tags_app, name="tags")
