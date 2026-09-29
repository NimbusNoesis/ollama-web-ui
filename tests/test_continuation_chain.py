"""get_continuation_chain must not crash on a history entry that has no children.

A re-indent once moved the child-chain append loop out of `for child in children`,
so for a childless entry `child_chain` was never assigned (UnboundLocalError).
"""
from types import SimpleNamespace

from app.utils.agents.ui_components import get_continuation_chain


def _group(*entries):
    return SimpleNamespace(execution_history=list(entries))


def test_entry_without_children_is_its_own_chain():
    root = {"id": "root"}
    assert get_continuation_chain(_group(root), "root") == [root]


def test_unknown_entry_gives_empty_chain():
    assert get_continuation_chain(_group({"id": "root"}), "missing") == []
