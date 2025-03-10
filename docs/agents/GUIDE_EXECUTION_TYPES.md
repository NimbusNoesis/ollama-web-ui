# Agent Execution Types: Quick Reference Guide

## Overview

The Ollama Web UI Agent System supports multiple execution types to provide flexibility for different tasks and workflows. This guide explains each execution type, its purpose, and when to use it.

## Execution Types Summary

| Type | Description | Best For | Accessed Via |
|------|-------------|----------|-------------|
| Manager Coordinated | Uses a manager agent to orchestrate multiple agents for complex tasks | Complex multi-step problems | "Execute with Manager" tab |
| Single Agent | Targets a specific agent for focused expertise | Specialized tasks | "Execute with Specific Agent" tab |
| Multiple Agents | Executes the same task with multiple selected agents in parallel | Gathering diverse perspectives | "Execute with Multiple Agents" tab |
| Directive-Based | Uses @agent_name syntax to assign specific subtasks to different agents | Parallel delegation | @agent syntax in prompt |

## 1. Manager Coordinated Execution

### What It Is
The manager agent breaks down complex tasks into subtasks, assigns them to appropriate agents, and synthesizes the results into a coherent output.

### How It Works
1. The manager agent creates a plan with specific steps
2. It assigns each step to an appropriate agent based on their expertise
3. Steps are executed in sequence
4. The manager synthesizes results into a final summary and outcome

### When To Use It
- For complex problems requiring multiple steps or types of expertise
- When you want a coordinated approach with a unified output
- For tasks requiring sequential reasoning or building upon previous steps

### Example
```
[Execute with Manager]
Research quantum computing advancements in 2023, analyze their potential impact on cryptography, and suggest preparations organizations should make.
```

## 2. Single Agent Execution

### What It Is
A direct interaction with a specific agent without manager coordination.

### How It Works
1. The task is sent directly to the selected agent
2. The agent processes the task using its specific expertise and system prompt
3. The agent returns its response with thought process

### When To Use It
- When you need a specialist's focused expertise
- For simpler tasks that don't require coordination
- To follow up on specific aspects from a previous execution
- When you want direct, unfiltered responses from a particular agent

### Example
```
[Execute with CodeAgent]
Write a Python function that implements the Sieve of Eratosthenes algorithm for finding prime numbers.
```

## 3. Multiple Agent Execution

### What It Is
The same task is executed by multiple selected agents in parallel, with all responses collected.

### How It Works
1. You select multiple agents from a multi-select dropdown
2. The same task is sent to each selected agent
3. Each agent processes the task independently
4. All responses are collected and displayed together

### When To Use It
- To gather diverse perspectives on the same question
- When comparing approaches from different specialists
- For brainstorming or idea generation
- When uncertain which agent might perform best for a task

### Example
```
[Execute with Multiple Agents: ResearchAgent, AnalysisAgent, StrategistAgent]
What are the potential business applications of large language models in the healthcare industry?
```

## 4. Directive-Based Execution

### What It Is
A method to assign different subtasks to specific agents in a single prompt using @agent_name syntax.

### How It Works
1. You include directives in the format `@AgentName: specific task` in your prompt
2. The system automatically detects these directives
3. Each agent receives only their designated portion of the task
4. Results from all agents are collected and displayed together

### When To Use It
- When you want different agents to work on different aspects of a problem simultaneously
- For efficient parallel delegation without manager overhead
- When you have clear subtasks that align with agent specialties

### Example
```
I need help planning a web application:

@DesignerAgent: Create a wireframe concept for a dashboard layout with key metrics and user activity.

@DatabaseAgent: Design a database schema for a user management system with roles and permissions.

@SecurityAgent: Provide best practices for implementing authentication and data protection.
```

## 5. Continuation-Based Execution

### What It Is
Building upon results from a previous execution by continuing the chain of thought.

### How It Works
1. After viewing results from any execution type, click "Prepare Continuation"
2. Edit the auto-generated continuation prompt as needed
3. Select targeting options (manager, specific agent, multiple agents)
4. Execute the continuation
5. The result is linked to the original execution in history with a parent/child relationship

### When To Use It
- To follow up on previous results with additional questions
- To refine or expand upon initial outputs
- To create step-by-step reasoning chains
- To branch into different directions from a common starting point

### Example
Original task result → Prepare Continuation → Add follow-up:
```
Based on your analysis of quantum computing risks, please provide specific recommendations for updating our encryption standards in the next 12 months.
```

## Execution Type Comparison

### Manager vs. Single Agent

| Manager Coordinated | Single Agent |
|---------------------|--------------|
| Handles complex, multi-step tasks | Best for focused, single-domain tasks |
| Provides a synthesized, integrated response | Gives direct, specialist perspective |
| Longer execution time | Faster execution |
| Creates a structured plan and summary | More conversational response style |

### Multiple Agents vs. Directive-Based

| Multiple Agents | Directive-Based |
|-----------------|----------------|
| Same task to all selected agents | Different tasks to different agents |
| Compare different approaches | Parallel work on different aspects |
| Selected via UI controls | Specified in prompt with @agent syntax |
| Good for gathering diverse perspectives | Good for coordinated parallel delegation |

## Tips for Choosing the Right Execution Type

1. **Start Broad, Then Narrow**: Begin with manager coordination for complex problems, then use continuations with specific agents to drill down.

2. **Use Directives for Efficiency**: When you know exactly which agent should handle which part of a task, use directive syntax to save time.

3. **Combine with Continuations**: Any execution type can be continued, allowing you to build complex workflows:
   - Start with manager → Continue with specialist
   - Start with multiple agents → Continue with synthesis by manager
   - Start with directive-based → Continue with focused follow-up

4. **Consider Task Complexity**:
   - Simple, focused questions → Single agent
   - Complex, multi-part problems → Manager
   - Comparative analysis → Multiple agents
   - Parallel sub-tasks → Directives

## Recording and History

All execution types are recorded in the execution history with:
- Unique ID
- Timestamp
- Execution type
- Task content
- Result details
- Parent/child relationships for continuations

This allows you to track, review, and continue from any past execution regardless of type. 