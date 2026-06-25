# embytools — Architecture & Growth Plan

How this CLI is structured and how it grows into a versatile Emby admin tool.

## Layout

```
src/embytools/
├── cli.py                # thin root app — mounts each command sub-app
├── config.py             # loads config.toml (or $EMBYTOOLS_CONFIG)
├── session.py            # emby_session() — configured client + friendly errors
├── output.py             # print_json / print_table (human table vs --json)
├── errors.py             # friendly_errors — HTTP/connection failures → clean messages
├── envelope.py           # self-describing JSON export/import wrapper
├── numbering.py          # pluggable channel-numbering schemes (registry + helpers)
├── client/               # the Emby API, split into resource namespaces
│   ├── core.py           #   EmbyClient — holds one httpx client + namespaces
│   ├── _resource.py      #   Resource base
│   ├── users.py          #   emby.users
│   ├── livetv.py         #   emby.livetv
│   ├── favorites.py      #   emby.favorites
│   └── sessions.py       #   emby.sessions
└── commands/             # one module per domain, each a typer sub-app
    ├── users.py          #   users_app
    ├── channels.py       #   channels_app
    └── sessions.py       #   sessions_app
```

## How to add a tool

1. Add API calls to the relevant `client/<resource>.py` (or a new resource
   class wired into `client/core.py`).
2. Add commands in `commands/<domain>.py` as a `typer.Typer()` sub-app.
3. Mount it in `cli.py` with `app.add_typer(...)`.

A new tool never grows an existing file unboundedly and never duplicates API
logic.

## Conventions

- **Reads** print a human table by default, JSON with `--json` (pipeable).
- **Writes** support `--dry-run` (preview only) and prompt for confirmation
  before mutating, unless `--yes`/`-y` is passed. Operations are idempotent
  where possible (skip work already done so previews are accurate).
- **Errors** go through `friendly_errors`: 401 → check API key, connection
  refused → is the server reachable, etc. No raw tracebacks for expected
  failures.
- **Export/import** uses one envelope (`envelope.py`): `{type, version,
  exported_at, server, data}`. Files are self-describing; imports verify the
  `type` before applying. Reuse this for every "snapshot → file → apply"
  feature.

## Roadmap

Validated and built:

- `users list`
- `channels list / all / copy / export / import` and `channels numbers
  schemes / generate / apply / export / clear` (name-keyed channel numbering,
  with pluggable `generate` schemes via `numbering.py` + `--plugin`). The first
  real tool. Copy
  proven valid: channel favorites are per-user user-data on a server-global
  item, so the same `ItemId` works for every user.
- `sessions list / message / stop / pause / unpause` — active sessions and
  playback control. Lists signed-in user clients by default; write commands
  target a session by user name, device name, or id prefix, skip sessions that
  don't allow remote control, and follow the dry-run/confirm convention.

Next domains, in priority order:

1. **User management** — create/delete, enable/disable, set-admin,
   reset-password, and `users copy-policy` (reuses the export envelope).
2. **Library control** — list libraries, trigger scan/refresh, stats.
   (`GET /Library/VirtualFolders`, `POST /Library/Refresh`.)
3. **Server ops** — server info, scheduled tasks, restart/shutdown; later,
   multiple-server connection profiles.
