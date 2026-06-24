import pytest


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """A temp config.toml wired via EMBYTOOLS_CONFIG for CLI-level tests."""
    cfg = tmp_path / "config.toml"
    cfg.write_text('[server]\nbase_url = "http://test"\napi_key = "k"\n')
    monkeypatch.setenv("EMBYTOOLS_CONFIG", str(cfg))
    return cfg
