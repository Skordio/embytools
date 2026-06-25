"""In-memory fakes for unit-testing command helpers without HTTP."""


class FakeFavorites:
    def __init__(self, fail_on_add=None):
        self.added = []
        self.removed = []
        self.fail_on_add = fail_on_add

    def add(self, user_id, item_id):
        if item_id == self.fail_on_add:
            raise RuntimeError("simulated failure")
        self.added.append((user_id, item_id))

    def remove(self, user_id, item_id):
        self.removed.append((user_id, item_id))


class FakeLiveTv:
    def __init__(
        self, favorites_by_user=None, manage=None, fail_on_set=None, tagged=None, fail_on_tag=None
    ):
        self.favorites_by_user = favorites_by_user or {}
        self.manage = manage or []
        self.fail_on_set = fail_on_set
        self.set_calls = []
        self.tagged = tagged or []
        self.fail_on_tag = fail_on_tag
        self.tag_calls = []

    def favorite_channels(self, user_id):
        return list(self.favorites_by_user.get(user_id, []))

    def manage_channels(self, limit=5000):
        return list(self.manage), len(self.manage)

    def set_channel_number(self, user_id, item_id, number):
        if item_id == self.fail_on_set:
            raise RuntimeError("simulated failure")
        self.set_calls.append((item_id, number))
        for c in self.manage:
            if c["Id"] == item_id:
                c["ChannelNumber"] = number

    # tags
    def channels_with_tags(self, user_id, limit=5000):
        return self.tagged

    def channels_by_tag(self, user_id, tag):
        return [c for c in self.tagged if tag in [t["Name"] for t in (c.get("TagItems") or [])]]

    def add_tags(self, item_id, tags):
        if item_id == self.fail_on_tag:
            raise RuntimeError("simulated failure")
        self.tag_calls.append(("add", item_id, list(tags)))
        for c in self.tagged:
            if c["Id"] == item_id:
                names = {t["Name"] for t in (c.get("TagItems") or [])} | set(tags)
                c["TagItems"] = [{"Name": n} for n in names]

    def remove_tags(self, item_id, tags):
        if item_id == self.fail_on_tag:
            raise RuntimeError("simulated failure")
        self.tag_calls.append(("remove", item_id, list(tags)))
        for c in self.tagged:
            if c["Id"] == item_id:
                names = {t["Name"] for t in (c.get("TagItems") or [])} - set(tags)
                c["TagItems"] = [{"Name": n} for n in names]


class FakeUsers:
    def __init__(self, users=None):
        self.users = users or []

    def list(self):
        return list(self.users)

    def find(self, name):
        for u in self.users:
            if u["Name"].lower() == name.lower():
                return u
        return None


class FakeSessions:
    def __init__(self, sessions=None):
        self.sessions = sessions or []
        self.messages = []
        self.playstates = []

    def list(self, active_within_seconds=None):
        return list(self.sessions)

    def send_message(self, session_id, text, header=None, timeout_ms=None):
        self.messages.append((session_id, text, header, timeout_ms))

    def playstate(self, session_id, command):
        self.playstates.append((session_id, command))


class FakeEmby:
    base_url = "http://test"

    def __init__(
        self,
        favorites_by_user=None,
        users=None,
        sessions=None,
        fail_on_add=None,
        manage=None,
        fail_on_set=None,
        tagged=None,
        fail_on_tag=None,
    ):
        self.favorites = FakeFavorites(fail_on_add)
        self.livetv = FakeLiveTv(favorites_by_user, manage, fail_on_set, tagged, fail_on_tag)
        self.users = FakeUsers(users)
        self.sessions = FakeSessions(sessions)
