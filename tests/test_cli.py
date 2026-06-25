import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from embytools.cli import app
from embytools.commands.channels import NUMBER_TYPE
from embytools.envelope import write_export

runner = CliRunner()
BASE = "http://test"
FAV_PLUGIN = str(Path(__file__).parent.parent / "schemes" / "favorites_bands.py")


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
    res = runner.invoke(
        app,
        [
            "channels", "numbers", "generate", "favorites-bands", str(out),
            "--plugin", FAV_PLUGIN, "--opt", "user=Steve",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(out.read_text())["data"]
    nums = {d["Name"]: int(d["Number"]) for d in data}
    assert nums["CNN"] < 1000
    assert nums["Junk"] >= 1000


def test_generate_requires_plugin(cli_env, tmp_path):
    res = runner.invoke(
        app, ["channels", "numbers", "generate", "favorites-bands", str(tmp_path / "x.json")]
    )
    assert res.exit_code == 1
    assert "requires at least one --plugin" in res.output


def test_channels_numbers_schemes_lists_plugin():
    res = runner.invoke(app, ["channels", "numbers", "schemes", "--plugin", FAV_PLUGIN])
    assert res.exit_code == 0
    assert "favorites-bands" in res.output


def test_schemes_empty_without_plugin():
    # Relies on the autouse reset_schemes fixture: no scheme should leak in from
    # other tests that loaded plugins in this same process.
    res = runner.invoke(app, ["channels", "numbers", "schemes"])
    assert res.exit_code == 0
    assert "No schemes registered" in res.output


@respx.mock
def test_channels_numbers_generate_with_plugin(cli_env, tmp_path):
    plugin = tmp_path / "p.py"
    plugin.write_text(
        "from embytools.numbering import scheme, even_fill\n"
        "@scheme('alpha-test')\n"
        "def a(ctx):\n"
        "    names = sorted(c['Name'] for c in ctx.channels)\n"
        "    return even_fill(names, 1, 100)\n"
    )
    respx.get(f"{BASE}/LiveTv/Manage/Channels").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [{"Id": "1", "Name": "Zed"}, {"Id": "2", "Name": "Abc"}],
                "TotalRecordCount": 2,
            },
        )
    )
    out = tmp_path / "out.json"
    res = runner.invoke(
        app,
        ["channels", "numbers", "generate", "alpha-test", str(out), "--plugin", str(plugin)],
    )
    assert res.exit_code == 0
    data = json.loads(out.read_text())["data"]
    assert [d["Name"] for d in data] == ["Abc", "Zed"]  # plugin sorted them


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


@respx.mock
def test_channels_tags_list_cli(cli_env):
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "s"}])
    )
    respx.get(f"{BASE}/LiveTv/Channels").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [
                    {"Id": "1", "Name": "CNN", "TagItems": [{"Name": "News"}]},
                    {"Id": "2", "Name": "ESPN", "TagItems": [{"Name": "Sports"}, {"Name": "News"}]},
                ]
            },
        )
    )
    res = runner.invoke(app, ["channels", "tags", "list"])
    assert res.exit_code == 0
    assert "News" in res.output and "Sports" in res.output


@respx.mock
def test_channels_tags_add_dry_run_cli(cli_env):
    respx.get(f"{BASE}/Users").mock(
        return_value=httpx.Response(200, json=[{"Name": "Steve", "Id": "s"}])
    )
    respx.get(f"{BASE}/LiveTv/Channels").mock(
        return_value=httpx.Response(
            200, json={"Items": [{"Id": "1", "Name": "CNN", "TagItems": []}]}
        )
    )
    res = runner.invoke(app, ["channels", "tags", "add", "Fav", "CNN", "--dry-run"])
    assert res.exit_code == 0
    assert "+Fav" in res.output
    assert "Dry run" in res.output
