from ._resource import Resource


class LiveTvAPI(Resource):
    def favorite_channels(self, user_id: str) -> list[dict]:
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "IsFavorite": "true"},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def manage_channels(self, limit: int = 5000) -> list[dict]:
        """All channels from the management endpoint.

        Unlike /LiveTv/Channels, this carries SortIndexNumber and ChannelNumber.
        Returned sorted by sort index.
        """
        r = self._http.get("/LiveTv/Manage/Channels", params={"Limit": limit})
        r.raise_for_status()
        items = r.json().get("Items", [])
        items.sort(key=lambda c: c.get("SortIndexNumber", 0))
        return items
