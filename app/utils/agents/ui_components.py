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

    # Check for existing results in session state
    has_results = "agent_execution_results" in st.session_state

    # Task input at the top (full width)
    task_value = st.session_state.get("current_task", "")
    task = st.text_area("Enter task for the agent group", value=task_value, height=100)

    # Clear results button if results exist
    if has_results and st.button("Clear Results"):
        if "agent_execution_results" in st.session_state:
            del st.session_state.agent_execution_results
        logger.info("Cleared execution results from session state")
        st.rerun()

    # Execution options in tabs
    st.write("### Execution Options")
    exec_tab1, exec_tab2 = st.tabs(["Execute with Manager", "Execute with Specific Agent"])

    with exec_tab1:
        if st.button("Execute Task with Manager"):
            if not task:
                st.error("Please enter a task")
                return

            logger.info(f"Execute Task with Manager button clicked for group {group.name}")
            
            # Check if we have agent directives in the task text
            agent_directives = parse_agent_directives(task, group.agents)
            
            # Check if this is a continuation with a specific target
            target_agent = None
            if st.session_state.get("in_continuation_mode", False):
                # Get the target agent from session state if set
                target_name = st.session_state.get("target_agent", "")
                if target_name and "manager" not in target_name:
                    # If a specific agent is targeted, execute with that agent instead
                    target_agent = next((a for a in group.agents if a.name == target_name), None)
            
            # If we have agent directives in the text, handle them directly
            if agent_directives and len(agent_directives) > 0:
                logger.info(f"Found {len(agent_directives)} agent directives in task text")
                st.info(f"Processing {len(agent_directives)} agent directives found in your task")
                
                # Execute the directives directly
                with st.spinner("Processing agent directives..."):
                    directive_result = execute_task_with_directives(group, task, agent_directives)
                    
                    # Store results in session state
                    st.session_state.agent_execution_results = {
                        "type": "directive",
                        "task": task,
                        "result": directive_result,
                        "agent_directives": agent_directives,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Reset continuation mode after execution
                    st.session_state.in_continuation_mode = False
                    
                    # Force rerun to display results
                    st.rerun()
                return
            
            # If a specific agent is targeted, execute with that agent
            if target_agent:
                logger.info(f"Targeting specific agent from dropdown: {target_agent.name}")
                st.info(f"Executing task directly with {target_agent.name} as specified")
                
                with st.spinner(f"Agent {target_agent.name} is working on the task..."):
                    result = target_agent.execute_task(task)
                    
                    # Store results in session state for persistence
                    st.session_state.agent_execution_results = {
                        "type": "single_agent",
                        "agent_name": target_agent.name,
                        "task": task,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Reset continuation mode after execution
                    st.session_state.in_continuation_mode = False
                    
                    # Force rerun to display results in the results section
                    st.rerun()
                return
            
            # If no directives or specific target, proceed with manager execution
            st.write("### Execution Progress")

            with st.spinner("Executing task with manager..."):
                # Use normal manager execution
                result = group.execute_task_with_manager(task)

                # Store results in session state for persistence
                st.session_state.agent_execution_results = {
                    "type": "manager",
                    "task": task,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Reset continuation mode after execution
                st.session_state.in_continuation_mode = False

                # Force rerun to display results in the results section
                st.rerun()

    with exec_tab2:
        agent_options = [agent.name for agent in group.agents]
        selected_agent = ""
        
        # If we're in continuation mode and have a targeted agent, pre-select it
        default_index = 0
        if st.session_state.get("in_continuation_mode", False) and st.session_state.get("target_agent", ""):
            target = st.session_state.get("target_agent", "")
            if "manager" not in target and target in agent_options:
                default_index = agent_options.index(target)
        
        if agent_options:
            selected_agent = st.selectbox(
                "Select Agent",
                options=agent_options,
                index=default_index,
                format_func=lambda x: f"🤖 {x}",
            )
            logger.info(f"Agent selected in dropdown: {selected_agent}")

        if st.button("Execute Task with Selected Agent"):
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

                    # Store results in session state for persistence
                    st.session_state.agent_execution_results = {
                        "type": "single_agent",
                        "agent_name": agent.name,
                        "task": task,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Reset continuation mode after execution
                    st.session_state.in_continuation_mode = False

                    # Force rerun to display results in the results section
                    st.rerun()

    # Results section (full width) - displayed if there are results in session state
    if "agent_execution_results" in st.session_state:
        st.write("---")
        st.subheader("Execution Results")
        
        results_data = st.session_state.agent_execution_results
                    
        # Display results based on type
        if results_data["type"] == "manager":
            result = results_data["result"]
            task = results_data["task"]
            
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
                st.error(
                    f"Task execution failed: {result.get('error', 'Unknown error')}"
                )
                
        elif results_data["type"] == "directive":
            result = results_data["result"]
            task = results_data["task"]
            directives = results_data.get("agent_directives", {})
            
            if result["status"] == "success":
                st.success("✅ All agent directives processed successfully")
                
                # Display directives summary
                st.markdown("### Agent Directives Processed")
                for agent_name, subtask in directives.items():
                    st.markdown(f"- **@{agent_name}**: {subtask}")
                
                # Display results
                st.markdown("### Results")
                st.markdown(process_markdown(result["response"]))
                
            elif result["status"] == "partial":
                st.warning("⚠️ Some agent directives processed, but with issues")
                
                # Display directive results
                for agent_result in result["results"]:
                    agent_name = agent_result["agent"]
                    subtask = agent_result["subtask"]
                    response = agent_result["result"].get("response", "No response")
                    
                    st.markdown(f"**@{agent_name}**: {subtask}")
                    st.markdown(process_markdown(response))
                    st.markdown("---")
                
                # Display errors
                if result["errors"]:
                    st.error("Errors encountered:")
                    for error in result["errors"]:
                        st.markdown(f"- **{error['agent']}**: {error['error']}")
            else:
                st.error("❌ Failed to process agent directives")
                
                # Display errors
                if result["errors"]:
                    for error in result["errors"]:
                        st.error(f"**{error['agent']}**: {error['error']}")
                
        elif results_data["type"] == "single_agent":
            result = results_data["result"]
            agent_name = results_data["agent_name"]
            
            if result["status"] == "success":
                st.success(f"Task completed by {agent_name}!")

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
            else:
                st.error(
                    f"Task execution failed: {result.get('error', 'Unknown error')}"
                )
                
        # Continuation UI - positioned AFTER results display
        st.write("---")
        st.subheader("Continue from this Result")
        
        # Add a continue button
        if not st.session_state.get("in_continuation_mode", False):
            if st.button("Prepare Continuation"):
                # Format previous task and results for continuation
                if results_data["type"] == "manager":
                    formatted_result = results_data["result"].get("summary", "No summary available")
                elif results_data["type"] == "directive":
                    formatted_result = results_data["result"].get("response", "No response available")
                else:
                    formatted_result = results_data["result"].get("response", "No response available")
                    
                continuation_prompt = f"""Previous task: {results_data['task']}
                
Result:
{formatted_result}

Continue from here:
"""
                # Set in session state
                st.session_state.current_task = continuation_prompt
                st.session_state.in_continuation_mode = True
                
                # Store the previous execution type and agent for continuation context
                st.session_state.previous_execution = {
                    "type": results_data["type"],
                    "agent_name": results_data.get("agent_name") if results_data["type"] == "single_agent" else None
                }
                
                st.rerun()
        
        # Show continuation mode indicator and targeting options
        if st.session_state.get("in_continuation_mode", False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.info("✨ You are continuing from a previous task")
            
            with col2:
                if st.button("Exit Continuation Mode"):
                    st.session_state.in_continuation_mode = False
                    st.session_state.current_task = ""
                    if "target_agent" in st.session_state:
                        del st.session_state.target_agent
                    st.rerun()
            
            # Add editable continuation prompt
            edited_prompt = st.text_area(
                "Edit Continuation Prompt",
                value=st.session_state.current_task,
                height=200,
                help="Edit this prompt to add additional context, questions, or @agent_name directives"
            )
            
            # Update the session state with edited prompt
            st.session_state.current_task = edited_prompt
            
            # Only show targeting options if we're in continuation mode
            st.write("### Target Specific Agent")
            
            # Default targeting option based on previous execution
            default_target = "manager"
            if st.session_state.get("previous_execution", {}).get("type") == "single_agent":
                default_target = st.session_state.get("previous_execution", {}).get("agent_name", "manager")
            
            # Create list of targeting options
            target_options = ["manager (coordinate all agents)"]
            target_options.extend([agent.name for agent in group.agents])
            
            # Find the index of the default target
            default_index = 0
            for i, option in enumerate(target_options):
                if default_target in option:
                    default_index = i
                    break
            
            # Agent targeting selector
            target_agent = st.selectbox(
                "Direct this continuation to:",
                options=target_options,
                index=default_index,
                help="Select which agent should handle this continuation. 'manager' will coordinate all agents."
            )
            
            # Store the selected target in session state
            st.session_state.target_agent = target_agent
            
            # Show syntax help
            with st.expander("Using @agent_name Syntax"):
                st.markdown("""
                You can also use `@agent_name:` syntax directly in your prompt to target specific agents:
                
                ```
                @ResearchAgent: Find information about quantum computing
                @CodeAgent: Write a Python function that demonstrates quantum superposition
                ```
                
                This allows you to direct different parts of your task to different agents.
                """)
            
            # Display currently targeted agent
            if st.session_state.get("target_agent"):
                if "manager" in st.session_state.target_agent:
                    st.write(f"📣 Your task will be coordinated by the manager")
                else:
                    st.write(f"📣 Your task will be sent directly to **{st.session_state.target_agent}**")
            
            # Add Execute Continuation button
            if st.button("Execute Continuation", type="primary"):
                logger.info("Execute Continuation button clicked")
                
                # Get the current task from session state
                continuation_task = st.session_state.current_task
                
                if not continuation_task:
                    st.error("Please enter a continuation task")
                    return
                
                # Get the targeted agent
                target_name = st.session_state.get("target_agent", "")
                target_agent = None
                
                # Check for agent directives
                agent_directives = parse_agent_directives(continuation_task, group.agents)
                
                # Determine execution path
                if agent_directives and len(agent_directives) > 0:
                    # Use directive execution
                    logger.info(f"Executing continuation with {len(agent_directives)} directives")
                    st.info(f"Processing {len(agent_directives)} agent directives in your continuation")
                    
                    with st.spinner("Processing agent directives..."):
                        directive_result = execute_task_with_directives(group, continuation_task, agent_directives)
                        
                        # Store results
                        st.session_state.agent_execution_results = {
                            "type": "directive",
                            "task": continuation_task,
                            "result": directive_result,
                            "agent_directives": agent_directives,
                            "timestamp": datetime.now().isoformat()
                        }
                
                elif target_name and "manager" not in target_name:
                    # Execute with specific agent
                    target_agent = next((a for a in group.agents if a.name == target_name), None)
                    
                    if target_agent:
                        logger.info(f"Executing continuation with specific agent: {target_name}")
                        st.info(f"Executing task with {target_name}")
                        
                        with st.spinner(f"Agent {target_name} is working on the task..."):
                            result = target_agent.execute_task(continuation_task)
                            
                            # Store results
                            st.session_state.agent_execution_results = {
                                "type": "single_agent",
                                "agent_name": target_name,
                                "task": continuation_task,
                                "result": result,
                                "timestamp": datetime.now().isoformat()
                            }
                    else:
                        st.error(f"Agent {target_name} not found")
                        return
                
                else:
                    # Execute with manager
                    logger.info("Executing continuation with manager")
                    st.info("Executing task with manager coordination")
                    
                    with st.spinner("Manager is coordinating task execution..."):
                        result = group.execute_task_with_manager(continuation_task)
                        
                        # Store results
                        st.session_state.agent_execution_results = {
                            "type": "manager",
                            "task": continuation_task,
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        }
                
                # Reset continuation mode
                st.session_state.in_continuation_mode = False
                
                # Rerun to show results
                st.rerun()


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


def execute_task_with_directives(group: AgentGroup, task: str, directives: Dict[str, str]) -> Dict:
    """
    Execute a task with explicit agent directives
    
    Args:
        group: The agent group
        task: The original task
        directives: Dictionary mapping agent names to their specific subtasks
        
    Returns:
        Results dictionary with combined output from all agents
    """
    logger.info(f"Executing task with explicit directives for {len(directives)} agents")
    
    results = []
    errors = []
    
    # First execute any agent-specific directives
    for agent_name, subtask in directives.items():
        logger.info(f"Executing directive for {agent_name}: {subtask[:50]}...")
        
        # Find the agent
        agent = next((a for a in group.agents if a.name == agent_name), None)
        if not agent:
            error_msg = f"Agent {agent_name} not found in group"
            logger.error(error_msg)
            errors.append({"agent": agent_name, "error": error_msg})
            continue
        
        # Execute the agent's subtask
        try:
            agent_result = agent.execute_task(subtask)
            
            # Add to results
            results.append({
                "agent": agent_name,
                "subtask": subtask,
                "result": agent_result
            })
            
            # Add to group's shared memory
            group.add_shared_memory(
                f"Agent {agent_name} processed: {subtask}\nResult: {agent_result.get('response', 'No response')}",
                source="agent_directive"
            )
            
        except Exception as e:
            error_msg = f"Error executing {agent_name}'s task: {str(e)}"
            logger.error(error_msg)
            errors.append({"agent": agent_name, "error": error_msg})
    
    # If there's any part of the task not covered by directives,
    # use the manager to handle the remaining part
    remaining_task = task
    
    # Handle any errors
    if errors:
        for error in errors:
            remaining_task += f"\nNote: Could not process directive for {error['agent']}: {error['error']}"
    
    # If all directives were processed successfully, return the results
    if len(results) == len(directives) and len(errors) == 0:
        # If the task was fully processed through directives, we're done
        combined_response = "# Results from Agent Directives\n\n"
        
        for result in results:
            agent_name = result["agent"]
            subtask = result["subtask"]
            response = result["result"].get("response", "No response")
            
            combined_response += f"## {agent_name}\n\n"
            combined_response += f"**Task:** {subtask}\n\n"
            combined_response += f"**Response:**\n{response}\n\n"
            combined_response += "---\n\n"
        
        return {
            "status": "success",
            "type": "directive_execution",
            "results": results,
            "response": combined_response,
            "errors": errors
        }
    
    return {
        "status": "partial" if results else "error",
        "type": "directive_execution",
        "results": results,
        "errors": errors,
        "remaining_task": remaining_task
    }
