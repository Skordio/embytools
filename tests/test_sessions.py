import pytest
import typer
from fakes import FakeEmby

from embytools.commands.sessions import (
    _is_real_user_session,
    _now_playing,
    _resolve_sessions,
    _select_targets,
)


def sess(**kw):
    base = {
        "Id": "id1",
        "UserName": "Steve",
        "DeviceName": "Edge",
        "Client": "Web",
        "RemoteEndPoint": "1.2.3.4",
        "SupportsRemoteControl": True,
        "NowPlayingItem": None,
        "PlayState": {},
    }
    base.update(kw)
    return base


def test_is_real_user_session():
    assert _is_real_user_session(sess(UserName="Steve"))
    assert not _is_real_user_session(sess(UserName=None))
    assert not _is_real_user_session(sess(UserName=""))


def test_now_playing_idle():
    assert _now_playing(sess(NowPlayingItem=None)) == "—"


def test_now_playing_active():
    assert _now_playing(sess(NowPlayingItem={"Name": "Fox"}, PlayState={"IsPaused": False})) == "Fox"


def test_now_playing_paused():
    s = sess(NowPlayingItem={"Name": "Fox"}, PlayState={"IsPaused": True})
    assert _now_playing(s) == "Fox (paused)"


def test_resolve_by_username():
    emby = FakeEmby(sessions=[sess(UserName="Steve", Id="a")])
    assert [s["Id"] for s in _resolve_sessions(emby, "steve")] == ["a"]


def test_resolve_by_device():
    emby = FakeEmby(sessions=[sess(DeviceName="Living Room", Id="a")])
    assert _resolve_sessions(emby, "living room")[0]["Id"] == "a"


def test_resolve_by_id_prefix():
    emby = FakeEmby(sessions=[sess(Id="abcdef")])
    assert _resolve_sessions(emby, "abc")[0]["Id"] == "abcdef"


def test_resolve_no_match_exits():
    emby = FakeEmby(sessions=[sess(UserName="Steve")])
    with pytest.raises(typer.Exit):
        _resolve_sessions(emby, "nobody")


def test_resolve_ignores_userless_sessions():
    emby = FakeEmby(sessions=[sess(UserName=None, DeviceName="Seerr")])
    with pytest.raises(typer.Exit):
        _resolve_sessions(emby, "seerr")


def test_select_skips_uncontrollable_leaving_single():
    emby = FakeEmby(
        sessions=[
            sess(UserName="Steve", Id="a", DeviceName="Web", SupportsRemoteControl=False),
            sess(UserName="Steve", Id="b", DeviceName="TV", SupportsRemoteControl=True),
        ]
    )
    assert [s["Id"] for s in _select_targets(emby, "Steve", all_matches=False)] == ["b"]


def test_select_ambiguous_exits_without_all():
    emby = FakeEmby(
        sessions=[
            sess(UserName="Steve", Id="a", DeviceName="TV1"),
            sess(UserName="Steve", Id="b", DeviceName="TV2"),
        ]
    )
    with pytest.raises(typer.Exit):
        _select_targets(emby, "Steve", all_matches=False)


def test_select_all_matches_allows_multiple():
    emby = FakeEmby(
        sessions=[
            sess(UserName="Steve", Id="a", DeviceName="TV1"),
            sess(UserName="Steve", Id="b", DeviceName="TV2"),
        ]
    )
    assert len(_select_targets(emby, "Steve", all_matches=True)) == 2


def test_select_none_controllable_exits():
    emby = FakeEmby(sessions=[sess(UserName="Steve", SupportsRemoteControl=False)])
    with pytest.raises(typer.Exit):
        _select_targets(emby, "Steve", all_matches=False)
