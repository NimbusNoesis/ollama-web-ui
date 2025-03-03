"""
JSON Schema definitions for agent responses.
"""

# JSON Schemas for agent responses
AGENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "thought_process": {
            "type": "string",
            "description": "Agent's reasoning about the task",
        },
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"tool": {"type": "string"}, "input": {"type": "object"}},
                "required": ["tool", "input"],
            },
        },
        "response": {"type": "string", "description": "Agent's final response"},
    },
    "required": ["thought_process", "response"],
}

MANAGER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "thought_process": {
            "type": "string",
            "description": "Manager's reasoning about task delegation",
        },
        "action": {
            "type": "string",
            "enum": ["assign_task", "complete"],
            "description": "What action the manager is taking",
        },
        "assignment": {
            "type": "object",
            "properties": {"agent": {"type": "string"}, "task": {"type": "string"}},
            "required": ["agent", "task"],
        },
        "summary": {"type": "string", "description": "Summary of completed tasks"},
    },
    "required": ["thought_process", "action"],
}

TOOL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success", "error"],
            "description": "Status of the tool execution",
        },
        "result": {"type": "object", "description": "Tool execution result data"},
        "error": {"type": "string", "description": "Error message if execution failed"},
    },
    "required": ["status"],
}
