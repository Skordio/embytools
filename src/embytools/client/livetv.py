import sys

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
        payload = r.json()
        items = payload.get("Items", [])
        total = payload.get("TotalRecordCount", len(items))
        if total > len(items):
            print(
                f"Warning: showing {len(items)} of {total} channels "
                f"(raise the limit to see all).",
                file=sys.stderr,
            )
        items.sort(key=lambda c: c.get("SortIndexNumber") or 0)
        return items
