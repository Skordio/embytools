import typer

from .commands.channels import channels_app
from .commands.users import users_app

app = typer.Typer(help="Tools for managing my Emby server.")
app.add_typer(users_app, name="users")
app.add_typer(channels_app, name="channels")


if __name__ == "__main__":
    app()
