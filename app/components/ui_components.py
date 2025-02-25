"""
Common UI components for reuse across pages
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Callable


def create_card(
    title: str, content: str, actions: Optional[List[Dict[str, Any]]] = None
):
    """
    Create a styled card component

    Args:
        title: Card title
        content: Card content (can include markdown)
        actions: Optional list of action buttons with keys: 'label', 'callback', 'args'
    """
    with st.container():
        st.markdown(f"### {title}")
        st.markdown(content)

        if actions:
            cols = st.columns(len(actions))
            for i, action in enumerate(actions):
                with cols[i]:
                    if st.button(action["label"], key=f"btn_{title}_{i}"):
                        if "callback" in action and callable(action["callback"]):
                            args = action.get("args", [])
                            action["callback"](*args)


def status_indicator(status: str, text: str):
    """
    Display a status indicator with text

    Args:
        status: Status type ('success', 'info', 'warning', 'error')
        text: Status text
    """
    if status == "success":
        st.success(text)
    elif status == "info":
        st.info(text)
    elif status == "warning":
        st.warning(text)
    elif status == "error":
        st.error(text)


def collapsible_section(
    header: str,
    content_callable: Callable,
    default_open: bool = False,
    key_suffix: str = "",
):
    """
    Create a collapsible section

    Args:
        header: Section header
        content_callable: Function to call to render section content
        default_open: Whether section is open by default
        key_suffix: Suffix to add to key for uniqueness
    """
    key = f"collapse_{header}_{key_suffix}".replace(" ", "_").lower()

    if key not in st.session_state:
        st.session_state[key] = default_open

    if st.button(f"{'▼' if st.session_state[key] else '▶'} {header}", key=f"btn_{key}"):
        st.session_state[key] = not st.session_state[key]

    if st.session_state[key]:
        content_callable()


def progress_indicator(progress: Dict[str, Any]):
    """
    Display a progress indicator

    Args:
        progress: Progress data with keys: 'value', 'max', 'status'
    """
    value = progress.get("value", 0)
    max_value = progress.get("max", 100)
    status = progress.get("status", "")

    if max_value > 0:
        percentage = min(100, int((value / max_value) * 100))
        st.progress(percentage / 100)
        st.text(f"{status}: {percentage}% ({value}/{max_value})")
    else:
        st.text(f"{status}")


def selection_grid(
    items: List[Dict[str, Any]],
    on_select: Callable[[Dict[str, Any]], None],
    key_field: str = "id",
    columns: int = 3,
    selected_item_key: str = "selected_item",
):
    """
    Display a grid of selectable items

    Args:
        items: List of items to display
        on_select: Callback function when an item is selected
        key_field: Field to use as the unique key for each item
        columns: Number of columns in the grid
        selected_item_key: Key to use in session state for selected item
    """
    if not items:
        st.info("No items to display")
        return

    # Create rows with the specified number of columns
    for i in range(0, len(items), columns):
        row_items = items[i : i + columns]
        cols = st.columns(columns)

        for j, item in enumerate(row_items):
            with cols[j]:
                if st.button(
                    item.get("title", f"Item {item.get(key_field, i+j)}"),
                    key=f"grid_item_{item.get(key_field, i+j)}",
                ):
                    st.session_state[selected_item_key] = item
                    on_select(item)
