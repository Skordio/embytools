"""Live TV-only logic: pluggable channel-numbering and channel-tagging schemes.

Both modules drive the same generate → review → apply workflow and share a
``SchemeContext``/``load_plugin``. They live together here because they only
apply to Live TV channels. Plugins can import the public API from one place:

    from embytools.livetv import scheme, even_fill, tag_scheme
"""

from .numbering import (
    SCHEMES,
    SchemeContext,
    even_fill,
    get_scheme,
    load_plugin,
    scheme,
)
from .tagging import TAG_SCHEMES, get_tag_scheme, tag_scheme

__all__ = [
    "SCHEMES",
    "SchemeContext",
    "even_fill",
    "get_scheme",
    "load_plugin",
    "scheme",
    "TAG_SCHEMES",
    "get_tag_scheme",
    "tag_scheme",
]
