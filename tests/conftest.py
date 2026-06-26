import pytest

from embytools import numbering
from embytools.livetv import tagging


@pytest.fixture(autouse=True)
def reset_schemes():
    """Isolate the global scheme registry so plugin loads don't leak across tests."""
    saved = dict(numbering.SCHEMES)
    try:
        yield
    finally:
        numbering.SCHEMES.clear()
        numbering.SCHEMES.update(saved)


@pytest.fixture(autouse=True)
def reset_tag_schemes():
    """Isolate the global tag-scheme registry so plugin loads don't leak across tests."""
    saved = dict(tagging.TAG_SCHEMES)
    try:
        yield
    finally:
        tagging.TAG_SCHEMES.clear()
        tagging.TAG_SCHEMES.update(saved)


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """A temp config.toml wired via EMBYTOOLS_CONFIG for CLI-level tests."""
    cfg = tmp_path / "config.toml"
    cfg.write_text('[server]\nbase_url = "http://test"\napi_key = "k"\n')
    monkeypatch.setenv("EMBYTOOLS_CONFIG", str(cfg))
    return cfg
