# Ollama Web UI Agent System

## Overview

The Ollama Web UI Agent System is a powerful framework for creating, managing, and orchestrating multiple AI agents. It enables complex workflows through collaborative problem-solving, specialized agent roles, and sophisticated task execution patterns.

## Key Features

### Agent Management

- **Create Custom Agents**: Define specialized agents with unique roles, descriptions, and models
- **Agent Groups**: Organize agents into collaborative teams with shared capabilities
- **Role Specialization**: Assign specific domains of expertise to individual agents
- **Custom Instructions**: Provide tailored instructions to guide agent behavior

### Task Execution

- **Multiple Execution Paths**:
  - Manager-coordinated execution (all agents)
  - Single agent focused execution
  - Directive-based parallel execution (@agent syntax)
  - Multi-agent subset execution (selected agents)
  
- **Continuation System**:
  - Continue from any execution result
  - Editable continuation prompts
  - Target specific agents or groups
  - Build complex reasoning chains
  - DAG-like workflow structures
  
- **Agent Memory**:
  - Individual agent memory
  - Shared group memory
  - Execution history tracking
  - Persistence across sessions

### Collaborative Workflows

- **Manager Coordination**: Use manager agents to break down complex tasks
- **Parallel Processing**: Execute tasks with multiple agents simultaneously
- **Sequential Chains**: Create step-by-step reasoning chains through continuations
- **Branching Paths**: Create multiple different continuations from any result

## Usage Guide

### Creating Agents

1. Navigate to the Agents tab in Ollama Web UI
2. Click "Create New Agent"
3. Provide a name, description, and model
4. Configure the agent's system prompt and settings
5. Add the agent to an existing group or create a new group

### Basic Task Execution

To execute a task with your agents:

1. Select an agent group
2. Enter a task in the text area
3. Choose an execution method:
   - "Execute with Manager" for coordinated multi-agent execution
   - "Execute with Specific Agent" for targeted execution
   - "Execute with Multiple Agents" for parallel execution with selected agents
4. Review the results displayed below the execution controls

### Using @agent Directives

You can target specific agents directly in your prompt using @agent_name syntax:

```
@ResearchAgent: Find information about quantum computing.
@CodeAgent: Write a Python function to calculate fibonacci numbers.
```

The system will automatically detect these directives and route tasks accordingly.

### Continuation Workflow

To continue from a previous result:

1. Click "Prepare Continuation" below any result
2. Edit the pre-filled continuation prompt
3. Select which agent(s) should handle the continuation
4. Click "Execute Continuation"
5. The result will be linked to the original execution in the history

### Working with History

The execution history provides a complete record of past interactions:

1. Navigate to the "Execution History" tab in the group view
2. Filter history by execution type or agent involvement
3. Expand any entry to view complete details
4. Click "Prepare Continuation from This" to continue from any historical point
5. Use "View Continuation Chain" to see related executions

## Memory Systems

The Agent System implements three distinct memory mechanisms:

### 1. Agent Memory (Short-term Context)

- Provides immediate reasoning context for individual agents
- Directly incorporated into agent prompts
- Displayed in the "Agent Memory" expander

### 2. Shared Group Memory (Collaborative Context)

- Facilitates information sharing between agents in a group
- Available to all agents in the group
- Visible in the "Shared Memory" expander

### 3. Execution History (Historical Record)

- Complete, persistent record of all past executions
- Supports continuation from any historical point
- Tracks parent/child relationships between continuations
- Available in the dedicated "Execution History" tab

## Advanced Features

### DAG-Based Continuation Chains

The system supports a Directed Acyclic Graph structure for continuations:

- Multiple parents: A continuation can reference a specific parent execution
- Multiple children: An execution can have multiple child continuations
- Branching paths: Create multiple different continuations from the same execution
- Chain visualization: View the full continuation chain for any entry

### Multi-Agent Selection

Target executions to specific combinations of agents:

- All agents (manager coordinated)
- Single specialist agent
- Custom subset of agents
- Directive-based targeting (@agent syntax)

### Persistence

All aspects of the agent system persist across application restarts:

- Agent definitions and groups
- Agent memory and shared memory
- Complete execution history with relationships
- Continuation chains and targeting preferences

## Best Practices

### Effective Agent Design

1. **Clear Role Definition**: Give each agent a specific, well-defined role
2. **Complementary Expertise**: Create agents with complementary knowledge domains
3. **Consistent Instructions**: Maintain consistent instruction patterns across agents
4. **Appropriate Models**: Match model capabilities to agent requirements

### Optimizing Workflows

1. **Start Broad, Then Narrow**: Begin with manager coordination, then continue with specialists
2. **Use Directives for Parallelism**: Use @agent syntax for tasks that can be handled in parallel
3. **Build Iterative Chains**: Use continuations to refine and build upon initial results
4. **Leverage History**: Return to previous points in history to explore alternative approaches

## Examples

### Research Workflow

```
[Execute with Manager]
Research the impact of quantum computing on cryptography and create a summary report.

[Continue with @ResearchAgent]
Based on the research, what are the most vulnerable encryption algorithms?

[Continue with @CodeAgent]
Write Python code demonstrating a post-quantum cryptography algorithm.

[Continue with Manager]
Synthesize a final report combining the research findings and code examples.
```

### Creative Writing Workflow

```
[Execute with @CreativeAgent]
Generate a story concept about a detective in a futuristic city.

[Continue with Multiple Agents: CreativeAgent, EditorAgent]
Expand this concept into a detailed outline with character descriptions.

[Continue with @CreativeAgent]
Write the first chapter based on this outline.

[Continue with @EditorAgent]
Review and improve the first chapter.
```

## Troubleshooting

### Common Issues

1. **Agent Not Following Instructions**: Review and refine the agent's system prompt
2. **Poor Collaboration**: Check the manager agent's instructions for coordination guidance
3. **Result Inconsistency**: Try changing the temperature setting for more consistent outputs
4. **Execution Failures**: Check model compatibility and token limits for complex tasks

### Performance Tips

1. **Limit History Size**: Filter history when dealing with large execution sets
2. **Use Appropriate Models**: Use lighter models for simple tasks, more powerful models for complex reasoning
3. **Clear Results**: Use the "Clear Results" button to improve UI performance with large outputs
4. **Optimize Prompts**: Keep directives clear and concise for more efficient processing

## Future Roadmap

Upcoming enhancements to the Agent System include:

1. **Enhanced Visualization**: Interactive graph visualization of continuation chains
2. **Agent Tools**: Integration with external tools and APIs
3. **Improved Search**: Full-text search across history entries
4. **Team Awareness**: Explicit agent awareness of team capabilities
5. **Workflow Templates**: Save and reuse common agent workflows
6. **Metrics and Analytics**: Track performance and usage patterns

---

For more detailed information, refer to the following documentation:
- [Memory and History Systems](memory_and_history_systems.md)
- [Continuation Feature](continuation_feature_refinements.md)
- [Implementation Progress](agent_system_implementation_progress.md) 