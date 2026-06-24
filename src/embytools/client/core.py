import httpx

from .favorites import FavoritesAPI
from .livetv import LiveTvAPI
from .sessions import SessionsAPI
from .users import UsersAPI


class EmbyClient:
    """Entry point to the Emby REST API.

    Holds one shared httpx client and exposes resource namespaces:
    ``emby.users``, ``emby.livetv``, ``emby.favorites``, ``emby.sessions``.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0):
        self.base_url = base_url
        self._http = httpx.Client(
            base_url=base_url,
            headers={"X-Emby-Token": api_key},
            timeout=timeout,
        )
        self.users = UsersAPI(self._http)
        self.livetv = LiveTvAPI(self._http)
        self.favorites = FavoritesAPI(self._http)
        self.sessions = SessionsAPI(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
