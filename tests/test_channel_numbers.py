import pytest
from fakes import FakeEmby

from embytools.commands.channels import (
    NUMBER_TYPE,
    _apply_numbers,
    _assign_numbers,
    _even_fill,
)
from embytools.envelope import read_export, write_export


def test_even_fill_spacing():
    # capacity 10, n 3 -> step 3 -> 1, 4, 7
    assert _even_fill(["a", "b", "c"], 1, 10) == [("a", "1"), ("b", "4"), ("c", "7")]


def test_even_fill_empty():
    assert _even_fill([], 1, 10) == []


def test_even_fill_single():
    assert _even_fill(["x"], 5, 9) == [("x", "5")]


def test_even_fill_overflow_raises():
    with pytest.raises(ValueError):
        _even_fill(["a", "b", "c"], 1, 2)  # only 2 slots for 3 channels


def test_assign_numbers_partitions_and_preserves_order():
    channels = [{"Name": "CNN"}, {"Name": "Junk1"}, {"Name": "Fox"}, {"Name": "Junk2"}]
    data = _assign_numbers(channels, {"CNN", "Fox"}, (1, 999), (1000, 9999))
    nums = {d["Name"]: int(d["Number"]) for d in data}
    assert nums["CNN"] < 1000 and nums["Fox"] < 1000
    assert nums["Junk1"] >= 1000 and nums["Junk2"] >= 1000
    fav_order = [d["Name"] for d in data if int(d["Number"]) < 1000]
    assert fav_order == ["CNN", "Fox"]  # original order kept within the band


def test_number_envelope_round_trip(tmp_path):
    path = tmp_path / "n.json"
    data = [{"Name": "CNN", "Number": "5"}]
    write_export(path, NUMBER_TYPE, "http://h", data)
    assert read_export(path, NUMBER_TYPE) == data


def _emby(manage, **kw):
    return FakeEmby(users=[{"Name": "admin", "Id": "u"}], manage=manage, **kw)


def test_apply_changes_only_differences():
    manage = [
        {"Id": "1", "Name": "CNN", "ChannelNumber": "5"},
        {"Id": "2", "Name": "Fox", "ChannelNumber": None},
    ]
    emby = _emby(manage)
    desired = [{"Name": "CNN", "Number": "5"}, {"Name": "Fox", "Number": "9"}]
    _apply_numbers(emby, desired, dry_run=False, yes=True, snapshot=False, export_dir=None)
    assert emby.livetv.set_calls == [("2", "9")]  # CNN already 5, skipped


def test_apply_dry_run_writes_nothing():
    manage = [{"Id": "1", "Name": "CNN", "ChannelNumber": None}]
    emby = _emby(manage)
    _apply_numbers(
        emby, [{"Name": "CNN", "Number": "5"}], dry_run=True, yes=True, snapshot=False, export_dir=None
    )
    assert emby.livetv.set_calls == []


def test_apply_reports_missing_and_ambiguous(capsys):
    manage = [
        {"Id": "1", "Name": "Dup", "ChannelNumber": None},
        {"Id": "2", "Name": "Dup", "ChannelNumber": None},
    ]
    emby = _emby(manage)
    desired = [{"Name": "Dup", "Number": "5"}, {"Name": "Ghost", "Number": "6"}]
    _apply_numbers(emby, desired, dry_run=False, yes=True, snapshot=False, export_dir=None)
    err = capsys.readouterr().err
    assert "ambiguous" in err and "missing" in err
    assert emby.livetv.set_calls == []


def test_apply_partial_failure_reports_and_raises(capsys):
    manage = [
        {"Id": "1", "Name": "A", "ChannelNumber": None},
        {"Id": "2", "Name": "B", "ChannelNumber": None},
        {"Id": "3", "Name": "C", "ChannelNumber": None},
    ]
    emby = _emby(manage, fail_on_set="2")
    desired = [{"Name": "A", "Number": "1"}, {"Name": "B", "Number": "2"}, {"Name": "C", "Number": "3"}]
    with pytest.raises(RuntimeError):
        _apply_numbers(emby, desired, dry_run=False, yes=True, snapshot=False, export_dir=None)
    assert emby.livetv.set_calls == [("1", "1")]  # A done, aborted on B
    assert "Aborted partway" in capsys.readouterr().err
