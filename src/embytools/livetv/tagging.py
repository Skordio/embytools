"""Pluggable channel-tagging schemes (Live TV).

A *tag scheme* is a function that, given a ``SchemeContext``, returns a
name-keyed desired tag set: ``list[{"Name": str, "Tags": list[str]}]``.
``channels tags generate`` runs a scheme by name and writes its output to a
full ``livetv-channel-tags`` export, which ``channels tags import --replace``
then applies as the exact per-channel tag set.

Tag schemes mirror numbering schemes and reuse the same ``SchemeContext`` and
``load_plugin`` (so ``ctx.channels``, ``ctx.options``, ``ctx.favorite_names``
all work the same). The registry is separate, though, so a numbering scheme
can't be run as a tag scheme by mistake. Register with ``@tag_scheme("name")``:

    # my_tags.py
    from embytools.livetv import tag_scheme

    @tag_scheme("drop-letters")
    def drop_letters(ctx):
        out = []
        for c in ctx.channels:
            tags = [t["Name"] for t in (c.get("TagItems") or [])]
            out.append({"Name": c["Name"], "Tags": [t for t in tags if len(t) > 1]})
        return out
"""

from typing import Callable

# Re-exported so plugins can pull everything tag-related from one module.
from .numbering import SchemeContext, load_plugin  # noqa: F401

TAG_SCHEMES: dict[str, Callable] = {}


def tag_scheme(name: str) -> Callable:
    """Register a tag-scheme function under ``name``."""

    def decorator(fn: Callable) -> Callable:
        TAG_SCHEMES[name] = fn
        return fn

    return decorator


def get_tag_scheme(name: str) -> Callable:
    try:
        return TAG_SCHEMES[name]
    except KeyError:
        available = ", ".join(sorted(TAG_SCHEMES)) or "(none)"
        raise ValueError(f"Unknown tag scheme {name!r}. Available: {available}.")
