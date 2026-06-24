import pytest
import typer
from fakes import FakeEmby

from embytools.commands.channels import (
    _apply_favorites,
    _resolve_user,
    _safe_filename,
    _slim,
)


def ch(id_, name):
    return {"Id": id_, "Name": name}


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
