from ._resource import Resource

# Upper bound for "give me every channel" reads. Sent explicitly on every
# channel list so the result never silently falls back to the server's default
# page size. Comfortably above any realistic Live TV lineup.
CHANNEL_LIMIT = 100000


class LiveTvAPI(Resource):
    def favorite_channels(self, user_id: str, limit: int = CHANNEL_LIMIT) -> list[dict]:
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "IsFavorite": "true", "Limit": limit},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def all_channels(self, user_id: str, limit: int = CHANNEL_LIMIT) -> list[dict]:
        """Every Live TV channel visible to a user (Id + Name).

        Used to resolve channel *names* to the server's current ids — favorites
        are restored by name, not by the (regenerable) ids saved in an export.
        """
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "Limit": limit},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def manage_channels(self, limit: int = CHANNEL_LIMIT) -> tuple[list[dict], int]:
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

    def set_channel_sort_index(self, item_id: str, management_id: str, new_index: int) -> None:
        """Move a channel to ``new_index`` in the manual sort order.

        Drives Emby's "Default Channel Order", which follows each channel's
        SortIndexNumber rather than its channel number. Insert-and-shift
        semantics: placing a channel at an index shifts the ones at/after it, so
        writing the desired order front-to-back (0, 1, 2, …) lands every channel
        correctly. ``management_id`` comes from the manage-channels entry.
        """
        r = self._http.post(
            f"/LiveTv/Manage/Channels/{item_id}/SortIndex",
            json={"Id": item_id, "ManagementId": management_id, "NewIndex": new_index},
        )
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

    # --- Tags ---
    def channels_with_tags(self, user_id: str, limit: int = CHANNEL_LIMIT) -> list[dict]:
        """All channels with their tags (``TagItems``), one request."""
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "Fields": "Tags", "Limit": limit},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def channels_by_tag(self, user_id: str, tag: str, limit: int = CHANNEL_LIMIT) -> list[dict]:
        """Channels that carry ``tag``."""
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "Tags": tag, "Fields": "Tags", "Limit": limit},
        )
        r.raise_for_status()
        return r.json().get("Items", [])

    def add_tags(self, item_id: str, tags: list[str]) -> None:
        r = self._http.post(
            f"/Items/{item_id}/Tags/Add",
            json={"Tags": [{"Name": t} for t in tags]},
        )
        r.raise_for_status()

    def remove_tags(self, item_id: str, tags: list[str]) -> None:
        r = self._http.post(
            f"/Items/{item_id}/Tags/Delete",
            json={"Tags": [{"Name": t} for t in tags]},
        )
        r.raise_for_status()
