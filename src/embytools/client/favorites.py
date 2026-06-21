from ._resource import Resource


class FavoritesAPI(Resource):
    def add(self, user_id: str, item_id: str) -> None:
        r = self._http.post(f"/Users/{user_id}/FavoriteItems/{item_id}")
        r.raise_for_status()

    def remove(self, user_id: str, item_id: str) -> None:
        r = self._http.delete(f"/Users/{user_id}/FavoriteItems/{item_id}")
        r.raise_for_status()
