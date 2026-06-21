from ._resource import Resource


class UsersAPI(Resource):
    def list(self) -> list[dict]:
        r = self._http.get("/Users")
        r.raise_for_status()
        return r.json()

    def find(self, name: str) -> dict | None:
        for user in self.list():
            if user.get("Name", "").lower() == name.lower():
                return user
        return None
