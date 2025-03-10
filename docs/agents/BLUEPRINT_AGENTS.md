# Agent System Blueprint

## Overview and Architecture

The Ollama Web UI's multi-agent system is a modular framework that enables the creation, management, and execution of collaborative AI agent networks. This document serves as a comprehensive technical guide to the architecture, components, workflows, and integration points of the agent system.

## 1. System Architecture

### 1.1 Core Components

The agent system is built around several key components:

- **Individual Agents**: Autonomous LLM-powered entities with specialized capabilities
- **Agent Groups**: Collections of agents designed to work together on complex tasks
- **Manager Coordination**: Protocol for task delegation and result aggregation
- **Memory Systems**: Individual, shared, and historical memory structures
- **Tool Integration**: External functionality made available to agents
- **Persistence Layer**: Storage of agent configurations, memories, and execution history
- **Continuation System**: Framework for building complex reasoning chains

The system follows an object-oriented design with clear separation of concerns between UI, logic, and data layers.

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                             │
│                                                             │
│ ┌───────────────────┐ ┌───────────────────┐ ┌─────────────┐ │
│ │  Agent Editor     │ │  Task Executor    │ │  History    │ │
│ │  Group Editor     │ │  Continuation UI  │ │  Viewer     │ │
│ └───────────────────┘ └───────────────────┘ └─────────────┘ │
└────────────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic                         │
│                                                             │
│ ┌───────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│ │  Agent Class  │ │  AgentGroup      │ │  Execution       │ │
│ │               │ │  Class           │ │  Engine          │ │
│ └───────────────┘ └──────────────────┘ └──────────────────┘ │
└────────────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Integrations                    │
│                                                             │
│ ┌───────────────┐ ┌──────────────────┐ ┌──────────────────┐ │
│ │  Ollama API   │ │  Tool Ecosystem  │ │  Persistence     │ │
│ │               │ │                  │ │  Layer           │ │
│ └───────────────┘ └──────────────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Directory Structure

The agent system code is organized into the following structure:

- `app/utils/agents/`: Core agent system implementation
  - `agent.py`: Individual agent implementation
  - `agent_group.py`: Agent group implementation
  - `ui_components.py`: Streamlit UI components
  - `schemas.py`: JSON schemas for structured responses
- `app/pages/agents_page.py`: Main agent UI page
- `app/data/agents/`: Storage location for agent configurations and history

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
- **execution_history**: Persistent record of all executions
- **created_at**: Timestamp of creation

### 3.2 Group Capabilities

Agent groups can:

1. **Manage Agents**: Add, remove, and configure member agents
2. **Execute Tasks**: Process complex tasks using member agents
3. **Coordinate Work**: Use a manager to delegate subtasks
4. **Share Memory**: Maintain group-level context accessible to all agents
5. **Track History**: Maintain a persistent record of all executions
6. **Aggregate Results**: Combine outputs from multiple agents into coherent responses
7. **Support Continuations**: Enable multi-step reasoning chains with context preservation

### 3.3 Group Implementation

The `AgentGroup` class provides methods for:

```python
class AgentGroup:
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
        # Initialize group properties
        
    def to_dict(self) -> Dict:
        # Convert group to dictionary for serialization
        
    @classmethod
    def from_dict(cls, data: Dict) -> "AgentGroup":
        # Create group from dictionary representation
        
    def add_shared_memory(self, content: str, source: str = "group"):
        # Add an entry to the group's shared memory
        
    def add_to_history(self, entry: Dict[str, Any]):
        # Add an execution entry to the group's history
        
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

## 4. Execution Modes

The system now supports four distinct execution pathways:

### 4.1 Manager Coordination

The manager agent is responsible for:

1. Analyzing complex tasks
2. Breaking tasks into appropriate subtasks
3. Matching subtasks to agent capabilities
4. Coordinating execution sequence
5. Aggregating results into coherent outputs
6. Maintaining context across subtasks

The execution flow is:
1. User submits task to the group
2. Manager agent receives task and agent capabilities
3. Manager creates execution plan with subtasks
4. System executes each subtask with the assigned agent
5. Results are collected and provided to the manager
6. Manager synthesizes a final response
7. Results are displayed to the user

### 4.2 Single Agent Execution

Direct execution with a specific agent:
1. User selects a specific agent from the dropdown
2. Task is sent directly to the selected agent
3. Agent processes the task using its expertise
4. Result is displayed without manager coordination
5. Execution is recorded in history

### 4.3 Multi-Agent Execution

Parallel execution with multiple selected agents:
1. User selects multiple agents via a multiselect interface
2. The same task is sent to each selected agent
3. Each agent processes the task independently
4. Responses are collected and combined
5. Combined result is displayed with individual sections
6. Execution is recorded in history with all agents involved

### 4.4 Directive-Based Execution

Targeted execution using @agent_name syntax:
1. User includes directives in the format `@AgentName: specific task`
2. System automatically detects these directives using regex
3. Each agent receives only their designated portion of the task
4. Results from all agents are collected and combined
5. Combined result is displayed with sections for each agent
6. Execution is recorded in history with directives

### 4.5 Execution Pathway Selection

The system determines the execution pathway based on:

1. **Explicit UI targeting**: If specific agent(s) are selected via dropdown/multiselect
2. **Directive presence**: If @agent_name syntax is detected in the task
3. **Default mode**: Falls back to manager coordination if no targeting

## 5. Memory and History Systems

The agent system implements three distinct memory mechanisms:

### 5.1 Agent Memory (Short-term Context)

Each agent maintains a personal memory store with entries containing:

- **content**: The memory content (observation, reasoning, task, etc.)
- **source**: Origin of the memory (task, observation, execution, etc.)
- **timestamp**: When the memory was created

Individual memory provides immediate reasoning context for individual agents during task execution. It is:
- Actively used in prompts to inform agent responses
- Limited in retention (recent items prioritized)
- Primarily focused on a single reasoning thread
- Persisted across sessions but focuses on immediate context

### 5.2 Shared Group Memory (Collaborative Context)

Agent groups maintain a shared memory store with a similar structure:

- **content**: The shared memory content
- **source**: Origin of the memory (often "manager" or "group")
- **timestamp**: When the memory was created

Shared memory facilitates information sharing between agents in a group. It is:
- Available to all agents in the group
- Persisted across multiple task executions
- Used to capture cross-agent insights and information
- Grows over time with group interactions
- Functions as a "working memory" for the group

### 5.3 Execution History (Historical Record)

Distinct from memory, execution history is a persistent record of all tasks executed by an agent group:

```json
{
  "id": "unique_uuid",
  "timestamp": "ISO-format timestamp",
  "type": "manager_execution|single_agent_execution|directive_execution|multi_agent_execution",
  "task": "Original task text",
  "agents_involved": ["agent1", "agent2"],
  "parent_id": "parent_execution_id",  // Optional: ID of parent execution for continuations
  "result": {
    "status": "success|error",
    "response": "Response text for single agent/directive executions",
    "thought_process": "Reasoning process",
    "plan": {},  // For manager executions
    "results": [],  // For manager executions
    "summary": "",  // For manager executions 
    "outcome": "",  // For manager executions
    "agent_results": []  // For directive/multi-agent executions
  },
  "execution_time": 1.23,  // Execution time in seconds
  "directives": {}  // For directive executions
}
```

Execution history provides a complete, persistent record of all past executions. It is:
- Pure historical record with no direct influence on agent reasoning
- Comprehensive log of past executions with full details
- Persisted across application restarts (saved to disk)
- Queryable and filterable in the UI
- Supports continuation from any historical point
- Tracks relationships between continuations as a directed acyclic graph (DAG)

## 6. Continuation System

The continuation system enables multi-step reasoning chains and complex workflows.

### 6.1 Basic Continuation Workflow

The continuation workflow includes:

1. **Preparation**: 
   - User clicks "Prepare Continuation" 
   - Previous task and results are formatted into a continuation prompt
   - System stores parent execution ID for relationship tracking

2. **Editing**: 
   - User can modify the pre-filled continuation prompt
   - Add context, questions, or @agent directives
   - Refine or redirect the task

3. **Targeting**: 
   - User selects which agent(s) should handle the continuation
   - Options include manager, specific agent, multiple agents, or directive syntax
   - System intelligently pre-selects based on previous execution

4. **Execution**: 
   - Continuation is executed through appropriate pathway
   - Parent-child relationship is recorded
   - Result is linked to the original execution in history

### 6.2 DAG Structure for Continuations

The system supports a Directed Acyclic Graph (DAG) structure for continuations:

1. **Multiple Parents**: A continuation can reference a specific parent execution
2. **Multiple Children**: An execution can have multiple child continuations
3. **Branching Paths**: Create multiple different continuations from the same execution
4. **Chain Visualization**: View the full continuation chain for any entry
5. **Non-Linear Workflows**: Jump to any point in history and continue from there

### 6.3 Multi-Agent Selection

Continuations support targeting executions to:
1. **All Agents (Manager)**: Using manager coordination for the task
2. **Single Agent**: Targeting a specific agent for focused execution
3. **Multiple Agents**: Selecting a subset of agents to work on the task in parallel
4. **Directive Syntax**: Using @agent_name syntax for fine-grained control

This enables complex workflows like:
- Starting with manager coordination → Continuing with a specialist agent
- Starting with a specialist → Continuing with multiple agents
- Executing with multiple agents → Synthesizing with manager coordination

### 6.4 Continuations from History

Users can continue from any point in the execution history:
1. Browse execution history with filters for type, agent, and time
2. View detailed information about past executions
3. Click "Prepare Continuation from This" on any history entry
4. Edit the continuation prompt and select targeting options
5. Execute the continuation, creating a new child of the selected history entry

## 7. UI Components

### 7.1 Agent and Group Editors

Provides interfaces for:
- Setting agent/group name and description
- Selecting Ollama model for agents
- Defining system prompts
- Managing member agents for groups
- Selecting available tools

### 7.2 Task Execution UI

Provides tabbed interface for execution modes:
- "Execute with Manager" for coordinated execution
- "Execute with Specific Agent" for targeted execution
- "Execute with Multiple Agents" for parallel execution

Additional features:
- @agent_name directive detection and highlighting
- Full-width result display
- Continuation controls after execution
- Result persistence between edits
- Clear results button

### 7.3 Execution History View

Provides a dedicated tab for exploring execution history:
- Filtering by execution type (Manager, Single Agent, etc.)
- Filtering by agent involvement
- Sorting options (newest/oldest first)
- Expandable entries with complete execution details
- Parent/child relationship indicators
- "Prepare Continuation from This" button
- "View Continuation Chain" functionality

### 7.4 Continuation Interface

Provides controls for multi-step workflows:
- Previous task and result context
- Editable continuation prompt
- Targeting options (manager, specific agent, multi-agent)
- JSON response parsing for consistent formatting
- Parent/child relationship tracking
- Chain visualization capabilities

## 8. JSON Response Handling

The system includes intelligent parsing of JSON-formatted responses:

### 8.1 Detection and Parsing

```python
# Check if response is likely JSON
if isinstance(response, str) and response.strip().startswith("{") and response.strip().endswith("}"):
    try:
        # Try to parse JSON response
        import json
        parsed_json = json.loads(response)
        
        # Extract fields if they exist
        if isinstance(parsed_json, dict):
            if "response" in parsed_json:
                response = parsed_json.get("response", "")
            if "thought_process" in parsed_json:
                thought_process = parsed_json.get("thought_process", "")
    except:
        # If parsing fails, use the original response
        logger.warning(f"Failed to parse JSON response")
```

### 8.2 Implementation Locations

JSON response handling is implemented in:
1. `display_directive_results` function for displaying individual agent results
2. `execute_with_multiple_agents` function for generating combined responses
3. `display_agent_results` function for single agent executions

### 8.3 Benefits

1. **Improved Readability**: The actual content is displayed instead of raw JSON
2. **Better Information Organization**: Thought process is shown separately from the main response
3. **Consistent Experience**: Response formatting is consistent regardless of whether an agent returns plain text or JSON
4. **Error Resilience**: The system gracefully handles cases where JSON parsing might fail

## 9. Persistence

### 9.1 Storage Format

Agent and group configurations are stored as JSON files:

- Location: `app/data/agents/agent_groups.json`
- Format: Array of serialized AgentGroup objects
- Includes: All agent configurations, group settings, memory, and execution history

### 9.2 Persistence Methods

```python
def load_agents():
    """Load saved agent groups from disk"""
    # Implementation details...

def save_agents():
    """Save agent groups to disk"""
    # Implementation details...
```

### 9.3 History Persistence

The execution history is persisted through:
1. Recording history entries for all executions via `add_to_history`
2. Saving agent groups to disk after each execution
3. Loading agent groups with their history on application start
4. Tracking parent/child relationships for continuation chains

## 10. Best Practices

### 10.1 Agent Design Principles

1. **Specialization**: Design agents with focused capabilities
2. **Clear Instruction**: Write explicit, detailed system prompts
3. **Context Management**: Be mindful of context window limitations
4. **Tool Integration**: Extend capabilities through tools where appropriate
5. **Memory Usage**: Add only significant information to memory

### 10.2 Optimizing Workflows

1. **Start Broad, Then Narrow**: Begin with manager coordination for complex problems, then continue with specialists
2. **Use Directives for Efficiency**: Use @agent syntax for tasks that can be handled in parallel
3. **Build Iterative Chains**: Use continuations to refine and build upon initial results
4. **Leverage History**: Return to previous points in history to explore alternative approaches

### 10.3 System Prompt Engineering

1. **Role Definition**: Clearly define the agent's role and purpose
2. **Capability Description**: List what the agent can and cannot do
3. **Output Format**: Specify exact response structure requirements
4. **Examples**: Include examples of expected interactions
5. **Constraints**: Define operational boundaries and limitations

## Conclusion

This blueprint provides a comprehensive overview of the agent system architecture, components, and workflows. By understanding these elements, developers can effectively extend and customize the system for specific use cases, or create entirely new collaborative agent experiences.

The system now supports:
- Four distinct execution pathways (manager, single-agent, multi-agent, directive-based)
- Three memory systems (agent memory, shared memory, execution history)
- DAG-based continuation structures for complex reasoning chains
- Persistent execution history with parent/child relationships
- JSON response handling for consistent formatting
- Multi-agent selection capabilities for parallel execution

This robust architecture enables sophisticated multi-agent workflows that leverage multiple agents with different expertise, maintain context across complex reasoning chains, and facilitate non-linear exploration of problem spaces. 