from ._resource import Resource


class SessionsAPI(Resource):
    def list(self, active_within_seconds: int | None = None) -> list[dict]:
        params = {}
        if active_within_seconds is not None:
            params["ActiveWithinSeconds"] = active_within_seconds
        r = self._http.get("/Sessions", params=params)
        r.raise_for_status()
        return r.json()

    def send_message(
        self,
        session_id: str,
        text: str,
        header: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        params = {"Text": text}
        if header is not None:
            params["Header"] = header
        if timeout_ms is not None:
            params["TimeoutMs"] = timeout_ms
        r = self._http.post(f"/Sessions/{session_id}/Message", params=params)
        r.raise_for_status()

    def playstate(self, session_id: str, command: str) -> None:
        """Issue a playstate command (Stop, Pause, Unpause, ...) to a session."""
        r = self._http.post(f"/Sessions/{session_id}/Playing/{command}")
        r.raise_for_status()
