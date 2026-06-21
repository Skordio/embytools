import typer

from ..output import print_json, print_table
from ..session import emby_session

users_app = typer.Typer(help="User commands.")


@users_app.command("list")
def users_list(as_json: bool = typer.Option(False, "--json", help="Emit JSON.")):
    """List all users and their IDs."""
    with emby_session() as emby:
        users = emby.users.list()
        rows = [{"Name": u["Name"], "Id": u["Id"]} for u in users]
        if as_json:
            print_json(rows)
        else:
            print_table(rows, [("Name", 20), ("Id", 0)])
