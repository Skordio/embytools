from ._resource import Resource


class LiveTvAPI(Resource):
    def favorite_channels(self, user_id: str) -> list[dict]:
        r = self._http.get(
            "/LiveTv/Channels",
            params={"UserId": user_id, "IsFavorite": "true"},
        )
        r.raise_for_status()
        return r.json().get("Items", [])
