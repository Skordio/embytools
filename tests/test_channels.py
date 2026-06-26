import pytest
import typer
from fakes import FakeEmby

from embytools.commands.channels import (
    EXPORT_TYPE,
    _apply_favorites,
    _first_user_id,
    _guarded_export,
    _resolve_user,
    _safe_filename,
    _slim,
    _snapshot_favorites,
    _snapshot_numbers,
    _validate_items,
)
from embytools.envelope import read_export, write_export


def ch(id_, name):
    return {"Id": id_, "Name": name}


def test_first_user_id_prefers_admin():
    emby = FakeEmby(
        users=[
            {"Name": "Kid", "Id": "k", "Policy": {"IsAdministrator": False}},
            {"Name": "Admin", "Id": "a", "Policy": {"IsAdministrator": True}},
        ]
    )
    assert _first_user_id(emby) == "a"


def test_first_user_id_falls_back_to_first_when_no_admin_flag():
    emby = FakeEmby(users=[{"Name": "A", "Id": "1"}, {"Name": "B", "Id": "2"}])
    assert _first_user_id(emby) == "1"


def test_validate_items_flags_missing_key():
    with pytest.raises(ValueError):
        _validate_items([{"Name": "CNN"}], ["Name", "Number"], "numbering file")


def test_validate_items_rejects_non_dict_entry():
    with pytest.raises(ValueError):
        _validate_items(["nope"], ["Name"], "favorites export")


def test_validate_items_accepts_well_formed():
    _validate_items([{"Name": "CNN", "Number": "5"}], ["Name", "Number"], "ok")  # no raise


def test_guarded_export_refuses_empty_overwrite(tmp_path):
    f = tmp_path / "b.json"
    write_export(f, EXPORT_TYPE, "http://h", [{"Name": "CNN"}])  # an existing good backup
    with pytest.raises(typer.Exit):
        _guarded_export(f, EXPORT_TYPE, "http://h", [], "favorites", allow_empty=False)
    assert read_export(f, EXPORT_TYPE) == [{"Name": "CNN"}]  # left intact


def test_guarded_export_allows_empty_with_flag(tmp_path):
    f = tmp_path / "b.json"
    write_export(f, EXPORT_TYPE, "http://h", [{"Name": "CNN"}])
    _guarded_export(f, EXPORT_TYPE, "http://h", [], "favorites", allow_empty=True)
    assert read_export(f, EXPORT_TYPE) == []


def test_guarded_export_writes_non_empty(tmp_path):
    f = tmp_path / "b.json"
    _guarded_export(f, EXPORT_TYPE, "http://h", [{"Name": "CNN"}], "favorites", allow_empty=False)
    assert read_export(f, EXPORT_TYPE) == [{"Name": "CNN"}]


def test_snapshot_favorites_lands_in_favorites_subdir(tmp_path):
    emby = FakeEmby()
    _snapshot_favorites(emby, tmp_path, [({"Name": "Steve", "Id": "u"}, [ch("1", "CNN")])])
    files = list((tmp_path / "favorites").glob("*.json"))
    assert len(files) == 1 and "favorite-channels" in files[0].name
    assert not list(tmp_path.glob("*.json"))  # nothing dumped at the root


def test_snapshot_numbers_lands_in_numbers_subdir(tmp_path):
    emby = FakeEmby()
    _snapshot_numbers(emby, tmp_path, [{"Name": "CNN", "ChannelNumber": "5"}])
    files = list((tmp_path / "numbers").glob("*.json"))
    assert len(files) == 1 and files[0].name.startswith("channel-numbers-")


def test_slim_keeps_only_id_and_name():
    assert _slim([{"Id": "1", "Name": "CNN", "Extra": 9}]) == [{"Id": "1", "Name": "CNN"}]


def test_safe_filename_sanitizes():
    assert _safe_filename("Living Room/TV") == "Living_Room_TV"
    assert _safe_filename("Steve") == "Steve"


def test_resolve_user_found():
    emby = FakeEmby(users=[{"Name": "Steve", "Id": "1"}])
    assert _resolve_user(emby, "steve")["Id"] == "1"


def test_resolve_user_missing_exits():
    emby = FakeEmby(users=[])
    with pytest.raises(typer.Exit):
        _resolve_user(emby, "nobody")


def test_additive_adds_missing_and_skips_existing():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN"), ch("2", "Fox")],
        dry_run=False,
        yes=True,
        existing_channels=[ch("1", "CNN")],
    )
    assert emby.favorites.added == [("u", "2")]
    assert emby.favorites.removed == []


def test_replace_removes_extras():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN"), ch("2", "Fox")],
        dry_run=False,
        yes=True,
        replace=True,
        existing_channels=[ch("1", "CNN"), ch("3", "Old")],
    )
    assert emby.favorites.added == [("u", "2")]
    assert emby.favorites.removed == [("u", "3")]


def test_additive_never_removes():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN")],
        dry_run=False,
        yes=True,
        replace=False,
        existing_channels=[ch("1", "CNN"), ch("3", "Old")],
    )
    assert emby.favorites.removed == []


def test_dry_run_writes_nothing():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("2", "Fox")],
        dry_run=True,
        yes=True,
        existing_channels=[],
    )
    assert emby.favorites.added == []


def test_replace_in_sync_writes_nothing():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN")],
        dry_run=False,
        yes=True,
        replace=True,
        existing_channels=[ch("1", "CNN")],
    )
    assert emby.favorites.added == []
    assert emby.favorites.removed == []


def test_fetches_existing_when_not_provided():
    emby = FakeEmby(favorites_by_user={"u": [ch("1", "CNN")]})
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN"), ch("2", "Fox")],
        dry_run=False,
        yes=True,
    )
    assert emby.favorites.added == [("u", "2")]


def test_import_resolves_stale_ids_by_name():
    # The file's ids are stale (e.g. after an M3U domain change); name_to_id
    # maps the channel names to the server's current ids.
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("OLD1", "CNN"), ch("OLD2", "Fox")],
        dry_run=False,
        yes=True,
        existing_channels=[],
        name_to_id={"CNN": "new1", "Fox": "new2"},
    )
    # Favorited by current ids, not the stale ones from the file.
    assert emby.favorites.added == [("u", "new1"), ("u", "new2")]


def test_import_skips_name_absent_from_server(capsys):
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("OLD1", "CNN"), ch("OLD2", "Gone")],
        dry_run=False,
        yes=True,
        existing_channels=[],
        name_to_id={"CNN": "new1"},  # "Gone" no longer exists on the server
    )
    assert emby.favorites.added == [("u", "new1")]
    assert "Gone" in capsys.readouterr().err


def test_already_favorited_matched_by_name_not_id():
    # The target already has CNN, but under a different (current) id than the
    # file records — matching by name must treat it as already favorited.
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("OLD", "CNN")],
        dry_run=False,
        yes=True,
        existing_channels=[ch("cur", "CNN")],
        name_to_id={"CNN": "cur"},
    )
    assert emby.favorites.added == []


def test_replace_removes_extras_by_name():
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("OLD", "CNN")],
        dry_run=False,
        yes=True,
        replace=True,
        existing_channels=[ch("cur", "CNN"), ch("x", "Old")],
        name_to_id={"CNN": "cur"},
    )
    assert emby.favorites.added == []  # CNN already present by name
    assert emby.favorites.removed == [("u", "x")]  # removed by its current id


def test_snapshot_cb_fires_before_write_but_not_on_dry_run():
    calls = []
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN")],
        dry_run=True,
        yes=True,
        existing_channels=[],
        name_to_id={"CNN": "1"},
        snapshot_cb=lambda: calls.append(1),
    )
    assert calls == []  # dry run writes nothing, snapshots nothing
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN")],
        dry_run=False,
        yes=True,
        existing_channels=[],
        name_to_id={"CNN": "1"},
        snapshot_cb=lambda: calls.append(1),
    )
    assert calls == [1]  # real write: snapshot taken first


def test_snapshot_cb_skipped_when_nothing_to_change():
    calls = []
    emby = FakeEmby()
    _apply_favorites(
        emby,
        {"Id": "u", "Name": "T"},
        [ch("1", "CNN")],
        dry_run=False,
        yes=True,
        existing_channels=[ch("1", "CNN")],
        name_to_id={"CNN": "1"},
        snapshot_cb=lambda: calls.append(1),
    )
    assert calls == []  # already in sync — no snapshot, no write


def test_partial_failure_reports_progress_and_raises(capsys):
    emby = FakeEmby(fail_on_add="2")
    with pytest.raises(RuntimeError):
        _apply_favorites(
            emby,
            {"Id": "u", "Name": "T"},
            [ch("1", "CNN"), ch("2", "Fox"), ch("3", "NM")],
            dry_run=False,
            yes=True,
            existing_channels=[],
        )
    assert emby.favorites.added == [("u", "1")]  # first succeeded, aborted on second
    assert "Aborted partway" in capsys.readouterr().err
