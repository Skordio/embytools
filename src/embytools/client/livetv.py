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

    def get_item(self, user_id: str, item_id: str) -> dict:
        """The full, editable item DTO (BaseItemDto)."""
        r = self._http.get(f"/Users/{user_id}/Items/{item_id}")
        r.raise_for_status()
        return r.json()

    def update_item(self, item: dict) -> None:
        """Write an item DTO back via the metadata update endpoint."""
        r = self._http.post(f"/Items/{item['Id']}", json=item)
        r.raise_for_status()

    def set_channel_number(self, user_id: str, item_id: str, number: str) -> None:
        """Set (or clear) a channel's number via item metadata.

        Pass an empty string to clear — Emby's update endpoint ignores ``null``
        (no change) and only clears the field on an empty string. ``user_id`` is
        any user that can see the channel; it's only the context for fetching the
        editable DTO (the write itself is admin-authed via the API key).
        """
        item = self.get_item(user_id, item_id)
        item["Number"] = number
        item["ChannelNumber"] = number
        self.update_item(item)
