"""Open a configured EmbyClient with friendly error handling.

Every command uses ``with emby_session() as emby:`` so config errors and HTTP
failures surface as clean messages instead of tracebacks.
"""

from contextlib import contextmanager

import typer

from .client import EmbyClient
from .config import ConfigError, load_config
from .errors import friendly_errors


@contextmanager
def emby_session():
    try:
        cfg = load_config()
    except ConfigError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    client = EmbyClient(cfg.base_url, cfg.api_key)
    try:
        with friendly_errors(cfg.base_url):
            yield client
    finally:
        client.close()
