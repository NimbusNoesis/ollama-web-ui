# Memory and History Systems in the Agent Framework

## Overview

The Ollama Web UI Agent Framework implements three distinct but complementary mechanisms for preserving information across agent interactions. This document clarifies the purpose, implementation, and behavior of each system.

## Three Types of Persistence

### 1. Agent Memory (Short-term Context)

**Purpose**: Provides immediate reasoning context for individual agents during task execution.

**Implementation**:
- Stored in the `Agent` class as `self.memory` (array of entries)
- Each entry contains `content`, `source`, and `timestamp`
- Added via `agent.add_to_memory(content, source)`

**Characteristics**:
- Actively used in prompts to inform agent responses
- Limited retention (recent items prioritized)
- Primarily focused on a single reasoning thread
- Persists across sessions but focuses on immediate context

**Example Usage**:
```python
agent.add_to_memory("The user's question was about quantum computing", "observation")
```

**Access Pattern**:
- Directly incorporated into agent prompts
- Usually the most recent 5-10 entries are used
- Displayed in the UI under "Agent Memory" expander

### 2. Shared Group Memory (Collaborative Context)

**Purpose**: Facilitates information sharing between agents in a group for collaborative task solving.

**Implementation**:
- Stored in the `AgentGroup` class as `self.shared_memory` (array of entries)
- Each entry contains `content`, `source`, and `timestamp`
- Added via `group.add_shared_memory(content, source)`

**Characteristics**:
- Available to all agents in the group
- Persists across multiple task executions
- Captures cross-agent insights and information
- Grows over time with group interactions
- Functions as a "working memory" for the group

**Example Usage**:
```python
group.add_shared_memory("Agent A found that the answer is 42", "collaboration")
```

**Access Pattern**:
- Incorporated into prompts for context
- Available to the manager for coordination
- Visible in the UI under "Shared Memory" expander

### 3. Execution History (Historical Record)

**Purpose**: Provides a complete, persistent record of all past executions without directly influencing agent reasoning.

**Implementation**:
- Stored in the `AgentGroup` class as `self.execution_history` (array of entries)
- Each entry contains execution details including task, results, and metadata
- Added via `group.add_to_history(entry)`
- Serialized and saved to disk with the agent group
- Supports parent/child relationships for tracking continuation chains

**Characteristics**:
- Pure historical record with no direct influence on agent reasoning
- Comprehensive log of past executions with full details
- Persists across application restarts (saved to disk)
- Queryable and filterable in the UI
- Supports continuation from any historical point
- Tracks relationships between continuations as a directed acyclic graph (DAG)

**Example Usage**:
```python
history_entry = {
    "type": "manager_execution",
    "task": "Analyze this data",
    "agents_involved": ["ResearchAgent", "AnalysisAgent"],
    "result": {...}
}
if parent_execution:
    history_entry["parent_id"] = parent_execution["id"]
group.add_to_history(history_entry)
```

**Access Pattern**:
- Viewed in the dedicated "Execution History" tab
- Filterable by execution type, agent, and chronological order
- Can view continuation chains from any entry
- Supports continuation from any historical point
- Persisted to disk automatically with agent groups

## Key Distinctions

### Memory vs. History

1. **Purpose**:
   - **Memory**: Active context for reasoning and decision-making
   - **History**: Passive record of past activities for reference

2. **Influence**:
   - **Memory**: Directly shapes agent responses through prompt context
   - **History**: No direct influence unless explicitly referenced

3. **Scope**:
   - **Memory**: Selective, focused on relevant context
   - **History**: Comprehensive, captures all execution details

4. **Usage**:
   - **Memory**: Automatic inclusion in reasoning processes
   - **History**: Manual consultation and continuation

### Individual vs. Shared Memory

1. **Access**:
   - **Individual**: Limited to a specific agent
   - **Shared**: Available to all agents in a group

2. **Focus**:
   - **Individual**: Agent-specific reasoning thread
   - **Shared**: Cross-agent findings and insights

3. **Context**:
   - **Individual**: Specialized to agent's role and function
   - **Shared**: Collaborative problem-solving context

## Implementation Details

### Memory Entry Structure

```json
{
  "content": "The observation or information",
  "source": "observation|execution|user|...",
  "timestamp": "ISO-format timestamp"
}
```

### History Entry Structure

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
    "agent_results": []  // For directive executions
  },
  "execution_time": 1.23,  // Execution time in seconds
  "directives": {}  // For directive executions
}
```

## UI Representation

### Memory Display

Memory is displayed in context during task execution:
- Individual agent memory appears in the "Agent Memory" expander
- Shared memory appears in the "Shared Memory" expander in the Group Details tab

### History Display

History has its own dedicated tab with powerful functionality:
- Displayed in the "Execution History" tab
- Provides filtering by execution type (Manager, Single Agent, etc.)
- Allows filtering by specific agent involvement
- Offers sorting options (newest/oldest first)
- Shows expandable entries with complete execution details
- Visualizes parent/child relationships with indicators
- Displays continuation chains graphically
- Offers "Prepare Continuation from This" button for any entry

## Continuation System

### Basic Continuation

When a user continues from a result:
1. The context is formatted into a continuation prompt
2. This prompt is presented in an editable text area
3. The user can modify the prompt before execution
4. The user selects targeting options (which agent(s) to use)
5. The continuation is executed as a new task
6. This new task is recorded in history with a parent/child relationship

### DAG Structure for Continuations

The system supports a Directed Acyclic Graph (DAG) structure for continuations:

1. **Multiple Parents**: A continuation can reference a specific parent execution
2. **Multiple Children**: An execution can have multiple child continuations
3. **Branching Paths**: Users can create multiple different continuations from the same execution
4. **Chain Visualization**: The UI can display the full continuation chain for any entry
5. **Non-Linear Workflows**: Users can jump to any point in history and continue from there

### Multi-Agent Selection

The system supports targeting executions to:
1. **All Agents (Manager)**: Using manager coordination for the task
2. **Single Agent**: Targeting a specific agent for focused execution
3. **Multiple Agents**: Selecting a subset of agents to work on the task in parallel
4. **Directive Syntax**: Using @agent_name syntax for fine-grained control

This enables complex workflows like:
- Starting with manager coordination → Continuing with a specialist agent
- Starting with a specialist → Continuing with multiple agents
- Executing with multiple agents → Synthesizing with manager coordination

### Persistence Mechanism

Execution history is persisted through:
1. Recording history entries for all executions
2. Saving agent groups to disk after each execution
3. Loading agent groups with their history on application start
4. Tracking parent/child relationships for continuation chains

## Summary

These three systems work together to provide a comprehensive information management framework:

1. **Agent Memory**: Immediate reasoning context for individual agents
2. **Shared Memory**: Collaborative context shared across a group of agents
3. **Execution History**: Complete record of all past executions with continuation tracking

The execution history system enables powerful workflows with:
- Persistent records across application restarts
- Comprehensive execution details
- DAG structure for continuation chains
- Multi-agent targeting capabilities
- Visualization of execution relationships 