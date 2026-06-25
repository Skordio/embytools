import pytest
from fakes import FakeEmby

from embytools.commands.channels import (
    _apply_tag_changes,
    _channels_by_name,
    _resolve_channels,
    _tag_import_plan,
    _tag_names,
)


def ch(id_, name, tags=()):
    return {"Id": id_, "Name": name, "TagItems": [{"Name": t} for t in tags]}


def test_tag_names():
    assert _tag_names(ch("1", "A", ["x", "y"])) == ["x", "y"]
    assert _tag_names({"Name": "A"}) == []  # no TagItems key


def test_resolve_channels_reports_missing_and_ambiguous(capsys):
    by_name = _channels_by_name([ch("1", "Dup"), ch("2", "Dup"), ch("3", "Solo")])
    resolved = _resolve_channels(by_name, ["Solo", "Dup", "Ghost"])
    assert [c["Id"] for c in resolved] == ["3"]
    err = capsys.readouterr().err
    assert "ambiguous" in err and "missing" in err


def test_apply_adds_and_removes():
    emby = FakeEmby()
    plan = [(ch("1", "A", ["keep", "drop"]), {"new"}, {"drop"})]
    _apply_tag_changes(emby, plan, dry_run=False, yes=True)
    assert ("add", "1", ["new"]) in emby.livetv.tag_calls
    assert ("remove", "1", ["drop"]) in emby.livetv.tag_calls


def test_apply_dry_run_writes_nothing():
    emby = FakeEmby()
    _apply_tag_changes(emby, [(ch("1", "A"), {"x"}, set())], dry_run=True, yes=True)
    assert emby.livetv.tag_calls == []


def test_apply_skips_no_op_entries():
    emby = FakeEmby()
    _apply_tag_changes(emby, [(ch("1", "A"), set(), set())], dry_run=False, yes=True)
    assert emby.livetv.tag_calls == []


def test_apply_snapshot_runs_only_when_changes_and_not_dry_run():
    calls = []
    emby = FakeEmby()
    # no changes -> snapshot callback must not fire
    _apply_tag_changes(
        emby, [(ch("1", "A"), set(), set())], dry_run=False, yes=True,
        snapshot_cb=lambda: calls.append("snap"),
    )
    assert calls == []
    # real change -> callback fires
    _apply_tag_changes(
        emby, [(ch("1", "A"), {"x"}, set())], dry_run=False, yes=True,
        snapshot_cb=lambda: calls.append("snap"),
    )
    assert calls == ["snap"]


def _plan_by_name(plan):
    return {c["Name"]: (add, rem) for c, add, rem in plan}


def test_tag_import_single_tag_additive_adds_only_that_tag():
    chans = [ch("1", "CNN", ["News"]), ch("2", "Fox", [])]
    desired = [{"Name": "CNN"}, {"Name": "Fox"}]  # membership file: both carry Fav
    by = _plan_by_name(_tag_import_plan(chans, desired, scope_tag="Fav", replace=False))
    assert by["CNN"] == ({"Fav"}, set())  # News left alone
    assert by["Fox"] == ({"Fav"}, set())


def test_tag_import_single_tag_replace_syncs_membership_without_wiping_others():
    # The regression: a single-tag --replace must not strip a channel's other tags.
    chans = [ch("1", "CNN", ["Fav", "News"]), ch("2", "Fox", ["Fav"]), ch("3", "ESPN", ["Sports"])]
    desired = [{"Name": "CNN"}]  # only CNN should keep Fav
    by = _plan_by_name(_tag_import_plan(chans, desired, scope_tag="Fav", replace=True))
    assert by["CNN"] == (set(), set())  # already has Fav; News untouched
    assert by["Fox"] == (set(), {"Fav"})  # loses Fav (not listed), keeps nothing else removed
    assert "ESPN" not in by  # never had Fav, so never in the plan
    # No remove set anywhere contains a non-Fav tag.
    assert all(rem <= {"Fav"} for _, _, rem in _tag_import_plan(chans, desired, "Fav", True))


def test_tag_import_full_replace_makes_exact_set():
    chans = [ch("1", "CNN", ["News", "HD"])]
    desired = [{"Name": "CNN", "Tags": ["News"]}]
    by = _plan_by_name(_tag_import_plan(chans, desired, scope_tag=None, replace=True))
    assert by["CNN"] == (set(), {"HD"})  # extra tag removed


def test_tag_import_full_additive_only_adds():
    chans = [ch("1", "CNN", ["News"])]
    desired = [{"Name": "CNN", "Tags": ["News", "Fav"]}]
    by = _plan_by_name(_tag_import_plan(chans, desired, scope_tag=None, replace=False))
    assert by["CNN"] == ({"Fav"}, set())


def test_apply_partial_failure_reports_and_raises(capsys):
    emby = FakeEmby(fail_on_tag="2")
    plan = [(ch("1", "A"), {"x"}, set()), (ch("2", "B"), {"y"}, set())]
    with pytest.raises(RuntimeError):
        _apply_tag_changes(emby, plan, dry_run=False, yes=True)
    assert ("add", "1", ["x"]) in emby.livetv.tag_calls
    assert "Aborted partway" in capsys.readouterr().err
