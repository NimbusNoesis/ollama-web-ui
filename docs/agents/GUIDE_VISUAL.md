# Agent System Visual Guide

## Core Concepts Visualization

This guide uses visual representations to explain the key concepts in the enhanced Agent System.

## 1. Four Execution Pathways

```
┌───────────────────────────────────────────────────────────────┐
│                        TASK INPUT                              │
└───────────────┬─────────────────┬───────────────┬─────────────┘
                │                 │               │
                ▼                 ▼               ▼              ▼
┌──────────────────┐  ┌─────────────────┐  ┌────────────┐  ┌────────────────┐
│ MANAGER EXECUTION │  │ SINGLE AGENT    │  │ MULTI-AGENT│  │ DIRECTIVE-BASED│
│                   │  │                 │  │            │  │                │
│ ┌─Manager Agent─┐ │  │  ┌──Agent 1──┐  │  │┌─Agent 1─┐ │  │ @Agent1: task1 │
│ │ Create Plan   │ │  │  │Process Task│  │  │└─────────┘ │  │ @Agent2: task2 │
│ │ Assign Steps  │ │  │  └───────────┘  │  │┌─Agent 2─┐ │  │ @Agent3: task3 │
│ │ Synthesize    │ │  │                 │  │└─────────┘ │  │                │
│ └──────────────┘ │  │                 │  │┌─Agent 3─┐ │  │                │
│                   │  │                 │  │└─────────┘ │  │                │
└───────┬──────────┘  └────────┬────────┘  └─────┬──────┘  └────────┬───────┘
        │                      │                  │                  │
        └──────────────────────┴──────────────────┴──────────────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │   EXECUTION RESULT  │
                           └─────────────────────┘
```

## 2. DAG-Based Continuation Structure

```
                    ┌─────────────┐
                    │ Initial Task│
                    └──────┬──────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Execution Result        │
              └──┬─────────────┬────────┘
                 │             │
        ┌────────▼─────┐   ┌───▼────────────┐
        │ Continuation 1│   │ Continuation 2 │
        └────────┬──────┘   └───────┬────────┘
                 │                  │
       ┌─────────┴─────────┐    ┌───▼────────────┐
       │                   │    │                │
┌──────▼─────┐      ┌──────▼───┐│ Continuation 4 │
│Continuation 3│      │Continuation 5││                │
└──────┬──────┘      └──────────┘└────────────────┘
       │
       │
┌──────▼─────┐
│Continuation 6│
└─────────────┘
```

## 3. Multi-Agent Selection

```
┌─────────────────────────────────────────────────────────────┐
│ MULTI-AGENT SELECTION                                       │
│                                                             │
│  Select agents to include:                                  │
│  ┌──────────────────────────────────────────────┐          │
│  │ ☑ ResearchAgent                              │          │
│  │ ☑ AnalysisAgent                              │          │
│  │ ☐ CodeAgent                                  │          │
│  │ ☑ StrategyAgent                              │          │
│  │ ☐ CreativeAgent                              │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  Task will be sent to: ResearchAgent, AnalysisAgent,       │
│                        StrategyAgent                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ PARALLEL EXECUTION                                          │
│ ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│ │ResearchAgent│    │AnalysisAgent│    │StrategyAgent│      │
│ │  Processing │    │  Processing │    │  Processing │      │
│ │    Task     │    │    Task     │    │    Task     │      │
│ └──────┬──────┘    └──────┬──────┘    └──────┬──────┘      │
│        │                  │                   │             │
└────────┼──────────────────┼───────────────────┼─────────────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Combined Response │
                  └───────────────────┘
```

## 4. Agent Directive Syntax

```
┌─────────────────────────────────────────────────────────────┐
│ TASK WITH DIRECTIVES                                        │
│                                                             │
│ I need help planning a new product:                         │
│                                                             │
│ @ResearchAgent: Research market trends for smart speakers.  │
│                                                             │
│ @AnalysisAgent: Analyze competition in this market segment. │
│                                                             │
│ @StrategyAgent: Recommend pricing strategy based on the     │
│                 above research.                             │
│                                                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ PARSER                                                      │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ directives = {                                         │  │
│ │   "ResearchAgent": "Research market trends for...",    │  │
│ │   "AnalysisAgent": "Analyze competition in...",        │  │
│ │   "StrategyAgent": "Recommend pricing strategy..."     │  │
│ │ }                                                      │  │
│ └───────────────────────────────────────────────────────┘  │
└──────┬──────────────┬─────────────────────┬────────────────┘
       │              │                     │
       ▼              ▼                     ▼
┌─────────────┐ ┌─────────────┐     ┌─────────────┐
│ResearchAgent│ │AnalysisAgent│     │StrategyAgent│
└──────┬──────┘ └──────┬──────┘     └──────┬──────┘
       │              │                    │
       └──────────────┼────────────────────┘
                      │
                      ▼
            ┌───────────────────┐
            │ Combined Response │
            └───────────────────┘
```

## 5. Memory Systems

```
┌─────────────────────────────────────────────────────────────┐
│  AGENT MEMORY SYSTEMS                                       │
│                                                             │
│  ┌───────────────────┐   ┌───────────────────┐              │
│  │  AGENT MEMORY     │   │  SHARED MEMORY    │              │
│  │  (Short-term)     │   │  (Collaborative)  │              │
│  │                   │   │                   │              │
│  │  • Recent context │   │  • Cross-agent    │              │
│  │  • Agent-specific │   │    insights       │              │
│  │  • Used in prompts│   │  • Shared context │              │
│  │  • Limited size   │   │  • Group-wide     │              │
│  │                   │   │                   │              │
│  └───────────────────┘   └───────────────────┘              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │             EXECUTION HISTORY                        │    │
│  │             (Persistent Record)                      │    │
│  │                                                      │    │
│  │  • Complete execution record                         │    │
│  │  • Persists across sessions                          │    │
│  │  • Parent/child relationships                        │    │
│  │  • Filterable and searchable                         │    │
│  │  • Continuation chains                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 6. Continuation Workflow

```
 ┌───────────────────┐
 │   INITIAL TASK    │
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────┐
 │  EXECUTION RESULT │
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────────────────────────────┐
 │ PREPARE CONTINUATION                       │
 │ ┌─────────────────────────────────────┐   │
 │ │ Previous task: Initial task         │   │
 │ │                                     │   │
 │ │ Result:                             │   │
 │ │ [Previous execution result]         │   │
 │ │                                     │   │
 │ │ Continue from here:                 │   │
 │ │ [Editable continuation prompt]      │   │
 │ └─────────────────────────────────────┘   │
 │                                           │
 │ Target: ┌───────────────────────┐         │
 │         │ Choose Agent/Manager  ▼│        │
 │         └───────────────────────┘         │
 │                                           │
 │ [EXECUTE CONTINUATION]                    │
 └───────────────────┬───────────────────────┘
                     │
                     ▼
           ┌───────────────────┐
           │ CONTINUATION      │
           │ EXECUTION RESULT  │
           └─────────┬─────────┘
                     │
                     ▼
           ┌───────────────────┐
           │ PREPARE NEXT      │
           │ CONTINUATION      │
           └───────────────────┘
```

## 7. Execution History View

```
┌─────────────────────────────────────────────────────────────┐
│ EXECUTION HISTORY                                           │
│                                                             │
│ Filter: [All Types ▼]  [All Agents ▼]  [Newest First ▼]    │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ ↪️ 2023-06-15 14:30 - Manager Execution               │  │
│ │   "Research quantum computing applications"           │  │
│ │   [View Details] [Prepare Continuation] [View Chain]  │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ ⤴️ 2023-06-15 14:15 - Single Agent: ResearchAgent     │  │
│ │   "Find latest developments in neural networks"       │  │
│ │   [View Details] [Prepare Continuation] [View Chain]  │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ 2023-06-15 14:00 - Multi-Agent Execution              │  │
│ │   "Compare approaches to sentiment analysis"          │  │
│ │   [View Details] [Prepare Continuation] [View Chain]  │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 8. Continuation Chain Visualization

```
┌─────────────────────────────────────────────────────────────┐
│ CONTINUATION CHAIN                                          │
│                                                             │
│ ┌─────────────────────────────────────────────┐            │
│ │ 2023-06-15 14:00 - Initial Task             │            │
│ │ "Research quantum computing basics"          │            │
│ └───────────────────┬─────────────────────────┘            │
│                     │                                       │
│                     ▼                                       │
│ ┌─────────────────────────────────────────────┐            │
│ │ 2023-06-15 14:15 - First Continuation       │            │
│ │ "Explain quantum entanglement in detail"     │            │
│ └───────────────────┬─────────────────────────┘            │
│                     │                                       │
│                     ├────────────────┐                      │
│                     │                │                      │
│                     ▼                ▼                      │
│ ┌───────────────────────┐  ┌────────────────────────┐      │
│ │ 2023-06-15 14:30      │  │ 2023-06-15 14:32       │      │
│ │ Second Continuation A │  │ Second Continuation B  │      │
│ │ "Quantum computing    │  │ "Applications in       │      │
│ │  algorithms"          │  │  cryptography"         │      │
│ └───────────┬───────────┘  └──────────┬─────────────┘      │
│             │                          │                    │
│             ▼                          │                    │
│ ┌───────────────────────┐             │                    │
│ │ 2023-06-15 14:45      │             │                    │
│ │ Third Continuation    │             │                    │
│ │ "Implementation       │             │                    │
│ │  challenges"          │             │                    │
│ └───────────────────────┘             │                    │
│                                       ▼                    │
│                         ┌────────────────────────┐         │
│                         │ 2023-06-15 14:40       │         │
│                         │ Continuation of B      │         │
│                         │ "Post-quantum          │         │
│                         │  cryptography"         │         │
│                         └────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 9. JSON Response Handling

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT RETURNS JSON RESPONSE                                 │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ {                                                      │  │
│ │   "thought_process": "First, I need to consider...",   │  │
│ │   "response": "The answer to your question is..."      │  │
│ │ }                                                      │  │
│ └────────────────────┬──────────────────────────────────┘  │
│                      │                                      │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ JSON PARSER                                                 │
│                                                             │
│ 1. Detect JSON structure                                    │
│ 2. Parse the JSON string                                    │
│ 3. Extract "thought_process" and "response" fields          │
│ 4. Format each field appropriately                          │
│                                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ UI DISPLAY                                                  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Response                                               │  │
│ │                                                        │  │
│ │ The answer to your question is...                      │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Thought Process                                        │  │
│ │                                                        │  │
│ │ First, I need to consider...                           │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Interactive Workflows

The Agent System's enhanced features enable sophisticated workflows:

### Research Workflow

```
 ┌───────────────────┐
 │ MANAGER EXECUTION │
 │ "Research quantum │
 │  computing"       │
 └─────────┬─────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ CONTINUATION WITH         │
 │ @ResearchAgent            │
 │ "Explore quantum          │
 │  entanglement in detail"  │
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │ CONTINUATION WITH         │
 │ MULTIPLE AGENTS           │
 │ "Compare with classical   │
 │  computing approaches"    │
 └─────────────┬─────────────┘
               │
               ▼
 ┌───────────────────────────┐
 │ FINAL CONTINUATION WITH   │
 │ MANAGER                   │
 │ "Synthesize findings into │
 │  comprehensive report"    │
 └───────────────────────────┘
```

## Technical Implementation Concepts

### Execution History Entry Structure

```
┌─────────────────────────────────────────────────────────────┐
│ HISTORY ENTRY STRUCTURE                                     │
│                                                             │
│  id: "unique-uuid-for-this-execution"                       │
│  ┌─────────────────────────┐                                │
│  │timestamp: "2023-06-15T14:30:00Z"                         │
│  ├─────────────────────────┤                                │
│  │type: "manager_execution | single_agent_execution |       │
│  │       directive_execution | multi_agent_execution"       │
│  ├─────────────────────────┤                                │
│  │task: "Original task text that was executed"              │
│  ├─────────────────────────┤                                │
│  │agents_involved: ["agent1", "agent2", ...]                │
│  ├─────────────────────────┤                                │
│  │parent_id: "optional-parent-execution-id"                 │
│  ├─────────────────────────┤                                │
│  │result: {                                                 │
│  │  status: "success | error"                               │
│  │  response: "Formatted response text"                     │
│  │  agent_results: [ detailed individual results ]          │
│  │  ...other execution-specific fields                      │
│  │}                                                         │
│  ├─────────────────────────┤                                │
│  │execution_time: 1.23 /* seconds */                        │
│  └─────────────────────────┘                                │
└─────────────────────────────────────────────────────────────┘
``` 