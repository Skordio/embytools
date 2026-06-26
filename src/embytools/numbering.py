"""Back-compat shim: the numbering scheme code now lives in
``embytools.livetv.numbering``.

It moved there so the Live TV-only numbering and tagging modules sit together
under ``embytools.livetv``. This module re-exports the public API so the
documented plugin import path keeps working unchanged:

    from embytools.numbering import scheme, even_fill

New code can import from ``embytools.livetv`` instead.
"""

from .livetv.numbering import (  # noqa: F401  (re-exported for back-compat)
    SCHEMES,
    SchemeContext,
    even_fill,
    get_scheme,
    load_plugin,
    scheme,
)

__all__ = ["SCHEMES", "SchemeContext", "even_fill", "get_scheme", "load_plugin", "scheme"]
