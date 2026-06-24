import pytest

from embytools.config import ConfigError, load_config


def _set_config(monkeypatch, tmp_path, text: str):
    path = tmp_path / "config.toml"
    path.write_text(text)
    monkeypatch.setenv("EMBYTOOLS_CONFIG", str(path))
    return path


def test_valid_config(monkeypatch, tmp_path):
    _set_config(
        monkeypatch,
        tmp_path,
        '[server]\nbase_url = "http://host:8096/"\napi_key = "abc"\n',
    )
    cfg = load_config()
    assert cfg.base_url == "http://host:8096"  # trailing slash stripped
    assert cfg.api_key == "abc"


def test_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBYTOOLS_CONFIG", str(tmp_path / "nope.toml"))
    with pytest.raises(ConfigError):
        load_config()


def test_invalid_toml(monkeypatch, tmp_path):
    _set_config(monkeypatch, tmp_path, "this is = = not toml\n")
    with pytest.raises(ConfigError):
        load_config()


def test_missing_server_section(monkeypatch, tmp_path):
    _set_config(monkeypatch, tmp_path, 'other = 1\n')
    with pytest.raises(ConfigError):
        load_config()


def test_missing_key(monkeypatch, tmp_path):
    _set_config(monkeypatch, tmp_path, '[server]\nbase_url = "http://h"\n')
    with pytest.raises(ConfigError):
        load_config()
