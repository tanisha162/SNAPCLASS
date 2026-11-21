"""Regression tests for the Supabase subjects round-trip (src/database/db.py).

Bug: the Supabase backend treated the subjects table as if it had the
columns the screens use ('name', 'section', 'total_students',
'total_classes'), but database_schema.sql defines subjects as
(id, teacher_id, subject_name, subject_code, join_code, created_at) -
no 'name', no 'section'. So in Supabase mode (the production mode when
secrets are configured):

* create_subject() inserted {'name': ..., 'section': ...} verbatim and
  PostgREST rejected the unknown columns, so 'Create Subject' failed
  every time;
* get_teacher_subjects() / get_all_subjects() returned raw rows, so the
  teacher screens crashed with KeyError on s['name'],
  sub['total_students'] / sub['total_classes'] and sub['section'];
* the nested 'subjects' dicts from get_student_subjects() and
  get_attendance_for_teacher() carried 'subject_name' instead of 'name'
  and no 'section', so the student dashboard and the Attendance Records
  tab crashed on sub['name'] / r['subjects']['name'] too.

The SQLite backend was already shaped to match the screens (see
test_db_sqlite.py); the Supabase backend never was. The Supabase client
is stubbed with a fake that enforces the real table columns on insert,
mimicking PostgREST's unknown-column rejection, and applies eq() filters
on select.

Run:  python -m unittest test_db_supabase_subjects -v
"""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TABLE_COLUMNS = {
    "subjects": {"id", "teacher_id", "subject_name", "subject_code",
                 "join_code", "created_at"},
    "enrollments": {"id", "student_id", "subject_id", "created_at"},
    "attendance": {"id", "subject_id", "student_id", "attendance_date",
                   "status", "created_at"},
}


class _FakeResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self._op = None
        self._payload = None
        self._filters = []
        self._count = None

    def select(self, *args, **kwargs):
        self._op = "select"
        self._count = kwargs.get("count")
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def execute(self):
        if self._op == "insert":
            rows = self._payload if isinstance(self._payload, list) else [self._payload]
            for row in rows:
                unknown = set(row) - TABLE_COLUMNS[self.table]
                if unknown:
                    raise Exception(
                        "Could not find the '%s' column of '%s' "
                        "in the schema cache" % (sorted(unknown)[0], self.table))
            stored = []
            for row in rows:
                new_row = dict(row)
                new_row.setdefault("id", self.client.next_id(self.table))
                self.client.tables[self.table].append(new_row)
                stored.append(dict(new_row))
            self.client.inserted.append((self.table, [dict(r) for r in rows]))
            return _FakeResponse(stored)
        rows = [dict(r) for r in self.client.tables[self.table]]
        for column, value in self._filters:
            # eq('subjects.teacher_id', ...) filters on the nested dict.
            def _lookup(row, column=column):
                current = row
                for part in column.split("."):
                    if not isinstance(current, dict):
                        return None
                    current = current.get(part)
                return current
            rows = [r for r in rows if _lookup(r) == value]
        count = len(rows) if self._count == "exact" else None
        return _FakeResponse(rows, count=count)


class _FakeClient:
    def __init__(self):
        self.tables = {name: [] for name in TABLE_COLUMNS}
        self.inserted = []
        self._ids = {name: 0 for name in TABLE_COLUMNS}

    def next_id(self, table):
        self._ids[table] += 1
        return self._ids[table]

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


class TestSupabaseSubjects(unittest.TestCase):
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
        self.client.tables["subjects"] = [
            {"id": 7, "teacher_id": 1, "subject_name": "Maths",
             "subject_code": "M101", "join_code": "M101",
             "created_at": "2026-11-18T10:00:00+00:00"},
            {"id": 8, "teacher_id": 1, "subject_name": "Physics",
             "subject_code": "P101", "join_code": "P101",
             "created_at": "2026-11-18T10:00:00+00:00"},
        ]
        self.client.tables["enrollments"] = [
            {"id": 1, "student_id": 3, "subject_id": 7},
            {"id": 2, "student_id": 4, "subject_id": 7},
            {"id": 3, "student_id": 3, "subject_id": 8},
        ]
        self.client.tables["attendance"] = [
            {"id": 1, "subject_id": 7, "student_id": 3,
             "attendance_date": "2026-11-18", "status": "present"},
            {"id": 2, "subject_id": 7, "student_id": 4,
             "attendance_date": "2026-11-18", "status": "present"},
            {"id": 3, "subject_id": 7, "student_id": 3,
             "attendance_date": "2026-11-19", "status": "present"},
        ]

    def test_create_subject_inserts_only_real_columns(self):
        """'name' and 'section' are not columns of the subjects table;
        the insert must use subject_name and send no unknown column."""
        result = self.db.create_subject("CS101", "Intro to CS", "A", 1)
        self.assertEqual(len(self.client.inserted), 1)
        table, rows = self.client.inserted[0]
        self.assertEqual(table, "subjects")
        self.assertEqual(rows[0], {
            "subject_code": "CS101", "subject_name": "Intro to CS",
            "teacher_id": 1, "join_code": "CS101"})
        # The returned record is shaped the way the screens expect.
        self.assertEqual(result[0]["name"], "Intro to CS")
        self.assertEqual(result[0]["section"], "A")
        self.assertEqual(result[0]["subject_code"], "CS101")
        self.assertIn("subject_id", result[0])

    def test_get_teacher_subjects_shape(self):
        """Take Attendance reads s['name']/s['subject_code']/s['subject_id'];
        Manage Subjects also reads total_students, total_classes, section."""
        subjects = self.db.get_teacher_subjects(teacher_id=1)
        self.assertEqual(len(subjects), 2)
        maths = subjects[0]
        self.assertEqual(maths["name"], "Maths")
        self.assertEqual(maths["subject_code"], "M101")
        self.assertEqual(maths["subject_id"], 7)
        self.assertEqual(maths["section"], None)
        self.assertEqual(maths["total_students"], 2)
        self.assertEqual(maths["total_classes"], 2)  # two distinct dates
        self.assertNotIn("id", maths)
        self.assertNotIn("subject_name", maths)
        physics = subjects[1]
        self.assertEqual(physics["total_students"], 1)
        self.assertEqual(physics["total_classes"], 0)

    def test_get_all_subjects_shape(self):
        subjects = self.db.get_all_subjects()
        self.assertEqual(len(subjects), 2)
        for sub in subjects:
            self.assertIn("name", sub)
            self.assertIn("subject_id", sub)
            self.assertIn("total_students", sub)
            self.assertIn("total_classes", sub)
            self.assertNotIn("subject_name", sub)

    def test_get_student_subjects_nested_shape(self):
        """The student dashboard reads sub['name'], sub['subject_code']
        and sub['section'] off the nested 'subjects' dict."""
        self.client.tables["enrollments"] = [
            {"id": 1, "student_id": 3, "subject_id": 7,
             "subjects": {"id": 7, "teacher_id": 1,
                          "subject_name": "Maths", "subject_code": "M101",
                          "join_code": "M101"}},
        ]
        subjects = self.db.get_student_subjects(student_id=3)
        self.assertEqual(len(subjects), 1)
        sub = subjects[0]["subjects"]
        self.assertEqual(sub["name"], "Maths")
        self.assertEqual(sub["subject_code"], "M101")
        self.assertEqual(sub["subject_id"], 7)
        self.assertEqual(sub["section"], None)
        self.assertNotIn("id", sub)
        self.assertNotIn("subject_name", sub)

    def test_get_subject_by_code_shape(self):
        """dialog_auto_enroll.py (share-link Quick Enrollment) reads
        subject['name'] and subject['subject_id']; the Supabase backend
        used to return the raw row ('subject_name', no 'section' or
        totals), so opening a shared join link crashed with KeyError
        in Supabase mode while the SQLite backend worked."""
        subject = self.db.get_subject_by_code("M101")
        self.assertIsNotNone(subject)
        self.assertEqual(subject["name"], "Maths")
        self.assertEqual(subject["subject_code"], "M101")
        self.assertEqual(subject["subject_id"], 7)
        self.assertEqual(subject["section"], None)
        self.assertEqual(subject["total_students"], 2)
        self.assertEqual(subject["total_classes"], 2)
        self.assertNotIn("id", subject)
        self.assertNotIn("subject_name", subject)
        self.assertIsNone(self.db.get_subject_by_code("NOPE"))

    def test_get_subject_total_classes_counts_held_sessions(self):
        """student_screen.py shows Total / Attended per subject. Only
        present students ever get an attendance row, so the dashboard
        used to count the student's own rows for 'Total' too - a student
        who missed sessions still showed Total == Attended (100%).
        Total must be the classes actually held for the subject.
        Fixture: subject 7 has rows on two distinct dates (student 3
        present on both, student 4 on one), subject 8 has none."""
        self.assertEqual(self.db.get_subject_total_classes(7), 2)
        self.assertEqual(self.db.get_subject_total_classes(8), 0)

    def test_get_attendance_for_teacher_nested_subject_name(self):
        """The records tab reads r['subjects']['name'] and
        r['subjects']['subject_code'] (and groups by r['timestamp'])."""
        self.client.tables["attendance"] = [
            {"id": 1, "subject_id": 7, "student_id": 3,
             "attendance_date": "2026-11-18", "status": "present",
             "created_at": "2026-11-18T10:00:00+00:00",
             "subjects": {"id": 7, "teacher_id": 1,
                          "subject_name": "Maths", "subject_code": "M101",
                          "join_code": "M101"}},
        ]
        records = self.db.get_attendance_for_teacher(teacher_id=1)
        self.assertEqual(len(records), 1)
        sub = records[0]["subjects"]
        self.assertEqual(sub["name"], "Maths")
        self.assertEqual(sub["subject_code"], "M101")
        self.assertEqual(sub["subject_id"], 7)
        self.assertEqual(records[0]["timestamp"], "2026-11-18T10:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
