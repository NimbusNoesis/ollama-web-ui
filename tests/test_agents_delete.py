"""Deleting an agent or a group needs its Confirm box ticked first, is saved to
disk, and is rolled back with an error if saving fails.

The confirm checkbox used to be created inside the Delete button's branch, so it
only appeared on the rerun after the click and could never be ticked; and a
confirmed delete then called load_agents() (re-read from disk) instead of
save_agents(). Agents and groups could not be deleted.

These tests use the real load_agents/save_agents against a temporary
agent_groups.json, except where a failing save is simulated.
"""
import json
import os

import streamlit as st
from streamlit.testing.v1 import AppTest

import app.pages.agents_page as agents_page
import app.utils.agents.ui_components as ui
from app.utils.agents.agent import Agent
from app.utils.agents.agent_group import AgentGroup

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


def _saved(tmp_path):
    with open(tmp_path / "agent_groups.json", encoding="utf-8") as f:
        return {g["name"]: [a["name"] for a in g["agents"]] for g in json.load(f)}


def _open_agents_page():
    at = AppTest.from_file(MAIN, default_timeout=60).run()
    next(b for b in at.sidebar.button if b.label == "Agents").click().run()  # the only group is auto-selected
    assert not at.exception, [e.value for e in at.exception]
    return at


def _app(monkeypatch, tmp_path):
    monkeypatch.setattr(ui, "agents_data_dir", lambda: str(tmp_path))
    group = AgentGroup("Team", "test group",
                       agents=[Agent("alpha", "m", "p"), Agent("beta", "m", "p")])
    with open(tmp_path / "agent_groups.json", "w", encoding="utf-8") as f:
        json.dump([group.to_dict()], f)
    return _open_agents_page(), group


def _failing_save(monkeypatch):
    """Replace the page's save_agents with one that fails, recording what it was asked to save."""
    calls = []

    def save():
        calls.append({g.name: [a.name for a in g.agents] for g in st.session_state["agent_groups"]})
        return False

    monkeypatch.setattr(agents_page, "save_agents", save)
    return calls


def _button(at, label, key=None):
    return next(b for b in at.button if b.label == label and (key is None or b.key == key))


def _names(at):
    return {g.name: [a.name for a in g.agents] for g in at.session_state["agent_groups"]}


def _delete_agent(at, agent):
    assert _button(at, "Delete Agent", f"delete_{agent.id}").disabled
    at.checkbox(key=f"confirm_{agent.id}").check().run()
    _button(at, "Delete Agent", f"delete_{agent.id}").click().run()


def _delete_group(at, group):
    assert _button(at, "Delete Group").disabled
    at.checkbox(key=f"confirm_group_{group.id}").check().run()
    _button(at, "Delete Group").click().run()


def test_delete_agent_is_saved_and_survives_reload(monkeypatch, tmp_path):
    at, group = _app(monkeypatch, tmp_path)
    _delete_agent(at, group.agents[0])
    assert not at.exception, [e.value for e in at.exception]
    assert _names(at) == {"Team": ["beta"]}
    assert _saved(tmp_path) == {"Team": ["beta"]}
    assert _names(_open_agents_page()) == {"Team": ["beta"]}  # fresh session reloads from disk


def test_delete_group_is_saved_and_survives_reload(monkeypatch, tmp_path):
    at, group = _app(monkeypatch, tmp_path)
    _delete_group(at, group)
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["agent_groups"] == []
    assert at.session_state["selected_group"] is None
    assert _saved(tmp_path) == {}
    assert _names(_open_agents_page()) == {}


def test_delete_agent_failed_save_is_rolled_back(monkeypatch, tmp_path):
    at, group = _app(monkeypatch, tmp_path)
    calls = _failing_save(monkeypatch)
    _delete_agent(at, group.agents[0])
    assert calls == [{"Team": ["beta"]}]  # save was asked to persist the deletion
    assert _names(at) == {"Team": ["alpha", "beta"]}
    assert [e.value for e in at.error] == ["Could not delete agent alpha: saving failed (see logs)."]
    assert not at.success
    assert _saved(tmp_path) == {"Team": ["alpha", "beta"]}


def test_delete_group_failed_save_is_rolled_back(monkeypatch, tmp_path):
    at, group = _app(monkeypatch, tmp_path)
    calls = _failing_save(monkeypatch)
    _delete_group(at, group)
    assert calls == [{}]
    assert _names(at) == {"Team": ["alpha", "beta"]}
    assert at.session_state["selected_group"].id == group.id
    assert [e.value for e in at.error] == ["Could not delete group Team: saving failed (see logs)."]
    assert not at.success
    assert _saved(tmp_path) == {"Team": ["alpha", "beta"]}
