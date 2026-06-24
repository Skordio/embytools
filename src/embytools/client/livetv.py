from ._resource import Resource


class LiveTvAPI(Resource):
    def favorite_channels(self, user_id: str) -> list[dict]:
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "IsFavorite": "true"},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def manage_channels(self, limit: int = 5000) -> tuple[list[dict], int]:
        """All channels from the management endpoint, sorted by sort index.

        Unlike /LiveTv/Channels, this carries SortIndexNumber and ChannelNumber.
        Returns ``(items, total)`` where ``total`` is the server's full count, so
        the caller can tell when the result was truncated by ``limit``.
        """
        r = self._http.get("/LiveTv/Manage/Channels", params={"Limit": limit})
        r.raise_for_status()
        payload = r.json()
        items = payload.get("Items", [])
        total = payload.get("TotalRecordCount", len(items))
        items.sort(key=lambda c: c.get("SortIndexNumber") or 0)
        return items, total
