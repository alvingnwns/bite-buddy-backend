from app.services import activity_service


class FakeInsertQuery:
    def __init__(self):
        self.row = None

    def insert(self, row):
        self.row = row
        return self

    def execute(self):
        return self


class FakeActivityClient:
    def __init__(self):
        self.query = FakeInsertQuery()

    def table(self, name):
        assert name == "activity_logs"
        return self.query


def test_activity_uses_utc_timestamp_and_wib_month(monkeypatch):
    client = FakeActivityClient()
    monkeypatch.setattr(activity_service, "get_supabase_service_client", lambda: client)

    activity_service.record_activity(
        actor_id="00000000-0000-0000-0000-000000000010",
        actor_role="doctor",
        action="auth.login",
        target_type="session",
        request_id="req-test",
    )

    row = client.query.row
    assert row["created_at"].endswith("+00:00")
    assert len(row["wib_month"]) == 7
    assert row["metadata"]["request_id"] == "req-test"
    assert row["metadata"]["outcome"] == "success"
