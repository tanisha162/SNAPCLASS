"""Regression tests for the teacher Attendance Records tab.

Bug: the session summary computed Total_Count as ('count', 'count') over
the attendance rows, but rows only exist for present students, so Total
always equalled Present and every session showed 100% - e.g. "✅ 1 /1
Students" for a session where only 1 of 2 enrolled students was present.
Total must be the number of students enrolled in the subject.

The screens need Streamlit plus the heavy face/voice deps (dlib, sklearn),
none of which is required to aggregate the records, so this test stubs
those modules and drives the tab with a fake `st` that records the
dataframe it is handed.

Run:  PYTHONDONTWRITEBYTECODE=1 python -m unittest test_teacher_attendance_records -v
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))


class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _SessionState(dict):
    """dict that also allows attribute access, like Streamlit's session_state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value


class FakeSt:
    """Minimal stand-in for the `streamlit` module used by the screens."""

    def __init__(self):
        self.session_state = _SessionState(
            {"teacher_data": {"teacher_id": 1, "name": "Ananya"}})
        self.dataframes = []

    def columns(self, n, **kw):
        if isinstance(n, int):
            return [_Ctx() for _ in range(n)]
        return [_Ctx() for _ in n]

    def button(self, *a, **k):
        return False

    def dataframe(self, df, **k):
        self.dataframes.append(df)

    def dialog(self, title):
        def deco(fn):
            return fn
        return deco

    def cache_resource(self, fn):
        return fn

    def __getattr__(self, name):
        return MagicMock(name=f"st.{name}")


def _install_stubs(fake_st):
    st_mod = types.ModuleType("streamlit")
    for name in ["session_state", "columns", "button", "dataframe",
                 "dialog", "cache_resource"]:
        setattr(st_mod, name, getattr(fake_st, name))
    st_mod.__getattr__ = lambda name: getattr(fake_st, name)  # PEP 562
    sys.modules["streamlit"] = st_mod
    for name in ["dlib", "face_recognition_models", "sklearn", "sklearn.svm",
                 "PIL", "PIL.Image", "segno"]:
        sys.modules.setdefault(name, MagicMock(name=name))


def _record(subject_id, timestamp, student_id=1):
    return {
        "id": student_id,
        "subject_id": subject_id,
        "student_id": student_id,
        "attendance_date": timestamp.split("T")[0],
        "status": "present",
        "timestamp": timestamp,
        "subjects": {"subject_id": subject_id, "name": "Intro to CS",
                     "subject_code": "CS101"},
    }


class TestAttendanceRecordsTotals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake_st = FakeSt()
        _install_stubs(cls.fake_st)
        # Another test file running first in the same process may have
        # stubbed pandas/numpy as MagicMocks; the records tab aggregates
        # with real pandas, so drop those stubs before re-importing.
        for name in ("pandas", "numpy"):
            if isinstance(sys.modules.get(name), MagicMock):
                del sys.modules[name]
        # The module may already be imported (e.g. by another test file
        # running first in the same process), still bound to that run's
        # streamlit stub: drop it so the re-import below binds to this
        # run's stub.
        sys.modules.pop("src.screens.teacher_screen", None)
        import src.screens.teacher_screen as ts
        cls.ts = ts

    @classmethod
    def tearDownClass(cls):
        # Drop the screen (and the streamlit-bound components it pulls
        # in) again so a later test file re-imports them bound to its own
        # streamlit stub instead of this run's.
        for name in list(sys.modules):
            if name in ("src.screens.teacher_screen",
                        "src.pipelines.face_pipeline") or \
                    name.startswith(("src.components.", "src.ui.")):
                sys.modules.pop(name, None)

    def setUp(self):
        self.fake_st.dataframes.clear()

    def _stats(self):
        self.assertEqual(len(self.fake_st.dataframes), 1)
        return list(self.fake_st.dataframes[0]["Attendance Stats"])

    def test_absent_student_counted_in_total(self):
        # 2 students enrolled, only 1 present in the session: the tab
        # used to show "✅ 1 /1 Students" (100%) for this session.
        self.ts.get_teacher_subjects = lambda teacher_id: [
            {"subject_id": 1, "name": "Intro to CS", "subject_code": "CS101",
             "section": "A", "total_students": 2, "total_classes": 1},
        ]
        self.ts.get_attendance_for_teacher = lambda teacher_id: [
            _record(1, "2026-11-16T10:00:00"),
        ]
        self.ts.teacher_tab_attendance_records()
        self.assertEqual(self._stats(), ["✅ 1 /2 Students"])

    def test_full_attendance_still_shows_full_total(self):
        self.ts.get_teacher_subjects = lambda teacher_id: [
            {"subject_id": 1, "name": "Intro to CS", "subject_code": "CS101",
             "section": "A", "total_students": 2, "total_classes": 1},
        ]
        self.ts.get_attendance_for_teacher = lambda teacher_id: [
            _record(1, "2026-11-16T10:00:00", student_id=1),
            _record(1, "2026-11-16T10:00:00", student_id=2),
        ]
        self.ts.teacher_tab_attendance_records()
        self.assertEqual(self._stats(), ["✅ 2 /2 Students"])

    def test_no_records_renders_nothing(self):
        self.ts.get_attendance_for_teacher = lambda teacher_id: []
        self.ts.teacher_tab_attendance_records()
        self.assertEqual(self.fake_st.dataframes, [])


if __name__ == "__main__":
    unittest.main()
