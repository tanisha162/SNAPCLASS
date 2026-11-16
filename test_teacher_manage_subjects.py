"""Regression tests for the teacher Manage Subjects tab.

Bug: in teacher_tab_manage_subjects() the `subject_card(...)` call (and the
`share_btn` helper) sat outside the `for sub in subjects:` loop, so a
teacher with several subjects only ever saw the last one rendered. The
loop body only rebuilt `stats` and threw it away.

The screens need Streamlit plus the heavy face/voice deps (dlib, sklearn),
none of which is required to render a subject card, so this test stubs
those modules and drives the tab with a fake `st` that records markdown.

Run:  PYTHONDONTWRITEBYTECODE=1 python -m unittest test_teacher_manage_subjects -v
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
        self.markdown_calls = []
        self.info_calls = []

    def columns(self, n, **kw):
        if isinstance(n, int):
            return [_Ctx() for _ in range(n)]
        return [_Ctx() for _ in n]

    def button(self, *a, **k):
        return False

    def markdown(self, html, **k):
        self.markdown_calls.append(html)

    def info(self, msg, **k):
        self.info_calls.append(msg)

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
    for name in ["session_state", "columns", "button", "markdown", "info",
                 "dialog", "cache_resource"]:
        setattr(st_mod, name, getattr(fake_st, name))
    st_mod.__getattr__ = lambda name: getattr(fake_st, name)  # PEP 562
    sys.modules["streamlit"] = st_mod
    for name in ["dlib", "face_recognition_models", "sklearn", "sklearn.svm",
                 "numpy", "pandas", "PIL", "PIL.Image", "segno"]:
        sys.modules.setdefault(name, MagicMock(name=name))


class TestManageSubjectsRendersAll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake_st = FakeSt()
        _install_stubs(cls.fake_st)
        import src.screens.teacher_screen as ts
        cls.ts = ts

    def setUp(self):
        self.fake_st.markdown_calls.clear()
        self.fake_st.info_calls.clear()

    def _rendered_names(self):
        return [name for name in ("Intro to CS", "Data Structures", "Databases")
                if any(name in html for html in self.fake_st.markdown_calls)]

    def test_all_subjects_rendered(self):
        self.ts.get_teacher_subjects = lambda teacher_id: [
            {"subject_id": 1, "name": "Intro to CS", "subject_code": "CS101",
             "section": "A", "total_students": 5, "total_classes": 3},
            {"subject_id": 2, "name": "Data Structures", "subject_code": "CS201",
             "section": "B", "total_students": 7, "total_classes": 4},
        ]
        self.ts.teacher_tab_manage_subjects()
        self.assertEqual(self._rendered_names(), ["Intro to CS", "Data Structures"])

    def test_single_subject_still_renders(self):
        self.ts.get_teacher_subjects = lambda teacher_id: [
            {"subject_id": 1, "name": "Intro to CS", "subject_code": "CS101",
             "section": "A", "total_students": 5, "total_classes": 3},
        ]
        self.ts.teacher_tab_manage_subjects()
        self.assertEqual(self._rendered_names(), ["Intro to CS"])

    def test_no_subjects_shows_empty_message(self):
        self.ts.get_teacher_subjects = lambda teacher_id: []
        self.ts.teacher_tab_manage_subjects()
        self.assertEqual(self._rendered_names(), [])
        self.assertTrue(any("NO SUBJECTS FOUND" in m for m in self.fake_st.info_calls))


if __name__ == "__main__":
    unittest.main()
