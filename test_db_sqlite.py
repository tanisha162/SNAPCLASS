"""Regression tests for the SQLite fallback backend (src/database/db_sqlite.py).

The screens in src/screens/ and src/components/ expect the same record
shapes the Supabase backend returns (teacher_id / student_id / subject_id,
subject 'name', nested 'subjects' dicts). The SQLite backend used to return
raw 'id' / 'subject_name' shapes, dropped the 'section' argument, and never
created its tables, so the teacher/student dashboards crashed with KeyError
(and confirming attendance failed) in local mode. The attendance and enroll
flows also queried a 'subject_students' table directly through the Supabase
client; that table does not exist (enrollments live in 'enrollments') and the
client is None in local mode, so Run Face Analysis and enrolling crashed too.
FaceID registration also crashed: student_screen.py calls
create_student(name, face_embedding=..., voice_embedding=...), but the
backends only accepted (username, password, name, roll_number) and stored
no embedding anywhere, so a new student could never be recognised.

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
        # setUp points db.DB_PATH at the temp dir; restore the module
        # default so a later import of src.database.db (which runs
        # init_db() at import time) does not point at the deleted dir.
        db.DB_PATH = Path(db.__file__).parent / "snapclass.db"

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

    def test_get_enrolled_students_nested_shape(self):
        # teacher_screen.py (Take Attendance) and dialog_voice_attendance.py
        # used to query a 'subject_students' table directly through the
        # Supabase client; that table does not exist (enrollments live in
        # 'enrollments') and the client is None in local mode, so Run Face
        # Analysis crashed with AttributeError every time.
        db.create_student("s2", "pw123456", "Meera", "R02")
        student2 = db.student_login("s2", "pw123456")
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        db.enroll_student_to_subject(
            student2["student_id"], self.subject["subject_id"])
        nodes = db.get_enrolled_students(self.subject["subject_id"])
        self.assertEqual(len(nodes), 2)
        by_id = {n["students"]["student_id"]: n["students"] for n in nodes}
        self.assertEqual(by_id[self.student["student_id"]]["name"], "Hamza")
        self.assertEqual(by_id[student2["student_id"]]["name"], "Meera")
        # A subject with no enrollments returns [] (not a crash).
        db.create_subject("CS102", "Data Structures", "B",
                          self.teacher["teacher_id"])
        empty = db.get_teacher_subjects(self.teacher["teacher_id"])
        empty_id = [s for s in empty
                    if s["subject_code"] == "CS102"][0]["subject_id"]
        self.assertEqual(db.get_enrolled_students(empty_id), [])

    def test_is_student_enrolled(self):
        # dialog_enroll.py / dialog_auto_enroll.py used the same broken
        # 'subject_students' query for their already-enrolled check.
        self.assertFalse(db.is_student_enrolled(
            self.student["student_id"], self.subject["subject_id"]))
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        self.assertTrue(db.is_student_enrolled(
            self.student["student_id"], self.subject["subject_id"]))

    def test_get_subject_by_code(self):
        # The enroll dialogs used to look subjects up through the Supabase
        # client directly (and one selected a non-existent 'subject_id'
        # column), so enrolling crashed in local mode.
        subject = db.get_subject_by_code("CS101")
        self.assertIsNotNone(subject)
        self.assertEqual(subject["subject_id"], self.subject["subject_id"])
        self.assertEqual(subject["name"], "Intro to CS")
        self.assertIsNone(db.get_subject_by_code("NOPE404"))

    def test_subject_total_classes_counts_held_sessions(self):
        # student_screen.py shows Total / Attended per subject. Only
        # present students ever get an attendance row, so the dashboard
        # used to count the student's own rows for 'Total' too - a student
        # who missed sessions still showed Total == Attended (100%).
        # Total must be the classes actually held for the subject.
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        db.create_student("s2", "pw123456", "Meera", "R02")
        student2 = db.student_login("s2", "pw123456")
        db.enroll_student_to_subject(
            student2["student_id"], self.subject["subject_id"])
        sid = self.subject["subject_id"]
        # 3 sessions; the first student attends 2 of them.
        for date, present in [("2026-11-16", [self.student, student2]),
                              ("2026-11-17", [student2]),
                              ("2026-11-18", [self.student, student2])]:
            db.create_attendance([{
                "student_id": st["student_id"], "subject_id": sid,
                "attendance_date": date, "status": "present",
            } for st in present])
        self.assertEqual(db.get_subject_total_classes(sid), 3)
        # Same date logged for two students counts as one class.
        self.assertEqual(
            db.get_teacher_subjects(
                self.teacher["teacher_id"])[0]["total_classes"], 3)
        # Dashboard computation (student_screen.py): total from the
        # subject, attended from the student's own rows.
        logs = db.get_student_attendance(self.student["student_id"])
        total = db.get_subject_total_classes(sid)
        attended = len([log for log in logs
                        if log["subject_id"] == sid])
        self.assertEqual((total, attended), (3, 2))
        # A subject with no sessions held reports 0, not a crash.
        db.create_subject("CS102", "Data Structures", "B",
                          self.teacher["teacher_id"])
        empty_id = [s for s in db.get_teacher_subjects(
            self.teacher["teacher_id"])
            if s["subject_code"] == "CS102"][0]["subject_id"]
        self.assertEqual(db.get_subject_total_classes(empty_id), 0)

    def test_create_attendance_dedupes_same_day_retake(self):
        # Re-taking attendance for the same subject on the same day (a
        # second photo batch, or a re-run after a mistake) used to insert
        # a second row for every present student, so the student
        # dashboard counted them twice and showed Attended > Total
        # ("Attended 2 / Total 1"). One row per student/subject/date.
        db.enroll_student_to_subject(
            self.student["student_id"], self.subject["subject_id"])
        sid = self.subject["subject_id"]
        log = {"student_id": self.student["student_id"],
               "subject_id": sid, "status": "present"}
        # Two sessions on the same day, as the teacher flow sends them
        # (timestamp key), plus the same row twice in one batch.
        inserted = db.create_attendance([
            {**log, "timestamp": "2026-11-22T10:00:00"},
            {**log, "timestamp": "2026-11-22T14:30:00"},
            {**log, "timestamp": "2026-11-22T14:30:00"},
        ])
        self.assertEqual(len(inserted), 1)
        logs = db.get_student_attendance(self.student["student_id"])
        self.assertEqual(len(logs), 1)
        self.assertEqual(db.get_subject_total_classes(sid), 1)
        # A genuinely different day still logs a second class.
        db.create_attendance([{**log, "attendance_date": "2026-11-23"}])
        logs = db.get_student_attendance(self.student["student_id"])
        self.assertEqual(len(logs), 2)
        self.assertEqual(db.get_subject_total_classes(sid), 2)
        # Dashboard computation (student_screen.py): attended counts
        # distinct dates, so even pre-existing duplicate rows cannot
        # push Attended past Total.
        attended = len({l["attendance_date"] for l in logs
                        if l["subject_id"] == sid})
        self.assertEqual(
            (db.get_subject_total_classes(sid), attended), (2, 2))

    def test_face_registration_call_shape(self):
        # student_screen.py registers a new student with exactly this call:
        # create_student(new_name, face_embedding=face_emb,
        # voice_embedding=voice_emb). create_student() used to take only
        # (username, password, name, roll_number), so registration crashed
        # with TypeError every time and no embedding was ever stored, which
        # also meant the face pipeline could never recognise the student.
        embedding = [0.1] * 128
        created = db.create_student(
            "Aarav Sharma", face_embedding=embedding, voice_embedding=None)
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["name"], "Aarav Sharma")
        students = db.get_all_students()
        registered = next(
            s for s in students if s["student_id"] == created[0]["student_id"])
        # face_pipeline.get_trained_model() reads student['face_embedding']
        # and feeds it to np.array(); it must come back as a list.
        self.assertEqual(registered["face_embedding"], embedding)
        self.assertIsNone(registered["voice_embedding"])
        # A face-only account has a random password nobody knows, so
        # password login must fail for it.
        self.assertIsNone(db.student_login("Aarav Sharma", "password"))
        self.assertIsNone(db.student_login("Aarav Sharma", ""))

    def test_embedding_columns_migrated_for_legacy_db(self):
        # Databases created before the embedding columns existed must gain
        # them on init_db() instead of failing the registration insert.
        import sqlite3
        legacy_dir = tempfile.TemporaryDirectory()
        self.addCleanup(legacy_dir.cleanup)
        try:
            db.DB_PATH = Path(legacy_dir.name) / "snapclass.db"
            conn = sqlite3.connect(db.DB_PATH)
            conn.execute('''CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                roll_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()
            conn.close()
            db.init_db()
            created = db.create_student(
                "Legacy Student", face_embedding=[0.2] * 128)
            self.assertEqual(len(created), 1)
            self.assertEqual(
                db.get_all_students()[0]["face_embedding"], [0.2] * 128)
        finally:
            # Restore the module-default DB path: the setUp temp dir is
            # deleted by tearDown, so restoring to it would leave later
            # imports of src.database.db (which runs init_db() at import
            # time) pointing at a deleted directory.
            db.DB_PATH = Path(db.__file__).parent / "snapclass.db"


if __name__ == "__main__":
    unittest.main()
