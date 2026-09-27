"""Deleting an agent or a group needs its Confirm box ticked first, and then works.

The confirm checkbox used to be created inside the Delete button's branch, so it
only appeared on the rerun after the click and could never be ticked; and a
confirmed delete then called load_agents() (re-read from disk) instead of
save_agents(). Agents and groups could not be deleted.
"""
import os

from streamlit.testing.v1 import AppTest

import app.pages.agents_page as agents_page
import app.utils.agents.ui_components as ui
from app.utils.agents.agent import Agent
from app.utils.agents.agent_group import AgentGroup

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


def _app(monkeypatch):
    # keep the test off disk: no loading or saving of app/data/agents
    monkeypatch.setattr(ui, "save_agents", lambda: None)
    monkeypatch.setattr(agents_page, "save_agents", lambda: None)
    monkeypatch.setattr(agents_page, "load_agents", lambda: None)
    group = AgentGroup("Team", "test group",
                       agents=[Agent("alpha", "m", "p"), Agent("beta", "m", "p")])
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["agent_groups"] = [group]
    at.run()
    next(b for b in at.sidebar.button if b.label == "Agents").click().run()  # the only group is auto-selected
    assert not at.exception, [e.value for e in at.exception]
    return at, group


def _button(at, label, key=None):
    return next(b for b in at.button if b.label == label and (key is None or b.key == key))


def test_delete_agent_needs_confirm_then_deletes(monkeypatch):
    at, group = _app(monkeypatch)
    alpha = group.agents[0]
    assert _button(at, "Delete Agent", f"delete_{alpha.id}").disabled
    at.checkbox(key=f"confirm_{alpha.id}").check().run()
    _button(at, "Delete Agent", f"delete_{alpha.id}").click().run()
    assert [a.name for a in at.session_state["agent_groups"][0].agents] == ["beta"]


def test_delete_group_needs_confirm_then_deletes(monkeypatch):
    at, group = _app(monkeypatch)
    assert _button(at, "Delete Group").disabled
    at.checkbox(key=f"confirm_group_{group.id}").check().run()
    _button(at, "Delete Group").click().run()
    assert at.session_state["agent_groups"] == []
    assert at.session_state["selected_group"] is None
