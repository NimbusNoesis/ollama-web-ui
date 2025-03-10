# Agent Targeting Feature Implementation

## Overview

This document details the implementation of the Agent Targeting feature for the Ollama Web UI's multi-agent system. The feature allows users to direct tasks to specific agents within a group, either through UI controls or natural language syntax in the prompt.

## Feature Capabilities

### User Interface Controls

- **Agent Selection Dropdown**: Allows explicit selection of which agent should handle a continuation task
- **Default Target Selection**: Intelligently pre-selects the previously used agent when continuing a task
- **Continuation Mode Indicator**: Visual indicator and controls for continuation mode
- **Syntax Help**: Expandable help section explaining the @agent_name syntax
- **Continuation Workflow**: Two-step process with "Prepare Continuation" and "Execute Continuation" buttons
- **Strategic UI Placement**: Continuation controls positioned after results for natural workflow

### @agent_name Directive Syntax

- **Natural Language Targeting**: Users can write `@AgentName: specific task` to target agents
- **Multi-Agent Tasking**: Multiple directives can be included in a single prompt
- **Case-Insensitive Matching**: Agent names are matched case-insensitively for convenience
- **Error Handling**: Unknown agent names are logged and reported to the user

### Execution Pathways

- **Direct Agent Targeting**: Tasks can be sent directly to a specific agent
- **Directive-Based Execution**: Multiple agents can be assigned different subtasks
- **Manager Coordination**: Complex tasks can still use manager for orchestration
- **Hybrid Approaches**: Combining targeted execution with manager oversight

## Implementation Details

### Core Components

1. **Agent Directive Parser**:
   ```python
   def parse_agent_directives(task: str, available_agents: List[Agent]) -> Dict[str, str]:
       # Regex pattern that matches @name: followed by text until the next @name: or end of string
       pattern = r'@([^:]+):(.*?)(?=@[^:]+:|$)'
       matches = re.findall(pattern, task, re.DOTALL)
       
       # Process matches into a dictionary mapping agent names to their tasks
       for agent_name, subtask in matches:
           # Case-insensitive matching with validation
           if agent_name.lower() in [a.name.lower() for a in available_agents]:
               # Use the correctly cased agent name
               correct_name = next(a.name for a in available_agents if a.name.lower() == agent_name.lower())
               directives[correct_name] = subtask.strip()
   ```

2. **Directive Execution Handler**:
   ```python
   def execute_task_with_directives(group: AgentGroup, task: str, directives: Dict[str, str]) -> Dict:
       # Execute each agent's directive individually
       for agent_name, subtask in directives.items():
           agent = next((a for a in group.agents if a.name == agent_name), None)
           agent_result = agent.execute_task(subtask)
           
           # Add to group's shared memory for context
           group.add_shared_memory(
               f"Agent {agent_name} processed: {subtask}\nResult: {agent_result.get('response')}",
               source="agent_directive"
           )
   ```

3. **UI Integration**:
   ```python
   # Check for agent directives in the task text
   agent_directives = parse_agent_directives(task, group.agents)
   
   # If directives found, use directive execution
   if agent_directives and len(agent_directives) > 0:
       directive_result = execute_task_with_directives(group, task, agent_directives)
   
   # If targeting a specific agent, execute with that agent
   elif target_agent:
       result = target_agent.execute_task(task)
       
   # Otherwise use manager execution
   else:
       result = group.execute_task_with_manager(task)
   ```

### Continuation Workflow

The continuation workflow follows a two-step process:

1. **Preparation Phase**:
   ```python
   # Step 1: Prepare the continuation
   if st.button("Prepare Continuation"):
       # Format previous task and results for continuation
       formatted_result = get_formatted_result(results_data)
       continuation_prompt = f"""Previous task: {results_data['task']}
       
       Result:
       {formatted_result}
       
       Continue from here:
       """
       # Set in session state
       st.session_state.current_task = continuation_prompt
       st.session_state.in_continuation_mode = True
   ```

2. **Configuration Phase**:
   - User reviews and edits the continuation prompt in a dedicated text area
   - User can add additional context, questions, or @agent_name directives
   - User selects targeting options for execution
   - System continuously updates session state with edited prompt
   ```python
   # Editable prompt area
   edited_prompt = st.text_area(
       "Edit Continuation Prompt",
       value=st.session_state.current_task,
       height=200,
       help="Edit this prompt to add additional context, questions, or @agent_name directives"
   )
   
   # Update the session state with edited prompt
   st.session_state.current_task = edited_prompt
   ```

3. **Execution Phase**:
   ```python
   # Step 3: Execute the prepared continuation
   if st.button("Execute Continuation", type="primary"):
       # Get the current task and targeting preference
       continuation_task = st.session_state.current_task
       target_name = st.session_state.get("target_agent", "")
       
       # Execute via appropriate pathway based on directives/targeting
       if agent_directives:
           execute_with_directives(...)
       elif target_agent:
           execute_with_specific_agent(...)
       else:
           execute_with_manager(...)
   ```

### Result Display

Different execution paths produce different result formats, requiring specialized display logic:

```python
if results_data["type"] == "directive":
    # Display directive summary
    for agent_name, subtask in directives.items():
        st.markdown(f"- **@{agent_name}**: {subtask}")
    
    # Display results in a combined view
    st.markdown(process_markdown(result["response"]))
```

## Technical Challenges

### 1. Regex Pattern Complexity

The regex pattern for extracting directives needed to handle:
- Variable whitespace around directives
- Multiple directives in a single prompt
- Directives that contain newlines and special characters
- Ensuring each directive extends until the next directive or end of text

### 2. Result Format Consistency

Each execution pathway (manager, single agent, directive) produces a different result structure:
- Manager results include plan, steps, and summary
- Single agent results include thought process and response
- Directive results include combined output from multiple agents

### 3. UI State Management

Continuation mode required tracking several state variables:
- The current task content
- Whether we're in continuation mode
- Which agent was previously used
- Which agent is targeted for continuation

### 4. Error Handling

Directive execution needed to gracefully handle:
- Unknown agent names
- Failed execution of individual directives
- Combining successful results with error information

### 5. UI Flow and Positioning

The positioning of UI elements was critical for usability:
- Continuation controls appear after results for natural reading flow
- Two-step continuation process (prepare, then execute) provides clarity
- Visual indicators ensure users understand the current state

## User Experience Considerations

### Discoverability

- Help text explains the @agent_name syntax
- UI controls make targeting options visible
- Default selections reduce friction for common cases
- Logical positioning of controls follows information flow

### Flexibility

- Users can choose between UI controls or natural syntax
- Both simple (single agent) and complex (multi-agent) workflows are supported
- Continuations remember context and targeting preferences
- Two-step process allows users to review and refine before execution

### Feedback

- Visual indicators show continuation mode status
- The targeted agent is clearly displayed
- Directive results are formatted to show which agent handled each part
- Execution status updates provide clear progress visibility

## Future Enhancements

1. **Visual Directive Builder**: Create a UI for constructing complex multi-agent tasks
2. **Hybrid Execution**: Allow combining directive execution with manager oversight
3. **Directive Templates**: Save and reuse common directive patterns
4. **Agent Capability Hints**: Show agent capabilities when targeting to guide appropriate assignment
5. **Continuation History**: Track and navigate through a history of continuations

## Conclusion

The agent targeting feature significantly enhances the flexibility and power of the multi-agent system by allowing precise control over which agents handle specific tasks. By supporting both UI-based selection and natural @agent_name syntax, the system accommodates different user preferences and workflow complexities.

The improved continuation workflow, with its two-step process and strategic UI positioning, creates a more intuitive experience that follows the natural flow of conversation: see results, decide to continue, prepare continuation, select targeting, and execute. 