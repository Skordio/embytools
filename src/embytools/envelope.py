"""Self-describing JSON export/import wrapper.

A lot of admin work is "snapshot state to a file, apply it elsewhere." Every
export shares one envelope so files are self-describing and imports can verify
they were handed the right kind of data.

    {
        "type": "livetv-favorite-channels",
        "version": 1,
        "exported_at": "2026-06-21T...Z",
        "server": "http://192.168.1.214:8096",
        "data": [...]
    }

An optional ``meta`` dict carries export-specific context (e.g. whether a tag
export covers all tags or just one) so an importer can apply the right
semantics. It is omitted when absent, keeping plain exports byte-identical.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ENVELOPE_VERSION = 1


def write_export(path: Path, type_: str, server: str, data, meta: dict | None = None) -> None:
    payload = {
        "type": type_,
        "version": ENVELOPE_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "server": server,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def _load(path: Path, expected_type: str) -> dict:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a valid export (expected a JSON object).")
    actual = payload.get("type")
    if actual != expected_type:
        raise ValueError(
            f"{path} is a {actual!r} export, expected {expected_type!r}."
        )
    if "data" not in payload:
        raise ValueError(f"{path} is missing its 'data' field.")
    return payload


def read_export(path: Path, expected_type: str):
    return _load(path, expected_type)["data"]


def read_export_meta(path: Path, expected_type: str):
    """Like :func:`read_export`, but returns ``(data, meta)`` (meta may be None)."""
    payload = _load(path, expected_type)
    return payload["data"], payload.get("meta")
