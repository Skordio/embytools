import typer

from ..output import print_json, print_table
from ..session import emby_session

sessions_app = typer.Typer(help="Active session and playback commands.")


def _is_real_user_session(s: dict) -> bool:
    """A session with a signed-in user (not an anonymous/API connection)."""
    return bool(s.get("UserName"))


def _now_playing(s: dict) -> str:
    item = s.get("NowPlayingItem")
    if not item:
        return "—"
    name = item.get("Name", "?")
    return f"{name} (paused)" if s.get("PlayState", {}).get("IsPaused") else name


def _session_rows(sessions: list[dict]) -> list[dict]:
    return [
        {
            "User": s.get("UserName") or "",
            "Client": s.get("Client") or "",
            "Device": s.get("DeviceName") or "",
            "NowPlaying": _now_playing(s),
            "IP": s.get("RemoteEndPoint") or "",
            "Id": s.get("Id"),
        }
        for s in sessions
    ]


def _resolve_sessions(emby, target: str) -> list[dict]:
    """Find real-user sessions matching target by user name, device, or id prefix."""
    sessions = [s for s in emby.sessions.list() if _is_real_user_session(s)]
    t = target.lower()
    matches = [
        s
        for s in sessions
        if (s.get("UserName") or "").lower() == t
        or (s.get("DeviceName") or "").lower() == t
        or (s.get("Id") or "").lower().startswith(t)
    ]
    if not matches:
        typer.echo(f"No active session matching {target!r}.", err=True)
        if sessions:
            typer.echo("Active sessions:", err=True)
            for s in sessions:
                typer.echo(f"  {s.get('UserName')} / {s.get('DeviceName')}", err=True)
        raise typer.Exit(1)
    return matches


def _select_targets(emby, target: str, all_matches: bool) -> list[dict]:
    """Resolve target to controllable sessions, enforcing disambiguation."""
    sessions = _resolve_sessions(emby, target)
    controllable = [s for s in sessions if s.get("SupportsRemoteControl")]
    for s in sessions:
        if not s.get("SupportsRemoteControl"):
            typer.echo(
                f"Skipping {s.get('UserName')} on {s.get('DeviceName')}: "
                "session does not allow remote control.",
                err=True,
            )
    if not controllable:
        typer.echo("No controllable sessions matched.", err=True)
        raise typer.Exit(1)
    if len(controllable) > 1 and not all_matches:
        typer.echo("Multiple sessions match — narrow the target or pass --all:", err=True)
        for s in controllable:
            typer.echo(f"  {s.get('UserName')} / {s.get('DeviceName')} / {s['Id']}", err=True)
        raise typer.Exit(1)
    return controllable


def _run_on_sessions(sessions, label: str, action, dry_run: bool, yes: bool) -> None:
    """Preview the action per session, confirm, then apply (shared write flow)."""
    for s in sessions:
        typer.echo(f"{label} -> {s.get('UserName')} on {s.get('DeviceName')} ({_now_playing(s)})")
    if dry_run:
        typer.echo("Dry run — nothing sent.")
        return
    if not yes:
        typer.confirm(f"{label} for {len(sessions)} session(s)?", abort=True)
    sent = 0
    try:
        for s in sessions:
            action(s)
            sent += 1
    except Exception:
        typer.echo(f"Aborted partway: sent to {sent}/{len(sessions)} before the error.", err=True)
        raise
    typer.echo(f"Done. {label} sent to {sent} session(s).")


def _playstate(target: str, command: str, all_matches: bool, dry_run: bool, yes: bool) -> None:
    with emby_session() as emby:
        sessions = _select_targets(emby, target, all_matches)
        _run_on_sessions(
            sessions, command, lambda s: emby.sessions.playstate(s["Id"], command), dry_run, yes
        )


@sessions_app.command("list")
def sessions_list(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON."),
    playing: bool = typer.Option(False, "--playing", help="Only sessions currently playing."),
    all_sessions: bool = typer.Option(
        False, "--all", help="Include sessions with no signed-in user."
    ),
):
    """List active sessions (signed-in user clients by default)."""
    with emby_session() as emby:
        sessions = emby.sessions.list()
        if not all_sessions:
            sessions = [s for s in sessions if _is_real_user_session(s)]
        if playing:
            sessions = [s for s in sessions if s.get("NowPlayingItem")]
        if not sessions:
            typer.echo("No active sessions." if not as_json else "[]")
            return
        rows = _session_rows(sessions)
        if as_json:
            print_json(rows)
        else:
            print_table(
                rows,
                [("User", 16), ("Client", 14), ("Device", 18), ("NowPlaying", 30), ("IP", 15), ("Id", 0)],
            )


@sessions_app.command("message")
def sessions_message(
    target: str = typer.Argument(..., help="User name, device name, or session id prefix."),
    text: str = typer.Argument(..., help="Message text to display."),
    header: str = typer.Option(None, "--header", help="Message header/title."),
    timeout: int = typer.Option(None, "--timeout", help="Display timeout in milliseconds."),
    all_matches: bool = typer.Option(False, "--all", help="Act on all matching sessions."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without sending."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Display a popup message on a user's session."""
    with emby_session() as emby:
        sessions = _select_targets(emby, target, all_matches)
        _run_on_sessions(
            sessions,
            f"message {text!r}",
            lambda s: emby.sessions.send_message(s["Id"], text, header, timeout),
            dry_run,
            yes,
        )


@sessions_app.command("stop")
def sessions_stop(
    target: str = typer.Argument(..., help="User name, device name, or session id prefix."),
    all_matches: bool = typer.Option(False, "--all", help="Act on all matching sessions."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without sending."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Stop playback on a user's session."""
    _playstate(target, "Stop", all_matches, dry_run, yes)


@sessions_app.command("pause")
def sessions_pause(
    target: str = typer.Argument(..., help="User name, device name, or session id prefix."),
    all_matches: bool = typer.Option(False, "--all", help="Act on all matching sessions."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without sending."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Pause playback on a user's session."""
    _playstate(target, "Pause", all_matches, dry_run, yes)


@sessions_app.command("unpause")
def sessions_unpause(
    target: str = typer.Argument(..., help="User name, device name, or session id prefix."),
    all_matches: bool = typer.Option(False, "--all", help="Act on all matching sessions."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without sending."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Resume playback on a user's session."""
    _playstate(target, "Unpause", all_matches, dry_run, yes)
