import pytest

from embytools.livetv import numbering, tagging
from embytools.livetv.tagging import get_tag_scheme, tag_scheme


def test_register_and_get():
    @tag_scheme("sample")
    def sample(ctx):
        return []

    assert get_tag_scheme("sample") is sample


def test_get_unknown_lists_available():
    @tag_scheme("only")
    def only(ctx):
        return []

    with pytest.raises(ValueError) as e:
        get_tag_scheme("nope")
    assert "only" in str(e.value)


def test_registries_are_separate():
    @tag_scheme("shared-name")
    def as_tag(ctx):
        return []

    # A name registered as a tag scheme must not be runnable as a numbering scheme.
    with pytest.raises(ValueError):
        numbering.get_scheme("shared-name")


def test_tagging_reexports_scheme_context():
    # Plugins can pull SchemeContext from the tagging module.
    ctx = tagging.SchemeContext(emby=object(), channels=[{"Name": "CNN"}])
    assert ctx.channels[0]["Name"] == "CNN"


def test_numbering_back_compat_shim():
    # The documented `from embytools.numbering import ...` path still works and
    # shares the same registry object as the relocated module.
    from embytools import numbering as shim

    assert shim.SCHEMES is numbering.SCHEMES
    assert shim.scheme is numbering.scheme
