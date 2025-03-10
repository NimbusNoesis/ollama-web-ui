# Ollama UI

A user-friendly web interface for [Ollama](https://ollama.com/), built with Streamlit and Python.

## Features

- Chat with Ollama models
- Compare different models side by side
- Manage and pull models
- Tool calling support
- Customizable system prompts
- Temperature adjustment
- Easy-to-use interface
- Multi-agent system for complex tasks

## Tool Calling Support

This UI supports tool calling with Ollama models that implement the OpenAI function calling API. The implementation allows models to:

1. Analyze user queries
2. Determine when to use tools
3. Call appropriate tools with arguments
4. Process tool results
5. Provide a final response incorporating the tool output

### Using Tools

To use tools, you can:

1. **Enable Installed Tools**: Use existing tools in the `app/tools` directory
2. **Create Custom Tools**: Create custom tools in the Tools page

### Creating Your Own Tools

To create a new tool:

1. Create a Python file in the `app/tools` directory
2. Define a function with proper docstrings and type hints
3. The function will be automatically loaded and available for use

Example tool function:

```python
def calculator(expression: str) -> dict:
    """
    Perform mathematical calculations

    Args:
        expression: The mathematical expression to evaluate

    Returns:
        Result of the calculation
    """
    # Implementation here
    return {"result": result}
```

### How Tool Calling Works

1. The user sends a message
2. If tools are enabled, the message is sent to the model with available tools
3. If the model decides to use tools, it returns tool calls
4. The UI executes the tool and returns results to the model
5. The model provides a final response incorporating the tool results

### Try the Example

Check out `app/examples/tool_usage_example.py` for a complete working example of tool calling.

## Agent System

The Ollama UI includes a powerful multi-agent system that enables complex workflows through collaborative problem-solving, specialized agent roles, and sophisticated task execution patterns.

### Key Capabilities

- Create custom agents with specialized roles
- Organize agents into collaborative teams
- Execute tasks using manager coordination
- Target specific agents for focused tasks
- Build complex reasoning chains with continuations
- Track execution history across sessions
- Support for DAG-based workflows

### Documentation

For comprehensive documentation on the Agent System, see:
- [Agent System Overview](docs/agents/README.md) - Introduction and usage guide
- [Agent Documentation Index](docs/agents/INDEX.md) - Complete documentation directory

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Make sure [Ollama](https://ollama.com/) is running
4. Run the UI: `python -m app.main`

## Requirements

- Python 3.8+
- Ollama installed and running
- Python packages: streamlit, ollama, requests

## License

MIT License
