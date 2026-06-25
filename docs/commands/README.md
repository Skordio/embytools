# Commands reference

Every command runs through the `embytools` CLI:

```fish
uv run embytools <group> <command> [arguments] [options]
```

Add `--help` to any command or group for its built-in usage.

## Command tree

| Group | Commands |
| --- | --- |
| [`users`](users.md) | `list` |
| [`channels`](channels.md) | `list`, `all`, `copy`, `export`, `import` |
| [`channels numbers`](channels-numbers.md) | `schemes`, `generate`, `apply`, `export`, `clear` |
| [`channels tags`](channels-tags.md) | `list`, `channels`, `show`, `add`, `remove`, `set`, `export`, `import` |
| [`sessions`](sessions.md) | `list`, `message`, `stop`, `pause`, `unpause` |

## Shared conventions

These apply across commands and aren't repeated in every entry.

### Invocation & configuration

Commands read a `config.toml` from the current directory (or the path in the
`EMBYTOOLS_CONFIG` environment variable):

```toml
[server]
base_url = "http://192.168.1.214:8096"
api_key  = "your-admin-api-key"
```

Run commands from the repo root so the default `config.toml` path resolves.
Configuration errors (missing file, missing `[server]`, bad TOML) are reported
as plain messages, not tracebacks.

### Output: tables vs JSON

Read commands print a human-readable table by default and emit JSON with
`--json`, so output can be piped into other tools.

### Write safety

Commands that change the server share a safety convention:

- `--dry-run` previews the exact changes and writes nothing.
- They prompt for confirmation before mutating; pass `--yes`/`-y` to skip the
  prompt (for scripts).
- They're idempotent where possible (work already done is skipped).
- If a write fails partway through, the command reports how far it got before
  re-raising, so you're never left guessing about partial state.

### Name-keyed matching

`channels import` and `channels numbers apply` match channels by **name**, not by
id. Emby regenerates channel ids when the upstream M3U source changes domain
(which can also wipe channel numbers), but names stay stable — so name-keyed
files keep working across those events.

### Snapshots

Write commands that can take a safety snapshot do so before mutating, writing a
timestamped backup into the `snapshots/` directory (override with `--export-dir`,
skip with `--no-snapshot` where offered).
