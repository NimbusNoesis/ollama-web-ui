import streamlit as st

from app.utils.logger import get_logger
from app.utils.agents.ui_components import (
    render_agent_editor,
    render_group_editor,
    render_group_view,
    render_task_executor,
    load_agents,
)

# Get application logger
logger = get_logger()


class AgentsPage:
    """Page for managing multi-agent systems"""

    def __init__(self):
        """Initialize the agents page"""
        logger.info("Initializing AgentsPage")

        # Initialize session state
        if "agent_groups" not in st.session_state:
            st.session_state["agent_groups"] = []
            logger.info("Created empty agent_groups in session state")

        if "selected_group" not in st.session_state:
            st.session_state.selected_group = None
            logger.info("Initialized selected_group as None in session state")

        if "editing_agent" not in st.session_state:
            st.session_state.editing_agent = None
            logger.info("Initialized editing_agent as None in session state")

        # Load agent data
        load_agents()

    def render(self):
        """Render the agents page"""
        logger.info("Rendering AgentsPage")
        st.title("Multi-Agent Systems")
        st.write("Create and manage groups of AI agents that can work together")

        # Left sidebar for group selection
        st.sidebar.subheader("Agent Groups")

        if not st.session_state.agent_groups:
            logger.info("No agent groups available")
            st.sidebar.info("No agent groups yet")
        else:
            group_names = [group.name for group in st.session_state.agent_groups]
            logger.info(f"Displaying {len(group_names)} groups in sidebar")

            selected_name = st.sidebar.selectbox(
                "Select Group",
                options=group_names,
                format_func=lambda x: f"👥 {x}",
            )
            if selected_name:
                logger.info(f"Group selected from sidebar: {selected_name}")
                st.session_state.selected_group = next(
                    g for g in st.session_state.agent_groups if g.name == selected_name
                )
                logger.info(
                    f"Set selected_group in session state: {st.session_state.selected_group.name} (ID: {st.session_state.selected_group.id})"
                )

        if st.sidebar.button("Create New Group"):
            logger.info("Create New Group button clicked in sidebar")
            st.session_state.selected_group = None
            st.session_state.editing_agent = None
            logger.info("Reset selected_group and editing_agent to None")

        # Main content area
        if st.session_state.editing_agent is not None:
            logger.info("Rendering agent editor (editing_agent is not None)")
            render_agent_editor(
                st.session_state.editing_agent, st.session_state.selected_group
            )
        elif not st.session_state.selected_group:
            logger.info("Rendering group editor (no selected_group)")
            render_group_editor()
        else:
            logger.info(
                f"Rendering tabs for group: {st.session_state.selected_group.name}"
            )
            tab1, tab2 = st.tabs(["Group Details", "Task Execution"])

            with tab1:
                render_group_view(st.session_state.selected_group)
            with tab2:
                render_task_executor(st.session_state.selected_group)
