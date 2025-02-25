import streamlit as st
import time
import json
from typing import Dict, List, Any, Optional, cast, Union
from app.api.ollama_api import OllamaAPI
from app.components.chat_ui import ChatUI
from app.utils.chat_manager import ChatManager
from app.utils.tool_loader import ToolLoader
from app.utils.logger import get_logger, exception_handler, ErrorHandler

# Get application logger
logger = get_logger()


class ChatPage:
    """Page for chatting with LLM models"""

    def __init__(self):
        """Initialize the chat page"""
        # Initialize chat manager
        self.chat_manager = ChatManager()

        # Initialize session state for models if needed
        if "available_models" not in st.session_state:
            st.session_state.available_models = []

        if "selected_model" not in st.session_state:
            st.session_state.selected_model = None

        if "chat_temperature" not in st.session_state:
            st.session_state.chat_temperature = 0.7

        if "system_prompt" not in st.session_state:
            st.session_state.system_prompt = ""

        if "use_tools" not in st.session_state:
            st.session_state.use_tools = False

        if "tools" not in st.session_state:
            st.session_state.tools = []

        if "tool_choice" not in st.session_state:
            st.session_state.tool_choice = "auto"

        if "use_installed_tools" not in st.session_state:
            st.session_state.use_installed_tools = False

        if "installed_tools" not in st.session_state:
            st.session_state.installed_tools = []

        # Initialize the chat UI
        self.chat_ui = ChatUI(on_message=self.process_message)

        # Load installed tools
        self.load_installed_tools()

    def load_installed_tools(self):
        """Load installed tools from the tools directory"""
        try:
            installed_tools = ToolLoader.load_all_tools()
            st.session_state.installed_tools = installed_tools
            logger.info(f"Loaded {len(installed_tools)} tools from tools directory")
        except Exception as e:
            logger.error(f"Error loading installed tools: {str(e)}", exc_info=True)
            st.session_state.installed_tools = []

    def process_message(self, message: str):
        """
        Process a new user message

        Args:
            message: The user message to process
        """
        if not message.strip():
            return

        # Get the current selected model
        model = st.session_state.get("selected_model")
        if not model:
            st.error("Please select a model first")
            return

        # Add user message to chat
        self.chat_manager.add_message("user", message)

        # Show thinking indicator
        self.chat_ui.add_thinking_indicator()

        # Don't call st.rerun() here as it's within a callback
        # Instead, we'll let the next normal render cycle handle showing the thinking state

    def handle_model_response(self):
        """Process the model's response"""
        if "thinking" not in st.session_state or not st.session_state.thinking:
            return

        try:
            # Get required data
            model = st.session_state.selected_model
            system_prompt = st.session_state.system_prompt
            temperature = st.session_state.chat_temperature
            messages = self.chat_manager.get_messages_for_api()

            # Get tools if needed
            tools = None
            tool_choice = None
            available_functions = {}

            if st.session_state.use_tools and st.session_state.tools:
                # User-created tools from the session
                tools = [tool["definition"] for tool in st.session_state.tools]
                tool_choice = st.session_state.tool_choice
            elif (
                st.session_state.use_installed_tools
                and st.session_state.installed_tools
            ):
                # Tools installed in the tools directory - use function references directly
                try:
                    function_tools = ToolLoader.load_all_tools()
                    available_functions = ToolLoader.load_all_tool_functions()
                    # Make sure we have the right type
                    if isinstance(function_tools, list):
                        tools = function_tools
                        tool_choice = st.session_state.tool_choice
                        logger.info(
                            f"Loaded {len(tools)} tool functions and {len(available_functions)} available functions"
                        )
                    else:
                        logger.warning(
                            "Loaded tools were not a list, falling back to installed tools"
                        )
                        tools = st.session_state.installed_tools
                except Exception as e:
                    logger.error(f"Error loading tool functions: {str(e)}")
                    tools = (
                        st.session_state.installed_tools
                    )  # Fall back to the old approach

            try:
                # Get model response - try with tools first
                if tools:
                    try:
                        # Ensure tools is definitely the correct type
                        valid_tools = []
                        for tool in tools:
                            if callable(tool) or (
                                isinstance(tool, dict) and "function" in tool
                            ):
                                valid_tools.append(tool)

                        response = OllamaAPI.chat_completion(
                            model=model,
                            messages=messages,
                            system=system_prompt,
                            temperature=temperature,
                            tools=valid_tools,
                        )
                    except Exception as e:
                        # If tools caused an error, try again without tools
                        logger.warning(
                            f"Error using tools, falling back to regular chat: {str(e)}"
                        )
                        response = OllamaAPI.chat_completion(
                            model=model,
                            messages=messages,
                            system=system_prompt,
                            temperature=temperature,
                        )
                else:
                    # Regular completion without tools
                    response = OllamaAPI.chat_completion(
                        model=model,
                        messages=messages,
                        system=system_prompt,
                        temperature=temperature,
                    )
            except Exception as e:
                # Final fallback - try minimal parameters
                logger.warning(
                    f"Error in chat completion, trying minimal parameters: {str(e)}"
                )
                response = OllamaAPI.chat_completion(
                    model=model,
                    messages=messages,
                )

            # Add the model's initial response to the chat
            if hasattr(response, "message") and hasattr(response.message, "content"):
                # Add the initial response text to chat
                if response.message.content:
                    self.chat_manager.add_message(
                        "assistant", str(response.message.content)
                    )
            elif (
                isinstance(response, dict)
                and "message" in response
                and "content" in response["message"]
            ):
                # Fallback for dictionary response format
                if response["message"]["content"]:
                    self.chat_manager.add_message(
                        "assistant", str(response["message"]["content"])
                    )

            # Check for tool calls and process them
            has_tool_calls = (
                hasattr(response, "message")
                and hasattr(response.message, "tool_calls")
                and response.message.tool_calls
            ) or (
                isinstance(response, dict)
                and "message" in response
                and "tool_calls" in response["message"]
                and response["message"]["tool_calls"]
            )

            if has_tool_calls and st.session_state.use_installed_tools:
                # Process tool calls using the new helper method
                tool_results = OllamaAPI.process_tool_calls(
                    response, available_functions
                )

                # Display tool calls and results in the UI
                for tool_id, result in tool_results.items():
                    function_name = result.get("function_name", "unknown_function")

                    # Display tool call
                    arg_str = "arguments not available"
                    if "output" in result:
                        # Format output for display
                        if isinstance(result["output"], (dict, list)):
                            result_str = json.dumps(result["output"], indent=2)
                        else:
                            result_str = str(result["output"])

                        # Add tool call and result to chat UI
                        self.chat_manager.add_message(
                            "system",
                            f"🛠️ **Tool Call**: `{function_name}`\n\n"
                            f"*Executing tool...*",
                        )

                        self.chat_manager.add_message(
                            "system",
                            f"🛠️ **Tool Result**:\n```json\n{result_str}\n```",
                        )
                    elif "error" in result:
                        # Handle tool execution error
                        self.chat_manager.add_message(
                            "system",
                            f"🛠️ **Tool Call**: `{function_name}`\n\n"
                            f"*Executing tool...*",
                        )

                        self.chat_manager.add_message(
                            "system",
                            f"❌ **Tool Error**: {result['error']}",
                        )

                # Update messages with tool results for follow-up
                updated_messages = OllamaAPI.add_tool_results_to_messages(
                    messages, response, tool_results
                )

                # Get follow-up response from model with the tool results
                follow_up_response = OllamaAPI.chat_completion(
                    model=model,
                    messages=updated_messages,
                    system=system_prompt,
                    temperature=temperature,
                )

                # Add the follow-up response to chat
                if hasattr(follow_up_response, "message") and hasattr(
                    follow_up_response.message, "content"
                ):
                    if follow_up_response.message.content:
                        self.chat_manager.add_message(
                            "assistant", str(follow_up_response.message.content)
                        )
                elif (
                    isinstance(follow_up_response, dict)
                    and "message" in follow_up_response
                ):
                    if follow_up_response["message"].get("content"):
                        self.chat_manager.add_message(
                            "assistant", str(follow_up_response["message"]["content"])
                        )

            elif has_tool_calls and not st.session_state.use_installed_tools:
                # Simulation mode for tool calls
                # Handle both object-based and dict-based formats
                tool_calls = []

                if (
                    hasattr(response, "message")
                    and hasattr(response.message, "tool_calls")
                    and response.message.tool_calls is not None
                ):
                    tool_calls = response.message.tool_calls
                elif (
                    isinstance(response, dict)
                    and "message" in response
                    and "tool_calls" in response["message"]
                ) and response["message"]["tool_calls"] is not None:
                    tool_calls = response["message"]["tool_calls"]

                for tool_call in tool_calls:
                    # Extract function info safely for both dict and object formats
                    if isinstance(tool_call, dict):
                        function_name = tool_call.get("function", {}).get(
                            "name", "unknown_function"
                        )
                        arguments = tool_call.get("function", {}).get("arguments", "{}")
                    else:
                        function_name = getattr(
                            getattr(tool_call, "function", {}),
                            "name",
                            "unknown_function",
                        )
                        arguments = getattr(
                            getattr(tool_call, "function", {}), "arguments", "{}"
                        )

                    # Display simulation message
                    self.chat_manager.add_message(
                        "system",
                        f"🛠️ **Tool Call**: `{function_name}`\n\n"
                        f"*This is a simulation. In a real application, "
                        f"you would implement the actual function logic and return results.*",
                    )

                # For simulation, just get a follow-up response with the original messages
                follow_up_response = OllamaAPI.chat_completion(
                    model=model,
                    messages=messages,
                    system=system_prompt,
                    temperature=temperature,
                )

                # Add the follow-up response to chat
                if hasattr(follow_up_response, "message") and hasattr(
                    follow_up_response.message, "content"
                ):
                    if follow_up_response.message.content:
                        self.chat_manager.add_message(
                            "assistant", str(follow_up_response.message.content)
                        )
                elif (
                    isinstance(follow_up_response, dict)
                    and "message" in follow_up_response
                ):
                    if follow_up_response["message"].get("content"):
                        self.chat_manager.add_message(
                            "assistant", str(follow_up_response["message"]["content"])
                        )

        except Exception as e:
            logger.error(f"Error getting chat response: {str(e)}", exc_info=True)
            self.chat_manager.add_message(
                "system",
                f"❌ Error: {str(e)}\n\nPlease try again or select a different model.",
            )
        finally:
            # Clear thinking state
            st.session_state.thinking = False

    def render_sidebar(self):
        """Render the chat sidebar"""
        st.sidebar.subheader("Chat Settings")

        # Model selector
        if st.session_state.available_models:
            # Extract model names from available models, handling different data structures
            models = []
            for model_data in st.session_state.available_models:
                if isinstance(model_data, dict):
                    # Try different possible keys for the model name
                    model_name = model_data.get("name") or model_data.get("model")
                    if model_name:
                        models.append(model_name)
                elif hasattr(model_data, "name"):
                    models.append(model_data.name)
                elif hasattr(model_data, "model"):
                    models.append(model_data.model)
                elif isinstance(model_data, str):
                    models.append(model_data)

            if models:
                selected_idx = 0
                if st.session_state.selected_model in models:
                    selected_idx = models.index(st.session_state.selected_model)

                model = st.sidebar.selectbox(
                    "Select Model",
                    models,
                    index=selected_idx,
                    key="sidebar_model_select",
                )
                st.session_state.selected_model = model
            else:
                st.sidebar.warning(
                    "No models available despite API response. Please check Ollama."
                )
        else:
            st.sidebar.warning(
                "No models available. Please pull models from the Models page."
            )

        # System prompt
        st.sidebar.subheader("System Prompt")
        system_prompt = st.sidebar.text_area(
            "Custom instructions for the AI",
            value=st.session_state.system_prompt,
            help="This sets the behavior and capabilities of the AI assistant.",
            key="system_prompt_input",
        )
        if system_prompt != st.session_state.system_prompt:
            st.session_state.system_prompt = system_prompt

        # Temperature
        st.sidebar.subheader("Temperature")
        temperature = st.sidebar.slider(
            "Controls randomness (higher = more creative, lower = more focused)",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.chat_temperature,
            step=0.1,
            key="temperature_slider",
        )
        if temperature != st.session_state.chat_temperature:
            st.session_state.chat_temperature = temperature

        # Tools settings
        st.sidebar.subheader("Tools")

        # Custom tools
        use_tools = st.sidebar.checkbox(
            "Enable Custom Tools",
            value=st.session_state.use_tools,
            help="Enable tools created in the Tools page",
            key="enable_custom_tools",
        )
        if use_tools != st.session_state.use_tools:
            st.session_state.use_tools = use_tools
            # Disable installed tools if custom tools are enabled
            if use_tools:
                st.session_state.use_installed_tools = False

        # Installed tools
        use_installed_tools = st.sidebar.checkbox(
            "Enable Installed Tools",
            value=st.session_state.use_installed_tools,
            help="Enable tools installed in the tools directory",
            key="enable_installed_tools",
        )
        if use_installed_tools != st.session_state.use_installed_tools:
            st.session_state.use_installed_tools = use_installed_tools
            # Disable custom tools if installed tools are enabled
            if use_installed_tools:
                st.session_state.use_tools = False

        # Show available tools based on selection
        if st.session_state.use_tools:
            # Tool selector - only show if tools exist
            if "tools" in st.session_state and st.session_state.tools:
                st.sidebar.write(f"Available Tools: {len(st.session_state.tools)}")

                # Show tools
                with st.sidebar.expander("View Available Tools"):
                    for tool in st.session_state.tools:
                        tool_name = tool["definition"]["function"]["name"]
                        st.sidebar.write(f"• {tool_name}")

                # Tool choice option
                tool_choice = st.sidebar.radio(
                    "Tool Selection Mode",
                    ["auto", "none"],
                    index=0 if st.session_state.tool_choice == "auto" else 1,
                    help="'auto' lets the model decide when to use tools, 'none' disables tools",
                    key="tool_choice_custom",
                )
                if tool_choice != st.session_state.tool_choice:
                    st.session_state.tool_choice = tool_choice
            else:
                st.sidebar.warning(
                    "No tools created yet. Go to the Tools page to create tools."
                )
        elif st.session_state.use_installed_tools:
            # Load installed tools if needed
            if not st.session_state.installed_tools:
                self.load_installed_tools()

            # Show installed tools
            if st.session_state.installed_tools:
                st.sidebar.write(
                    f"Installed Tools: {len(st.session_state.installed_tools)}"
                )

                # Show tools
                with st.sidebar.expander("View Installed Tools"):
                    for i, tool in enumerate(st.session_state.installed_tools):
                        if callable(tool):
                            # Function reference
                            tool_name = tool.__name__
                            description = (
                                getattr(tool, "__doc__", "").split("\n")[0]
                                if getattr(tool, "__doc__", "")
                                else f"Function {tool_name}"
                            )
                        else:
                            # Dictionary tool definition
                            tool_name = tool["function"]["name"]
                            description = tool["function"]["description"]
                        st.sidebar.write(f"• **{tool_name}**: {description[:50]}...")

                # Tool choice option
                tool_choice = st.sidebar.radio(
                    "Tool Selection Mode",
                    ["auto", "none"],
                    index=0 if st.session_state.tool_choice == "auto" else 1,
                    help="'auto' lets the model decide when to use tools, 'none' disables tools",
                    key="tool_choice_installed",
                )
                if tool_choice != st.session_state.tool_choice:
                    st.session_state.tool_choice = tool_choice

                # Refresh tools button
                if st.sidebar.button(
                    "Refresh Installed Tools", key="refresh_tools_btn"
                ):
                    self.load_installed_tools()
                    st.sidebar.success(
                        f"Loaded {len(st.session_state.installed_tools)} tools"
                    )
            else:
                st.sidebar.warning(
                    "No tools installed. Go to the Tools page to install tools."
                )

        # Chat actions
        st.sidebar.subheader("Actions")
        if st.sidebar.button("Clear Chat", key="sidebar_clear_chat"):
            self.chat_manager.reset()
            st.rerun()

    def render(self):
        """Render the chat page"""
        st.title("Ollama Chat")
        st.write("Chat with your installed Ollama models")

        # Fetch available models and update session state
        models = OllamaAPI.get_local_models()
        st.session_state.available_models = models

        # Render the sidebar
        self.render_sidebar()

        # Display the chat title
        st.subheader(self.chat_manager.get_current_chat_title())

        # Handle model response if thinking
        self.handle_model_response()

        # Render the chat UI with current messages
        self.chat_ui.render(self.chat_manager.get_messages_for_api())
