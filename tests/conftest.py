"""Keep every test off the Ollama server.

Chat, Compare Models and Models call ollama.list() while rendering, so without
this the smoke test would talk to whatever server is (or isn't) on localhost.
list() returns one fake model; any other Ollama call fails the test loudly.
"""
import ollama
import pytest

FAKE_MODEL = "smoke-test:latest"


def _unexpected(name):
    def call(*args, **kwargs):
        raise AssertionError(f"unexpected Ollama call during test: ollama.{name}()")
    return call


@pytest.fixture(autouse=True)
def fake_ollama(monkeypatch):
    listed = ollama.ListResponse(models=[ollama.ListResponse.Model(model=FAKE_MODEL, size=1)])
    monkeypatch.setattr(ollama, "list", lambda *a, **k: listed)
    for name in ("chat", "generate", "show", "pull", "push", "delete", "create", "copy", "ps", "embed"):
        monkeypatch.setattr(ollama, name, _unexpected(name))
    return listed
