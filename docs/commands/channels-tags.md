# channels tags

Manage Live TV channel **tags**. Channels typically arrive already tagged from
the M3U source (group-titles like "National News", "Business News"); these
commands let you read those tags, add your own, and back them up.

See the [shared conventions](README.md#shared-conventions) for `--json` output,
write safety, name-keyed matching, and snapshots.

> Tags come from the source, so an M3U refresh can reset channel tags (the same
> wipe risk as channel numbers). `export` your tags so `import` can restore them.

Reads use one request (`GET /LiveTv/Channels?Fields=Tags`), scoped to an
administrator so every channel is visible; the write commands (`add`, `remove`,
`set`, `import`) follow the house convention — `--dry-run`, confirm unless
`--yes`/`-y`, idempotent, and partial-progress on failure.

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
  skipped. If **none** of the given names resolve, the command exits non-zero
  (so a typo doesn't look like success in a script).

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
embytools channels tags export <file> [--tag <tag>] [--allow-empty]
```

**Arguments**

- `file` (required) — destination JSON path (parent dirs are created).

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--tag <tag>` | none | Only export channels having this tag (writes a single-tag membership file). |
| `--allow-empty` | off | Allow overwriting an existing file with an empty export (refused by default so a transient empty read can't clobber a good backup). |

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

---

### channels tags schemes

List the **tag schemes** a plugin provides. A tag scheme is the tag-side analog
of a numbering scheme: a function that maps the current channel list to a desired
tag set. Schemes only come from `--plugin` files — there are no built-ins.

**Synopsis**

```
embytools channels tags schemes [--plugin <file.py>]...
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--plugin <file.py>` | none | Load tag scheme(s) from a `.py` file (repeatable). |

---

### channels tags generate

Run a tag scheme from a `--plugin` file and write its result to a **full**
`livetv-channel-tags` file (no server changes). Apply it with
`channels tags import --replace`, which makes each channel's tags exactly match
the file — so a scheme can both add tags and strip unwanted ones (e.g. the
source's `A`–`Z` letter-index tags) in one pass.

**Synopsis**

```
embytools channels tags generate <scheme> <file> [--opt key=value]... --plugin <file.py>...
```

**Arguments**

- `scheme` (required) — the tag scheme name (see `channels tags schemes`).
- `file` (required) — destination JSON path.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--opt key=value` | none | Scheme option, repeatable (e.g. `--opt user=Steve`). |
| `--plugin <file.py>` | none (required) | Load scheme(s) from a `.py` file (repeatable). |

**Writing a tag scheme**

A tag scheme takes a `SchemeContext` (the same one numbering schemes get —
`ctx.channels` carry their `TagItems`, plus `ctx.options` and
`ctx.favorite_names(user)`) and returns
`list[{"Name": str, "Tags": list[str]}]`. Register it with `@tag_scheme("name")`:

```python
# my_tags.py
from embytools.livetv import tag_scheme

@tag_scheme("drop-letters")
def drop_letters(ctx):
    out = []
    for c in ctx.channels:
        tags = [t["Name"] for t in (c.get("TagItems") or [])]
        out.append({"Name": c["Name"], "Tags": [t for t in tags if len(t) > 1]})
    return out
```

**Examples**

```fish
uv run embytools channels tags generate drop-letters /tmp/tags.json --plugin my_tags.py
uv run embytools channels tags import /tmp/tags.json --replace --dry-run
uv run embytools channels tags import /tmp/tags.json --replace
```

The workflow is **generate → review the file → `import --replace --dry-run` →
`import --replace`** — the same shape as `channels numbers`. `--plugin` executes
the file's Python, so only load schemes you trust.
