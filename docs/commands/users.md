# users

Commands for inspecting Emby users. See the [shared conventions](README.md#shared-conventions)
for configuration and output behavior.

---

### users list

List all users on the server and their ids. User ids are what other commands
resolve names to internally; this is the quickest way to see who exists.

**Synopsis**

```
embytools users list [--json]
```

**Options**

| Option | Default | Description |
| --- | --- | --- |
| `--json` | off | Emit JSON instead of a table. |

**Examples**

```fish
# Table of users and ids
uv run embytools users list

# Machine-readable
uv run embytools users list --json
```
