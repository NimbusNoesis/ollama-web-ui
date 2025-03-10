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