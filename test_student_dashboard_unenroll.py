"""Regression tests for the student dashboard unenroll buttons.

Bug: student_dashboard() rendered one "Unenroll from this course" button
per enrolled subject with the same label and no `key`. Streamlit assigns
an auto-generated ID from the button's type and parameters, so a student
enrolled in two or more subjects hit StreamlitDuplicateElementId and the
whole dashboard crashed (verified against real Streamlit 1.67.0 with
AppTest: two identical unkeyed buttons raise; keyed buttons render fine).
Each unenroll button must carry a unique key per subject.

The screens need Streamlit plus the heavy face/voice deps (dlib, sklearn),
none of which is required to render the dashboard, so this test stubs
those modules and drives the dashboard with a fake `st` that records
button keys and rejects duplicate auto-generated button IDs the way
real Streamlit does.

Run:  PYTHONDONTWRITEBYTECODE=1 python -m unittest test_student_dashboard_unenroll -v
"""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent))


class DuplicateButtonIdError(Exception):
    """Stand-in for streamlit.errors.StreamlitDuplicateElementId."""


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
            {"student_data": {"student_id": 1, "name": "Hamza"}})
        self.button_calls = []
        self._seen_button_ids = set()

    def columns(self, n, **kw):
        if isinstance(n, int):
            return [_Ctx() for _ in range(n)]
        return [_Ctx() for _ in n]

    def button(self, *a, **k):
        label = a[0] if a else k.get("label", "")
        key = k.get("key")
        # Real Streamlit derives the element ID from the widget's type and
        # parameters; two buttons with identical parameters and no key
        # collide. A unique key keeps them distinct.
        element_id = (label, k.get("type"), k.get("width"), k.get("icon"),
                      key if key is not None else "auto")
        if element_id in self._seen_button_ids:
            raise DuplicateButtonIdError(
                "There are multiple `button` elements with the same "
                "auto-generated ID. Pass a unique `key` argument.")
        self._seen_button_ids.add(element_id)
        self.button_calls.append((label, key))
        return False

    def spinner(self, *a, **k):
        return _Ctx()

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
    for name in ["session_state", "columns", "button", "spinner", "dialog",
                 "cache_resource"]:
        setattr(st_mod, name, getattr(fake_st, name))
    st_mod.__getattr__ = lambda name: getattr(fake_st, name)  # PEP 562
    sys.modules["streamlit"] = st_mod
    for name in ["dlib", "face_recognition_models", "sklearn", "sklearn.svm",
                 "numpy", "pandas", "PIL", "PIL.Image", "segno", "librosa",
                 "resemblyzer", "supabase"]:
        sys.modules.setdefault(name, MagicMock(name=name))
    # The screen imports the face pipeline; stub it before import.
    face_pipeline = types.ModuleType("src.pipelines.face_pipeline")
    face_pipeline.predict_attendance = MagicMock()
    face_pipeline.get_face_embeddings = MagicMock()
    face_pipeline.train_classifier = MagicMock()
    sys.modules["src.pipelines.face_pipeline"] = face_pipeline


def _subjects(*specs):
    return [{"subjects": {"subject_id": sid, "name": name,
                          "subject_code": code, "section": "A"}}
            for sid, name, code in specs]


class TestStudentDashboardUnenroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake_st = FakeSt()
        _install_stubs(cls.fake_st)
        import src.screens.student_screen as ss
        cls.ss = ss

    def setUp(self):
        self.fake_st.button_calls.clear()
        self.fake_st._seen_button_ids.clear()
        self.ss.get_student_subjects = lambda student_id: _subjects(
            (1, "Intro to CS", "CS101"), (2, "Data Structures", "CS201"))
        self.ss.get_student_attendance = lambda student_id: []
        self.ss.get_subject_total_classes = lambda subject_id: 3

    def _unenroll_keys(self):
        return [key for label, key in self.fake_st.button_calls
                if label.startswith("Unenroll")]

    def test_two_subjects_render_without_duplicate_button_id(self):
        # Before the fix this raised DuplicateButtonIdError: both unenroll
        # buttons shared one label and no key.
        self.ss.student_dashboard()
        keys = self._unenroll_keys()
        self.assertEqual(len(keys), 2)
        self.assertEqual(len(set(keys)), 2)

    def test_unenroll_key_identifies_its_subject(self):
        self.ss.student_dashboard()
        keys = sorted(self._unenroll_keys())
        self.assertEqual(keys, ["unenroll_1", "unenroll_2"])

    def test_single_subject_still_renders(self):
        self.ss.get_student_subjects = lambda student_id: _subjects(
            (1, "Intro to CS", "CS101"))
        self.ss.student_dashboard()
        self.assertEqual(self._unenroll_keys(), ["unenroll_1"])


if __name__ == "__main__":
    unittest.main()
