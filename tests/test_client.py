import httpx
import respx

from embytools.client import EmbyClient

BASE = "http://test"


@respx.mock
def test_users_find_case_insensitive():
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "1"}])
    )
    with EmbyClient(BASE, "k") as e:
        assert e.users.find("STEVE")["Id"] == "1"


@respx.mock
def test_users_find_missing_returns_none():
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "1"}])
    )
    with EmbyClient(BASE, "k") as e:
        assert e.users.find("nobody") is None


@respx.mock
def test_auth_header_sent():
    route = respx.get(f"{BASE}/Users").mock(return_value=httpx.Response(200, json=[]))
    with EmbyClient(BASE, "secret") as e:
        e.users.list()
    assert route.calls.last.request.headers["X-Emby-Token"] == "secret"


@respx.mock
def test_favorite_channels_extracts_items():
    respx.get(f"{BASE}/LiveTv/Channels").mock(
        return_value=httpx.Response(200, json={"Items": [{"Id": "1", "Name": "CNN"}]})
    )
    with EmbyClient(BASE, "k") as e:
        assert e.livetv.favorite_channels("u") == [{"Id": "1", "Name": "CNN"}]


@respx.mock
def test_manage_channels_sorts_and_returns_total():
    items = [
        {"Id": "a", "Name": "A", "SortIndexNumber": 2},
        {"Id": "b", "Name": "B", "SortIndexNumber": None},  # null -> treated as 0
        {"Id": "c", "Name": "C", "SortIndexNumber": 1},
    ]
    respx.get(f"{BASE}/LiveTv/Manage/Channels").mock(
        return_value=httpx.Response(200, json={"Items": items, "TotalRecordCount": 10})
    )
    with EmbyClient(BASE, "k") as e:
        got, total = e.livetv.manage_channels()
    assert total == 10
    assert [c["Id"] for c in got] == ["b", "c", "a"]


@respx.mock
def test_favorites_add_and_remove():
    add = respx.post(f"{BASE}/Users/u/FavoriteItems/1").mock(return_value=httpx.Response(204))
    rem = respx.delete(f"{BASE}/Users/u/FavoriteItems/1").mock(return_value=httpx.Response(204))
    with EmbyClient(BASE, "k") as e:
        e.favorites.add("u", "1")
        e.favorites.remove("u", "1")
    assert add.called and rem.called


@respx.mock
def test_sessions_send_message_uses_query_params():
    route = respx.post(f"{BASE}/Sessions/sid/Message").mock(return_value=httpx.Response(204))
    with EmbyClient(BASE, "k") as e:
        e.sessions.send_message("sid", "hi", header="H", timeout_ms=5000)
    params = route.calls.last.request.url.params
    assert params["Text"] == "hi"
    assert params["Header"] == "H"
    assert params["TimeoutMs"] == "5000"


@respx.mock
def test_sessions_playstate_posts_command():
    route = respx.post(f"{BASE}/Sessions/sid/Playing/Pause").mock(return_value=httpx.Response(204))
    with EmbyClient(BASE, "k") as e:
        e.sessions.playstate("sid", "Pause")
    assert route.called
