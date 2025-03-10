"""
UI components for the agents page.
"""

import streamlit as st
import os
import json
import traceback
import re
from typing import Dict, List, Any, Optional
import time
from datetime import datetime
import uuid

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.tool_loader import ToolLoader
from app.utils.agents.agent import Agent
from app.utils.agents.agent_group import AgentGroup

# Get application logger
logger = get_logger()


def parse_agent_directives(task: str, available_agents: List[Agent]) -> Dict[str, str]:
    """
    Parse @agent_name directives in the task text

    Args:
        task: The task text to parse
        available_agents: List of available agents

    Returns:
        Dictionary mapping agent names to their subtasks
    """
    logger.info(f"Parsing agent directives in task: {task[:50]}...")

    # Get list of agent names
    agent_names = [agent.name.lower() for agent in available_agents]

    # Check for @agent_name pattern
    directives = {}

    # Use regex pattern that matches @name: followed by text until the next @name: or end of string
    pattern = r'@([^:]+):(.*?)(?=@[^:]+:|$)'
    matches = re.findall(pattern, task, re.DOTALL)

    for agent_name, subtask in matches:
        agent_name = agent_name.strip().lower()
        subtask = subtask.strip()

        # Check if this is a valid agent
        for available_name in agent_names:
            if agent_name == available_name.lower():
                # Use the correctly cased agent name
                correct_name = next(a.name for a in available_agents if a.name.lower() == agent_name)
                directives[correct_name] = subtask
                logger.info(f"Found directive for agent {correct_name}: {subtask[:30]}...")
                break
        else:
            logger.warning(f"Directive for unknown agent '{agent_name}' found in task")

    return directives


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

                # Find the agent in the group by ID and update it
                for i, existing_agent in enumerate(selected_group.agents):
                    if existing_agent.id == agent.id:
                        logger.info(
                            f"Found agent {agent.name} (ID: {agent.id}) in group at index {i}"
                        )
                        # Replace the agent in the group with the updated version
                        selected_group.agents[i] = agent
                        logger.info(
                            f"Updated agent in group: {agent.name} (ID: {agent.id}, Model: {agent.model})"
                        )
                        break
                else:
                    # Agent not found in group, add it
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
    """Render the details of an agent group (without tabs)."""
    st.subheader(f"Group: {group.name}")

    # Display group details
    st.markdown(f"**Description**: {group.description}")
    st.markdown(f"**Created**: {group.created_at}")
    st.markdown(f"**Number of Agents**: {len(group.agents)}")

    # Display the agents in this group
    st.subheader("Agents in this Group")
    for agent in group.agents:
        with st.expander(f"{agent.name} ({agent.model})"):
            st.markdown(f"**ID**: {agent.id}")
            st.markdown(f"**Model**: {agent.model}")
            st.markdown("**System Prompt**:")
            st.markdown(f"```\n{agent.system_prompt}\n```")

            if agent.tools:
                st.markdown("**Tools**:")
                for tool in agent.tools:
                    st.markdown(f"- {tool['function']['name']}: {tool['function']['description']}")

            # Buttons for agent actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Edit Agent", key=f"edit_{agent.id}"):
                    st.session_state.editing_agent = agent
                    st.session_state.editing_agent_original_group = group
            with col2:
                if st.button("Delete Agent", key=f"delete_{agent.id}"):
                    confirm_delete = st.checkbox("Confirm deletion", key=f"confirm_{agent.id}")
                    if confirm_delete:
                        group.agents = [a for a in group.agents if a.id != agent.id]
                        save_agents()
                        st.success(f"Agent {agent.name} deleted!")
                        st.rerun()

    # Display shared memory
    if group.shared_memory:
        st.subheader("Shared Memory")
        with st.expander("View Shared Memory"):
            for memory in group.shared_memory[-10:]:
                st.markdown(f"**{memory['source']}** ({memory['timestamp']})")
                st.markdown(memory['content'])
                st.markdown("---")

    # Add group actions
    st.subheader("Group Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add New Agent"):
            # Create a new empty agent and set it as editing_agent
            st.session_state.editing_agent = Agent(
                name="", model="", system_prompt="", tools=[]
            )
            st.rerun()
    with col2:
        if st.button("Delete Group"):
            confirm_delete = st.checkbox("Confirm group deletion")
            if confirm_delete:
                if group in st.session_state.get("agent_groups", []):
                    st.session_state["agent_groups"].remove(group)
            st.session_state.selected_group = None
            save_agents()
            st.rerun()


def render_task_executor(group: AgentGroup):
    """Render the task execution UI for an agent group."""
    # Check if we're in continuation mode
    in_continuation_mode = st.session_state.get("in_continuation_mode", False)

    # Create the task input
    if in_continuation_mode:
        # Display an indicator that we're in continuation mode
        st.info("✨ You are continuing from a previous task")

        # Add a button to exit continuation mode
        if st.button("❌ Exit Continuation Mode"):
            st.session_state.in_continuation_mode = False
            if "current_task" in st.session_state:
                del st.session_state.current_task
            if "target_agent" in st.session_state:
                del st.session_state.target_agent
            st.rerun()

    # Task input field
    task = st.text_area(
        "Enter task for agents",
        value=st.session_state.get("current_task", ""),
        height=150,
        help="Enter a natural language task for the agent group. You can use @AgentName: syntax to direct parts of the task to specific agents."
    )

    # If we're in continuation mode, show the editable continuation prompt
    if in_continuation_mode:
        # Update the session state with the edited task
        st.session_state.current_task = task

        # Show agent targeting options for continuation
        st.subheader("Agent Targeting")

        # Check if there are @agent directives in the task
        directives = parse_agent_directives(task, group.agents)

        if directives:
            # Display the detected directives
            st.success(f"Detected directives for {len(directives)} agents: {', '.join(directives.keys())}")
            agent_targeting = "directive"
        else:
            # If no directives, show targeting options
            target_options = ["All Agents (Manager Coordinated)"]

            # Add a "Multiple Agents" option
            target_options.append("Select Multiple Agents")

            # Add individual agents
            target_options.extend([agent.name for agent in group.agents])

            # Pre-select the agent that was used in the previous execution if available
            default_index = 0
            if "target_agent" in st.session_state and st.session_state.target_agent:
                if st.session_state.target_agent in [agent.name for agent in group.agents]:
                    default_index = target_options.index(st.session_state.target_agent)

            target = st.selectbox(
                "Direct this continuation to:",
                options=target_options,
                index=default_index,
                help="Select which agent(s) should handle this continuation. Choose 'Select Multiple Agents' to target a subset."
            )

            # If "Select Multiple Agents" is chosen, show multiselect
            if target == "Select Multiple Agents":
                agent_names = [agent.name for agent in group.agents]
                selected_agents = st.multiselect(
                    "Select agents to include:",
                    options=agent_names,
                    default=st.session_state.get("selected_agents", []),
                    help="Choose which agents should process this task."
                )

                # Store selected agents in session state
                st.session_state.selected_agents = selected_agents
                agent_targeting = "multi_agent"

                # Show selected agents
                if selected_agents:
                    st.success(f"Task will be sent to: {', '.join(selected_agents)}")
                else:
                    st.warning("Please select at least one agent")
            # Store the selected agent in session state
            elif target != "All Agents (Manager Coordinated)":
                st.session_state.target_agent = target
                agent_targeting = "specific"
            else:
                st.session_state.target_agent = ""
                agent_targeting = "manager"

        # If user is continuing, add an option to include parent task ID for tracking the continuation chain
        if "parent_execution_id" not in st.session_state:
            st.session_state.parent_execution_id = None

        if "agent_execution_results" in st.session_state:
            parent_result = st.session_state.agent_execution_results
            if "history_id" in parent_result:
                st.session_state.parent_execution_id = parent_result["history_id"]

        # Store parent/child relationships for continuation chains
        track_chain = st.checkbox(
            "Track continuation chain",
            value=True,
            help="Adds metadata to link this continuation with its parent execution"
        )

        # Help section for agent targeting
        with st.expander("ℹ️ Agent Targeting Help"):
            st.markdown("""
            ### You can target specific agents in two ways:

            1. **Using the dropdown above**: Select a specific agent from the dropdown

            2. **Using @agent_name syntax**: Include directives in your prompt like:
               ```
               @ResearchAgent: Find information about quantum computing.
               @CodeAgent: Write a Python function to calculate fibonacci numbers.
               ```

            The system will automatically detect @agent directives and route tasks accordingly.

            You can combine multiple agent directives in a single continuation for parallel execution.
            """)

        # Execute continuation button
        cont_col1, cont_col2 = st.columns([1, 5])
        with cont_col1:
            execute_button = st.button("▶️ Execute Continuation", type="primary")
        with cont_col2:
            st.markdown(f"**Targeting:** {'Multiple Agents via Directives' if agent_targeting == 'directive' else ('Manager Coordination' if agent_targeting == 'manager' else f'Specific Agent ({st.session_state.target_agent})')}")

    # Normal execution mode (not continuation)
    else:
        # If task is empty, skip execution
        if not task.strip():
            st.warning("Please enter a task")
            return

        # Check if there are @agent directives in the task
        directives = parse_agent_directives(task, group.agents)

        if directives:
            # Display the detected directives
            st.success(f"Detected directives for {len(directives)} agents: {', '.join(directives.keys())}")
            st.write("Executing with detected agent directives...")

            with st.spinner("Processing..."):
                result = execute_task_with_directives(group, task, directives)

            # Store in session state for continuation with history ID
            history_id = result.get("history_id", str(uuid.uuid4()))
            st.session_state.agent_execution_results = {
                "type": "directive",
                "task": task,
                "result": result,
                "directives": directives,
                "timestamp": datetime.now().isoformat(),
                "history_id": history_id
            }

            # Display results
            display_directive_results(result, directives)

        else:
            # Use tabs for execution options
            exec_tab1, exec_tab2, exec_tab3 = st.tabs(["Execute with Manager", "Execute with Specific Agent", "Execute with Multiple Agents"])

            with exec_tab1:
                # Manager execution button
                if st.button("▶️ Execute with Manager", type="primary"):
                    with st.spinner("Manager processing task..."):
                        result = group.execute_task_with_manager(task)

                        # Store in session state for continuation with history ID
                        history_id = str(uuid.uuid4())
                        st.session_state.agent_execution_results = {
                            "type": "manager",
                            "task": task,
                            "result": result,
                            "timestamp": datetime.now().isoformat(),
                            "history_id": history_id
                        }

                        # Display results
                        display_manager_results(result)

            with exec_tab2:
                # Agent selection
                agent_name = st.selectbox(
                    "Select agent",
                    options=[agent.name for agent in group.agents],
                    help="Choose which agent to execute this task"
                )

                # Specific agent execution button
                if st.button("▶️ Execute with Selected Agent", type="primary"):
                    with st.spinner(f"Agent {agent_name} processing..."):
                        result = execute_with_agent(group, agent_name, task)

                    # Store in session state for continuation with history ID
                    history_id = str(uuid.uuid4())
                    st.session_state.agent_execution_results = {
                        "type": "single_agent",
                        "task": task,
                        "result": result,
                        "agent_name": agent_name,
                        "timestamp": datetime.now().isoformat(),
                        "history_id": history_id
                    }

                    # Display results
                    display_agent_results(result, agent_name, group)

            with exec_tab3:
                # Multiple agent selection
                agent_names = [agent.name for agent in group.agents]
                selected_agents = st.multiselect(
                    "Select agents to include:",
                    options=agent_names,
                    help="Choose which agents should process this task."
                )

                # Multi-agent execution button
                if st.button("▶️ Execute with Selected Agents", type="primary"):
                    if not selected_agents:
                        st.warning("Please select at least one agent")
                    else:
                        with st.spinner(f"Processing with {len(selected_agents)} agents..."):
                            result = execute_with_multiple_agents(group, task, selected_agents)

                        # Store in session state for continuation with history ID
                        history_id = result.get("history_id", str(uuid.uuid4()))
                        st.session_state.agent_execution_results = {
                            "type": "multi_agent",
                            "task": task,
                            "result": result,
                            "agent_names": selected_agents,
                            "timestamp": datetime.now().isoformat(),
                            "history_id": history_id
                        }

                        # Display results
                        display_directive_results(result, {agent_name: task for agent_name in selected_agents})

    # Handle continuation execution
    if in_continuation_mode and execute_button:
        # Store whether to track the continuation chain
        st.session_state.track_chain = track_chain

        with st.spinner("Processing continuation..."):
            # Check if there are directives in the prompt
            if directives:
                result = execute_task_with_directives(group, task, directives)

                # Store in session state with history ID
                history_id = result.get("history_id", str(uuid.uuid4()))
                st.session_state.agent_execution_results = {
                    "type": "directive",
                    "task": task,
                    "result": result,
                    "directives": directives,
                    "timestamp": datetime.now().isoformat(),
                    "history_id": history_id
                }

                # Add parent/child relationship for continuation chains
                if st.session_state.get("parent_execution_id") and st.session_state.get("track_chain", True):
                    st.session_state.agent_execution_results["parent_id"] = st.session_state.parent_execution_id

                # Display results
                display_directive_results(result, directives)

            # If targeting multiple agents
            elif agent_targeting == "multi_agent" and st.session_state.get("selected_agents"):
                selected_agents = st.session_state.selected_agents
                result = execute_with_multiple_agents(group, task, selected_agents)

                # Store in session state with history ID
                history_id = result.get("history_id", str(uuid.uuid4()))
                st.session_state.agent_execution_results = {
                    "type": "multi_agent",
                    "task": task,
                    "result": result,
                    "agent_names": selected_agents,
                    "timestamp": datetime.now().isoformat(),
                    "history_id": history_id
                }

                # Add parent/child relationship for continuation chains
                if st.session_state.get("parent_execution_id") and st.session_state.get("track_chain", True):
                    st.session_state.agent_execution_results["parent_id"] = st.session_state.parent_execution_id

                # Display results
                display_directive_results(result, {agent_name: task for agent_name in selected_agents})

            # If targeting a specific agent
            elif st.session_state.get("target_agent"):
                agent_name = st.session_state.target_agent
                result = execute_with_agent(group, agent_name, task)

                # Store in session state with history ID
                history_id = str(uuid.uuid4())
                st.session_state.agent_execution_results = {
                    "type": "single_agent",
                    "task": task,
                    "result": result,
                    "agent_name": agent_name,
                    "timestamp": datetime.now().isoformat(),
                    "history_id": history_id
                }

                # Add parent/child relationship for continuation chains
                if st.session_state.get("parent_execution_id") and st.session_state.get("track_chain", True):
                    st.session_state.agent_execution_results["parent_id"] = st.session_state.parent_execution_id

                # Display results
                display_agent_results(result, agent_name, group)

            # Default to manager
            else:
                result = group.execute_task_with_manager(task)

                # Store in session state with history ID
                history_id = str(uuid.uuid4())
                st.session_state.agent_execution_results = {
                    "type": "manager",
                    "task": task,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                    "history_id": history_id
                }

                # Add parent/child relationship for continuation chains
                if st.session_state.get("parent_execution_id") and st.session_state.get("track_chain", True):
                    st.session_state.agent_execution_results["parent_id"] = st.session_state.parent_execution_id

                # Display results
                display_manager_results(result)

        # Reset continuation mode after execution
        st.session_state.in_continuation_mode = False

        # Clear parent execution ID after using it
        st.session_state.parent_execution_id = None

    # Display results if available in session state (but not in continuation mode)
    if not in_continuation_mode and "agent_execution_results" in st.session_state:
        results_data = st.session_state.agent_execution_results

        # Clear button for results
        if st.button("🗑️ Clear Results"):
            del st.session_state.agent_execution_results
            st.rerun()

        # Display based on result type
        if results_data["type"] == "manager":
            display_manager_results(results_data["result"])
        elif results_data["type"] == "single_agent":
            display_agent_results(results_data["result"], results_data["agent_name"], group)
        elif results_data["type"] == "directive":
            display_directive_results(results_data["result"], results_data.get("directives", {}))
        elif results_data["type"] == "multi_agent":
            display_directive_results(
                results_data["result"],
                {agent_name: results_data["task"] for agent_name in results_data.get("agent_names", [])}
            )

        # Show continuation information if this was a continuation itself
        if "parent_id" in results_data:
            st.info(f"This execution continues from a previous task (ID: {results_data['parent_id']})")

        # Show continuation button
        st.markdown("### Continue from these results")
        if st.button("✨ Prepare Continuation"):
            # Format previous task and results for continuation
            formatted_result = get_formatted_result(results_data)

            continuation_prompt = f"""Previous task: {results_data['task']}

Result:
{formatted_result}

Continue from here:
"""
            # Set in session state
            st.session_state.current_task = continuation_prompt
            st.session_state.in_continuation_mode = True

            # Store the parent execution ID for the continuation chain
            if "history_id" in results_data:
                st.session_state.parent_execution_id = results_data["history_id"]

            # Set targeting based on previous execution
            if results_data["type"] == "single_agent":
                st.session_state.target_agent = results_data["agent_name"]
                st.session_state.selected_agents = []
            elif results_data["type"] == "multi_agent":
                st.session_state.target_agent = ""
                st.session_state.selected_agents = results_data.get("agent_names", [])
            else:
                st.session_state.target_agent = ""
                st.session_state.selected_agents = []

            st.rerun()


def get_formatted_result(results_data: Dict[str, Any]) -> str:
    """Format the result based on its type for continuation."""
    result_type = results_data.get("type")
    result = results_data.get("result", {})

    if result_type == "manager":
        return f"Summary: {result.get('summary', '')}\n\nOutcome: {result.get('outcome', '')}"

    elif result_type == "single_agent":
        return result.get("response", "")

    elif result_type == "directive":
        # Return the combined response for directives
        return result.get("response", "")

    return "No result available."


def display_manager_results(result: Dict[str, Any]):
    """Display the results from a manager execution."""
    if result.get("status") == "error":
        st.error(f"Error: {result.get('message', 'Unknown error')}")
        return

    # Display the results in tabs
    plan_tab, results_tab, summary_tab = st.tabs(["Plan", "Results", "Summary"])

    with plan_tab:
        st.subheader("Manager's Plan")
        plan = result.get("plan", {})

        # Display thought process
        st.markdown("### Thought Process")
        st.markdown(process_markdown(plan.get("thought_process", "No thought process provided")))

        # Display steps
        st.markdown("### Execution Steps")
        for i, step in enumerate(plan.get("steps", [])):
            with st.expander(f"Step {i+1}: {step.get('agent')} - {step.get('task')[:50]}..."):
                st.markdown(f"**Agent**: {step.get('agent')}")
                st.markdown(f"**Task**: {step.get('task')}")
                st.markdown(f"**Reason**: {step.get('reason')}")

    with results_tab:
        st.subheader("Agent Results")
        for i, agent_result in enumerate(result.get("results", [])):
            agent_name = agent_result.get("agent")
            agent_data = agent_result.get("result", {})

            with st.expander(f"{agent_name} - {agent_data.get('response', '')[:50]}..."):
                # Display response
                st.markdown("### Response")
                st.markdown(process_markdown(agent_data.get("response", "No response provided")))

                # If available, show thought process
                if "thought_process" in agent_data:
                    st.markdown("### Thought Process")
                    st.markdown(process_markdown(agent_data.get("thought_process", "")))

    with summary_tab:
        st.subheader("Execution Summary")

        # Display summary
        st.markdown("### Summary")
        st.markdown(process_markdown(result.get("summary", "No summary provided")))

        # Display outcome
        st.markdown("### Outcome")
        st.markdown(process_markdown(result.get("outcome", "No outcome provided")))

        # Display next steps if available
        if "next_steps" in result and result["next_steps"]:
            st.markdown("### Next Steps")
            for step in result["next_steps"]:
                st.markdown(f"- {step}")


def display_agent_results(result: Dict[str, Any], agent_name: str, group: AgentGroup):
    """Display the results from a single agent execution."""
    if result.get("status") == "error":
        st.error(f"Error: {result.get('message', 'Unknown error')}")
        return

    st.subheader(f"Results from {agent_name}")

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

    # Show memory context in a separate expander (not nested)
    with st.expander("💭 Agent Memory", expanded=False):
        # Find the agent to get its memory
        agent = next((a for a in group.agents if a.name == agent_name), None)
        if agent:
                            recent_memories = agent.memory[-5:] if agent.memory else []
                            for memory in recent_memories:
                                timestamp = memory["timestamp"]
                                source = memory["source"]
                                content = memory["content"]

                                st.markdown(f"**{source}** ({timestamp})")
                                st.markdown(process_markdown(content))
                                st.markdown("---")
        else:
            st.info("No memory found for this agent")


def display_directive_results(result: Dict[str, Any], directives: Dict[str, str]):
    """Display the results from a directive-based execution."""
    if result.get("status") == "error":
        st.error(f"Error: {result.get('message', 'Unknown error')}")
        return

    st.subheader("Agent Execution Results")

    # Show directives
    with st.expander("📋 Agent Directives", expanded=True):
        st.markdown("The following agents were targeted with specific tasks:")
        for agent_name, subtask in directives.items():
            st.markdown(f"**@{agent_name}**: {subtask}")

    # Show combined response
    st.markdown("### Combined Response")
    st.markdown(process_markdown(result.get("response", "No response available")))

    # Show individual agent results
    with st.expander("🔍 Individual Agent Results", expanded=False):
        for agent_result in result.get("individual_results", []):
            agent_name = agent_result.get("agent")
            agent_data = agent_result.get("result", {})

            st.markdown(f"### {agent_name}")

            if agent_data.get("status") == "error":
                st.error(f"Error: {agent_data.get('message', 'Unknown error')}")
            else:
                # Process the response (handle JSON format if needed)
                response = agent_data.get("response", "No response provided")
                thought_process = agent_data.get("thought_process", "")

                # Try to detect if response is a JSON string with thought_process and response
                if isinstance(response, str) and response.strip().startswith("{") and response.strip().endswith("}"):
                    try:
                        # Try to parse JSON response
                        import json
                        parsed_json = json.loads(response)

                        # Extract fields if they exist
                        if isinstance(parsed_json, dict):
                            if "response" in parsed_json:
                                response = parsed_json.get("response", "")
                            if "thought_process" in parsed_json and not thought_process:
                                thought_process = parsed_json.get("thought_process", "")
                    except:
                        # If parsing fails, use the original response
                        logger.warning(f"Failed to parse JSON response from agent {agent_name}")

                # Display response
                st.markdown("#### Response")
                st.markdown(process_markdown(response))

                # If available, show thought process
                if thought_process:
                    st.markdown("#### Thought Process")
                    st.markdown(process_markdown(thought_process))

            st.markdown("---")


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

                # Clear existing groups if any
                if "agent_groups" in st.session_state:
                    st.session_state["agent_groups"] = []

                # Create agent groups from loaded data
                st.session_state["agent_groups"] = [
                    AgentGroup.from_dict(group_data) for group_data in data
                ]

                # Log details of loaded groups
                for group in st.session_state["agent_groups"]:
                    logger.info(
                        f"Loaded group: {group.name} (ID: {group.id}) with {len(group.agents)} agents"
                    )
                    for agent in group.agents:
                        logger.info(
                            f"  - Agent: {agent.name} (ID: {agent.id}, Model: {agent.model})"
                        )
        else:
            logger.info(
                f"Agent groups file not found at {path}. Starting with empty list."
            )
            # Initialize empty list if file doesn't exist
            st.session_state["agent_groups"] = []
    except Exception as e:
        logger.error(f"Error loading agent groups: {str(e)}")
        logger.info(f"Exception details: {traceback.format_exc()}")
        # Initialize empty list on error
        st.session_state["agent_groups"] = []


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
                # Log the group and agent IDs before saving
                logger.info(f"Saving group: {group.name} (ID: {group.id})")
                for agent in group.agents:
                    logger.info(
                        f"  - Saving agent: {agent.name} (ID: {agent.id}, Model: {agent.model})"
                    )

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

        # Log the actual JSON data being saved
        try:
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            logger.info(
                f"JSON data to be saved (first 500 chars): {json_data[:500]}..."
            )
        except Exception as e:
            logger.error(f"Error serializing JSON data: {str(e)}")

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
            # Ensure data is flushed to disk
            f.flush()
            os.fsync(f.fileno())

        # Force a sync to ensure file is written to disk
        time.sleep(0.1)  # Small delay to ensure file system has time to complete write

        logger.info(f"Successfully saved {len(data)} agent groups to {path}")

        # Verify the file was written correctly
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                logger.info(f"Verified saved file contains {len(saved_data)} groups")
                # Check if the first group has the expected agents
                if saved_data and saved_data[0]["agents"]:
                    for agent in saved_data[0]["agents"]:
                        logger.info(
                            f"  - Verified agent: {agent['name']} (Model: {agent['model']})"
                        )
        except Exception as e:
            logger.error(f"Error verifying saved file: {str(e)}")

        return True
    except Exception as e:
        logger.error(f"Error saving agent groups: {str(e)}")
        logger.info(f"Exception details: {traceback.format_exc()}")
        return False


def execute_with_agent(group: AgentGroup, agent_name: str, task: str) -> Dict[str, Any]:
    """Execute a task with a specific agent."""
    try:
        # Find the agent by name
        agent = next((a for a in group.agents if a.name == agent_name), None)
        if not agent:
            return {"status": "error", "message": f"Agent '{agent_name}' not found in group '{group.name}'"}

        start_time = time.time()
        result = agent.execute_task(task)
        execution_time = time.time() - start_time

        # Add to agent memory
        agent.add_to_memory(f"Task: {task}\nResponse: {result['response']}", "execution")

        # Add to group shared memory
        group.add_shared_memory(
            f"Agent {agent_name} processed: {task}\nResult: {result['response']}",
            source="agent_execution"
        )

        # Record in history
        history_entry = {
            "type": "single_agent_execution",
            "task": task,
            "agents_involved": [agent_name],
            "result": {
                "status": "success",
                "response": result.get("response", ""),
                "thought_process": result.get("thought_process", ""),
                "tool_calls": result.get("tool_calls", [])
            },
            "execution_time": execution_time
        }
        history_id = group.add_to_history(history_entry)
        logger.info(f"Added execution to history with ID: {history_id}, current history size: {len(group.execution_history)}")

        # Save changes to disk
        save_agents()
        logger.info(f"Saved agent groups with updated history to disk")

        return result
    except Exception as e:
        logger.error(f"Error executing task with agent {agent_name}: {str(e)}")
        logger.debug(traceback.format_exc())
        return {"status": "error", "message": str(e)}


def execute_task_with_directives(group: AgentGroup, task: str, directives: Dict[str, str]) -> Dict:
    """Execute a task with agent directives."""
    combined_results = []
    agents_involved = []
    start_time = time.time()

    for agent_name, subtask in directives.items():
        logger.info(f"Executing directive for agent {agent_name}: {subtask}")
        agent = next((a for a in group.agents if a.name == agent_name), None)
        if not agent:
            combined_results.append({
                "agent": agent_name,
                "result": {
                    "status": "error",
                    "message": f"Agent '{agent_name}' not found in group '{group.name}'"
                }
            })
            continue

        result = agent.execute_task(subtask)

        # Add to agent memory
        agent.add_to_memory(f"Task: {subtask}\nResponse: {result['response']}", "execution")

        # Add to group shared memory
        group.add_shared_memory(
            f"Agent {agent_name} processed: {subtask}\nResult: {result['response']}",
            source="agent_directive"
        )

        combined_results.append({
            "agent": agent_name,
            "result": result
        })

        agents_involved.append(agent_name)

    # Combine responses into a single response
    combined_response = "# Agent Responses\n\n"
    for result in combined_results:
        agent_name = result["agent"]
        agent_result = result["result"]
        if agent_result["status"] == "error":
            combined_response += f"## {agent_name}\n\n❌ Error: {agent_result['message']}\n\n"
        else:
            combined_response += f"## {agent_name}\n\n{agent_result['response']}\n\n"

    execution_time = time.time() - start_time

    # Record in history
    history_entry = {
        "type": "directive_execution",
        "task": task,
        "directives": directives,
        "agents_involved": agents_involved,
        "result": {
            "status": "success",
            "response": combined_response,
            "agent_results": combined_results
        },
        "execution_time": execution_time
    }
    history_id = group.add_to_history(history_entry)
    logger.info(f"Added directive execution to history with ID: {history_id}, current history size: {len(group.execution_history)}")

    # Save changes to disk
    save_agents()
    logger.info(f"Saved agent groups with updated history to disk")

    return {
        "status": "success",
        "response": combined_response,
        "directives": directives,
        "individual_results": combined_results,
        "execution_time": execution_time,
        "history_id": history_id
    }


def render_execution_history(group: AgentGroup):
    """Render the execution history for an agent group."""
    if not group.execution_history:
        st.info("No execution history available for this agent group.")
        return

    # Add debug info
    logger.info(f"Rendering execution history for group {group.name}, found {len(group.execution_history)} entries")

    st.subheader("Execution History")

    # Add filters
    col1, col2, col3 = st.columns(3)
    with col1:
        execution_types = ["All Types", "Manager", "Single Agent", "Directive", "Multi-Agent"]
        selected_type = st.selectbox("Filter by type:", execution_types)

    with col2:
        # Get unique agent names from the group
        agent_names = ["All Agents"] + [agent.name for agent in group.agents]
        selected_agent = st.selectbox("Filter by agent:", agent_names)

    with col3:
        # Sorting options
        sort_options = ["Newest First", "Oldest First"]
        sort_order = st.selectbox("Sort by:", sort_options)

    # Filter and sort history
    filtered_history = group.execution_history.copy()

    # Apply type filter
    if selected_type != "All Types":
        type_map = {
            "Manager": "manager_execution",
            "Single Agent": "single_agent_execution",
            "Directive": "directive_execution",
            "Multi-Agent": "multi_agent_execution"
        }
        filter_type = type_map.get(selected_type)
        if filter_type:
            filtered_history = [entry for entry in filtered_history if entry.get("type") == filter_type]

    # Apply agent filter
    if selected_agent != "All Agents":
        filtered_history = [
            entry for entry in filtered_history
            if selected_agent in entry.get("agents_involved", [])
        ]

    # Apply sorting
    filtered_history.sort(
        key=lambda x: x.get("timestamp", ""),
        reverse=(sort_order == "Newest First")
    )

    # Show history count
    st.markdown(f"**Showing {len(filtered_history)} of {len(group.execution_history)} history entries**")

    # Display history entries
    for i, entry in enumerate(filtered_history):
        entry_type = entry.get("type", "unknown")
        timestamp = entry.get("timestamp", "No timestamp")
        task = entry.get("task", "No task")
        agents = ", ".join(entry.get("agents_involved", ["Unknown"]))
        entry_id = entry.get("id", str(i))

        # Get parent/child relationships
        parent_id = entry.get("parent_id", None)
        children = [e for e in group.execution_history if e.get("parent_id") == entry_id]

        # Format the timestamp to be more readable
        try:
            dt = datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp

        # Create a unique key for the expander
        expander_key = f"history_{entry_id}"

        # Create title with parent/child info
        title = f"**{formatted_time}** - "
        if parent_id:
            title += "↪️ "  # Indicate this is a continuation
        if children:
            title += "⤴️ "  # Indicate this has continuations

        title += f"{task[:60]}..." if len(task) > 60 else task

        # Display the entry in an expander
        with st.expander(title):
            st.markdown(f"**ID**: {entry_id}")
            st.markdown(f"**Task**: {task}")
            st.markdown(f"**Type**: {entry_type.replace('_', ' ').title()}")
            st.markdown(f"**Agents Involved**: {agents}")
            st.markdown(f"**Timestamp**: {formatted_time}")

            # Show parent/child relationships
            if parent_id:
                st.markdown(f"**Continues from**: {parent_id}")

            if children:
                child_ids = [child.get("id") for child in children]
                st.markdown(f"**Continued by**: {', '.join(child_ids)}")

            # Display the result based on execution type
            result = entry.get("result", {})

            if entry_type == "manager_execution":
                tabs = st.tabs(["Plan", "Results", "Summary"])
                with tabs[0]:
                    plan = result.get("plan", {})
                    if plan:
                        st.markdown("### Thought Process")
                        st.markdown(process_markdown(plan.get("thought_process", "")))

                        st.markdown("### Steps")
                        for step in plan.get("steps", []):
                            st.markdown(f"**Agent**: {step.get('agent')}")
                            st.markdown(f"**Task**: {step.get('task')}")
                            st.markdown(f"**Reason**: {step.get('reason')}")
                            st.markdown("---")

                with tabs[1]:
                    for result_item in result.get("results", []):
                        agent_name = result_item.get("agent", "Unknown")
                        agent_result = result_item.get("result", {})
                        st.markdown(f"### {agent_name}")
                        st.markdown(process_markdown(agent_result.get("response", "")))
                        st.markdown("---")

                with tabs[2]:
                    st.markdown("### Summary")
                    st.markdown(process_markdown(result.get("summary", "")))

                    st.markdown("### Outcome")
                    st.markdown(process_markdown(result.get("outcome", "")))

                    st.markdown("### Next Steps")
                    for step in result.get("next_steps", []):
                        st.markdown(f"- {step}")

            elif entry_type == "single_agent_execution":
                st.markdown("### Thought Process")
                st.markdown(process_markdown(result.get("thought_process", "")))

                st.markdown("### Response")
                st.markdown(process_markdown(result.get("response", "")))

                if result.get("tool_calls"):
                    st.markdown("### Tools Used")
                    for tool_call in result.get("tool_calls", []):
                        tool_name = tool_call.get("tool", "Unknown")
                        tool_input = json.dumps(tool_call.get("input", {}), indent=2)
                        st.markdown(f"**Tool**: {tool_name}")
                        st.markdown(f"```json\n{tool_input}\n```")

            elif entry_type in ["directive_execution", "multi_agent_execution"]:
                if entry_type == "directive_execution":
                    st.markdown("### Directives")
                    directives = entry.get("directives", {})
                    for agent_name, subtask in directives.items():
                        st.markdown(f"**@{agent_name}**: {subtask}")

                st.markdown("### Response")
                st.markdown(process_markdown(result.get("response", "")))

                st.markdown("### Individual Results")
                for agent_result in result.get("agent_results", []):
                    agent_name = agent_result.get("agent", "Unknown")
                    result_data = agent_result.get("result", {})
                    st.markdown(f"**{agent_name}**:")
                    st.markdown(process_markdown(result_data.get("response", "")))
                    st.markdown("---")

            # Add execution time if available
            if "execution_time" in entry:
                st.markdown(f"**Execution Time**: {entry['execution_time']:.2f} seconds")

            # Add buttons for continuation
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Prepare Continuation from This", key=f"cont_{expander_key}"):
                    prepare_continuation_from_history(entry)

            with col2:
                if st.button("View Continuation Chain", key=f"chain_{expander_key}"):
                    # Find all related entries in the chain
                    chain = get_continuation_chain(group, entry_id)

                    # Display the chain
                    st.markdown("### Continuation Chain")
                    for chain_entry in chain:
                        is_current = chain_entry.get("id") == entry_id
                        prefix = "➡️ " if is_current else "   "
                        chain_id = chain_entry.get("id", "Unknown")
                        chain_type = chain_entry.get("type", "Unknown").replace("_", " ").title()
                        chain_time = chain_entry.get("timestamp", "")
                        try:
                            chain_dt = datetime.fromisoformat(chain_time)
                            chain_time = chain_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            pass

                        st.markdown(f"{prefix} **{chain_id}** - {chain_type} - {chain_time}")


def get_continuation_chain(group: AgentGroup, entry_id: str) -> List[Dict[str, Any]]:
    """Get all entries in a continuation chain, including parents and children."""
    chain = []

    # Find the entry
    entry = next((e for e in group.execution_history if e.get("id") == entry_id), None)
    if not entry:
        return chain

    # Add the entry
    chain.append(entry)

    # Recursively add parents
    parent_id = entry.get("parent_id")
    if parent_id:
        parent_entry = next((e for e in group.execution_history if e.get("id") == parent_id), None)
        if parent_entry:
            parent_chain = get_continuation_chain(group, parent_id)
            # Add parents at the start
            for parent in parent_chain:
                if parent not in chain:
                    chain.insert(0, parent)

    # Add children
    children = [e for e in group.execution_history if e.get("parent_id") == entry_id]
    for child in children:
        child_chain = get_continuation_chain(group, child.get("id"))
        # Add children at the end
        for child_entry in child_chain:
            if child_entry not in chain:
                chain.append(child_entry)

    return chain


def prepare_continuation_from_history(history_entry: Dict[str, Any]):
    """Prepare a continuation from a history entry."""
    entry_type = history_entry.get("type", "unknown")
    task = history_entry.get("task", "")
    result = history_entry.get("result", {})
    entry_id = history_entry.get("id", "")

    # Format result based on execution type
    formatted_result = ""
    if entry_type == "manager_execution":
        formatted_result = f"Summary: {result.get('summary', '')}\n\nOutcome: {result.get('outcome', '')}"

    elif entry_type == "single_agent_execution":
        formatted_result = result.get("response", "")

    elif entry_type in ["directive_execution", "multi_agent_execution"]:
        formatted_result = result.get("response", "")

    continuation_prompt = f"""Previous task: {task}

Result:
{formatted_result}

Continue from here:
"""

    # Set in session state
    st.session_state.current_task = continuation_prompt
    st.session_state.in_continuation_mode = True

    # Store parent ID for continuation chain tracking
    st.session_state.parent_execution_id = entry_id

    # Set targeting based on execution type
    if entry_type == "single_agent_execution" and history_entry.get("agents_involved"):
        st.session_state.target_agent = history_entry["agents_involved"][0]
        st.session_state.selected_agents = []
    elif entry_type == "multi_agent_execution" and history_entry.get("agents_involved"):
        st.session_state.target_agent = ""
        st.session_state.selected_agents = history_entry["agents_involved"]
    elif entry_type == "directive_execution" and history_entry.get("agents_involved"):
        st.session_state.target_agent = ""
        st.session_state.selected_agents = history_entry["agents_involved"]
    else:
        st.session_state.target_agent = ""
        st.session_state.selected_agents = []

    # Track continuation by default
    st.session_state.track_chain = True

    # Rerun to show the continuation interface
    st.rerun()


def execute_with_multiple_agents(group: AgentGroup, task: str, agent_names: List[str]) -> Dict[str, Any]:
    """Execute a task with multiple specific agents."""
    if not agent_names:
        return {"status": "error", "message": "No agents selected for execution"}

    combined_results = []
    start_time = time.time()

    for agent_name in agent_names:
        logger.info(f"Executing task with agent {agent_name}: {task}")

        # Find the agent by name
        agent = next((a for a in group.agents if a.name == agent_name), None)
        if not agent:
            combined_results.append({
                "agent": agent_name,
                "result": {
                    "status": "error",
                    "message": f"Agent '{agent_name}' not found in group '{group.name}'"
                }
            })
            continue

        # Execute with this agent
        agent_result = agent.execute_task(task)

        # Add to agent memory
        agent.add_to_memory(f"Task: {task}\nResponse: {agent_result['response']}", "execution")

        # Add to group shared memory
        group.add_shared_memory(
            f"Agent {agent_name} processed: {task}\nResult: {agent_result['response']}",
            source="multi_agent_execution"
        )

        combined_results.append({
            "agent": agent_name,
            "result": agent_result
        })

    # Combine responses into a single response
    combined_response = "# Agent Responses\n\n"
    for result in combined_results:
        agent_name = result["agent"]
        agent_result = result["result"]
        if agent_result["status"] == "error":
            combined_response += f"## {agent_name}\n\n❌ Error: {agent_result['message']}\n\n"
        else:
            # Process the response (handle JSON format if needed)
            response = agent_result.get("response", "No response provided")

            # Try to detect if response is a JSON string with thought_process and response
            if isinstance(response, str) and response.strip().startswith("{") and response.strip().endswith("}"):
                try:
                    # Try to parse JSON response
                    import json
                    parsed_json = json.loads(response)

                    # Extract response if it exists
                    if isinstance(parsed_json, dict) and "response" in parsed_json:
                        response = parsed_json.get("response", "")
                except:
                    # If parsing fails, use the original response
                    logger.warning(f"Failed to parse JSON response from agent {agent_name}")

            combined_response += f"## {agent_name}\n\n{response}\n\n"

    execution_time = time.time() - start_time

    # Record in history
    history_entry = {
        "type": "multi_agent_execution",
        "task": task,
        "agents_involved": agent_names,
        "result": {
            "status": "success",
            "response": combined_response,
            "agent_results": combined_results
        },
        "execution_time": execution_time
    }

    # Add parent/child relationship for continuation chains
    if st.session_state.get("parent_execution_id") and st.session_state.get("track_chain", True):
        history_entry["parent_id"] = st.session_state.parent_execution_id

    history_id = group.add_to_history(history_entry)
    logger.info(f"Added multi-agent execution to history with ID: {history_id}, current history size: {len(group.execution_history)}")

    # Save changes to disk
    save_agents()
    logger.info(f"Saved agent groups with updated history to disk")

    return {
        "status": "success",
        "response": combined_response,
        "individual_results": combined_results,
        "execution_time": execution_time,
        "history_id": history_id
    }
