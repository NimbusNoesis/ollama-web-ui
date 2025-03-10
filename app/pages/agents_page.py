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
                # logger.info(
                #     f"Rendering agent editor for agent: {st.session_state.editing_agent.name}"
                # )
                try:
                    render_agent_editor(
                        st.session_state.editing_agent, st.session_state.selected_group
                    )
                    # logger.debug(
                    #     f"Successfully rendered agent editor for {st.session_state.editing_agent.name}"
                    # )
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
                group_tab, task_tab, history_tab = st.tabs(
                    ["Group Details", "Task Execution", "Execution History"]
                )

                with group_tab:
                    logger.debug(f"Rendering Group Details tab for {group_name}")
                    try:
                        # Render group details without inner tabs
                        st.subheader(f"Group: {group_name}")
                        st.markdown(
                            f"**Description**: {st.session_state.selected_group.description}"
                        )
                        st.markdown(
                            f"**Created**: {st.session_state.selected_group.created_at}"
                        )
                        st.markdown(
                            f"**Number of Agents**: {len(st.session_state.selected_group.agents)}"
                        )

                        # Display the agents in this group
                        st.subheader("Agents in this Group")
                        for agent in st.session_state.selected_group.agents:
                            with st.expander(f"{agent.name} ({agent.model})"):
                                st.markdown(f"**ID**: {agent.id}")
                                st.markdown(f"**Model**: {agent.model}")
                                st.markdown("**System Prompt**:")
                                st.markdown(f"```\n{agent.system_prompt}\n```")

                                if agent.tools:
                                    st.markdown("**Tools**:")
                                    for tool in agent.tools:
                                        st.markdown(
                                            f"- {tool['function']['name']}: {tool['function']['description']}"
                                        )

                                # Buttons for agent actions
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("Edit Agent", key=f"edit_{agent.id}"):
                                        st.session_state.editing_agent = agent
                                        st.session_state.editing_agent_original_group = st.session_state.selected_group
                                with col2:
                                    if st.button(
                                        "Delete Agent", key=f"delete_{agent.id}"
                                    ):
                                        confirm_delete = st.checkbox(
                                            "Confirm deletion",
                                            key=f"confirm_{agent.id}",
                                        )
                                        if confirm_delete:
                                            st.session_state.selected_group.agents = [
                                                a
                                                for a in st.session_state.selected_group.agents
                                                if a.id != agent.id
                                            ]
                                            load_agents()
                                            st.success(f"Agent {agent.name} deleted!")
                                            st.rerun()

                        # Display shared memory
                        if st.session_state.selected_group.shared_memory:
                            st.subheader("Shared Memory")
                            with st.expander("View Shared Memory"):
                                for (
                                    memory
                                ) in st.session_state.selected_group.shared_memory[
                                    -10:
                                ]:
                                    st.markdown(
                                        f"**{memory['source']}** ({memory['timestamp']})"
                                    )
                                    st.markdown(memory["content"])
                                    st.markdown("---")

                        # Add group actions
                        st.subheader("Group Actions")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Add New Agent"):
                                st.session_state.editing_agent = (
                                    next(
                                        (
                                            a
                                            for a in st.session_state.selected_group.agents
                                            if not a.name
                                        ),
                                        None,
                                    )
                                    or {}
                                )
                                st.rerun()
                        with col2:
                            if st.button("Delete Group"):
                                confirm_delete = st.checkbox("Confirm group deletion")
                                if confirm_delete:
                                    st.session_state.agent_groups = [
                                        g
                                        for g in st.session_state.agent_groups
                                        if g.id != st.session_state.selected_group.id
                                    ]
                                    st.session_state.selected_group = None
                                    load_agents()
                                    st.success(f"Group {group_name} deleted!")
                                    st.rerun()

                        logger.debug(
                            f"Successfully rendered group details for {group_name}"
                        )
                    except Exception as e:
                        error_msg = log_exception(
                            e, f"Error rendering group details for {group_name}"
                        )
                        st.error(f"Failed to render group details: {error_msg}")

                with task_tab:
                    logger.debug(f"Rendering Task Execution tab for {group_name}")
                    try:
                        if st.session_state.selected_group is not None:
                            render_task_executor(st.session_state.selected_group)
                        else:
                            st.error("No group selected for task execution.")
                        logger.debug(
                            f"Successfully rendered task executor for {group_name}"
                        )
                    except Exception as e:
                        error_msg = log_exception(
                            e, f"Error rendering task executor for {group_name}"
                        )
                        st.error(f"Failed to render task executor: {error_msg}")

                with history_tab:
                    logger.debug(f"Rendering Execution History tab for {group_name}")
                    try:
                        # Import the render_execution_history function
                        from app.utils.agents.ui_components import (
                            render_execution_history,
                        )

                        if st.session_state.selected_group is not None:
                            render_execution_history(st.session_state.selected_group)
                        else:
                            st.error("No group selected for execution history.")
                        logger.debug(
                            f"Successfully rendered execution history for {group_name}"
                        )
                    except Exception as e:
                        error_msg = log_exception(
                            e, f"Error rendering execution history for {group_name}"
                        )
                        st.error(f"Failed to render execution history: {error_msg}")

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
