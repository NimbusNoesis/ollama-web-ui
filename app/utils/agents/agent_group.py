"""
AgentGroup class for multi-agent systems.
"""

from typing import Dict, List, Any, Union, Optional
import uuid
import json
import traceback
import time
from datetime import datetime

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.agents.agent import Agent

# Get application logger
logger = get_logger()


class AgentGroup:
    """Class representing a group of agents that can work together"""

    def __init__(
        self,
        name: str,
        description: str,
        id: Optional[str] = None,
        agents: Optional[List[Agent]] = None,
        shared_memory: Optional[List[Dict[str, Any]]] = None,
        execution_history: Optional[List[Dict[str, Any]]] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.agents = agents or []
        self.shared_memory = shared_memory or []
        self.execution_history = execution_history or []
        self.created_at = created_at or datetime.now().isoformat()
        logger.info(f"Created new AgentGroup: {name} (ID: {self.id})")
        logger.debug(f"AgentGroup {name} description: {description}")

    def to_dict(self) -> Dict[str, Any]:
        logger.debug(f"Converting AgentGroup {self.name} to dictionary")
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agents": [agent.to_dict() for agent in self.agents],
            "shared_memory": self.shared_memory,
            "execution_history": self.execution_history,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentGroup":
        logger.debug(f"Creating AgentGroup from dictionary: {data.get('name')}")
        # Convert agent dictionaries to Agent objects
        agents = [Agent.from_dict(agent_data) for agent_data in data.get("agents", [])]
        
        return cls(
            id=data.get("id"),
            name=data.get("name", "Unnamed Group"),
            description=data.get("description", ""),
            agents=agents,
            shared_memory=data.get("shared_memory", []),
            execution_history=data.get("execution_history", []),
            created_at=data.get("created_at"),
        )

    def add_shared_memory(self, content: str, source: str = "group"):
        """Add a memory entry to the group's shared memory"""
        timestamp = datetime.now().isoformat()
        self.shared_memory.append(
            {
                "content": content,
                "source": source,
                "timestamp": timestamp,
            }
        )
        logger.info(f"Added shared memory to group {self.name} from source: {source}")
        logger.debug(f"Shared memory content: {content}, Timestamp: {timestamp}")

    def add_to_history(self, entry: Dict[str, Any]):
        """
        Add an execution entry to the group's history.
        
        Args:
            entry: Dictionary containing execution details
        """
        # Add timestamp and ID if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now().isoformat()
        
        if "id" not in entry:
            entry["id"] = str(uuid.uuid4())
            
        self.execution_history.append(entry)
        
        # Trim history if it gets too large (keep last 100 entries)
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
        
        return entry["id"]

    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for the manager prompt"""
        logger.debug(f"Formatting agent capabilities for group {self.name}")
        if not self.agents:
            logger.warning(f"No agents available in group {self.name}")
            return "No agents available."

        capabilities = []
        for agent in self.agents:
            # Skip any agent with the name "manager" (case-insensitive)
            if agent.name.lower() == "manager":
                logger.debug(
                    f"Skipping manager agent {agent.name} in capabilities list"
                )
                continue

            capabilities.append(
                f"- Name: {agent.name}\n-- System Prompt: ```{agent.system_prompt}```"
            )

        if not capabilities:
            logger.warning(f"No non-manager agents available in group {self.name}")
            return "No non-manager agents available."

        logger.debug(
            f"Formatted capabilities for {len(capabilities)} agents in group {self.name}"
        )
        return "\n".join(capabilities)

    def get_manager_prompt(self) -> str:
        """Get the system prompt for the manager agent"""
        logger.debug(f"Generating manager prompt for group {self.name}")
        prompt = f"""You are the manager of a group of AI agents named '{self.name}'. Your role is to:
1. Analyze tasks and break them down into subtasks
2. Assign subtasks to appropriate agents based on their capabilities.
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
        logger.debug(f"Generated manager prompt of length {len(prompt)}")
        return prompt

    def execute_task_with_manager(self, task: str) -> Dict[str, Any]:
        """Execute a task using a manager agent to coordinate"""
        start_time = time.time()
        logger.info(f"Group {self.name} executing task with manager: {task}")

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
                manager_model = self.agents[0].model if self.agents else "llama2"
                logger.warning(
                    f"No agent named 'manager' found. Using model {manager_model} as fallback"
                )

            # Get the base manager prompt
            system_prompt = self.get_manager_prompt()

            # Add shared memory context to the system prompt if available
            if self.shared_memory:
                memory_context = "Group Memory Context:\n" + "\n".join(
                    f"- {m['content']}" for m in self.shared_memory
                )
                system_prompt = f"{system_prompt}\n\n{memory_context}"
                logger.debug(
                    f"Added {len(self.shared_memory)} shared memories to manager prompt"
                )

            # Set up messages with a single system prompt followed by the user message
            planning_messages: List[Dict[str, Union[str, List[Any]]]] = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"""Task: {task}

Analyze this task and create a plan using the available agents. If an agent does not exist, do not assign it any tasks. Break it down into clear steps. Respond in JSON and only assign tasks to agents that exist in the group. Ensure each agent is called only once in the plan.""",
                },
            ]

            # Get plan from manager with JSON formatting
            logger.info(f"Requesting plan from manager using model {manager_model}")
            plan_start_time = time.time()
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
            plan_duration = time.time() - plan_start_time
            logger.info(f"Received plan from manager in {plan_duration:.2f} seconds")

            # Parse plan response
            if isinstance(plan_response, dict) and "message" in plan_response:
                plan_content = plan_response["message"].get("content", "{}")
            else:
                plan_content = getattr(
                    getattr(plan_response, "message", None), "content", "{}"
                )

            try:
                logger.debug(f"Parsing plan response: {plan_content}")
                plan = json.loads(plan_content)
                logger.info(f"Manager created plan with {len(plan['steps'])} steps")
                self.add_shared_memory(
                    f"Task Planning: {plan['thought_process']}", source="manager"
                )

                # Execute each step with the assigned agent
                results = []
                step_count = len(plan["steps"])

                for step_index, step in enumerate(plan["steps"]):
                    agent_name = step["agent"]
                    subtask = step["task"]
                    reason = step.get("reason", "No reason provided")

                    logger.info(
                        f"Executing step {step_index+1}/{step_count}: Agent {agent_name}"
                    )
                    logger.debug(f"Step {step_index+1} reason: {reason}")

                    agent = next((a for a in self.agents if a.name == agent_name), None)

                    if agent:
                        step_start_time = time.time()
                        logger.info(
                            f"Executing step with agent {agent_name}: {subtask}"
                        )

                        # Share relevant group memory with the agent before executing the task
                        if self.shared_memory:
                            relevant_memories = self.shared_memory
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
                        step_duration = time.time() - step_start_time
                        logger.info(
                            f"Step {step_index+1} completed in {step_duration:.2f} seconds with status: {result['status']}"
                        )

                        # Add agent's response to its own memory for future reference
                        if result["status"] == "success":
                            agent.add_to_memory(
                                f"I completed task: {subtask}\nResponse: {result['response']}",
                                source="self_reflection",
                            )
                            logger.debug(
                                f"Added self-reflection to agent {agent_name}'s memory"
                            )

                        results.append(
                            {
                                "agent": agent_name,
                                "subtask": subtask,
                                "reason": step.get("reason", ""),
                                "result": result,
                                "execution_time": step_duration,
                            }
                        )

                        # Add result to shared memory
                        if result["status"] == "success":
                            self.add_shared_memory(
                                f"Agent {agent_name} completed task: {subtask}\nThought process: {result.get('thought_process', '')}\nResponse: {result['response']}",
                                source="execution",
                            )

                            logger.info(
                                f"Added memory summary from agent {agent_name} to group shared memory"
                            )
                        else:
                            self.add_shared_memory(
                                f"Agent {agent_name} failed task: {subtask}\nError: {result.get('error', 'Unknown error')}",
                                source="execution",
                            )
                            logger.warning(
                                f"Agent {agent_name} failed to complete task: {result.get('error', 'Unknown error')}"
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
                                "execution_time": 0,
                            }
                        )

                # Get final summary from manager
                logger.info("Generating final summary from manager")
                summary_start_time = time.time()

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
                logger.info("Requesting final summary from manager")
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
                summary_duration = time.time() - summary_start_time
                logger.info(
                    f"Received summary from manager in {summary_duration:.2f} seconds"
                )

                # Parse summary response
                if isinstance(summary_response, dict) and "message" in summary_response:
                    summary_content = summary_response["message"].get("content", "{}")
                else:
                    summary_content = getattr(
                        getattr(summary_response, "message", None), "content", "{}"
                    )

                try:
                    logger.debug(f"Parsing summary response: {summary_content}")
                    summary_data = json.loads(summary_content)
                    self.add_shared_memory(
                        f"Task Summary: {summary_data['summary']}", source="manager"
                    )

                    total_duration = time.time() - start_time
                    outcome = summary_data["outcome"]
                    logger.info(
                        f"Task execution completed with outcome: {outcome} in {total_duration:.2f} seconds"
                    )

                    if "next_steps" in summary_data and summary_data["next_steps"]:
                        logger.info(
                            f"Manager suggested {len(summary_data['next_steps'])} next steps"
                        )

                    # Record in history after execution
                    history_entry = {
                        "type": "manager_execution",
                        "task": task,
                        "agents_involved": [step["agent"] for step in plan["steps"]],
                        "result": {
                            "status": "success",
                            "plan": plan,
                            "results": results,
                            "summary": summary_data["summary"],
                            "outcome": outcome,
                            "next_steps": summary_data.get("next_steps", []),
                        }
                    }
                    history_id = self.add_to_history(history_entry)
                    logger.info(f"Added manager execution to history with ID: {history_id}, current history size: {len(self.execution_history)}")
                    
                    # Import and call save_agents to persist changes
                    from app.utils.agents.ui_components import save_agents
                    save_agents()
                    logger.info(f"Saved agent groups with updated history to disk")

                    return {
                        "status": "success",
                        "plan": plan,
                        "results": results,
                        "summary": summary_data["summary"],
                        "outcome": outcome,
                        "next_steps": summary_data.get("next_steps", []),
                        "execution_time": total_duration,
                    }

                except json.JSONDecodeError:
                    total_duration = time.time() - start_time
                    logger.error(
                        f"Failed to parse manager summary response: {summary_content}"
                    )
                    return {
                        "status": "error",
                        "error": "Failed to parse manager summary response",
                        "raw_content": summary_content,
                        "execution_time": total_duration,
                    }

            except json.JSONDecodeError:
                total_duration = time.time() - start_time
                logger.error(f"Failed to parse manager plan response: {plan_content}")
                return {
                    "status": "error",
                    "error": "Failed to parse manager plan response",
                    "raw_content": plan_content,
                    "execution_time": total_duration,
                }

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"Error in manager task execution for group {self.name} ({total_duration:.2f}s): {str(e)}"
            )
            logger.debug(f"Task that caused error: {task}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": total_duration,
            }
