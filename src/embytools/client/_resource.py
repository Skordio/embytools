import httpx


class Resource:
    """Base for resource namespaces. Holds the shared httpx client."""

    def __init__(self, http: httpx.Client):
        self._http = http
