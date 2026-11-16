"""Regression tests for the SQLite fallback backend (src/database/db_sqlite.py).

The screens in src/screens/ and src/components/ expect the same record
shapes the Supabase backend returns (teacher_id / student_id / subject_id,
subject 'name', nested 'subjects' dicts). The SQLite backend used to return
raw 'id' / 'subject_name' shapes, dropped the 'section' argument, and never
created its tables, so the teacher/student dashboards crashed with KeyError
(and confirming attendance failed) in local mode.

Run:  python -m unittest test_db_sqlite -v
Requires: bcrypt (in requirements.txt).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.database import db_sqlite as db


class TestSqliteBackendShapes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self._tmp.name) / "snapclass.db"
        db.init_db()
        db.create_teacher("t1", "pw123456", "Ananya")
        self.teacher = db.teacher_login("t1", "pw123456")
        db.create_student("s1", "pw123456", "Hamza", "R01")
        self.student = db.student_login("s1", "pw123456")
        db.create_subject("CS101", "Intro to CS", "A", self.teacher["teacher_id"])
        self.subject = db.get_teacher_subjects(self.teacher["teacher_id"])[0]

    def tearDown(self):
        self._tmp.cleanup()

    def test_teacher_login_returns_teacher_id(self):
        # teacher_screen.py reads teacher_data['teacher_id']
        self.assertIn("teacher_id", self.teacher)
        self.assertNotIn("id", self.teacher)

    def test_student_login_and_list_return_student_id(self):
        # student_screen.py reads student_data['student_id'] and
        # s['student_id'] from get_all_students()
        self.assertIn("student_id", self.student)
        self.assertNotIn("id", self.student)
        self.assertEqual(
            [s["student_id"] for s in db.get_all_students()],
            [self.student["student_id"]],
        )

    def test_teacher_subjects_have_screen_keys(self):
        # teacher_screen.py reads s['name'], s['subject_id'] (Take Attendance)
        # and sub['section'], sub['total_students'], sub['total_classes']
        # (Manage Subjects)
        self.assertEqual(self.subject["name"], "Intro to CS")
        self.assertEqual(self.subject["subject_code"], "CS101")
        self.assertEqual(self.subject["section"], "A")
        self.assertEqual(self.subject["total_students"], 0)
        self.assertEqual(self.subject["total_classes"], 0)

    def test_totals_reflect_enrollments_and_classes(self):
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        db.create_attendance([{
            "student_id": self.student["student_id"],
            "subject_id": self.subject["subject_id"],
            "attendance_date": "2026-11-16",
            "status": "present",
        }])
        subject = db.get_teacher_subjects(self.teacher["teacher_id"])[0]
        self.assertEqual(subject["total_students"], 1)
        self.assertEqual(subject["total_classes"], 1)

    def test_student_subjects_are_nested(self):
        # student_screen.py reads sub_node['subjects']['subject_id']
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        nodes = db.get_student_subjects(self.student["student_id"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(
            nodes[0]["subjects"]["subject_id"], self.subject["subject_id"])
        self.assertEqual(nodes[0]["subjects"]["name"], "Intro to CS")

    def test_create_attendance_accepts_timestamp_key(self):
        # teacher_screen.py builds logs with a 'timestamp' key, not
        # 'attendance_date'; previously this raised IntegrityError
        # (NOT NULL constraint failed: attendance.attendance_date).
        db.create_attendance([{
            "student_id": self.student["student_id"],
            "subject_id": self.subject["subject_id"],
            "timestamp": "2026-11-16T10:00:00",
            "status": "present",
        }])
        logs = db.get_student_attendance(self.student["student_id"])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["attendance_date"], "2026-11-16")

    def test_attendance_for_teacher_has_nested_subjects_and_timestamp(self):
        # teacher_screen.py reads r['subjects']['name'] and r.get('timestamp')
        db.create_attendance([{
            "student_id": self.student["student_id"],
            "subject_id": self.subject["subject_id"],
            "attendance_date": "2026-11-16",
            "status": "present",
        }])
        records = db.get_attendance_for_teacher(self.teacher["teacher_id"])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["subjects"]["name"], "Intro to CS")
        self.assertEqual(
            records[0]["subjects"]["subject_code"], "CS101")
        self.assertTrue(records[0]["timestamp"])

    def test_get_all_subjects_shape(self):
        # check_subjects.py reads .get('name') / .get('section') /
        # .get('subject_id')
        subjects = db.get_all_subjects()
        self.assertEqual(len(subjects), 1)
        self.assertEqual(subjects[0]["name"], "Intro to CS")
        self.assertEqual(subjects[0]["section"], "A")


if __name__ == "__main__":
    unittest.main()
