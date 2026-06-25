# CLAUDE.md

Guidance for working in this repo. These rules override default behavior.

## What this is

embytools is a personal Python CLI (Typer + httpx, **uv-managed**) for managing
an Emby server through its **REST API** (not its database). A thin `cli.py`
mounts one Typer sub-app per domain; all API access goes through a single
`EmbyClient` with resource namespaces (`emby.users`, `emby.livetv`,
`emby.favorites`, `emby.sessions`) under `src/embytools/client/`.

## Dev commands

- `uv sync` — set up the environment (installs the package + dev deps)
- `uv run embytools <group> <command> …` — run the CLI
- `uv run pytest` — run the test suite (must stay green)
- `uv add --dev <pkg>` — add a dev dependency

## Workflow rules (must follow)

- **Change a command → update its docs.** Any change to a command's arguments,
  options, or behavior must be reflected in `docs/commands/`. Keep the docs
  matched to the live `--help` output.
- **Change anything that affects a test → update the test.** If you change
  command behavior, client methods, shared helpers, or schemes, update or add
  the corresponding test in `tests/`. Run `uv run pytest` and keep it green
  before committing.
- **Adding a command** means all of: add it to `src/embytools/commands/<domain>.py`,
  mount its sub-app in `cli.py`, document it in `docs/commands/`, and add tests.
- Update `README.md` and `ARCHITECTURE.md` when a change affects the surface or
  structure they describe.

## Conventions

- **Layering:** the client layer (`client/`) does HTTP only — no user-facing
  output. The commands layer (`commands/`) owns UX via `typer.echo`.
- **Friendly errors, never tracebacks for expected failures:** config problems
  raise `ConfigError` (caught in `session.py`); HTTP/connection failures go
  through `friendly_errors` (`errors.py`). Widen these rather than letting raw
  exceptions escape to the user.
- **Reads** print a table by default and emit JSON with `--json` (use the
  helpers in `output.py`).
- **Writes** support `--dry-run` (preview), confirm before mutating unless
  `--yes`/`-y`, are idempotent (skip work already done), and report partial
  progress if a write fails partway through.
- **Match channels and favorites by name, not id.** Emby regenerates channel ids
  when the upstream M3U source changes domain (which can also wipe channel
  numbers/favorites); names stay stable, so name-keyed files survive it.
- **Snapshot before destructive writes** to `snapshots/` where practical, and
  reuse the self-describing envelope in `envelope.py` for export/import files.

## Testing

- `pytest` + `respx` (mock httpx) — no live server. Unit-test command helpers
  with the fakes in `tests/fakes.py`; test the client over respx; CLI smoke
  tests use `CliRunner` with the `cli_env` temp-config fixture.
- The global scheme registry is reset per test by the autouse `reset_schemes`
  fixture; don't rely on cross-test registration.

## Secrets

- `config.toml` (holds the admin API key) and `snapshots/` are gitignored —
  never commit them.
