# Agent System Blueprint

## Overview and Architecture

The Ollama Web UI's multi-agent system is a modular framework that enables the creation, management, and execution of collaborative AI agent networks. This document serves as a comprehensive technical guide to the architecture, components, workflows, and integration points of the agent system.

## 1. System Architecture

### 1.1 Core Components

The agent system is built around several key components:

- **Individual Agents**: Autonomous LLM-powered entities with specialized capabilities
- **Agent Groups**: Collections of agents designed to work together on complex tasks
- **Manager Coordination**: Protocol for task delegation and result aggregation
- **Memory Systems**: Both individual and shared memory structures for context retention
- **Tool Integration**: External functionality made available to agents
- **Persistence Layer**: Storage of agent configurations, memories, and execution logs

The system follows an object-oriented design with clear separation of concerns between UI, logic, and data layers.

```
┌─────────────────────────┐      ┌──────────────────────┐
│      UI Components      │◄────►│     Agent Logic      │
│                         │      │                      │
│ - Agent Editor          │      │ - Agent Class        │
│ - Group Editor          │      │ - AgentGroup Class   │
│ - Task Execution UI     │      │ - Execution Engine   │
└─────────────────────────┘      └──────────┬───────────┘
                                            │
                 ┌──────────────────────────▼───────────────────────┐
                 │               External Integrations               │
                 │                                                   │
                 │ - Ollama API                                      │
                 │ - Tool Ecosystem                                  │
                 │ - Persistence Layer                               │
                 └───────────────────────────────────────────────────┘
```

### 1.2 Directory Structure

The agent system code is organized into the following structure:

- `app/utils/agents/`: Core agent system implementation
  - `agent.py`: Individual agent implementation
  - `agent_group.py`: Agent group implementation
  - `ui_components.py`: Streamlit UI components
  - `schemas.py`: JSON schemas for structured responses
- `app/pages/agents_page.py`: Main agent UI page
- `app/data/agents/`: Storage location for agent configurations

## 2. Individual Agent Architecture

### 2.1 Agent Data Model

Each agent is represented by the `Agent` class with the following properties:

- **id**: Unique UUID for the agent
- **name**: Human-readable name
- **model**: Ollama model name to use (e.g., "llama2", "mistral")
- **system_prompt**: Instructions defining the agent's role and behavior
- **tools**: List of function tools available to the agent
- **memory**: List of past observations, tasks, and executions
- **created_at**: Timestamp of creation

### 2.2 Agent Capabilities

Individual agents can:

1. **Execute Tasks**: Process natural language instructions using their assigned LLM
2. **Use Tools**: Call external functions to extend capabilities beyond pure text generation
3. **Maintain Memory**: Record interactions and context for future reference
4. **Serialize/Deserialize**: Convert to/from JSON representation for persistence
5. **Reason**: Demonstrate explicit reasoning via thought processes in responses

### 2.3 Agent Implementation

The `Agent` class provides methods for:

```python
class Agent:
    def __init__(self, name, model, system_prompt, tools=None):
        # Initialize agent properties
        
    def to_dict(self) -> Dict:
        # Convert agent to dictionary for serialization
        
    @classmethod
    def from_dict(cls, data: Dict) -> "Agent":
        # Create agent from dictionary representation
        
    def add_to_memory(self, content: str, source: str = "observation"):
        # Add an entry to the agent's memory
        
    def execute_task(self, task: str) -> Dict[str, Any]:
        # Execute a natural language task
        
    def execute_tool(self, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Execute a specific tool with given inputs
```

### 2.4 Agent Response Format

Agent responses follow a structured JSON format:

```json
{
  "status": "success",
  "thought_process": "Detailed reasoning about the task...",
  "response": "Final answer or output for the user",
  "tool_calls": [
    {
      "tool": "tool_name",
      "input": { "param1": "value1", "param2": "value2" }
    }
  ],
  "execution_time": 1.23
}
```

## 3. Agent Group System

### 3.1 Group Data Model

Agent groups are represented by the `AgentGroup` class with these properties:

- **id**: Unique UUID for the group
- **name**: Human-readable name
- **description**: Purpose and capabilities of the group
- **agents**: List of Agent objects in the group
- **shared_memory**: Group-level memory accessible to all agents
- **created_at**: Timestamp of creation

### 3.2 Group Capabilities

Agent groups can:

1. **Manage Agents**: Add, remove, and configure member agents
2. **Execute Tasks**: Process complex tasks using member agents
3. **Coordinate Work**: Use a manager to delegate subtasks
4. **Share Memory**: Maintain group-level context accessible to all agents
5. **Aggregate Results**: Combine outputs from multiple agents into coherent responses

### 3.3 Group Implementation

The `AgentGroup` class provides methods for:

```python
class AgentGroup:
    def __init__(self, name: str, description: str):
        # Initialize group properties
        
    def to_dict(self) -> Dict:
        # Convert group to dictionary for serialization
        
    @classmethod
    def from_dict(cls, data: Dict) -> "AgentGroup":
        # Create group from dictionary representation
        
    def add_shared_memory(self, content: str, source: str = "group"):
        # Add an entry to the group's shared memory
        
    def _format_agent_capabilities(self) -> str:
        # Internal method to format agent capabilities for the manager
        
    def get_manager_prompt(self) -> str:
        # Generate system prompt for the manager agent
        
    def execute_task_with_manager(self, task: str) -> Dict[str, Any]:
        # Execute a task using the manager coordination protocol
```

### 3.4 Group Response Format

Group execution responses follow this structure:

```json
{
  "status": "success",
  "plan": {
    "thought_process": "Manager's analysis of the task...",
    "steps": [
      {
        "agent": "agent_name",
        "task": "Subtask description",
        "reason": "Why this agent was chosen"
      }
    ]
  },
  "results": [
    {
      "agent": "agent_name",
      "result": {
        "status": "success",
        "response": "Agent's response to the subtask"
      }
    }
  ],
  "summary": "Overall summary of the results",
  "outcome": "Final outcome of the task",
  "next_steps": ["Suggested follow-up action 1", "Suggested follow-up action 2"]
}
```

## 4. Manager Coordination Protocol

### 4.1 Manager Role

The manager agent is responsible for:

1. Analyzing complex tasks
2. Breaking tasks into appropriate subtasks
3. Matching subtasks to agent capabilities
4. Coordinating execution sequence
5. Aggregating results into coherent outputs
6. Maintaining context across subtasks

### 4.2 Manager Prompt Template

The manager uses a specialized system prompt:

```
You are the manager of a group of AI agents named '{group_name}'. Your role is to:
1. Analyze tasks and break them down into subtasks
2. Assign subtasks to appropriate agents based on their capabilities
3. Coordinate between agents and aggregate their responses
4. Maintain group coherence and shared context

Available Agents:
{formatted_agent_capabilities}

IMPORTANT FORMATTING INSTRUCTIONS:
You must respond in valid JSON format with this schema:
{
    "thought_process": "Your analysis of the task and plan",
    "steps": [
        {
            "agent": "agent_name",
            "task": "detailed task description",
            "reason": "why this agent was chosen"
        }
    ]
}
```

### 4.3 Execution Flow

1. User submits task to the group
2. Manager agent receives task and agent capabilities
3. Manager creates execution plan with subtasks
4. System executes each subtask with the assigned agent
5. Results are collected and provided to the manager
6. Manager synthesizes a final response
7. Results are displayed to the user

## 5. Memory Systems

### 5.1 Individual Memory

Each agent maintains a personal memory store with entries containing:

- **content**: The memory content (observation, reasoning, task, etc.)
- **source**: Origin of the memory (task, observation, execution, etc.)
- **timestamp**: When the memory was created

Individual memory is used to provide context for future tasks assigned to the specific agent.

### 5.2 Shared Memory

Agent groups maintain a shared memory store with similar structure:

- **content**: The shared memory content
- **source**: Origin of the memory (often "manager" or "group")
- **timestamp**: When the memory was created

Shared memory is accessible to all agents in the group and provides group-level context.

### 5.3 Memory Integration

Memory is incorporated into prompts as contextual information:

```
System Prompt: {agent_system_prompt}

Group Shared Context:
- {shared_memory_item_1}
- {shared_memory_item_2}
```

## 6. Tool Integration

### 6.1 Tool Structure

Tools follow the OpenAI function calling format:

```json
{
  "function": {
    "name": "tool_name",
    "description": "What the tool does",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "Description of parameter 1"
        }
      },
      "required": ["param1"]
    }
  }
}
```

### 6.2 Tool Loading

Tools are loaded dynamically using the `ToolLoader` utility:

1. Available tools are listed in the agent editor
2. Selected tools are attached to agent configurations
3. During execution, tools are made available to the LLM
4. The LLM can choose to call tools as needed

### 6.3 Tool Execution Flow

1. Agent recognizes need for tool in task response
2. Agent formats a tool call with name and parameters
3. System intercepts tool call and executes the actual function
4. Tool results are returned to the agent
5. Agent incorporates tool results into final response

## 7. Persistence

### 7.1 Storage Format

Agent and group configurations are stored as JSON files:

- Location: `app/data/agents/agent_groups.json`
- Format: Array of serialized AgentGroup objects
- Includes: All agent configurations, group settings, and memory

### 7.2 Persistence Methods

```python
def load_agents():
    """Load saved agent groups from disk"""
    # Implementation details...

def save_agents():
    """Save agent groups to disk"""
    # Implementation details...
```

### 7.3 Backup Strategy

The system creates backups of existing configuration files before saving:
- Creates `.json.bak` before overwriting existing files
- Handles serialization errors gracefully
- Logs detailed information about save operations

## 8. UI Components

### 8.1 Agent Editor

Provides interface for:
- Setting agent name
- Selecting Ollama model
- Defining system prompt
- Selecting available tools

### 8.2 Group Editor

Provides interface for:
- Setting group name and description
- Managing member agents
- Viewing agent relationships

### 8.3 Task Execution UI

Provides interface for:
- Submitting tasks to agents or groups
- Viewing execution progress
- Exploring execution results
- Examining agent reasoning

### 8.4 Agent View

Displays:
- Agent configuration details
- Edit and delete options
- Memory inspection

## 9. Execution Workflow

### 9.1 Individual Agent Execution

1. Task submitted to specific agent
2. System retrieves agent configuration
3. System builds prompt with:
   - Agent's system prompt
   - Relevant memory context
   - Task description
4. Model generates structured JSON response
5. System processes response, executing any tool calls
6. Results displayed to user
7. Interaction added to agent's memory

### 9.2 Group Execution with Manager

1. Task submitted to group
2. System identifies manager (or creates temporary one)
3. System builds manager prompt with:
   - Manager system prompt template
   - Available agent capabilities
   - Shared memory context
   - Task description
4. Manager creates execution plan with subtasks
5. System sequentially executes each subtask:
   - Assigns to specified agent
   - Provides relevant context
   - Collects results
6. All subtask results provided to manager
7. Manager synthesizes final response
8. Results displayed to user
9. Key information added to shared memory

## 10. Extension Points

### 10.1 Adding New Agent Types

To create specialized agent types:
1. Extend the `Agent` class with domain-specific methods
2. Create specialized system prompts
3. Develop custom tool integrations
4. Add UI components for configuration

### 10.2 Adding New Tools

To add new tools:
1. Define tool function specification
2. Implement actual function logic
3. Register with ToolLoader system
4. Add to available tools list

### 10.3 Custom Execution Protocols

To create new execution flows:
1. Add new methods to AgentGroup class
2. Implement specialized manager prompts
3. Define interaction patterns between agents
4. Create UI components for new protocols

## 11. Best Practices

### 11.1 Agent Design Principles

1. **Specialization**: Design agents with focused capabilities
2. **Clear Instruction**: Write explicit, detailed system prompts
3. **Context Management**: Be mindful of context window limitations
4. **Tool Integration**: Extend capabilities through tools where appropriate
5. **Memory Usage**: Add only significant information to memory

### 11.2 Group Composition

1. **Complementary Skills**: Combine agents with different specialties
2. **Manager Selection**: Use a capable model for the manager role
3. **Size Limits**: Keep groups small enough to be manageable
4. **Communication Paths**: Design clear information flow between agents

### 11.3 System Prompt Engineering

1. **Role Definition**: Clearly define the agent's role and purpose
2. **Capability Description**: List what the agent can and cannot do
3. **Output Format**: Specify exact response structure requirements
4. **Examples**: Include examples of expected interactions
5. **Constraints**: Define operational boundaries and limitations

## 12. System Integration

### 12.1 Ollama API Integration

The agent system interacts with Ollama through the OllamaAPI class:

```python
response = OllamaAPI.chat_completion(
    model=agent.model,
    messages=messages,
    temperature=0.3,
    stream=False,
    tools=agent.tools,
    format=AGENT_RESPONSE_SCHEMA,
)
```

### 12.2 Streamlit Integration

The system integrates with Streamlit for:
- State management (st.session_state)
- UI rendering (st.form, st.button, etc.)
- Progress tracking (st.spinner, st.progress)
- Result visualization (st.expander, st.markdown)

### 12.3 Logging System

Comprehensive logging is integrated throughout the agent system:
- Debug-level tracking of all operations
- Info-level summaries of key actions
- Warning and error capture
- Performance metrics
- Configurable log levels via UI

## Conclusion

This blueprint provides a comprehensive overview of the agent system architecture, components, and workflows. By understanding these elements, developers can effectively extend and customize the system for specific use cases, or create entirely new collaborative agent experiences.

The modular design enables incremental improvements while maintaining backward compatibility, and the clear separation of concerns simplifies maintenance and extension of the codebase. 