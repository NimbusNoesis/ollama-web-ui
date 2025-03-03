"""
Agent class for multi-agent systems.
"""

from typing import Dict, List, Any, Union, Optional
import uuid
import json
import traceback
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

        # Start with the agent's system prompt
        system_content = self.system_prompt

        # Add relevant memories as context, prioritizing group shared memory
        if self.memory:
            # Separate group shared memory from individual memory
            group_memories = [
                m for m in self.memory if m.get("source") == "group_memory"
            ]
            individual_memories = [
                m for m in self.memory if m.get("source") != "group_memory"
            ]

            # Format memory sections
            memory_sections = []

            # Add group shared memory first if available
            if group_memories:
                group_memory_context = "Group Shared Context:\n" + "\n".join(
                    f"- {m['content']}" for m in group_memories[-5:]
                )
                memory_sections.append(group_memory_context)

            # Add individual memories
            if individual_memories:
                individual_memory_context = "My Previous Knowledge:\n" + "\n".join(
                    f"- {m['content']}" for m in individual_memories[-5:]
                )
                memory_sections.append(individual_memory_context)

            # Combine all memory sections
            if memory_sections:
                system_content += "\n\n" + "\n\n".join(memory_sections)

        # Add JSON formatting instructions
        json_format_instructions = """

You must respond in JSON format according to this schema:
{
    "thought_process": "Your reasoning about the task",
    "response": "Your final response"
}
Think through your actions first, then list any tools needed, and finally provide your response."""

        system_content += json_format_instructions

        # Create messages list with a single system message followed by the user task
        messages: List[Dict[str, Union[str, List[Any]]]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": task},
        ]

        try:
            logger.info(f"Agent {self.name} calling OllamaAPI with model {self.model}")
            response = OllamaAPI.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.7,
                stream=False,
                tools=self.tools,
                format=AGENT_RESPONSE_SCHEMA,
            )

            # Extract response content
            if isinstance(response, dict) and "message" in response:
                content = response["message"].get("content", "{}")
            else:
                content = getattr(getattr(response, "message", None), "content", "{}")

            # Parse JSON response
            try:
                parsed_response = json.loads(content)

                # Add task and response to memory
                self.add_to_memory(f"Task: {task}", source="task")
                self.add_to_memory(
                    f"Thought process: {parsed_response['thought_process']}",
                    source="reasoning",
                )
                self.add_to_memory(
                    f"Response: {parsed_response['response']}", source="execution"
                )

                logger.info(f"Agent {self.name} completed task successfully")
                return {
                    "status": "success",
                    "thought_process": parsed_response["thought_process"],
                    "response": parsed_response["response"],
                    "tool_calls": parsed_response.get("tool_calls", []),
                }

            except json.JSONDecodeError:
                error_msg = "Failed to parse agent response as JSON"
                logger.error(f"{error_msg}: {content}")
                return {"status": "error", "error": error_msg}

        except Exception as e:
            logger.error(f"Error when agent {self.name} executed task: {str(e)}")
            logger.info(f"Exception details: {traceback.format_exc()}")
            return {"status": "error", "error": str(e)}

    def execute_tool(
        self, tool_name: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool and validate its response"""
        logger.info(f"Agent {self.name} executing tool: {tool_name}")

        # Find tool definition
        tool_def = next(
            (t for t in self.tools if t["function"]["name"] == tool_name), None
        )
        if not tool_def:
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

            response = OllamaAPI.chat_completion(
                model=self.model,
                messages=messages,
                stream=False,
                format=TOOL_RESPONSE_SCHEMA,
            )

            # Extract and parse response
            if isinstance(response, dict) and "message" in response:
                content = response["message"].get("content", "{}")
            else:
                content = getattr(getattr(response, "message", None), "content", "{}")

            result = json.loads(content)
            return result

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"status": "error", "error": str(e)}
