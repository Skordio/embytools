import httpx
import respx
from typer.testing import CliRunner

from embytools.cli import app

runner = CliRunner()
BASE = "http://test"


@respx.mock
def test_users_list_cli(cli_env):
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "1"}])
    )
    res = runner.invoke(app, ["users", "list"])
    assert res.exit_code == 0
    assert "Steve" in res.output


@respx.mock
def test_config_error_is_friendly(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBYTOOLS_CONFIG", str(tmp_path / "missing.toml"))
    res = runner.invoke(app, ["users", "list"])
    assert res.exit_code == 1
    assert "No config" in res.output


@respx.mock
def test_sessions_list_hides_userless(cli_env):
    respx.get(f"{BASE}/Sessions").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "Id": "a",
                    "UserName": "Steve",
                    "Client": "Web",
                    "DeviceName": "Edge",
                    "RemoteEndPoint": "1.2.3.4",
                    "NowPlayingItem": None,
                    "PlayState": {},
                    "SupportsRemoteControl": True,
                },
                {
                    "Id": "b",
                    "UserName": None,
                    "Client": "Seerr",
                    "DeviceName": "Seerr",
                    "RemoteEndPoint": "5.6.7.8",
                    "NowPlayingItem": None,
                    "PlayState": {},
                    "SupportsRemoteControl": False,
                },
            ],
        )
    )
    res = runner.invoke(app, ["sessions", "list"])
    assert res.exit_code == 0
    assert "Steve" in res.output
    assert "Seerr" not in res.output  # userless session hidden by default


@respx.mock
def test_channels_copy_dry_run_cli(cli_env):
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(
            200, json=[{"Name": "Grace", "Id": "g"}, {"Name": "Steve", "Id": "s"}]
        )
    )
    respx.get(f"{BASE}/LiveTv/Channels", params={"UserId": "g", "IsFavorite": "true"}).mock(
        return_value=httpx.Response(200, json={"Items": [{"Id": "1", "Name": "CNN"}]})
    )
    respx.get(f"{BASE}/LiveTv/Channels", params={"UserId": "s", "IsFavorite": "true"}).mock(
        return_value=httpx.Response(200, json={"Items": []})
    )
    res = runner.invoke(app, ["channels", "copy", "Grace", "Steve", "--dry-run"])
    assert res.exit_code == 0
    assert "1 to add" in res.output
    assert "Dry run" in res.output
