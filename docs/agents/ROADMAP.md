# Agent System UI/UX Improvements

## Overview

This document outlines a series of improvements to the Agent System UI/UX in the Ollama Web UI. These improvements aim to enhance usability, maintain context during interactions, improve history tracking, and provide better control over task execution and continuation.

## Prioritized Improvements

### 1. Task Execution UI Layout Redesign

**Current Issue:**
The Task Execution tab uses a two-column layout with "Execute with Manager" in the left column and "Select Agent" in the right column. When using the "Execute with Manager" option, results are constrained to a narrow column, limiting readability.

**Proposed Solution:**
Redesign the task execution layout to use a vertical flow instead of side-by-side columns:
- Place the task input field at the top
- Follow with action buttons in a single row
- Display results in a full-width container
- Move "Select Agent" to a more appropriate location that doesn't compete with results display

**Implementation Plan:**
1. Modify `render_task_executor` in ui_components.py to use a sequential layout
2. Replace the `col1, col2 = st.columns(2)` pattern with sequential UI elements
3. Use full page width for result display to maximize readability
4. Add separation between "Execute with Manager" workflow and "Execute with Selected Agent" workflow

**Code Changes:**
```python
# Current implementation (simplified):
col1, col2 = st.columns(2)
with col1:
    # Execute with Manager button and results
with col2:
    # Agent selection and Execute with Selected Agent button

# Proposed implementation:
# Task input (full width)
task = st.text_area("Enter task for the agent group", height=100)

# Execution options
st.subheader("Execution Options")
exec_tab1, exec_tab2 = st.tabs(["Execute with Manager", "Execute with Specific Agent"])

with exec_tab1:
    # Manager execution button and logic
    
with exec_tab2:
    # Agent selection dropdown and execution button

# Results section (full width)
if "execution_results" in st.session_state:
    st.subheader("Execution Results")
    # Display results using full width
```

**Benefits:**
- Better readability of execution results
- Clearer separation between execution methods
- More intuitive workflow from task input to execution to results
- Improved use of screen real estate

### 2. Preserve Execution Results Between Task Edits

**Current Issue:**
Changing the task input text clears previous execution results, forcing users to re-run tasks after making even minor edits to their prompts.

**Proposed Solution:**
- Store execution results in session state to persist across UI interactions
- Add a clear button to explicitly reset results when desired
- Preserve previous results until new execution or explicit clearing

**Implementation Plan:**
1. Add execution results to session state in both manager and single agent execution methods
2. Check for existing results in session state when rendering the task execution UI
3. Display stored results if available
4. Add a "Clear Results" button for explicitly clearing previous execution

**Code Changes:**
```python
# In the execution handler:
def handle_execution_with_manager(group, task):
    result = group.execute_task_with_manager(task)
    # Store in session state
    st.session_state.execution_results = {
        "type": "manager",
        "task": task,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }
    return result

# In the UI rendering:
if st.button("Clear Results"):
    if "execution_results" in st.session_state:
        del st.session_state.execution_results

# Display results if available
if "execution_results" in st.session_state:
    display_execution_results(st.session_state.execution_results)
```

**Benefits:**
- Prevents frustrating loss of results during task refinement
- Allows users to reference previous results while crafting new prompts
- Provides explicit control over when to clear results

### 3. Agent Execution History Tracking

**Current Issue:**
There is no persistent history for agent executions unlike the chat feature. While agents have memory, it's not presented in a user-accessible history view.

**Proposed Solution:**
- Implement an execution history feature that preserves:
  - Task inputs
  - Execution plans (for manager executions)
  - Agent responses
  - Timestamps
- Create a new "History" tab in the agent group view
- Allow filtering, searching, and reusing past executions

**Implementation Plan:**
1. Create a new data structure for execution history in `AgentGroup` class
2. Add methods to add to history in both execution pathways
3. Create a new `render_execution_history` function in ui_components.py
4. Add a "History" tab to the group view alongside "Group Details" and "Task Execution"
5. Implement filtering and search capabilities for history

**Code Changes:**
```python
# Add to AgentGroup class:
class AgentGroup:
    def __init__(self, name, description):
        # Existing initialization
        self.execution_history = []
        
    def add_to_history(self, entry):
        self.execution_history.append({
            **entry,
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())
        })
        
    # Then in the execution methods, add to history
    def execute_task_with_manager(self, task):
        result = # existing execution logic
        self.add_to_history({
            "type": "manager_execution",
            "task": task,
            "result": result
        })
        return result
```

**Benefits:**
- Provides reference for past executions
- Enables learning from previous interactions
- Allows reusing successful prompts
- Creates continuity between sessions

### 4. Task Continuation Capability

**Current Issue:**
Each task execution is isolated with no way to continue or build upon previous tasks, requiring users to manually copy-paste previous context.

**Proposed Solution:**
- Add a "Continue Task" button to execution results
- When clicked, populate the task input with the previous task and results as context
- Append a "Continue from here:" prompt to make it clear the user is extending
- Provide an option to include or exclude previous execution history

**Implementation Plan:**
1. Store the full execution context (task, results) in session state
2. Add a "Continue Task" button to the results display
3. Create a function to format continuation prompts appropriately
4. Update the UI to show visual indication when in "continuation mode"

**Code Changes:**
```python
# In results display:
if st.button("Continue Task"):
    # Format previous task and results
    continuation_prompt = f"""Previous task: {previous_task}
    
Result:
{formatted_result}

Continue from here:
"""
    # Set in session state
    st.session_state.current_task = continuation_prompt
    st.session_state.in_continuation_mode = True
    
# In task input:
task = st.text_area(
    "Enter task for the agent group",
    value=st.session_state.get("current_task", ""),
    height=150
)

# Visual indicator for continuation mode
if st.session_state.get("in_continuation_mode", False):
    st.info("✨ You are continuing from a previous task")
```

**Benefits:**
- Enables multi-step workflows
- Reduces manual copying of context
- Makes complex interactions more manageable
- Provides clear visual feedback about continuation status

### 5. Explicit Agent Targeting for Continuations

**Current Issue:**
There's no way to specify which agents should handle specific parts of a continuation, limiting the flexibility of multi-agent workflows.

**Proposed Solution:**
- Add agent targeting controls for continuations:
  - Checkboxes to select specific agents for the continuation
  - A "direct to" dropdown for single-agent targeting
  - Options for "continue with same agent" or "continue with manager"
- Allow explicit addressing via @agent_name syntax in the prompt

**Implementation Plan:**
1. Add agent selection UI elements to the continuation interface
2. Create a parser for @agent_name syntax in prompts
3. Modify the execution flow to respect agent targeting preferences
4. Update both the manager prompt and direct execution logic to handle targeted continuations

**Code Changes:**
```python
# Function to parse agent directives in prompts
def parse_agent_directives(task, available_agents):
    # Check for @agent_name pattern
    directives = re.findall(r'@(\w+):', task)
    targets = {}
    
    for agent_name in directives:
        if agent_name in [a.name for a in available_agents]:
            # Extract the part after @agent_name: until next directive or end
            pattern = f'@{agent_name}:(.*?)(?=@\w+:|$)'
            matches = re.findall(pattern, task, re.DOTALL)
            if matches:
                targets[agent_name] = matches[0].strip()
                
    return targets

# In continuation UI:
if st.session_state.get("in_continuation_mode", False):
    st.subheader("Target specific agents")
    target_options = ["All agents (manager coordinated)", "Same as previous execution"]
    target_options.extend([a.name for a in group.agents])
    
    targeting_method = st.radio(
        "Direct this continuation to:",
        target_options
    )
```

**Benefits:**
- Precise control over which agents handle specific tasks
- More natural multi-agent conversation flow
- Ability to leverage specific agent strengths
- Reduces management overhead for focused tasks

### 6. Additional Enhancement Opportunities

#### 6.1. Agent Templates Library
- Create a template library with pre-configured agent roles
- Allow saving current agents as templates
- Implement template import/export

#### 6.2. Visual Agent Relationship Map
- Create a visual graph showing agent relationships within a group
- Show communication patterns from past executions
- Visualize which agents are used most frequently

#### 6.3. Execution Metrics and Analytics
- Track and display metrics like:
  - Response times per agent
  - Tool usage frequency
  - Success/failure rates
  - Token consumption

### 7. Improve Inter-Agent Awareness

**Current Issue:**
When tasks are assigned to individual agents in a group, the agents may not have awareness of other agents' capabilities or outputs until their results are recombined for the final output. This leads to isolated reasoning without the benefit of team awareness.

**Proposed Solution:**
- Enhance the prompt context for agents with information about other group members
- Include summaries of other agents' specialties in each agent's context
- For continuations, provide relevant information about previous agent contributions
- Consider adding an optional "team thinking" phase before individual execution

**Implementation Plan:**
1. Modify the agent execution pathway to include group context
2. Create a method to generate concise agent capability summaries
3. Add a toggle for "team-aware mode" vs. "isolated mode"
4. Update manager prompt to explicitly instruct about information sharing

**Code Changes:**
```python
# In AgentGroup class:
def generate_team_awareness_context(self, for_agent=None):
    """Generate context about other agents in the group"""
    context = "Other agents in your team:\n"
    
    for agent in self.agents:
        # Skip the current agent when generating team context
        if for_agent and agent.id == for_agent.id:
            continue
            
        # Generate a summary of this agent's capabilities
        context += f"- {agent.name}: {self._summarize_agent_capabilities(agent)}\n"
        
    return context

# When executing a task with an individual agent:
def execute_agent_with_team_awareness(self, agent, task, team_aware=True):
    # Start with the agent's system prompt
    system_content = agent.system_prompt
    
    # Add team awareness if enabled
    if team_aware:
        team_context = self.generate_team_awareness_context(for_agent=agent)
        system_content += f"\n\n{team_context}"
```

**Benefits:**
- Enables more collaborative problem-solving
- Reduces redundant work across agents
- Creates more coherent multi-agent responses
- Better emulates human team dynamics

## 1. Agent Group Management

## 2. Agent Targeting Feature

This feature allows users to direct tasks to specific agents instead of routing everything through the manager.

- **Completion status**: ✅ COMPLETED
- **Complexity**: Medium
- **Primary benefits**: Flexibility, directness, reduced overhead for simple tasks
- **Implementation details**:
  - Added a tab interface to choose between manager and direct targeting
  - Added agent selection dropdown in the direct targeting tab
  - Added support for @agent_name: syntax in task prompts
  - Implemented parser for @agent_name directives

### How It Works

The agent targeting feature works in two ways:

1. **UI-based targeting**:
   - Users select "Execute with Specific Agent" tab
   - Choose an agent from the dropdown menu
   - The task goes directly to that agent, bypassing the manager

2. **Syntax-based targeting**:
   - Users include @agent_name: directives in their prompt
   - Example: "@ResearchAgent: Find information about quantum computing"
   - The system parses these directives and routes subtasks to appropriate agents

### Continuation Workflow Integration

The targeting feature has been integrated with the continuation workflow to support complex reasoning chains:

1. Users can start with manager-directed tasks and then continue with specialists
2. Users can start with specialist tasks and then continue with others
3. The system intelligently pre-selects the agent used in the previous execution
4. Users can override the target selection at any continuation step
5. The continuation prompt is editable before execution
6. Multiple sequential continuations can be performed without losing context

This integration supports DAG-like workflows, where you might:
- Start with the manager coordinating multiple agents
- Continue with a specific agent for deeper analysis
- Branch back to the manager for synthesis
- Split into multiple specialist continuations 

The memory system retains context through these transitions, allowing for complex multi-stage workflows.

## 3. Agent Execution History Tracking

This feature will provide a persistent record of all tasks executed by agent groups.

- **Completion status**: 🔄 PLANNED
- **Complexity**: High
- **Primary benefits**: Traceability, learning, continuity across sessions
- **Implementation details**:
  - Store execution history in the `AgentGroup` object
  - Add persistence mechanism to save history to disk
  - Create UI component for viewing execution history
  - Integrate with continuation feature

### Distinction from Agent Memory

It's important to clarify the distinction between two related concepts:

1. **Agent Memory**:
   - Short-term context for agent reasoning
   - Helps individual agents maintain coherence within a conversation
   - Limited to recent interactions (typically last 5-10 exchanges)
   - Used internally by the agent to inform its thinking
   - Primarily serves the agent's reasoning process

2. **Execution History**:
   - Long-term record of all tasks and their outcomes
   - Persists across sessions (saved to disk)
   - Comprehensive record of all interactions
   - User-accessible for reference and continuation
   - Primarily serves the user's need for traceability and continuity

The current implementation has robust agent memory functionality, but the execution history feature will extend this with persistent, user-facing history tracking.

### Data Structure Design

Each history entry will include:

```json
{
  "id": "unique_id",
  "timestamp": "ISO-format timestamp",
  "task": "The original task prompt",
  "execution_type": "manager|single_agent|directive",
  "agents_involved": ["agent1", "agent2"],
  "result": {
    "status": "success|error|partial",
    "response": "The main response text",
    "details": {}  // Execution-specific details
  },
  "metadata": {
    "continuation_of": "parent_execution_id",  // If this was a continuation
    "session_id": "session_identifier"
  }
}
```

This structure will allow for rich querying and filtering of history entries.

## 6. Continuation Features

- **Completion status**: ✅ COMPLETED
- **Complexity**: Medium-High
- **Primary benefits**: Enable multi-step reasoning, maintain context across executions
- **Implementation details**:
  - Add "Prepare Continuation" button after execution results
  - Format previous task and results for continuation
  - Add UI for editing continuation prompt before execution
  - Implement agent targeting options for continuations
  - Support for multi-step continuation chains

### Continuation Workflow

The continuation workflow now includes:

1. **Preparation**: Format previous context into a continuation prompt
2. **Editing**: User can modify the continuation prompt to add context, questions, directives
3. **Targeting**: User can select which agent(s) should handle the continuation
4. **Execution**: The continuation is processed through the normal execution pathways

This workflow supports:
- Branching (starting with manager, continuing with specialists)
- Converging (starting with specialists, continuing with manager)
- Chaining (multiple sequential continuations)
- Parallel tracks (using @agent_name directives)

### Memory Preservation

The continuation feature preserves context through:
1. Formatting previous task and results in the prompt
2. Retaining agent memory across tasks
3. Maintaining shared memory context in the agent group

This ensures coherence across multiple steps in a complex reasoning process.

### Future Enhancements

Potential future improvements to the continuation feature:
- Visual mapping of continuation chains
- Ability to fork continuations from any previous result
- Ability to merge multiple continuation branches
- Integration with the planned execution history feature

## Implementation Roadmap

### Phase 1: Core UI Improvements
- Task Execution UI Layout Redesign
- Preserve Execution Results Between Task Edits

### Phase 2: Continuity Features
- Task Continuation Capability
- Agent Execution History Tracking

### Phase 3: Advanced Coordination
- Explicit Agent Targeting for Continuations
- Improve Inter-Agent Awareness

### Phase 4: Enhanced Capabilities
- Agent Templates Library
- Visual Agent Relationship Map
- Execution Metrics and Analytics

## Testing Plan

Each improvement should be tested for:
- Usability with different screen sizes
- Performance with large task inputs
- Compatibility with existing agent configurations
- State preservation across page navigation
- Error handling with invalid inputs

## Conclusion

These improvements will significantly enhance the usability and capability of the agent system, creating a more intuitive, powerful, and flexible user experience. By implementing them in phases, we can deliver incremental value while building toward a comprehensive multi-agent workflow system. 