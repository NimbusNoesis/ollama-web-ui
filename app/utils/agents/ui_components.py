"""
UI components for the agents page.
"""

import streamlit as st
import os
import json
import traceback
import re
from typing import Dict, List, Any, Optional

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.tool_loader import ToolLoader
from app.utils.agents.agent import Agent
from app.utils.agents.agent_group import AgentGroup

# Get application logger
logger = get_logger()


def process_markdown(content: str) -> str:
    """
    Process markdown content for better rendering

    Args:
        content: The markdown content to process

    Returns:
        Processed markdown content
    """
    if not content:
        return ""

    # Ensure code blocks are properly formatted
    # This helps with proper syntax highlighting
    content = re.sub(r"```(\w+)\n", r"```\1\n", content)

    return content


def render_agent_editor(
    editing_agent: Optional[Agent], selected_group: Optional[AgentGroup]
):
    """Render the agent creation/editing form"""
    logger.info("Rendering agent editor")
    st.subheader("Agent Editor")

    # Get available models
    models = OllamaAPI.get_local_models()
    model_names = [m.get("model", "unknown") for m in models]
    logger.info(f"Loaded {len(model_names)} available models")

    # Get available tools
    installed_tools = ToolLoader.list_available_tools()
    logger.info(f"Loaded {len(installed_tools)} available tools")

    with st.form("agent_editor"):
        name = st.text_input(
            "Agent Name",
            value=editing_agent.name if editing_agent else "",
        )

        # Set the default model value correctly when editing
        default_model_index = 0
        if editing_agent and editing_agent.model:
            try:
                default_model_index = model_names.index(editing_agent.model)
            except ValueError:
                # If the model isn't in the list, default to first option
                logger.warning(
                    f"Model {editing_agent.model} not found in available models"
                )

        model = st.selectbox("Model", model_names, index=default_model_index)

        system_prompt = st.text_area(
            "System Prompt",
            value=editing_agent.system_prompt if editing_agent else "",
        )

        # Tool selection
        st.write("### Available Tools")
        selected_tools = []
        current_tool_names = []

        if editing_agent and editing_agent.tools:
            current_tool_names = [
                tool["function"]["name"] for tool in editing_agent.tools
            ]
            logger.info(f"Editing agent has {len(current_tool_names)} tools selected")

        for tool_name in installed_tools:
            if st.checkbox(
                tool_name,
                value=tool_name in current_tool_names,
            ):
                _, tool_def = ToolLoader.load_tool_function(tool_name)
                if tool_def:
                    selected_tools.append(tool_def)
                    logger.info(f"Tool selected: {tool_name}")

        if st.form_submit_button("Save Agent"):
            logger.info(f"Save Agent button clicked for agent: {name}")

            if not name:
                logger.warning("Agent name is required but was empty")
                st.error("Agent name is required")
                return

            # Check if the selected group exists
            if not selected_group:
                logger.warning("No group selected when trying to save agent")
                st.error("No group selected. Please select a group first.")
                return

            logger.info(f"Saving agent to group: {selected_group.name}")

            if editing_agent:
                # Update existing agent
                agent = editing_agent
                logger.info(f"Updating existing agent {agent.name} (ID: {agent.id})")

                # Log the changes for debugging
                logger.info(f"Updating agent properties:")
                logger.info(f"  Name: {agent.name} -> {name}")
                logger.info(f"  Model: {agent.model} -> {model}")
                logger.info(
                    f"  System prompt length: {len(agent.system_prompt)} -> {len(system_prompt)}"
                )
                logger.info(f"  Tools: {len(agent.tools)} -> {len(selected_tools)}")

                # Update the agent properties
                agent.name = name
                agent.model = model
                agent.system_prompt = system_prompt
                agent.tools = selected_tools

                # Check if agent is already in the group, if not, add it
                agent_in_group = any(
                    existing_agent.id == agent.id
                    for existing_agent in selected_group.agents
                )

                if not agent_in_group:
                    logger.info(
                        f"Adding existing agent {name} (ID: {agent.id}) to group {selected_group.name}"
                    )
                    selected_group.agents.append(agent)
                    logger.info(f"Group now has {len(selected_group.agents)} agents")
            else:
                # Create new agent
                agent = Agent(
                    name=name,
                    model=model,
                    system_prompt=system_prompt,
                    tools=selected_tools,
                )
                logger.info(f"Created new agent {agent.name} (ID: {agent.id})")
                selected_group.agents.append(agent)
                logger.info(f"Added agent to group {selected_group.name}")

            # Reset editing state
            st.session_state.editing_agent = None
            logger.info("Reset editing_agent to None")

            # Save changes to disk
            save_agents()
            logger.info("Saved changes to disk")

            # Show success message
            st.success(f"Agent '{name}' saved successfully!")
            st.rerun()


def render_group_editor():
    """Render the group creation form"""
    logger.info("Rendering group editor")
    st.subheader("Create New Agent Group")

    with st.form("group_editor"):
        name = st.text_input("Group Name")
        description = st.text_area("Description")

        if st.form_submit_button("Create Group"):
            logger.info(f"Create Group button clicked for group: {name}")

            if not name:
                logger.warning("Group name is required but was empty")
                st.error("Group name is required")
                return

            # Create new group
            group = AgentGroup(name=name, description=description)
            logger.info(f"Created new group {group.name} (ID: {group.id})")

            # Add to session state
            if "agent_groups" not in st.session_state:
                st.session_state["agent_groups"] = []
            st.session_state["agent_groups"].append(group)
            st.session_state.selected_group = group
            logger.info(f"Added group to session state and set as selected_group")

            # Save to disk
            save_agents()
            st.rerun()


def render_group_view(group: AgentGroup):
    """Render the group details view"""
    logger.info(f"Rendering group view for {group.name}")
    st.subheader(f"Group: {group.name}")
    st.markdown(process_markdown(group.description))

    # Group actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add New Agent"):
            logger.info(f"Add New Agent button clicked for group {group.name}")
            # Create a new empty agent and set it as editing_agent
            st.session_state.editing_agent = Agent(
                name="", model="", system_prompt="", tools=[]
            )
            logger.info("Created empty agent and set as editing_agent")
            st.rerun()
    with col2:
        if st.button("Delete Group"):
            logger.info(f"Delete Group button clicked for group {group.name}")
            st.session_state["agent_groups"].remove(group)
            st.session_state.selected_group = None
            save_agents()
            st.rerun()

    # Display agents in this group
    st.write("### Agents")
    if not group.agents:
        st.info("No agents in this group yet")
    else:
        # Sort agents by name for consistent display
        sorted_agents = sorted(group.agents, key=lambda a: a.name)

        for i, agent in enumerate(sorted_agents):
            try:
                with st.expander(f"{agent.name} ({agent.model})"):
                    st.markdown(f"**System Prompt:**")
                    st.markdown(process_markdown(agent.system_prompt))

                    if agent.tools:
                        tool_names = [t["function"]["name"] for t in agent.tools]
                        st.markdown(f"**Tools:** {', '.join(tool_names)}")
                    else:
                        st.markdown("**Tools:** None")

                    # Display agent ID for debugging - using checkbox instead of nested expander
                    show_debug = st.checkbox("Show Debug Info", key=f"debug_{agent.id}")
                    if show_debug:
                        st.markdown(f"**Agent ID:** {agent.id}")
                        st.markdown(f"**Model:** {agent.model}")
                        st.markdown(f"**Created At:** {agent.created_at}")
                        st.markdown("---")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Edit", key=f"edit_{i}"):
                            logger.info(
                                f"Edit button clicked for agent {agent.name} (ID: {agent.id})"
                            )
                            # Store a reference to the actual agent object
                            st.session_state.editing_agent = agent
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"delete_{i}"):
                            logger.info(
                                f"Delete button clicked for agent {agent.name} (ID: {agent.id})"
                            )
                            group.agents.remove(agent)
                            if save_agents():
                                st.success(
                                    f"Agent '{agent.name}' deleted successfully!"
                                )
                            else:
                                st.error(
                                    f"Failed to save changes after deleting agent '{agent.name}'"
                                )
                            st.rerun()
            except Exception as e:
                st.error(f"Error displaying agent: {str(e)}")
                logger.error(f"Error displaying agent: {str(e)}")
                logger.info(f"Exception details: {traceback.format_exc()}")


def render_task_executor(group: AgentGroup):
    """Render the task execution interface"""
    logger.info(f"Rendering task executor for group {group.name}")
    st.subheader("Task Execution")

    if not group.agents:
        st.warning("Add at least one agent to the group before executing tasks")
        return

    task = st.text_area("Enter task for the agent group", height=100)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Execute with Manager"):
            if not task:
                st.error("Please enter a task")
                return

            logger.info(f"Execute Task button clicked for group {group.name}")
            st.write("### Execution Progress")

            with st.spinner("Executing task..."):
                result = group.execute_task_with_manager(task)

                if result["status"] == "success":
                    st.success("Task completed successfully")

                    # Display plan
                    with st.expander("Execution Plan", expanded=True):
                        st.markdown(f"**Thought Process:**")
                        st.markdown(process_markdown(result["plan"]["thought_process"]))
                        st.markdown("**Steps:**")
                        for i, step in enumerate(result["plan"]["steps"]):
                            st.markdown(
                                f"{i+1}. Assign to **{step['agent']}**: {step['task']}"
                            )
                            if "reason" in step:
                                st.markdown(f"   *Reason: {step['reason']}*")

                    # Display results
                    with st.expander("Execution Results", expanded=True):
                        for i, step_result in enumerate(result["results"]):
                            if step_result["result"]["status"] == "success":
                                st.markdown(f"**{step_result['agent']}**:")
                                st.markdown(
                                    process_markdown(step_result["result"]["response"])
                                )
                            else:
                                st.error(
                                    f"**{step_result['agent']}**: Error - {step_result['result'].get('error', 'Unknown error')}"
                                )

                    # Display summary
                    with st.expander("Summary", expanded=True):
                        st.markdown(f"**Outcome:** {result['outcome']}")
                        st.markdown(f"**Summary:**")
                        st.markdown(process_markdown(result["summary"]))
                        if result.get("next_steps"):
                            st.markdown("**Next Steps:**")
                            for step in result["next_steps"]:
                                st.markdown(f"- {step}")
                else:
                    logger.error(
                        f"Agent task execution failed: {result.get('error', 'Unknown error')}"
                    )
                    st.error(
                        f"Task execution failed: {result.get('error', 'Unknown error')}"
                    )

    with col2:
        agent_options = [agent.name for agent in group.agents]
        selected_agent = ""
        if agent_options:
            selected_agent = st.selectbox(
                "Select Agent",
                options=agent_options,
                format_func=lambda x: f"🤖 {x}",
            )
            logger.info(f"Agent selected in dropdown: {selected_agent}")

        if st.button("Execute with Selected Agent"):
            logger.info(f"Execute with Selected Agent button clicked: {selected_agent}")

            if not task or not selected_agent:
                logger.warning("Task or agent selection is missing")
                st.error("Please enter a task and select an agent")
                return

            agent = next((a for a in group.agents if a.name == selected_agent), None)
            if agent:
                logger.info(f"Executing task with agent {agent.name}: {task[:50]}...")
                with st.spinner(f"Agent {agent.name} is working on the task..."):
                    result = agent.execute_task(task)

                    if result["status"] == "success":
                        logger.info(f"Agent {agent.name} completed task successfully")
                        st.success("Task completed!")

                        # Show detailed agent response
                        with st.expander("🤖 Agent Response", expanded=True):
                            st.markdown("### Thought Process")
                            st.markdown(process_markdown(result["thought_process"]))

                            st.markdown("### Response")
                            st.markdown(process_markdown(result["response"]))

                            if result.get("tool_calls"):
                                st.markdown("### Tools Used")
                                for tool_call in result["tool_calls"]:
                                    tool_name = tool_call["tool"]
                                    tool_input = json.dumps(
                                        tool_call["input"], indent=2
                                    )
                                    st.markdown(f"**Tool**: {tool_name}")
                                    st.markdown(f"```json\n{tool_input}\n```")

                        # Show memory context
                        with st.expander("💭 Agent Memory"):
                            recent_memories = agent.memory[-5:] if agent.memory else []
                            for memory in recent_memories:
                                timestamp = memory["timestamp"]
                                source = memory["source"]
                                content = memory["content"]

                                st.markdown(f"**{source}** ({timestamp})")
                                st.markdown(process_markdown(content))
                                st.markdown("---")
                    else:
                        logger.error(
                            f"Agent task execution failed: {result.get('error', 'Unknown error')}"
                        )
                        st.error(
                            f"Task execution failed: {result.get('error', 'Unknown error')}"
                        )


def load_agents():
    """Load saved agent groups from disk"""
    logger.info("Loading agent groups from disk")

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "app",
        "data",
        "agents",
    )
    os.makedirs(data_dir, exist_ok=True)
    logger.info(f"Agent data directory: {data_dir}")

    try:
        path = os.path.join(data_dir, "agent_groups.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} agent groups from {path}")
                st.session_state["agent_groups"] = [
                    AgentGroup.from_dict(group_data) for group_data in data
                ]

                # Log details of loaded groups
                for group in st.session_state["agent_groups"]:
                    logger.info(
                        f"Loaded group: {group.name} with {len(group.agents)} agents"
                    )
                    for agent in group.agents:
                        logger.info(f"  - Agent: {agent.name} (ID: {agent.id})")
        else:
            logger.info(
                f"Agent groups file not found at {path}. Starting with empty list."
            )
    except Exception as e:
        logger.error(f"Error loading agent groups: {str(e)}")
        logger.info(f"Exception details: {traceback.format_exc()}")


def save_agents():
    """Save agent groups to disk"""
    logger.info("Saving agent groups to disk")

    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "app",
        "data",
        "agents",
    )

    try:
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)

        path = os.path.join(data_dir, "agent_groups.json")
        logger.info(f"Will save to path: {path}")

        # Verify that agent_groups exists in session state
        if "agent_groups" not in st.session_state:
            logger.warning("No agent_groups in session state, initializing empty list")
            st.session_state["agent_groups"] = []

        # Convert groups to dict format
        data = []
        for group in st.session_state["agent_groups"]:
            try:
                group_dict = group.to_dict()
                data.append(group_dict)

                # Log detailed information about each agent for debugging
                logger.info(
                    f"Group: {group.name} (ID: {group.id}) has {len(group.agents)} agents"
                )
                for agent in group.agents:
                    logger.info(f"  - Agent: {agent.name} (ID: {agent.id})")
                    logger.info(f"    Model: {agent.model}")
                    logger.info(f"    System prompt length: {len(agent.system_prompt)}")
                    logger.info(f"    Tools: {len(agent.tools)}")
            except Exception as e:
                logger.error(f"Error converting group {group.name} to dict: {str(e)}")
                logger.info(f"Exception details: {traceback.format_exc()}")

        # Create a backup of the existing file if it exists
        if os.path.exists(path):
            backup_path = f"{path}.bak"
            try:
                import shutil

                shutil.copy2(path, backup_path)
                logger.info(f"Created backup of agent groups file at {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {str(e)}")

        # Write to file with proper encoding
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully saved {len(data)} agent groups to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving agent groups: {str(e)}")
        logger.info(f"Exception details: {traceback.format_exc()}")
        return False
