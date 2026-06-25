# channels tags

Manage Live TV channel **tags**. Channels typically arrive already tagged from
the M3U source (group-titles like "National News", "Business News"); these
commands let you read those tags, add your own, and back them up.

See the [shared conventions](README.md#shared-conventions) for `--json` output,
write safety, name-keyed matching, and snapshots.

> Tags come from the source, so an M3U refresh can reset channel tags (the same
> wipe risk as channel numbers). `export` your tags so `import` can restore them.

Reads use one request (`GET /LiveTv/Channels?Fields=Tags`); the write commands
(`add`, `remove`, `set`, `import`) follow the house convention — `--dry-run`,
confirm unless `--yes`/`-y`, idempotent, and partial-progress on failure.

---

### channels tags list

List every channel tag and how many channels carry it.

**Synopsis**

```
embytools channels tags list [--json]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--json` | off | Emit JSON instead of a table. |

---

### channels tags channels

List the channels that have a given tag.

**Synopsis**

```
embytools channels tags channels <tag> [--json]
```

**Arguments**

- `tag` (required) — the tag to filter by.

**Examples**

```fish
uv run embytools channels tags channels "National News"
```

---

### channels tags show

Show one channel's tags.

**Synopsis**

```
embytools channels tags show <channel> [--json]
```

**Arguments**

- `channel` (required) — channel name.

---

### channels tags add

Add a tag to one or more channels. Creates the tag if it doesn't exist yet.

**Synopsis**

```
embytools channels tags add <tag> <channel>... [--dry-run] [--yes]
```

**Arguments**

- `tag` (required) — the tag to add.
- `channel...` (one or more) — channel name(s) to add it to.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
uv run embytools channels tags add Favorites "CNN USA" "Fox News" --dry-run
uv run embytools channels tags add Favorites "CNN USA"
```

**Notes**

- Idempotent: channels that already have the tag are skipped.
- Channel names that match no channel, or match more than one, are reported and
  skipped.

---

### channels tags remove

Remove a tag from one or more channels.

**Synopsis**

```
embytools channels tags remove <tag> <channel>... [--dry-run] [--yes]
```

**Arguments**

- `tag` (required) — the tag to remove.
- `channel...` (one or more) — channel name(s) to remove it from.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

---

### channels tags set

Set a channel's tags to **exactly** the given set — adds the ones missing and
removes any not listed.

**Synopsis**

```
embytools channels tags set <channel> <tag>... [--dry-run] [--yes]
```

**Arguments**

- `channel` (required) — channel name.
- `tag...` (one or more) — the exact tag set the channel should have.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Notes**

- Destructive: any existing tag on the channel that you don't list is **removed**
  (including source group tags). Use `--dry-run` to confirm the plan.

---

### channels tags export

Export channel tags (name-keyed) to a file. Without `--tag`, every channel that
has at least one tag is written with its full tag set. With `--tag X`, only the
channels carrying `X` are written and the file is marked as a single-tag
(membership) export — handy for backing up just one tag's membership. `import`
reads that marker and syncs only that tag, so re-importing it never disturbs a
channel's other tags (see `import` below).

**Synopsis**

```
embytools channels tags export <file> [--tag <tag>]
```

**Arguments**

- `file` (required) — destination JSON path (parent dirs are created).

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--tag <tag>` | none | Only export channels having this tag. |

**Examples**

```fish
# Back up all channel tags
uv run embytools channels tags export snapshots/channel-tags.json

# Back up just the "Favorites" tag's membership
uv run embytools channels tags export snapshots/favorites-tag.json --tag Favorites
```

---

### channels tags import

Apply channel tags from a file, matching channels by **name**. Snapshots current
tags first. The behavior depends on the file's scope:

- A **full** export (no `--tag`): additive by default (adds the file's tags,
  leaves others); `--replace` makes each channel's tags exactly match the file
  (removing tags the file doesn't list).
- A **single-tag** export (`--tag X`): adds `X` to the listed channels;
  `--replace` additionally removes `X` from channels *not* listed (a membership
  sync). Either way it only ever touches `X` — a channel's other tags are safe.

**Synopsis**

```
embytools channels tags import <file> [--replace] [--no-snapshot] [--export-dir <dir>] [--dry-run] [--yes]
```

**Arguments**

- `file` (required) — a tag export file.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--replace` | off | Exact sync. For a full export, makes each channel's tags exactly match the file. For a single-tag export, also removes that tag from channels not listed. |
| `--snapshot` / `--no-snapshot` | `--snapshot` | Back up current tags before applying. |
| `--export-dir <dir>` | `snapshots` | Directory for the pre-import snapshot. |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
# Restore tags after a source refresh wiped them
uv run embytools channels tags import snapshots/channel-tags.json --dry-run
uv run embytools channels tags import snapshots/channel-tags.json
```

**Notes**

- Because matching is by name, a backup keeps working even after the upstream
  source regenerates channel ids.
