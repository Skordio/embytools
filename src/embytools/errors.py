"""Map raw HTTP/connection failures to actionable CLI messages."""

from contextlib import contextmanager

import httpx
import typer


@contextmanager
def friendly_errors(base_url: str):
    try:
        yield
    except httpx.ConnectError:
        typer.echo(
            f"Could not reach Emby at {base_url}. Is the server up and the URL correct?",
            err=True,
        )
        raise typer.Exit(1)
    except httpx.TimeoutException:
        typer.echo(f"Timed out talking to Emby at {base_url}.", err=True)
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 401:
            typer.echo("Unauthorized (401). Check the api_key in config.toml.", err=True)
        elif code == 403:
            typer.echo("Forbidden (403). This key lacks permission for that action.", err=True)
        elif code == 404:
            typer.echo(f"Not found (404): {e.request.url}", err=True)
        else:
            typer.echo(f"Emby returned {code}: {e.response.text[:200]}", err=True)
        raise typer.Exit(1)
