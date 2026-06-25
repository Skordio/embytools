"""The `favorites-bands` numbering scheme (example plugin).

A user's favorites go in a low band, everything else in a high band, each
even-filled and kept in the channel list's existing (alphabetical) order.

    channels numbers generate favorites-bands out.json \\
        --plugin schemes/favorites_bands.py --opt user=Steve

Options: user=<name> (required); fav_start/fav_end/other_start/other_end.
"""
from embytools.numbering import even_fill, scheme


@scheme("favorites-bands")
def favorites_bands(ctx):
    """A user's favorites in a low band, everything else high, alphabetical."""
    user = ctx.require_opt("user")
    fav_band = (ctx.int_opt("fav_start", 1), ctx.int_opt("fav_end", 999))
    other_band = (ctx.int_opt("other_start", 1000), ctx.int_opt("other_end", 9999))
    favorites = ctx.favorite_names(user)
    favs = [c["Name"] for c in ctx.channels if c["Name"] in favorites]
    others = [c["Name"] for c in ctx.channels if c["Name"] not in favorites]
    return even_fill(favs, *fav_band) + even_fill(others, *other_band)
