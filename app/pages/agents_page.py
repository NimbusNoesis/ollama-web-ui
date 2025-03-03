import streamlit as st
from typing import Dict, List, Any, Union, Optional
import uuid
import json
import os
from datetime import datetime
import traceback

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.tool_loader import ToolLoader

# Get application logger
logger = get_logger()


class Agent:
    """Class representing an individual agent"""

    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else []
        self.memory: List[Dict[str, str]] = []
        self.created_at = datetime.now().isoformat()
        logger.info(f"Created new Agent: {name} (ID: {self.id}) with model: {model}")
        if tools:
            logger.info(f"Agent {name} initialized with {len(tools)} tools")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "memory": self.memory,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Agent":
        agent = cls(
            name=data["name"],
            model=data["model"],
            system_prompt=data["system_prompt"],
            tools=data.get("tools", []),
        )
        agent.id = data["id"]
        agent.memory = data.get("memory", [])
        agent.created_at = data["created_at"]
        return agent

    def add_to_memory(self, content: str, source: str = "observation"):
        """Add a memory entry for this agent"""
        self.memory.append(
            {
                "content": content,
                "source": source,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute a task using this agent's capabilities"""
        logger.info(f"Agent {self.name} (ID: {self.id}) executing task: {task[:50]}...")

        messages: List[Dict[str, Union[str, List[Any]]]] = []

        # Add relevant memories as context
        if self.memory:
            memory_context = "Previous relevant information:\n" + "\n".join(
                f"- {m['content']}"
                for m in self.memory[-5:]  # Last 5 memories
            )
            messages.append({"role": "system", "content": memory_context})
            logger.info(
                f"Added {min(5, len(self.memory))} memories as context for agent {self.name}"
            )

        # Add the task
        messages.append({"role": "user", "content": task})

        try:
            logger.info(f"Agent {self.name} calling OllamaAPI with model {self.model}")
            response = OllamaAPI.chat_completion(
                model=self.model,
                messages=messages,
                system=self.system_prompt,
                temperature=0.7,
                stream=False,
                tools=self.tools,
            )

            # Handle different response formats
            if isinstance(response, dict) and "message" in response:
                content = response["message"].get("content", "")
                tool_calls = response["message"].get("tool_calls", [])
            else:
                # Handle object-style response
                content = getattr(getattr(response, "message", None), "content", "")
                tool_calls = getattr(
                    getattr(response, "message", None), "tool_calls", []
                )

            # Add task and response to memory
            self.add_to_memory(f"Task: {task}", source="task")
            self.add_to_memory(f"Response: {content}", source="execution")

            # Log tool usage if any
            if tool_calls:
                logger.info(
                    f"Agent {self.name} used {len(tool_calls)} tools in response"
                )
                for tool in tool_calls:
                    if isinstance(tool, dict) and "function" in tool:
                        logger.info(
                            f"Tool used: {tool['function'].get('name', 'unknown')}"
                        )

            logger.info(f"Agent {self.name} completed task successfully")
            return {"status": "success", "response": content, "tool_calls": tool_calls}

        except Exception as e:
            logger.error(f"Error when agent {self.name} executed task: {str(e)}")
            logger.info(f"Exception details: {traceback.format_exc()}")
            return {"status": "error", "error": str(e)}


class AgentGroup:
    """Class representing a group of agents that can work together"""

    def __init__(self, name: str, description: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.agents: List[Agent] = []
        self.shared_memory: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        logger.info(f"Created new AgentGroup: {name} (ID: {self.id})")

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": [agent.to_dict() for agent in self.agents],
            "shared_memory": self.shared_memory,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentGroup":
        group = cls(name=data["name"], description=data["description"])
        group.id = data["id"]
        group.agents = [Agent.from_dict(agent_data) for agent_data in data["agents"]]
        group.shared_memory = data.get("shared_memory", [])
        group.created_at = data["created_at"]
        return group

    def add_shared_memory(self, content: str, source: str = "group"):
        """Add a memory entry to the group's shared memory"""
        self.shared_memory.append(
            {
                "content": content,
                "source": source,
                "timestamp": datetime.now().isoformat(),
            }
        )
        logger.info(f"Added shared memory to group {self.name} from source: {source}")

    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for the manager prompt"""
        if not self.agents:
            return "No agents available."

        capabilities = []
        for agent in self.agents:
            tools_info = ""
            if agent.tools:
                tool_names = [
                    tool.get("function", {}).get("name", "unknown")
                    for tool in agent.tools
                ]
                tools_info = f" with tools: {', '.join(tool_names)}"

            capabilities.append(f"- {agent.name}: {agent.model} model{tools_info}")

        return "\n".join(capabilities)

    def get_manager_prompt(self) -> str:
        """Get the system prompt for the manager agent"""
        return f"""You are the manager of a group of AI agents named '{self.name}'. Your role is to:
1. Analyze tasks and break them down into subtasks
2. Assign subtasks to appropriate agents based on their capabilities
3. Coordinate between agents and aggregate their responses
4. Maintain group coherence and shared context

Available Agents:
{self._format_agent_capabilities()}

IMPORTANT FORMATTING INSTRUCTIONS:
- When assigning a subtask to an agent, always use the exact format: "Assign to [agent_name]: [subtask description]"
- When the task is complete, include the phrase "TASK COMPLETE" in your response
- Be precise with agent names - only assign tasks to agents that exist in the list above
- Do not assign a task to an agent that doesn't exist

Use the shared memory to maintain context and track progress. Be decisive in task delegation and clear in your communication."""

    def execute_task_with_manager(self, task: str) -> Dict[str, Any]:
        """Execute a task using a manager agent to coordinate"""
        logger.info(f"Group {self.name} executing task with manager: {task[:50]}...")

        try:
            # Create manager agent with the first available model
            manager_model = self.agents[0].model if self.agents else "llama2"
            logger.info(f"Using model {manager_model} for manager agent")

            # Get task planning response from manager
            planning_messages: List[Dict[str, Union[str, List[Any]]]] = [
                {"role": "system", "content": self.get_manager_prompt()},
                {
                    "role": "user",
                    "content": f"""Task: {task}

Analyze this task and create a plan using the available agents. For each subtask, specify which agent should handle it and why.

IMPORTANT: Your planning should be structured and clear. List each step with the agent who will perform it.""",
                },
            ]

            # Add shared memory context
            if self.shared_memory:
                memory_context = "Group Memory Context:\n" + "\n".join(
                    f"- {m['content']}" for m in self.shared_memory[-5:]
                )
                planning_messages.insert(
                    1, {"role": "system", "content": memory_context}
                )
                logger.info(
                    f"Added {min(5, len(self.shared_memory))} group memories to manager context"
                )

            # Get plan from manager
            logger.info(
                f"Requesting plan from manager agent using model {manager_model}"
            )
            plan_response = OllamaAPI.chat_completion(
                model=manager_model, messages=planning_messages, stream=False
            )

            # Extract plan from response
            if isinstance(plan_response, dict) and "message" in plan_response:
                plan = plan_response["message"].get("content", "")
            else:
                plan = getattr(getattr(plan_response, "message", None), "content", "")

            logger.info(f"Manager agent created plan for task: {plan[:100]}...")
            self.add_shared_memory(f"Task Planning: {plan}", source="manager")

            # Execute subtasks with individual agents
            results = []
            execution_messages: List[Dict[str, Union[str, List[Any]]]] = (
                planning_messages.copy()
            )
            execution_messages.append({"role": "assistant", "content": plan})
            execution_messages.append(
                {
                    "role": "user",
                    "content": """Execute this plan by coordinating with the agents. Process one subtask at a time and aggregate the results.

IMPORTANT FORMATTING REQUIREMENTS:
1. To assign a task to an agent, use exactly this format: "Assign to [agent_name]: [subtask description]"
2. When all subtasks are complete, include "TASK COMPLETE" in your response

Example assignment:
Assign to ResearchAgent: Find the latest research on quantum computing from the past year.

Process each step one at a time and wait for the results before proceeding to the next step.""",
                }
            )

            step_count = 0
            while True:
                step_count += 1
                logger.info(f"Manager execution step {step_count}")

                # Get next action from manager
                manager_response = OllamaAPI.chat_completion(
                    model=manager_model, messages=execution_messages, stream=False
                )

                # Extract action from response
                if isinstance(manager_response, dict) and "message" in manager_response:
                    action = manager_response["message"].get("content", "")
                else:
                    action = getattr(
                        getattr(manager_response, "message", None), "content", ""
                    )

                if "TASK COMPLETE" in action:
                    logger.info(
                        f"Manager declared task complete after {step_count} steps"
                    )
                    break

                # Parse agent assignment from action
                # Expecting format: "Assign to [agent_name]: [subtask]"
                if "Assign to" in action:
                    agent_name = action.split("Assign to")[1].split(":")[0].strip()
                    subtask = action.split(":", 1)[1].strip()

                    logger.info(
                        f"Manager assigned subtask to agent {agent_name}: {subtask[:50]}..."
                    )

                    agent = next((a for a in self.agents if a.name == agent_name), None)
                    if agent:
                        # Execute subtask with assigned agent
                        logger.info(f"Executing subtask with agent {agent_name}")
                        result = agent.execute_task(subtask)
                        results.append(
                            {"agent": agent_name, "subtask": subtask, "result": result}
                        )

                        # Add result to shared memory
                        self.add_shared_memory(
                            f"Agent {agent_name} completed subtask: {subtask}\nResult: {result['response']}",
                            source="execution",
                        )

                        # Update manager with result
                        execution_messages.append(
                            {"role": "assistant", "content": action}
                        )
                        execution_messages.append(
                            {
                                "role": "user",
                                "content": f"""Result from {agent_name}: {result['response']}

What's the next step in the plan? Remember to use the format: "Assign to [agent_name]: [subtask description]"
If all steps are complete, include "TASK COMPLETE" in your response.""",
                            }
                        )
                    else:
                        logger.warning(
                            f"Manager tried to assign task to non-existent agent: {agent_name}"
                        )
                        # Provide feedback to the manager about the error
                        execution_messages.append(
                            {"role": "assistant", "content": action}
                        )
                        execution_messages.append(
                            {
                                "role": "user",
                                "content": f"""Error: Agent "{agent_name}" does not exist in this group.
Available agents are: {', '.join([a.name for a in self.agents])}

Please assign the task to one of the available agents using the format: "Assign to [agent_name]: [subtask description]"
If all steps are complete, include "TASK COMPLETE" in your response.""",
                            }
                        )
                else:
                    logger.warning(
                        f"Manager response didn't follow expected format: {action[:100]}..."
                    )
                    # Provide feedback to the manager about the format error
                    execution_messages.append({"role": "assistant", "content": action})
                    execution_messages.append(
                        {
                            "role": "user",
                            "content": """Your response format is incorrect. Please use exactly this format to assign a task:

"Assign to [agent_name]: [subtask description]"

If all steps are complete, include "TASK COMPLETE" in your response.
What's the next step in the plan?""",
                        }
                    )

            # Get final summary from manager
            logger.info("Requesting final summary from manager agent")
            summary_response = OllamaAPI.chat_completion(
                model=manager_model,
                messages=execution_messages
                + [
                    {
                        "role": "user",
                        "content": "Provide a final summary of the task execution and results. Include what was accomplished and any conclusions drawn.",
                    }
                ],
                stream=False,
            )

            # Extract summary from response
            if isinstance(summary_response, dict) and "message" in summary_response:
                summary = summary_response["message"].get("content", "")
            else:
                summary = getattr(
                    getattr(summary_response, "message", None), "content", ""
                )

            logger.info(f"Manager provided task summary: {summary[:100]}...")
            self.add_shared_memory(f"Task Summary: {summary}", source="manager")

            return {
                "status": "success",
                "plan": plan,
                "results": results,
                "summary": summary,
            }

        except Exception as e:
            logger.error(
                f"Error in manager task execution for group {self.name}: {str(e)}"
            )
            logger.info(f"Exception details: {traceback.format_exc()}")
            return {"status": "error", "error": str(e)}


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
        self.load_agents()

    def load_agents(self):
        """Load saved agent groups from disk"""
        logger.info("Loading agent groups from disk")

        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
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

    def save_agents(self):
        """Save agent groups to disk"""
        logger.info("Saving agent groups to disk")

        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "app",
            "data",
            "agents",
        )

        try:
            # Ensure directory exists
            os.makedirs(data_dir, exist_ok=True)

            path = os.path.join(data_dir, "agent_groups.json")
            logger.info(f"Will save to path: {path}")

            # Convert groups to dict format
            data = [group.to_dict() for group in st.session_state["agent_groups"]]

            # Log what we're about to save for debugging
            logger.info(f"Saving {len(data)} agent groups")
            for group in data:
                logger.info(
                    f"Group: {group['name']} (ID: {group['id']}) has {len(group['agents'])} agents"
                )
                for agent in group["agents"]:
                    logger.info(f"  - Agent: {agent['name']} (ID: {agent['id']})")

            # Write to file with proper encoding
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Successfully saved agent groups to {path}")
        except Exception as e:
            logger.error(f"Error saving agent groups: {str(e)}")
            logger.info(f"Exception details: {traceback.format_exc()}")

    def render_agent_editor(self):
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
                value=st.session_state.editing_agent.name
                if st.session_state.editing_agent
                else "",
            )
            model = st.selectbox("Model", model_names)
            system_prompt = st.text_area(
                "System Prompt",
                value=st.session_state.editing_agent.system_prompt
                if st.session_state.editing_agent
                else "",
            )

            # Tool selection
            st.write("### Available Tools")
            selected_tools = []
            current_tool_names = []

            if st.session_state.editing_agent and st.session_state.editing_agent.tools:
                current_tool_names = [
                    tool["function"]["name"]
                    for tool in st.session_state.editing_agent.tools
                ]
                logger.info(
                    f"Editing agent has {len(current_tool_names)} tools selected"
                )

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
                if not st.session_state.selected_group:
                    logger.warning("No group selected when trying to save agent")
                    st.error("No group selected. Please select a group first.")
                    return

                logger.info(
                    f"Saving agent to group: {st.session_state.selected_group.name}"
                )

                if st.session_state.editing_agent:
                    # Update existing agent
                    agent = st.session_state.editing_agent
                    logger.info(
                        f"Updating existing agent {agent.name} (ID: {agent.id})"
                    )
                    agent.name = name
                    agent.model = model
                    agent.system_prompt = system_prompt
                    agent.tools = selected_tools
                    logger.info(f"Updated agent with {len(selected_tools)} tools")

                    # Check if agent is already in the group, if not, add it
                    agent_in_group = False
                    for existing_agent in st.session_state.selected_group.agents:
                        if existing_agent.id == agent.id:
                            agent_in_group = True
                            logger.info(
                                f"Agent {agent.name} (ID: {agent.id}) already exists in group"
                            )
                            break

                    if not agent_in_group:
                        logger.info(
                            f"Adding existing agent {name} (ID: {agent.id}) to group {st.session_state.selected_group.name}"
                        )
                        st.session_state.selected_group.agents.append(agent)
                        logger.info(
                            f"Group now has {len(st.session_state.selected_group.agents)} agents"
                        )
                else:
                    # Create new agent
                    logger.info(f"Creating new agent: {name}")
                    agent = Agent(
                        name=name,
                        model=model,
                        system_prompt=system_prompt,
                        tools=selected_tools,
                    )
                    logger.info(
                        f"Adding new agent {name} (ID: {agent.id}) to group {st.session_state.selected_group.name}"
                    )
                    st.session_state.selected_group.agents.append(agent)
                    logger.info(
                        f"Group now has {len(st.session_state.selected_group.agents)} agents"
                    )

                # Reset editing state
                logger.info("Resetting editing_agent to None")
                st.session_state.editing_agent = None

                # Save changes to disk
                logger.info("Calling save_agents() to persist changes")
                self.save_agents()

                # Show success message and rerun to update UI
                logger.info(f"Agent '{name}' saved successfully!")
                st.success(f"Agent '{name}' saved successfully!")
                st.rerun()

    def render_group_editor(self):
        """Render the group creation/editing form"""
        logger.info("Rendering group editor")
        st.subheader("Create Agent Group")

        with st.form("group_editor"):
            name = st.text_input("Group Name")
            description = st.text_area("Description")

            if st.form_submit_button("Create Group"):
                logger.info(f"Create Group button clicked for group: {name}")

                if not name:
                    logger.warning("Group name is required but was empty")
                    st.error("Group name is required")
                    return

                logger.info(f"Creating new group: {name}")
                group = AgentGroup(name=name, description=description)
                st.session_state.agent_groups.append(group)
                st.session_state.selected_group = group
                logger.info(f"Created group {name} (ID: {group.id})")
                logger.info(f"Total groups now: {len(st.session_state.agent_groups)}")

                self.save_agents()
                st.rerun()

    def render_group_view(self, group: AgentGroup):
        """Render the view of a specific agent group"""
        logger.info(f"Rendering view for group: {group.name} (ID: {group.id})")
        st.subheader(f"Group: {group.name}")
        st.write(group.description)

        # Agents list
        st.write("### Agents")
        if not group.agents:
            logger.info(f"Group {group.name} has no agents")
            st.info("No agents in this group yet")
        else:
            logger.info(f"Group {group.name} has {len(group.agents)} agents")

        for agent in group.agents:
            logger.info(f"Rendering agent: {agent.name} (ID: {agent.id})")
            with st.expander(f"🤖 {agent.name}"):
                st.write(f"**Model:** {agent.model}")
                st.write(f"**System Prompt:** {agent.system_prompt}")
                if agent.tools:
                    st.write("**Tools:**")
                    for tool in agent.tools:
                        st.write(f"- {tool['function']['name']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key=f"edit_{agent.id}"):
                        logger.info(
                            f"Edit button clicked for agent {agent.name} (ID: {agent.id})"
                        )
                        st.session_state.editing_agent = agent
                        logger.info("Set editing_agent in session state")
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{agent.id}"):
                        logger.info(
                            f"Delete button clicked for agent {agent.name} (ID: {agent.id})"
                        )
                        group.agents.remove(agent)
                        logger.info(
                            f"Removed agent from group. Group now has {len(group.agents)} agents"
                        )
                        self.save_agents()
                        st.rerun()

        # Add agent button
        if st.button("Add Agent"):
            logger.info("Add Agent button clicked")
            # Create a new empty agent and set it as editing_agent
            st.session_state.editing_agent = Agent(
                name="", model="", system_prompt="", tools=[]
            )
            logger.info("Created empty agent and set as editing_agent")
            st.rerun()

        # Shared memory
        st.write("### Shared Memory")
        if not group.shared_memory:
            st.info("No shared memories yet")
        else:
            logger.info(
                f"Group {group.name} has {len(group.shared_memory)} shared memories"
            )
            for memory in group.shared_memory:
                st.write(f"- {memory['content']}")

    def render_task_executor(self, group: AgentGroup):
        """Render the task execution interface"""
        logger.info(f"Rendering task executor for group: {group.name}")
        st.subheader("Execute Task")

        task = st.text_area("Task Description")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Execute with Manager"):
                logger.info(
                    f"Execute with Manager button clicked for group {group.name}"
                )

                if not task:
                    logger.warning("Task description is required but was empty")
                    st.error("Please enter a task description")
                    return
                if not group.agents:
                    logger.warning(f"Group {group.name} has no agents")
                    st.error("Add some agents to the group first")
                    return

                logger.info(
                    f"Executing task with manager for group {group.name}: {task[:50]}..."
                )
                with st.spinner("Manager agent is coordinating task execution..."):
                    result = group.execute_task_with_manager(task)

                    if result["status"] == "success":
                        logger.info("Task execution completed successfully")
                        st.success("Task completed successfully!")

                        # Show the execution plan
                        with st.expander("📋 Task Execution Plan", expanded=True):
                            st.markdown(result["plan"])

                        # Show individual agent results
                        with st.expander("🤖 Agent Executions", expanded=True):
                            for execution in result["results"]:
                                st.markdown(f"**Agent**: {execution['agent']}")
                                st.markdown(f"**Subtask**: {execution['subtask']}")
                                if execution["result"]["status"] == "success":
                                    st.markdown(
                                        f"**Response**: {execution['result']['response']}"
                                    )
                                    if execution["result"].get("tool_calls"):
                                        st.markdown("**Tools Used**:")
                                        for tool in execution["result"]["tool_calls"]:
                                            st.markdown(f"- {tool['function']['name']}")
                                else:
                                    st.error(f"Error: {execution['result']['error']}")
                                st.markdown("---")

                        # Show final summary
                        with st.expander("📝 Task Summary", expanded=True):
                            st.markdown(result["summary"])
                    else:
                        logger.error(
                            f"Task execution failed: {result.get('error', 'Unknown error')}"
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
                logger.info(
                    f"Execute with Selected Agent button clicked: {selected_agent}"
                )

                if not task or not selected_agent:
                    logger.warning("Task or agent selection is missing")
                    st.error("Please enter a task and select an agent")
                    return

                agent = next(
                    (a for a in group.agents if a.name == selected_agent), None
                )
                if agent:
                    logger.info(
                        f"Executing task with agent {agent.name}: {task[:50]}..."
                    )
                    with st.spinner(f"Agent {agent.name} is working on the task..."):
                        result = agent.execute_task(task)

                        if result["status"] == "success":
                            logger.info(
                                f"Agent {agent.name} completed task successfully"
                            )
                            st.success("Task completed!")

                            # Show the agent's response
                            with st.expander("🤖 Agent Response", expanded=True):
                                st.markdown(result["response"])

                                # Show tool usage if any
                                if result.get("tool_calls"):
                                    logger.info(
                                        f"Agent {agent.name} used {len(result['tool_calls'])} tools"
                                    )
                                    st.markdown("**Tools Used**:")
                                    for tool in result["tool_calls"]:
                                        st.markdown(f"- {tool['function']['name']}")

                            # Show memory context
                            with st.expander("💭 Agent Memory"):
                                recent_memories = (
                                    agent.memory[-5:] if agent.memory else []
                                )
                                for memory in recent_memories:
                                    st.markdown(
                                        f"**{memory['source']}** ({memory['timestamp']}): {memory['content']}"
                                    )
                        else:
                            logger.error(
                                f"Agent task execution failed: {result.get('error', 'Unknown error')}"
                            )
                            st.error(
                                f"Task execution failed: {result.get('error', 'Unknown error')}"
                            )

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
            self.render_agent_editor()
        elif not st.session_state.selected_group:
            logger.info("Rendering group editor (no selected_group)")
            self.render_group_editor()
        else:
            logger.info(
                f"Rendering tabs for group: {st.session_state.selected_group.name}"
            )
            tab1, tab2 = st.tabs(["Group Details", "Task Execution"])

            with tab1:
                self.render_group_view(st.session_state.selected_group)
            with tab2:
                self.render_task_executor(st.session_state.selected_group)
