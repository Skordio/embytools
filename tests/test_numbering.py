from pathlib import Path

import pytest
from fakes import FakeEmby

from embytools.numbering import (
    SCHEMES,
    SchemeContext,
    even_fill,
    get_scheme,
    load_plugin,
    scheme,
)

FAV_PLUGIN = Path(__file__).parent.parent / "schemes" / "favorites_bands.py"


def test_even_fill_spacing_and_shape():
    # capacity 10, n 3 -> step 3 -> 1, 4, 7
    assert even_fill(["a", "b", "c"], 1, 10) == [
        {"Name": "a", "Number": "1"},
        {"Name": "b", "Number": "4"},
        {"Name": "c", "Number": "7"},
    ]


def test_even_fill_empty():
    assert even_fill([], 1, 10) == []


def test_even_fill_overflow_raises():
    with pytest.raises(ValueError):
        even_fill(["a", "b", "c"], 1, 2)


def test_register_and_get():
    @scheme("test-temp-scheme")
    def _s(ctx):
        return []

    assert get_scheme("test-temp-scheme") is _s


def test_get_unknown_raises():
    with pytest.raises(ValueError) as exc:
        get_scheme("does-not-exist")
    assert "Unknown scheme" in str(exc.value)


def test_favorites_bands_plugin_partitions():
    load_plugin(FAV_PLUGIN)
    channels = [{"Name": "CNN"}, {"Name": "Junk1"}, {"Name": "Fox"}, {"Name": "Junk2"}]
    emby = FakeEmby(
        users=[{"Name": "Steve", "Id": "s"}],
        favorites_by_user={"s": [{"Name": "CNN"}, {"Name": "Fox"}]},
    )
    ctx = SchemeContext(emby=emby, channels=channels, options={"user": "Steve"})
    data = get_scheme("favorites-bands")(ctx)
    nums = {d["Name"]: int(d["Number"]) for d in data}
    assert nums["CNN"] < 1000 and nums["Fox"] < 1000
    assert nums["Junk1"] >= 1000 and nums["Junk2"] >= 1000
    assert [d["Name"] for d in data if int(d["Number"]) < 1000] == ["CNN", "Fox"]


def test_favorites_bands_requires_user_opt():
    load_plugin(FAV_PLUGIN)
    emby = FakeEmby(users=[{"Name": "Steve", "Id": "s"}])
    ctx = SchemeContext(emby=emby, channels=[], options={})
    with pytest.raises(ValueError):
        get_scheme("favorites-bands")(ctx)


def test_load_plugin_registers_scheme(tmp_path):
    plugin = tmp_path / "myplugin.py"
    plugin.write_text(
        "from embytools.numbering import scheme, even_fill\n"
        "@scheme('plugin-temp')\n"
        "def s(ctx):\n"
        "    return even_fill([c['Name'] for c in ctx.channels], 1, 100)\n"
    )
    load_plugin(plugin)
    assert "plugin-temp" in SCHEMES
    ctx = SchemeContext(emby=None, channels=[{"Name": "A"}], options={})
    assert get_scheme("plugin-temp")(ctx) == [{"Name": "A", "Number": "1"}]


def test_load_plugin_missing_file_raises(tmp_path):
    with pytest.raises(ValueError):
        load_plugin(tmp_path / "nope.py")
