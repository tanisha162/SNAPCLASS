"""Regression tests for the Supabase attendance round-trip (src/database/db.py).

Bug: the teacher and voice flows build attendance logs as
{'student_id', 'subject_id', 'timestamp'}, but the Supabase backend
inserted those dicts verbatim and the attendance table (database_schema.sql)
has no 'timestamp' column - it has attendance_date / status / created_at.
PostgREST rejects inserts carrying an unknown column, so 'Confirm & Save'
failed every time in Supabase mode (local SQLite mode was fine: its
create_attendance maps 'timestamp' to attendance_date). The same backend
also never returned a 'timestamp' key from get_attendance_for_teacher,
while teacher_tab_attendance_records groups and displays by
r.get('timestamp'), so every session showed "N'A" and all sessions merged
into one row.

The Supabase client is stubbed with a fake that enforces the real table's
columns on insert, mimicking PostgREST's unknown-column rejection.

Run:  python -m unittest test_db_supabase_attendance -v
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))

ATTENDANCE_COLUMNS = {"id", "subject_id", "student_id", "attendance_date",
                      "status", "created_at"}


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self._op = None
        self._payload = None

    def select(self, *args, **kwargs):
        self._op = "select"
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        if self._op == "insert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            for row in rows:
                unknown = set(row) - ATTENDANCE_COLUMNS
                if unknown:
                    raise Exception(
                        "Could not find the '%s' column of 'attendance' "
                        "in the schema cache" % sorted(unknown)[0])
            self.client.inserted.append((self.table, rows))
            return _FakeResponse(rows)
        return _FakeResponse(self.client.select_rows)


class _FakeClient:
    def __init__(self):
        self.inserted = []
        self.select_rows = []

    def table(self, name):
        return _FakeQuery(self, name)


def _install_stubs(fake_client):
    """Stub streamlit + supabase before importing src.database.db."""
    st = types.ModuleType("streamlit")
    st.secrets = {"SUPABASE_URL": "https://example.supabase.co",
                  "SUPABASE_KEY": "test-key"}
    st.warning = lambda *a, **k: None
    st.info = lambda *a, **k: None
    sys.modules["streamlit"] = st

    supabase_mod = types.ModuleType("supabase")
    supabase_mod.create_client = lambda url, key: fake_client
    supabase_mod.Client = object
    sys.modules["supabase"] = supabase_mod


class TestSupabaseAttendance(unittest.TestCase):
    def setUp(self):
        self.client = _FakeClient()
        _install_stubs(self.client)
        # Fresh import each time so the DB_TYPE branch is re-evaluated.
        for mod in [m for m in list(sys.modules)
                    if m.startswith("src.database")]:
            del sys.modules[mod]
        from src.database import db
        self.db = db
        self.assertEqual(db.DB_TYPE, "supabase")

    def test_create_attendance_teacher_flow_logs(self):
        """Logs built by the teacher/voice flows ('timestamp' key) insert
        as real columns instead of failing on the unknown column."""
        logs = [
            {"student_id": 3, "subject_id": 7,
             "timestamp": "2026-11-18T10:00:00"},
            {"student_id": 4, "subject_id": 7,
             "timestamp": "2026-11-18T10:00:00"},
        ]
        result = self.db.create_attendance(logs)
        self.assertEqual(len(self.client.inserted), 1)
        table, rows = self.client.inserted[0]
        self.assertEqual(table, "attendance")
        for row in rows:
            self.assertEqual(set(row), {"subject_id", "student_id",
                                        "attendance_date", "status"})
            self.assertEqual(row["attendance_date"], "2026-11-18")
            self.assertEqual(row["status"], "present")
        self.assertEqual(len(result), 2)

    def test_create_attendance_keeps_explicit_date_and_status(self):
        logs = [{"student_id": 3, "subject_id": 7,
                 "attendance_date": "2026-11-17", "status": "absent"}]
        self.db.create_attendance(logs)
        _, rows = self.client.inserted[0]
        self.assertEqual(rows[0]["attendance_date"], "2026-11-17")
        self.assertEqual(rows[0]["status"], "absent")

    def test_create_attendance_empty_logs_inserts_nothing(self):
        self.assertEqual(self.db.create_attendance([]), [])
        self.assertEqual(self.client.inserted, [])

    def test_get_attendance_for_teacher_exposes_timestamp(self):
        """The records tab groups by r.get('timestamp'); it must be present
        (sourced from created_at, as the SQLite backend does)."""
        self.client.select_rows = [{
            "id": 1, "subject_id": 7, "student_id": 3,
            "attendance_date": "2026-11-18", "status": "present",
            "created_at": "2026-11-18T10:00:00+00:00",
            "subjects": {"id": 7, "name": "Maths", "subject_code": "M101"},
        }]
        records = self.db.get_attendance_for_teacher(teacher_id=1)
        self.assertEqual(records[0]["timestamp"], "2026-11-18T10:00:00+00:00")
        self.assertEqual(records[0]["subjects"]["subject_id"], 7)
        self.assertNotIn("id", records[0]["subjects"])


if __name__ == "__main__":
    unittest.main()
