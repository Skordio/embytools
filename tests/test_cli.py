import json

import httpx
import respx
from typer.testing import CliRunner

from embytools.cli import app
from embytools.commands.channels import NUMBER_TYPE
from embytools.envelope import write_export

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


@respx.mock
def test_channels_numbers_generate_cli(cli_env, tmp_path):
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "s"}])
    )
    respx.get(f"{BASE}/LiveTv/Channels", params={"UserId": "s", "IsFavorite": "true"}).mock(
        return_value=httpx.Response(200, json={"Items": [{"Id": "1", "Name": "CNN"}]})
    )
    respx.get(f"{BASE}/LiveTv/Manage/Channels").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [
                    {"Id": "1", "Name": "CNN", "SortIndexNumber": 0},
                    {"Id": "2", "Name": "Junk", "SortIndexNumber": 1},
                ],
                "TotalRecordCount": 2,
            },
        )
    )
    out = tmp_path / "nums.json"
    res = runner.invoke(app, ["channels", "numbers", "generate", "Steve", str(out)])
    assert res.exit_code == 0
    data = json.loads(out.read_text())["data"]
    nums = {d["Name"]: int(d["Number"]) for d in data}
    assert nums["CNN"] < 1000
    assert nums["Junk"] >= 1000


@respx.mock
def test_channels_numbers_apply_dry_run_cli(cli_env, tmp_path):
    f = tmp_path / "nums.json"
    write_export(f, NUMBER_TYPE, "http://test", [{"Name": "CNN", "Number": "5"}])
    respx.get(f"{BASE}/LiveTv/Manage/Channels").mock(
        return_value=httpx.Response(
            200, json={"Items": [{"Id": "1", "Name": "CNN", "ChannelNumber": None}], "TotalRecordCount": 1}
        )
    )
    res = runner.invoke(app, ["channels", "numbers", "apply", str(f), "--dry-run"])
    assert res.exit_code == 0
    assert "1 channel(s) to change" in res.output
    assert "Dry run" in res.output
