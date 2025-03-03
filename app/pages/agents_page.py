import streamlit as st
import time
import traceback

from app.utils.logger import get_logger, log_exception, set_log_level
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
        start_time = time.time()

        # Initialize session state
        if "agent_groups" not in st.session_state:
            st.session_state["agent_groups"] = []
            logger.info("Created empty agent_groups in session state")
        else:
            logger.debug(
                f"Found {len(st.session_state.agent_groups)} existing agent groups in session state"
            )

        if "selected_group" not in st.session_state:
            st.session_state.selected_group = None
            logger.info("Initialized selected_group as None in session state")
        elif st.session_state.selected_group:
            logger.debug(
                f"Found selected_group in session state: {st.session_state.selected_group.name}"
            )

        if "editing_agent" not in st.session_state:
            st.session_state.editing_agent = None
            logger.info("Initialized editing_agent as None in session state")
        elif st.session_state.editing_agent:
            logger.debug(
                f"Found editing_agent in session state: {st.session_state.editing_agent.name}"
            )

        try:
            # Load agent data
            logger.info("Loading agent data")
            load_agents()
            logger.info(
                f"Successfully loaded {len(st.session_state.get('agent_groups', []))} agent groups"
            )
        except Exception as e:
            error_msg = log_exception(e, "Error loading agent data")
            st.error(f"Failed to load agent data: {error_msg}")
            logger.error(f"AgentsPage initialization failed: {error_msg}")

        init_duration = time.time() - start_time
        logger.info(
            f"AgentsPage initialization completed in {init_duration:.2f} seconds"
        )

    def render(self):
        """Render the agents page"""
        render_start_time = time.time()
        logger.info("Rendering AgentsPage")
        st.title("Multi-Agent Systems")
        st.write("Create and manage groups of AI agents that can work together")

        try:
            # Left sidebar for group selection
            logger.debug("Rendering sidebar for group selection")
            st.sidebar.subheader("Agent Groups")

            # Add log level selector to sidebar
            self._render_log_level_selector()

            if not st.session_state.agent_groups:
                logger.info("No agent groups available")
                st.sidebar.info("No agent groups yet")
            else:
                group_names = [group.name for group in st.session_state.agent_groups]
                logger.info(f"Displaying {len(group_names)} groups in sidebar")
                logger.debug(f"Available groups: {', '.join(group_names)}")

                selected_name = st.sidebar.selectbox(
                    "Select Group",
                    options=group_names,
                    format_func=lambda x: f"👥 {x}",
                )
                if selected_name:
                    logger.info(f"Group selected from sidebar: {selected_name}")
                    previous_group = getattr(
                        st.session_state.selected_group, "name", None
                    )
                    st.session_state.selected_group = next(
                        g
                        for g in st.session_state.agent_groups
                        if g.name == selected_name
                    )
                    if previous_group != selected_name:
                        logger.info(
                            f"Changed selected_group from {previous_group} to {selected_name} (ID: {st.session_state.selected_group.id})"
                        )
                    else:
                        logger.debug(f"Selected same group: {selected_name}")

            if st.sidebar.button("Create New Group"):
                logger.info("Create New Group button clicked in sidebar")
                previous_group = getattr(st.session_state.selected_group, "name", None)
                previous_agent = getattr(st.session_state.editing_agent, "name", None)

                st.session_state.selected_group = None
                st.session_state.editing_agent = None

                logger.info(
                    f"Reset selected_group (was: {previous_group}) and editing_agent (was: {previous_agent}) to None"
                )

            # Main content area
            logger.debug("Rendering main content area")
            if st.session_state.editing_agent is not None:
                logger.info(
                    f"Rendering agent editor for agent: {st.session_state.editing_agent.name}"
                )
                try:
                    render_agent_editor(
                        st.session_state.editing_agent, st.session_state.selected_group
                    )
                    logger.debug(
                        f"Successfully rendered agent editor for {st.session_state.editing_agent.name}"
                    )
                except Exception as e:
                    error_msg = log_exception(
                        e,
                        f"Error rendering agent editor for {getattr(st.session_state.editing_agent, 'name', 'unknown')}",
                    )
                    st.error(f"Failed to render agent editor: {error_msg}")
            elif not st.session_state.selected_group:
                logger.info("Rendering group editor (no selected_group)")
                try:
                    render_group_editor()
                    logger.debug("Successfully rendered group editor")
                except Exception as e:
                    error_msg = log_exception(e, "Error rendering group editor")
                    st.error(f"Failed to render group editor: {error_msg}")
            else:
                group_name = st.session_state.selected_group.name
                logger.info(f"Rendering tabs for group: {group_name}")
                tab1, tab2 = st.tabs(["Group Details", "Task Execution"])

                with tab1:
                    logger.debug(f"Rendering Group Details tab for {group_name}")
                    try:
                        render_group_view(st.session_state.selected_group)
                        logger.debug(
                            f"Successfully rendered group view for {group_name}"
                        )
                    except Exception as e:
                        error_msg = log_exception(
                            e, f"Error rendering group view for {group_name}"
                        )
                        st.error(f"Failed to render group view: {error_msg}")

                with tab2:
                    logger.debug(f"Rendering Task Execution tab for {group_name}")
                    try:
                        render_task_executor(st.session_state.selected_group)
                        logger.debug(
                            f"Successfully rendered task executor for {group_name}"
                        )
                    except Exception as e:
                        error_msg = log_exception(
                            e, f"Error rendering task executor for {group_name}"
                        )
                        st.error(f"Failed to render task executor: {error_msg}")

            render_duration = time.time() - render_start_time
            logger.info(
                f"AgentsPage rendering completed in {render_duration:.2f} seconds"
            )

        except Exception as e:
            render_duration = time.time() - render_start_time
            error_msg = log_exception(
                e, f"Unexpected error rendering AgentsPage ({render_duration:.2f}s)"
            )
            st.error(f"An unexpected error occurred: {error_msg}")
            logger.error(f"AgentsPage rendering failed: {error_msg}")
            logger.debug(f"Exception details: {traceback.format_exc()}")

    def _render_log_level_selector(self):
        """Render a log level selector in the sidebar"""
        st.sidebar.subheader("Logging Settings")

        # Initialize log level in session state if not present
        if "log_level" not in st.session_state:
            st.session_state.log_level = "INFO"

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        selected_level = st.sidebar.selectbox(
            "Log Level",
            options=log_levels,
            index=log_levels.index(st.session_state.log_level),
            help="Set the logging level. DEBUG shows all messages, while ERROR shows only errors.",
        )

        if selected_level != st.session_state.log_level:
            st.session_state.log_level = selected_level
            set_log_level(selected_level)
            logger.debug(f"Log level changed to {selected_level}")

            # Add a note about debug logging
            if selected_level == "DEBUG":
                st.sidebar.info(
                    "Debug logging is now enabled. Check the console or log files for detailed messages."
                )
