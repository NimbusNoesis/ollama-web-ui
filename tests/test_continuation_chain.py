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


# The chain used to recurse from a child up to its parent and from the parent
# back down to the child without end: any parent/child pair raised RecursionError.

def _ids(chain):
    return [e["id"] for e in chain]


def test_parent_and_child_give_the_same_chain_from_either_end():
    group = _group({"id": "a"}, {"id": "b", "parent_id": "a"})
    assert _ids(get_continuation_chain(group, "a")) == ["a", "b"]
    assert _ids(get_continuation_chain(group, "b")) == ["a", "b"]


def test_chain_is_ancestors_then_entry_then_descendants():
    group = _group(
        {"id": "root"},
        {"id": "mid", "parent_id": "root"},
        {"id": "leaf1", "parent_id": "mid"},
        {"id": "leaf2", "parent_id": "mid"},
        {"id": "leaf1-child", "parent_id": "leaf1"},
        {"id": "other-root"},
    )
    assert _ids(get_continuation_chain(group, "mid")) == ["root", "mid", "leaf1", "leaf1-child", "leaf2"]


def test_siblings_are_not_part_of_the_chain():
    group = _group({"id": "p"}, {"id": "c1", "parent_id": "p"}, {"id": "c2", "parent_id": "p"})
    assert _ids(get_continuation_chain(group, "c1")) == ["p", "c1"]


def test_parent_cycle_terminates():
    group = _group({"id": "a", "parent_id": "b"}, {"id": "b", "parent_id": "a"})
    assert _ids(get_continuation_chain(group, "a")) == ["b", "a"]


def test_missing_parent_is_ignored():
    assert _ids(get_continuation_chain(_group({"id": "x", "parent_id": "gone"}), "x")) == ["x"]
