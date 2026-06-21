"""Shared output helpers so every command formats consistently.

Read commands print a human-readable table by default and emit JSON with
``--json`` so output can be piped into other tools.
"""

import json as _json

import typer


def print_json(data) -> None:
    typer.echo(_json.dumps(data, indent=2, default=str))


def print_table(rows: list[dict], columns: list[tuple[str, int]]) -> None:
    """Print rows as a fixed-width table.

    ``columns`` is a list of ``(key, width)`` pairs; the last column is not
    padded so it never trails whitespace.
    """
    for row in rows:
        cells = []
        for i, (key, width) in enumerate(columns):
            value = str(row.get(key, ""))
            cells.append(value if i == len(columns) - 1 else f"{value:<{width}}")
        typer.echo(" ".join(cells))
