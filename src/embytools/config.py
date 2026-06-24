import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """A config file that is missing, unreadable, or incomplete."""


@dataclass
class Config:
    base_url: str
    api_key: str


def load_config() -> Config:
    path = Path(os.environ.get("EMBYTOOLS_CONFIG", "config.toml"))
    if not path.exists():
        raise ConfigError(
            f"No config at {path}. Copy config.example.toml to config.toml and fill it in."
        )
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}")
    try:
        server = data["server"]
        return Config(base_url=server["base_url"].rstrip("/"), api_key=server["api_key"])
    except (KeyError, TypeError, AttributeError):
        raise ConfigError(
            f"{path} is missing a [server] section with base_url and api_key. "
            "See config.example.toml."
        )
