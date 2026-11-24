"""Regression tests for the share-subject dialog (src/components/dialog_share_subject.py).

Bug: the dialog built the join URL as "snapclass-main.streamlit.app/
?join-code=<code>" with no scheme. That string is not a valid absolute
URL, so the QR code it encodes is not openable by a phone camera (it is
read as plain text / a search query instead of a link) and the "Scan to
Join" flow fails; the copied link shown in the dialog was schemeless too.
The app reads the code from `st.query_params['join-code']` (app.py), so
the shared URL must be a full https:// URL to the deployed app.

The dialog needs Streamlit plus segno, neither of which is required to
build the URL, so this test stubs those modules and drives the dialog
with a fake `st` that records the code blocks shown and the URL handed
to segno.

Run:  PYTHONDONTWRITEBYTECODE=1 python -m unittest test_share_subject_url -v
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


class FakeSt:
    """Minimal stand-in for the `streamlit` module used by the dialog."""

    def __init__(self):
        self.session_state = {}
        self.code_calls = []

    def columns(self, n, **kw):
        if isinstance(n, int):
            return [_Ctx() for _ in range(n)]
        return [_Ctx() for _ in n]

    def code(self, text, **k):
        self.code_calls.append(text)

    def dialog(self, title):
        def deco(fn):
            return fn
        return deco

    def __getattr__(self, name):
        return MagicMock(name=f"st.{name}")


def _install_stubs(fake_st):
    st_mod = types.ModuleType("streamlit")
    for name in ["session_state", "columns", "code", "dialog"]:
        setattr(st_mod, name, getattr(fake_st, name))
    st_mod.__getattr__ = lambda name: getattr(fake_st, name)  # PEP 562
    sys.modules["streamlit"] = st_mod
    sys.modules.setdefault("segno", MagicMock(name="segno"))


class TestShareSubjectUrl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake_st = FakeSt()
        _install_stubs(cls.fake_st)
        # The dialog module may already be imported (e.g. by another test
        # file running first in the same process, via teacher_screen),
        # still bound to that run's streamlit stub: drop it so the
        # re-import below binds to this run's stub.
        sys.modules.pop("src.components.dialog_share_subject", None)
        import src.components.dialog_share_subject as d
        cls.dialog = d

    def setUp(self):
        self.fake_st.code_calls.clear()
        sys.modules["segno"].make.reset_mock()

    def test_join_url_is_absolute_https(self):
        self.dialog.share_subject_dialog("Intro to CS", "CS101")
        qr_url = sys.modules["segno"].make.call_args[0][0]
        self.assertEqual(
            qr_url, "https://snapclass-main.streamlit.app/?join-code=CS101")
        # The link shown to copy must be the same absolute URL.
        self.assertIn(qr_url, self.fake_st.code_calls)

    def test_join_url_carries_the_subject_code(self):
        self.dialog.share_subject_dialog("Data Structures", "CS201")
        qr_url = sys.modules["segno"].make.call_args[0][0]
        self.assertTrue(qr_url.startswith("https://"))
        self.assertIn("join-code=CS201", qr_url)


if __name__ == "__main__":
    unittest.main()
