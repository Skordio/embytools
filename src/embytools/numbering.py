"""Pluggable channel-numbering schemes.

A *scheme* is a function that, given a ``SchemeContext``, returns a name-keyed
numbering: ``list[{"Name": str, "Number": str}]``. ``channels numbers generate``
runs a scheme by name and writes its output to a file for ``apply`` to consume.

Schemes always come from plugins — ``generate`` requires at least one
``--plugin`` file and there are no built-ins. Write a ``.py`` file that imports
from this module and decorates functions, then load it with ``--plugin``.
Example schemes ship in the repo's ``schemes/`` directory:

    # my_schemes.py
    from embytools.numbering import scheme, even_fill

    @scheme("alpha")
    def alpha(ctx):
        names = sorted(c["Name"] for c in ctx.channels)
        return even_fill(names, 1, 9999)
"""

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SCHEMES: dict[str, Callable] = {}


def scheme(name: str) -> Callable:
    """Register a scheme function under ``name``."""

    def decorator(fn: Callable) -> Callable:
        SCHEMES[name] = fn
        return fn

    return decorator


def get_scheme(name: str) -> Callable:
    try:
        return SCHEMES[name]
    except KeyError:
        available = ", ".join(sorted(SCHEMES)) or "(none)"
        raise ValueError(f"Unknown scheme {name!r}. Available: {available}.")


def load_plugin(path: Path) -> None:
    """Import a user .py file so its @scheme decorators register."""
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Plugin file not found: {path}")
    spec = importlib.util.spec_from_file_location(f"embytools_plugin_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load plugin: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def even_fill(names: list[str], lo: int, hi: int) -> list[dict]:
    """Spread names across the band [lo, hi], maximizing even gaps.

    Channel i gets ``lo + i*step``; ``step`` packs the band as loosely as it can
    while keeping every channel inside it. Returns ``{"Name", "Number"}`` dicts
    (Emby's channel-number field is a string), ready to concatenate and return.
    """
    n = len(names)
    if n == 0:
        return []
    capacity = hi - lo + 1
    if n > capacity:
        raise ValueError(
            f"{n} channels can't fit in band {lo}-{hi} ({capacity} slots); widen the band."
        )
    step = max(1, capacity // n)
    return [{"Name": name, "Number": str(lo + i * step)} for i, name in enumerate(names)]


@dataclass
class SchemeContext:
    """Everything a scheme needs: the client, the channel list, and options."""

    emby: object
    channels: list[dict]
    options: dict[str, str] = field(default_factory=dict)

    def favorite_names(self, user: str) -> set[str]:
        u = self.emby.users.find(user)
        if u is None:
            raise ValueError(f"No user named {user!r}.")
        return {c["Name"] for c in self.emby.livetv.favorite_channels(u["Id"])}

    def require_opt(self, key: str) -> str:
        if key not in self.options:
            raise ValueError(f"This scheme needs --opt {key}=<value>.")
        return self.options[key]

    def int_opt(self, key: str, default: int) -> int:
        try:
            return int(self.options.get(key, default))
        except ValueError:
            raise ValueError(f"--opt {key} must be an integer, got {self.options[key]!r}.")
