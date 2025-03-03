"""
Agent class for multi-agent systems.
"""

from typing import Dict, List, Any, Union, Optional
import uuid
import json
import traceback
import time
from datetime import datetime

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger
from app.utils.agents.schemas import AGENT_RESPONSE_SCHEMA, TOOL_RESPONSE_SCHEMA

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
            logger.info(
                f"Agent {name} initialized with {len(tools)} tools: {[t['function']['name'] for t in tools]}"
            )
        logger.debug(f"Agent {name} system prompt: {system_prompt}")

    def to_dict(self) -> Dict:
        logger.debug(f"Converting Agent {self.name} to dictionary")
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
        logger.debug(f"Creating Agent from dictionary: {data.get('name')}")
        agent = cls(
            name=data["name"],
            model=data["model"],
            system_prompt=data["system_prompt"],
            tools=data.get("tools", []),
        )
        agent.id = data["id"]
        agent.memory = data.get("memory", [])
        agent.created_at = data["created_at"]
        logger.debug(
            f"Restored Agent {agent.name} (ID: {agent.id}) with {len(agent.memory)} memory entries"
        )
        return agent

    def add_to_memory(self, content: str, source: str = "observation"):
        """Add a memory entry for this agent"""
        timestamp = datetime.now().isoformat()
        self.memory.append(
            {
                "content": content,
                "source": source,
                "timestamp": timestamp,
            }
        )
        logger.debug(
            f"Agent {self.name} memory added - Source: {source}, Content: {content}, Timestamp: {timestamp}"
        )

    def execute_task(self, task: str) -> Dict[str, Any]:
        """Execute a task using this agent's capabilities"""
        start_time = time.time()
        logger.info(f"Agent {self.name} (ID: {self.id}) executing task: {task}")

        # Start with the agent's system prompt
        system_content = self.system_prompt

        # Add relevant memories as context, prioritizing group shared memory
        if self.memory:
            # Separate group shared memory from individual memory
            group_memories = [
                m for m in self.memory if m.get("source") == "group_memory"
            ]

            logger.debug(
                f"Agent {self.name} has {len(group_memories)} group memories and {len(self.memory) - len(group_memories)} individual memories"
            )

            # Format memory sections
            memory_sections = []

            # Add group shared memory first if available
            if group_memories:
                group_memory_context = "Group Shared Context:\n" + "\n".join(
                    f"- {m['content']}" for m in group_memories
                )
                memory_sections.append(group_memory_context)
                logger.debug(
                    f"Added {len(group_memories)} group memories to context for Agent {self.name}"
                )

            # Combine all memory sections
            if memory_sections:
                system_content += "\n\n" + "\n\n".join(memory_sections)
                logger.debug(
                    f"Added memory sections to system content for Agent {self.name}"
                )

        # Add JSON formatting instructions
        json_format_instructions = """

You must respond in JSON format according to this schema:
{
    "thought_process": "Your reasoning about the task",
    "response": "Your final response"
}
Think through your actions first, then list any tools needed, and finally provide your response.

Do a detailed review of all provided memories and context, use this information to formulate your response."""

        system_content += json_format_instructions

        # Create messages list with a single system message followed by the user task
        messages: List[Dict[str, Union[str, List[Any]]]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": task},
        ]

        try:
            logger.info(f"Agent {self.name} calling OllamaAPI with model {self.model}")
            api_start_time = time.time()
            response = OllamaAPI.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.3,
                stream=False,
                tools=self.tools,
                format=AGENT_RESPONSE_SCHEMA,
            )
            api_duration = time.time() - api_start_time
            logger.info(
                f"Agent {self.name} received response from OllamaAPI in {api_duration:.2f} seconds"
            )

            # Extract response content
            if isinstance(response, dict) and "message" in response:
                content = response["message"].get("content", "{}")
            else:
                content = getattr(getattr(response, "message", None), "content", "{}")

            # Parse JSON response
            try:
                logger.debug(f"Agent {self.name} parsing response: {content}")
                parsed_response = json.loads(content)

                # Add task and response to memory
                self.add_to_memory(f"Task: {task}", source="task")
                self.add_to_memory(
                    f"Thought process: {parsed_response['thought_process']}",
                    source="reasoning",
                )
                self.add_to_memory(
                    f"Response: {parsed_response['response']}",
                    source="execution",
                )

                total_duration = time.time() - start_time
                logger.info(
                    f"Agent {self.name} completed task successfully in {total_duration:.2f} seconds"
                )

                # Log tool calls if present
                if "tool_calls" in parsed_response and parsed_response["tool_calls"]:
                    logger.info(
                        f"Agent {self.name} requested {len(parsed_response['tool_calls'])} tool calls"
                    )
                    for i, tool_call in enumerate(parsed_response["tool_calls"]):
                        logger.debug(
                            f"Tool call {i+1}: {tool_call.get('name', 'unknown')}"
                        )

                return {
                    "status": "success",
                    "thought_process": parsed_response["thought_process"],
                    "response": parsed_response["response"],
                    "tool_calls": parsed_response.get("tool_calls", []),
                    "execution_time": total_duration,
                }

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse agent response as JSON: {str(e)}"
                logger.error(f"{error_msg}: {content}")
                return {"status": "error", "error": error_msg, "raw_content": content}

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"Error when agent {self.name} executed task ({total_duration:.2f}s): {str(e)}"
            )
            logger.debug(f"Task that caused error: {task}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": total_duration,
            }

    def execute_tool(
        self, tool_name: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool and validate its response"""
        start_time = time.time()
        logger.info(
            f"Agent {self.name} executing tool: {tool_name} with input: {str(input_data)}"
        )

        # Find tool definition
        tool_def = next(
            (t for t in self.tools if t["function"]["name"] == tool_name), None
        )
        if not tool_def:
            logger.error(f"Tool {tool_name} not found in agent {self.name}'s tools")
            return {
                "status": "error",
                "error": f"Tool {tool_name} not found in agent's tools",
            }

        try:
            # Execute tool with format validation
            messages: List[Dict[str, Union[str, List[Any]]]] = [
                {
                    "role": "system",
                    "content": "Execute the tool and return results in JSON format according to the schema.",
                },
                {
                    "role": "user",
                    "content": json.dumps({"tool": tool_name, "input": input_data}),
                },
            ]

            api_start_time = time.time()
            response = OllamaAPI.chat_completion(
                model=self.model,
                messages=messages,
                stream=False,
                format=TOOL_RESPONSE_SCHEMA,
            )
            api_duration = time.time() - api_start_time
            logger.debug(
                f"Tool {tool_name} API call completed in {api_duration:.2f} seconds"
            )

            # Extract and parse response
            if isinstance(response, dict) and "message" in response:
                content = response["message"].get("content", "{}")
            else:
                content = getattr(getattr(response, "message", None), "content", "{}")

            result = json.loads(content)
            total_duration = time.time() - start_time
            logger.info(
                f"Tool {tool_name} executed successfully in {total_duration:.2f} seconds"
            )

            # Add execution details
            result["execution_time"] = total_duration
            return result

        except Exception as e:
            total_duration = time.time() - start_time
            logger.error(
                f"Error executing tool {tool_name} ({total_duration:.2f}s): {str(e)}"
            )
            logger.debug(f"Tool input that caused error: {str(input_data)}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": total_duration,
            }
