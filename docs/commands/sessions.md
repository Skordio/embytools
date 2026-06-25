# sessions

See who's connected to the server and control playback on their sessions. See
the [shared conventions](README.md#shared-conventions) for `--json` output and
write safety.

## Targeting a session

The write commands (`message`, `stop`, `pause`, `unpause`) take a `target` that
matches a session by **user name**, **device name**, or **session id prefix**
(case-insensitive). Targeting behavior:

- Only sessions with a signed-in user are considered.
- Sessions that don't allow remote control are skipped with a notice.
- If the target matches more than one controllable session, the command lists
  them and asks you to narrow it or pass `--all` to act on all matches.

---

### sessions list

List active sessions. By default shows only signed-in user clients (the noise of
anonymous/service connections is hidden).

**Synopsis**

```
embytools sessions list [--playing] [--all] [--json]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--playing` | off | Only sessions currently playing something. |
| `--all` | off | Include sessions with no signed-in user (service/anonymous). |
| `--json` | off | Emit JSON instead of a table. |

**Examples**

```fish
uv run embytools sessions list
uv run embytools sessions list --playing
uv run embytools sessions list --all --json
```

The table shows user, client, device, now-playing (with a paused marker), IP,
and the session id.

---

### sessions message

Display a popup message on a user's session.

**Synopsis**

```
embytools sessions message <target> <text> [--header <text>] [--timeout <ms>] [--all] [--dry-run] [--yes]
```

**Arguments**

- `target` (required) — user name, device name, or session id prefix.
- `text` (required) — the message body to display.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--header <text>` | none | Message header/title. |
| `--timeout <ms>` | none | Display timeout in milliseconds. |
| `--all` | off | Act on all matching sessions instead of requiring a single match. |
| `--dry-run` | off | Preview without sending. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
uv run embytools sessions message Steve "Server maintenance in 10 minutes" --header "Heads up"
uv run embytools sessions message "Living Room Onn" "Dinner's ready" --dry-run
```

---

### sessions stop / pause / unpause

Control playback on a user's session: `stop` ends playback, `pause` pauses it,
and `unpause` resumes it. All three share the same arguments and options.

**Synopsis**

```
embytools sessions stop    <target> [--all] [--dry-run] [--yes]
embytools sessions pause   <target> [--all] [--dry-run] [--yes]
embytools sessions unpause <target> [--all] [--dry-run] [--yes]
```

**Arguments**

- `target` (required) — user name, device name, or session id prefix.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--all` | off | Act on all matching sessions instead of requiring a single match. |
| `--dry-run` | off | Preview without sending. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
# Preview pausing a specific device
uv run embytools sessions pause "Living Room Onn" --dry-run

# Stop playback on Steve's only controllable session
uv run embytools sessions stop Steve

# Resume it
uv run embytools sessions unpause Steve
```
