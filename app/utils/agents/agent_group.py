"""
AgentGroup class for multi-agent systems.
"""

from typing import Dict, List, Any, Union, Optional
import uuid
import json
import traceback
from datetime import datetime

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.agents.agent import Agent

# Get application logger
logger = get_logger()


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
            # Skip any agent with the name "manager" (case-insensitive)
            if agent.name.lower() == "manager":
                continue

            capabilities.append(f"- {agent.name}: {agent.system_prompt}")

        if not capabilities:
            return "No non-manager agents available."

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
You must respond in valid JSON format with this schema:
{{
    "thought_process": "Your analysis of the task and plan",
    "steps": [
        {{
            "agent": "agent_name",
            "task": "detailed task description",
            "reason": "why this agent was chosen"
        }}
    ]
}}

- When assigning a subtask to an agent, always use the exact format: "Assign to [agent_name]: [subtask description]"
- When the task is complete, include the phrase "TASK COMPLETE" in your response
- Be precise with agent names - only assign tasks to agents that exist in the list above
- Do not assign a task to an agent that doesn't exist

Use the shared memory to maintain context and track progress. Be decisive in task delegation and clear in your communication."""

    def execute_task_with_manager(self, task: str) -> Dict[str, Any]:
        """Execute a task using a manager agent to coordinate"""
        logger.info(f"Group {self.name} executing task with manager: {task[:50]}...")

        try:
            # Find the first agent with name "manager" (case-insensitive)
            manager_agent = next(
                (agent for agent in self.agents if agent.name.lower() == "manager"),
                None,
            )

            # If no manager agent found, use the first agent or default to llama2
            if manager_agent:
                manager_model = manager_agent.model
                logger.info(
                    f"Using manager agent '{manager_agent.name}' with model {manager_model}"
                )
            else:
                manager_model = self.agents[0].model
                logger.warning(
                    f"No agent named 'manager' found. Using model {manager_model} as fallback"
                )

            # Get the base manager prompt
            system_prompt = self.get_manager_prompt()

            # Add shared memory context to the system prompt if available
            if self.shared_memory:
                memory_context = "Group Memory Context:\n" + "\n".join(
                    f"- {m['content']}" for m in self.shared_memory[-5:]
                )
                system_prompt = f"{system_prompt}\n\n{memory_context}"

            # Set up messages with a single system prompt followed by the user message
            planning_messages: List[Dict[str, Union[str, List[Any]]]] = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"""Task: {task}

Analyze this task and create a plan using the available agents. If an agent does not exist, do not assign it any tasks. Break it down into clear steps. Respond in JSON and only assign tasks to agents that exist in the group.""",
                },
            ]

            # Get plan from manager with JSON formatting
            plan_response = OllamaAPI.chat_completion(
                model=manager_model,
                messages=planning_messages,
                stream=False,
                temperature=0.3,
                format={
                    "type": "object",
                    "properties": {
                        "thought_process": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "agent": {"type": "string"},
                                    "task": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                                "required": ["agent", "task"],
                            },
                        },
                    },
                    "required": ["thought_process", "steps"],
                },
            )

            # Parse plan response
            if isinstance(plan_response, dict) and "message" in plan_response:
                plan_content = plan_response["message"].get("content", "{}")
            else:
                plan_content = getattr(
                    getattr(plan_response, "message", None), "content", "{}"
                )

            try:
                plan = json.loads(plan_content)
                logger.info(f"Manager created plan with {len(plan['steps'])} steps")
                self.add_shared_memory(
                    f"Task Planning: {plan['thought_process']}", source="manager"
                )

                # Execute each step with the assigned agent
                results = []
                for step in plan["steps"]:
                    agent_name = step["agent"]
                    subtask = step["task"]
                    agent = next((a for a in self.agents if a.name == agent_name), None)

                    if agent:
                        logger.info(
                            f"Executing step with agent {agent_name}: {subtask[:50]}..."
                        )

                        # Share relevant group memory with the agent before executing the task
                        if self.shared_memory:
                            # Get the last 5 shared memories or all if less than 5
                            relevant_memories = self.shared_memory[-5:]
                            for memory in relevant_memories:
                                # Add shared memory to agent's individual memory
                                agent.add_to_memory(
                                    f"Group shared: {memory['content']}",
                                    source="group_memory",
                                )
                            logger.info(
                                f"Shared {len(relevant_memories)} group memories with agent {agent_name}"
                            )

                        result = agent.execute_task(subtask)

                        # Add agent's response to its own memory for future reference
                        if result["status"] == "success":
                            agent.add_to_memory(
                                f"I completed task: {subtask}\nResponse: {result['response']}",
                                source="self_reflection",
                            )

                        results.append(
                            {
                                "agent": agent_name,
                                "subtask": subtask,
                                "reason": step.get("reason", ""),
                                "result": result,
                            }
                        )

                        # Add result to shared memory
                        if result["status"] == "success":
                            self.add_shared_memory(
                                f"Agent {agent_name} completed task: {subtask}\nThought process: {result.get('thought_process', '')}\nResponse: {result['response']}",
                                source="execution",
                            )

                            # Share agent's recent individual memories with the group
                            agent_individual_memories = [
                                m
                                for m in agent.memory
                                if m.get("source") != "group_memory"
                            ][-3:]
                            for memory in agent_individual_memories:
                                if (
                                    memory.get("source") != "task"
                                ):  # Skip task descriptions
                                    self.add_shared_memory(
                                        f"Agent {agent_name}'s memory: {memory['content']}",
                                        source=f"agent_{agent_name}",
                                    )
                        else:
                            self.add_shared_memory(
                                f"Agent {agent_name} failed task: {subtask}\nError: {result.get('error', 'Unknown error')}",
                                source="execution",
                            )
                    else:
                        logger.warning(f"Invalid agent name in plan: {agent_name}")
                        results.append(
                            {
                                "agent": agent_name,
                                "subtask": subtask,
                                "reason": step.get("reason", ""),
                                "result": {
                                    "status": "error",
                                    "error": f"Agent {agent_name} not found",
                                },
                            }
                        )

                # Get final summary from manager
                summary_messages: List[Dict[str, Union[str, List[Any]]]] = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"""Task: {task}

Analyze this task and create a plan using the available agents. Break it down into clear steps. Respond in JSON and only assign tasks to agents that exist in the group.""",
                    },
                    {"role": "assistant", "content": json.dumps(plan)},
                ]

                # Add results for summary
                result_content = ""
                for result in results:
                    if result["result"]["status"] == "success":
                        result_content += f"Result from {result['agent']}: {result['result']['response']}\n\n"
                    else:
                        result_content += f"Error from {result['agent']}: {result['result'].get('error', 'Unknown error')}\n\n"

                # Add results as a user message
                if result_content:
                    summary_messages.append(
                        {
                            "role": "user",
                            "content": f"Here are the results from the agents:\n\n{result_content.strip()}\n\nProvide a final summary of the task execution and results. Include what was accomplished and any conclusions drawn.",
                        }
                    )
                else:
                    summary_messages.append(
                        {
                            "role": "user",
                            "content": "Provide a final summary of the task execution and results. Include what was accomplished and any conclusions drawn.",
                        }
                    )

                # Get summary with JSON formatting
                summary_response = OllamaAPI.chat_completion(
                    model=manager_model,
                    messages=summary_messages,
                    temperature=0.3,
                    stream=False,
                    format={
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                            "outcome": {
                                "type": "string",
                                "enum": ["success", "partial", "failure"],
                            },
                            "next_steps": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["summary", "outcome"],
                    },
                )

                # Parse summary response
                if isinstance(summary_response, dict) and "message" in summary_response:
                    summary_content = summary_response["message"].get("content", "{}")
                else:
                    summary_content = getattr(
                        getattr(summary_response, "message", None), "content", "{}"
                    )

                try:
                    summary_data = json.loads(summary_content)
                    self.add_shared_memory(
                        f"Task Summary: {summary_data['summary']}", source="manager"
                    )

                    return {
                        "status": "success",
                        "plan": plan,
                        "results": results,
                        "summary": summary_data["summary"],
                        "outcome": summary_data["outcome"],
                        "next_steps": summary_data.get("next_steps", []),
                    }

                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to parse manager summary response: {summary_content}"
                    )
                    return {
                        "status": "error",
                        "error": "Failed to parse manager summary response",
                    }

            except json.JSONDecodeError:
                logger.error(f"Failed to parse manager plan response: {plan_content}")
                return {
                    "status": "error",
                    "error": "Failed to parse manager plan response",
                }

        except Exception as e:
            logger.error(
                f"Error in manager task execution for group {self.name}: {str(e)}"
            )
            logger.info(f"Exception details: {traceback.format_exc()}")
            return {"status": "error", "error": str(e)}
