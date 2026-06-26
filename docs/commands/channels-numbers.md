# channels numbers

Assign Live TV channel **numbers** so clients that sort by channel number show
your channels in a meaningful order. A numbering is produced by a **scheme** (a
plugin function), written to a file, then applied to the server — matching
channels by **name** so it survives id regeneration.

See the [shared conventions](README.md#shared-conventions) for write safety,
name-keyed matching, and snapshots.

> Assigning numbers doesn't reorder the list by itself: Emby's default channel
> order follows each channel's sort index, and clients may have their own sort
> setting. Use `channels numbers sort` to push the sort index into number order.

## Workflow

```
generate  →  (review/edit the file)  →  apply --dry-run  →  apply
```

`export` backs up the live numbers; `apply <backup>` restores them after a wipe;
`clear` removes them.

---

### channels numbers schemes

List the numbering schemes available, including any provided by `--plugin`
files. There are **no built-in schemes**, so without `--plugin` this reports an
empty registry.

**Synopsis**

```
embytools channels numbers schemes [--plugin <file>]...
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--plugin <file>` | none | Load scheme(s) from a `.py` file (repeatable). |

**Examples**

```fish
uv run embytools channels numbers schemes --plugin schemes/favorites_bands.py
```

---

### channels numbers generate

Run a scheme and write the resulting numbering to a file. Makes **no server
changes**. A `--plugin` providing the scheme is **required** — there are no
built-ins.

**Synopsis**

```
embytools channels numbers generate <scheme> <file> --plugin <file> [--opt key=value]...
```

**Arguments**

- `scheme` (required) — the name a loaded plugin registered (e.g.
  `favorites-bands`).
- `file` (required) — destination JSON path for the numbering.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--plugin <file>` | none | Load scheme(s) from a `.py` file (repeatable). **Required** — `generate` errors without at least one. |
| `--opt key=value` | none | Pass an option to the scheme (repeatable). E.g. `--opt user=Steve`. |

**Examples**

```fish
# Favorites in a low band, everything else high (shipped example scheme)
uv run embytools channels numbers generate favorites-bands numbers.json \
    --plugin schemes/favorites_bands.py --opt user=Steve
```

**Notes**

- The output is a name-keyed file; review or hand-edit it before `apply`.
- `--plugin` executes the file's Python — only load schemes you trust.

#### Writing a scheme

A scheme is a function that takes a `SchemeContext` and returns a name-keyed
numbering — `list[{"Name": str, "Number": str}]`. Register it with `@scheme`:

```python
# my_schemes.py
from embytools.numbering import scheme, even_fill

@scheme("alpha")
def alpha(ctx):
    names = sorted(c["Name"] for c in ctx.channels)   # ctx.channels = the full lineup
    return even_fill(names, 1, 9999)                  # spreads them with even gaps
```

The `ctx` (a `SchemeContext`) offers:

- `ctx.channels` — all channels (the management list), in sort-index order.
- `ctx.options` — the `--opt` key/values as a dict; `ctx.require_opt("user")`
  fetches a required one, `ctx.int_opt("fav_end", 999)` coerces with a default.
- `ctx.favorite_names("Steve")` — the set of a user's favorite channel names.

The `even_fill(names, lo, hi)` helper spreads names across the band `[lo, hi]`
with the largest possible even gaps (leaving room to insert later), returning the
`{"Name", "Number"}` dicts a scheme returns.

Two example schemes ship with the project:

- `schemes/favorites_bands.py` — `favorites-bands`: a user's favorites in the low
  band (1–999), everything else high (1000+). Options: `user=` (required),
  `fav_start`/`fav_end`/`other_start`/`other_end`.
- `snapshots/categorize.py` (personal, untracked) — `categories`: favorites
  grouped into ordered categories, alphabetical within each.

---

### channels numbers apply

Set channel numbers from a file, matching channels by **name**. Idempotent —
channels already at their target number are skipped. Doubles as **restore**
(apply a backup).

**Synopsis**

```
embytools channels numbers apply <file> [--no-snapshot] [--export-dir <dir>] [--dry-run] [--yes]
```

**Arguments**

- `file` (required) — a numbering file from `generate` or `export`.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--snapshot` / `--no-snapshot` | `--snapshot` | Back up current numbers before applying. |
| `--export-dir <dir>` | `snapshots` | Directory for the pre-apply snapshot. |
| `--dry-run` | off | Preview the changes without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
uv run embytools channels numbers apply numbers.json --dry-run
uv run embytools channels numbers apply numbers.json
```

**Notes**

- Names in the file that match no current channel, or match more than one, are
  reported and skipped.
- If a write fails partway, the command reports how many changed before the error.

---

### channels numbers sort

Set every channel's **manual sort index** to match channel-number order. Emby's
"Default Channel Order" follows each channel's sort index (`SortIndexNumber`),
**not** its channel number — so after `apply` you also need `sort` for the list
to actually read in number order on clients using the default sort.

**Synopsis**

```
embytools channels numbers sort [--dry-run] [--yes]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
uv run embytools channels numbers apply numbers.json
uv run embytools channels numbers sort --dry-run
uv run embytools channels numbers sort
```

**Notes**

- Derives the order from the channels' **current** numbers — run it after
  `apply`. Channels without a number sort last (by name).
- Idempotent: only channels out of place are moved (0 writes when already
  sorted). It writes via `POST /LiveTv/Manage/Channels/{Id}/SortIndex`, whose
  insert-and-shift behavior means a full re-sort is one write per channel.
- If a write fails partway, the command reports how many were reordered first.

---

### channels numbers export

Back up the current channel numbers (name-keyed) to a file, for safety against a
wipe. Restore later with `channels numbers apply <file>`.

**Synopsis**

```
embytools channels numbers export <file> [--allow-empty]
```

**Arguments**

- `file` (required) — destination JSON path.

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--allow-empty` | off | Allow overwriting an existing file with an empty export (refused by default so a transient empty read can't clobber a good backup). |

**Examples**

```fish
uv run embytools channels numbers export snapshots/numbers-backup.json
```

---

### channels numbers clear

Remove the number from every channel that has one (sets it empty). Useful to
reset before applying a fresh numbering.

**Synopsis**

```
embytools channels numbers clear [--no-snapshot] [--export-dir <dir>] [--dry-run] [--yes]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--snapshot` / `--no-snapshot` | `--snapshot` | Back up current numbers before clearing. |
| `--export-dir <dir>` | `snapshots` | Directory for the pre-clear snapshot. |
| `--dry-run` | off | Preview without writing. |
| `--yes`, `-y` | off | Skip the confirmation prompt. |

**Examples**

```fish
uv run embytools channels numbers clear --dry-run
```
