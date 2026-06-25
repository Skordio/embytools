# channels

Manage Live TV channel **favorites** — list them, copy them between users, and
export/import them to files. Channel **numbering** lives in a separate page:
[channels numbers](channels-numbers.md).

See the [shared conventions](README.md#shared-conventions) for configuration,
`--json` output, write safety, name-keyed matching, and snapshots.

---

### channels list

List one user's favorite Live TV channels (name + id).

**Synopsis**

```
embytools channels list <user> [--json]
```

**Arguments**

- `user` (required) — the user whose favorites to list.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--json` | off | Emit JSON instead of a table. |

**Examples**

```fish
uv run embytools channels list Steve
uv run embytools channels list Steve --json
```

---

### channels all

List **every** Live TV channel on the server with its sort index and channel
number (blank if unnumbered), sorted by sort index. Useful for seeing the full
lineup and which channels carry numbers.

**Synopsis**

```
embytools channels all [--json]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--json` | off | Emit JSON instead of a table. |

**Notes**

- Reads from the management endpoint, the only one that exposes both the sort
  index and the channel number. If the server has more channels than the
  internal page limit, a warning notes the result was truncated.

---

### channels copy

Copy a source user's favorite Live TV channels onto a target user.

**Synopsis**

```
embytools channels copy <source> <target> [--replace] [--export] [--export-dir <dir>] [--dry-run] [--yes]
```

**Arguments**

- `source` (required) — user to copy favorites from.
- `target` (required) — user to copy favorites onto.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--replace` | off | Make the target's favorites **exactly match** the source — adds missing and removes extras. Without it, the copy is additive (adds only, never removes). |
| `--export` | off | Snapshot **both** users' favorites (source, and the target's pre-copy state) before copying. |
| `--export-dir <dir>` | `snapshots` | Directory for `--export` snapshots. |
| `--dry-run` | off | Preview the plan without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
# Preview an additive copy
uv run embytools channels copy Grace Steve --dry-run

# Copy, snapshotting both users first
uv run embytools channels copy Grace Steve --export

# Make Steve's favorites exactly match Grace's (adds + removes)
uv run embytools channels copy Grace Steve --replace
```

**Notes**

- Idempotent: channels already favorited on the target are skipped.
- With `--dry-run`, `--export` snapshots are **not** written (dry-run writes
  nothing).

---

### channels export

Save a user's favorite Live TV channels to a JSON file (a self-describing export
keyed by channel name and id).

**Synopsis**

```
embytools channels export <user> <file>
```

**Arguments**

- `user` (required) — user whose favorites to export.
- `file` (required) — destination JSON path (parent directories are created).

**Examples**

```fish
uv run embytools channels export Steve snapshots/steve-favorites.json
```

---

### channels import

Apply favorite Live TV channels from an export file to a user, matching channels
by **name**.

**Synopsis**

```
embytools channels import <target> <file> [--replace] [--dry-run] [--yes]
```

**Arguments**

- `target` (required) — user to apply favorites to.
- `file` (required) — an export file produced by `channels export` (or `copy
  --export`).

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--replace` | off | Make the target's favorites **exactly match** the file — adds missing and removes extras. Without it, the import is additive. |
| `--dry-run` | off | Preview the plan without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
# Restore Steve's favorites from a backup (additive)
uv run embytools channels import Steve snapshots/steve-favorites.json

# Make them exactly match the file
uv run embytools channels import Steve snapshots/steve-favorites.json --replace
```

**Notes**

- Because matching is by name, a backup keeps working even after the upstream
  source regenerates channel ids. `--replace` makes a snapshot a true restore
  point (it removes favorites not in the file); plain import only adds.
- Reading a file that isn't a valid favorites export fails with a clear message.
