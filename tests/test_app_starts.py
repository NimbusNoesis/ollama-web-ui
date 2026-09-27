"""Smoke test: the app starts and every sidebar page renders without an exception.

Run: pip install pytest && python -m pytest tests/ -q
(No Ollama server needed — pages only call it on user actions.)
"""
import os

from streamlit.testing.v1 import AppTest

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
PAGES = ["Chat", "Compare Models", "Models", "Tools", "Agents", "Logs"]


def test_app_starts_and_every_page_renders():
    at = AppTest.from_file(MAIN, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    for label in PAGES:
        nav = [b for b in at.sidebar.button if b.label == label]
        assert nav, f"no '{label}' button in the sidebar"
        nav[0].click().run()
        assert not at.exception, (label, [e.value for e in at.exception])
