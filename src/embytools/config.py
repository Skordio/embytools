import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    base_url: str
    api_key: str


def load_config() -> Config:
    path = Path(os.environ.get("EMBYTOOLS_CONFIG", "config.toml"))
    if not path.exists():
        raise FileNotFoundError(
            f"No config at {path}. Copy config.example.toml to config.toml and fill it in."
        )
    data = tomllib.loads(path.read_text())
    server = data["server"]
    return Config(base_url=server["base_url"].rstrip("/"), api_key=server["api_key"])
