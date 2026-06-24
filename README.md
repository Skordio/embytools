# embytools

A personal command-line toolkit for managing an [Emby](https://emby.media/)
media server.

embytools is built to grow into a **robust, unified admin tool** for Emby —
the kind of thing you reach for instead of clicking through the dashboard.
Each capability is a focused subcommand under one CLI, sharing a single API
client and a consistent set of conventions (human-readable tables by default,
`--json` for scripting, dry-run previews and confirmation prompts before any
write, and self-describing export/import files).

The first tool copies a user's favorite **Live TV channels** onto another user
and snapshots them to a file; more admin tools (sessions/playback, user
management, library control, server ops) are on the roadmap below.

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) for environment + dependency management
- An Emby server reachable on your network, and an **admin API key**
  (Dashboard → Advanced → API Keys → New API Key)

## Setup

```fish
uv sync
```

That creates the virtual environment, installs the project (editable) and its
dependencies from the committed `uv.lock`, and puts the `embytools` command on
`uv run`. To reproduce the exact environment on another machine, `uv sync` is
the only step.

## Configuration

Copy the template and fill in your server URL and admin key:

```fish
cp config.example.toml config.toml
```

```toml
[server]
# On the Emby host itself: http://localhost:8096
# From another LAN machine:  http://<host-lan-ip>:8096
base_url = "http://192.168.1.214:8096"
api_key  = "your-admin-api-key"
```

`config.toml` holds your admin key and is **gitignored** — never commit it.
Each machine keeps its own. By default the CLI reads `config.toml` from the
current directory; point it elsewhere with the `EMBYTOOLS_CONFIG` environment
variable. Run commands from the repo root so the default config path resolves.

## Usage

Run any command with `uv run`:

```fish
uv run embytools users list
uv run embytools channels list Steve
```

Add `--help` to any command or subcommand to see its options.

### Users

| Command | Description |
| --- | --- |
| `users list` | List all users and their IDs. `--json` for machine-readable output. |

### Live TV channels

| Command | Description |
| --- | --- |
| `channels list <user>` | List a user's favorite Live TV channels. `--json` supported. |
| `channels all` | List every channel with its sort index and channel number. `--json` supported. |
| `channels copy <source> <target>` | Copy the source user's favorite channels onto the target user. |
| `channels export <user> <file>` | Save a user's favorite channels to a JSON file. |
| `channels import <target> <file>` | Apply favorites from an export file to a user. |

Write commands (`copy`, `import`) share safety conventions:

- `--dry-run` previews the exact changes without writing.
- They prompt for confirmation before mutating; pass `--yes`/`-y` to skip the
  prompt (for scripts).
- They're idempotent — channels already favorited are skipped, so re-running is
  safe.

`channels copy` also accepts `--export` to snapshot **both** users' favorites
before copying — the source's, and the target's pre-copy state. Files are
auto-named (`<user>-favorite-channels-<timestamp>.json`) into `snapshots/` by
default, or wherever `--export-dir <dir>` points. The target snapshot is your
safety net: it's an exact record of what the target had before the copy.

Note: `import` is **additive** — it re-adds favorites but never removes any, so
it can restore favorites that were lost, but it can't by itself undo channels a
copy added. (A prune/replace mode is on the roadmap.)

```fish
# Preview copying Grace's favorite channels onto Steve
uv run embytools channels copy Grace Steve --dry-run

# Do it, snapshotting both users' favorites first
uv run embytools channels copy Grace Steve --export
```

### Export files

Exports use a self-describing envelope so files are safe to re-apply later:

```json
{
  "type": "livetv-favorite-channels",
  "version": 1,
  "exported_at": "2026-06-24T...Z",
  "server": "http://192.168.1.214:8096",
  "data": [ { "Id": "...", "Name": "..." } ]
}
```

Imports verify the `type` before applying, so you can't accidentally feed the
wrong kind of file to the wrong command. Snapshotting favorites before a risky
server change (e.g. reconfiguring Live TV) is the recommended safety net.

## Architecture & roadmap

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the project is structured and how
to add a new tool. In short: a thin `cli.py` mounts one Typer sub-app per domain
from `src/embytools/commands/`, and all API access goes through a single
resource-namespaced `EmbyClient` (`emby.users`, `emby.livetv`, `emby.favorites`).

Planned domains, in priority order:

1. **Sessions / playback** — see active streams, message users, stop playback
2. **User management** — create/delete, enable/disable, set-admin, copy policies
3. **Library control** — list libraries, trigger scans/refreshes, stats
4. **Server ops** — server info, scheduled tasks, multi-server profiles
