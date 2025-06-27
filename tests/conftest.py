import pathlib
import sys
import types
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

class DummySession(dict):
    def __getattr__(self, item):
        return self.get(item)
    def __setattr__(self, key, value):
        self[key] = value

ChatResponse = type("ChatResponse", (), {})

@pytest.fixture(autouse=True)
def dummy_modules(monkeypatch):
    st = types.SimpleNamespace(session_state=DummySession())
    sys.modules['streamlit'] = st
    ollama = types.SimpleNamespace(
        ChatResponse=ChatResponse,
        list=lambda: {'models': []},
        pull=lambda name, stream=True: [],
        delete=lambda name: True,
        show=lambda name: {},
        chat=lambda **kwargs: []
    )
    sys.modules['ollama'] = ollama
    sys.modules['ollama.chat'] = types.SimpleNamespace()
    sys.modules['requests'] = types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(status_code=200, text=""))
    yield
    for mod in ['streamlit', 'ollama', 'ollama.chat', 'requests']:
        sys.modules.pop(mod, None)
