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
                # This is the new approach using direct function references
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

            # Handle tool calls - look for them in different possible structures
            tool_calls = []

            # First try the new structure with message.tool_calls
            if (
                response
                and hasattr(response, "message")
                and hasattr(response.message, "tool_calls")
            ):
                tool_calls = response.message.tool_calls or []
                content = (
                    response.message.content or "I'll use a tool to help with this."
                )
                self.chat_manager.add_message("assistant", str(content))
            # Fall back to previous dict structure
            elif (
                response
                and isinstance(response, dict)
                and "message" in response
                and "tool_calls" in response["message"]
                and response["message"]["tool_calls"]
            ):
                tool_calls = response["message"]["tool_calls"]
                content = (
                    response["message"]["content"]
                    or "I'll use a tool to help with this."
                )
                self.chat_manager.add_message("assistant", str(content))

            # Process tool calls if any
            if tool_calls:
                for tool_call in tool_calls:
                    # Handle both old and new format
                    if isinstance(tool_call, dict):
                        # Old format (dict)
                        function_name = tool_call["function"]["name"]
                        function_id = tool_call["id"]
                        arguments_str = tool_call["function"]["arguments"]
                    else:
                        # New format (object)
                        # Access attributes safely
                        function_name = getattr(tool_call.function, "name", "")
                        function_id = getattr(tool_call, "id", "")
                        arguments_str = getattr(tool_call.function, "arguments", {})

                    try:
                        # Parse arguments
                        if isinstance(arguments_str, str):
                            try:
                                arguments = json.loads(arguments_str)
                            except json.JSONDecodeError:
                                arguments = {"raw_arguments": arguments_str}
                        else:
                            # If it's already a dict or similar object, use it directly
                            arguments = dict(arguments_str) if arguments_str else {}
                    except Exception:
                        # Last resort for arguments
                        arguments = {"raw_arguments": str(arguments_str)}

                    # Format arguments for display
                    arg_display = ", ".join(
                        [f"{k}={repr(v)}" for k, v in arguments.items()]
                    )

                    # Check if we should use installed tools
                    use_real_tools = st.session_state.use_installed_tools
                    tool_result = None

                    if use_real_tools:
                        try:
                            # Execute the tool function - try the new approach first
                            self.chat_manager.add_message(
                                "system",
                                f"🛠️ **Tool Call**: `{function_name}({arg_display})`\n\n"
                                f"*Executing tool...*",
                            )

                            # Find the function to execute
                            function_to_call = available_functions.get(function_name)

                            if function_to_call and callable(function_to_call):
                                # New approach: directly call the function
                                tool_result = function_to_call(**arguments)
                                logger.info(
                                    f"Executed tool function {function_name} directly"
                                )
                            else:
                                # Fall back to the old approach
                                tool_result = ToolLoader.execute_tool(
                                    function_name, dict(arguments)
                                )
                                logger.info(
                                    f"Executed tool {function_name} via ToolLoader"
                                )

                            # Convert result to string if needed
                            if not isinstance(tool_result, (str, dict, list)):
                                tool_result = str(tool_result)

                            # Format result for display
                            if isinstance(tool_result, (dict, list)):
                                result_str = json.dumps(tool_result, indent=2)
                            else:
                                result_str = str(tool_result)

                            # Add tool result display to chat
                            self.chat_manager.add_message(
                                "system",
                                f"🛠️ **Tool Result**:\n```json\n{result_str}\n```",
                            )
                        except Exception as e:
                            # Handle tool execution error
                            error_msg = (
                                f"Error executing tool {function_name}: {str(e)}"
                            )
                            logger.error(error_msg, exc_info=True)
                            tool_result = {"error": error_msg}

                            # Add error message to chat
                            self.chat_manager.add_message(
                                "system",
                                f"❌ **Tool Error**: {error_msg}",
                            )
                    else:
                        # Simulation mode
                        self.chat_manager.add_message(
                            "system",
                            f"🛠️ **Tool Call**: `{function_name}({arg_display})`\n\n"
                            f"*This is a simulation. In a real application, "
                            f"you would implement the actual function logic and return results.*",
                        )

                        # Simulate a tool response
                        tool_result = f"Simulated result for {function_name} with arguments: {arguments_str}"

                    # Create the tool response message based on format
                    if isinstance(tool_call, dict):
                        # Old format (dict)
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": function_id,
                            "name": function_name,
                            "content": (
                                json.dumps(tool_result)
                                if isinstance(tool_result, (dict, list))
                                else tool_result
                            ),
                        }
                    else:
                        # New format (object)
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": function_id,
                            "name": function_name,
                            "content": (
                                json.dumps(tool_result)
                                if isinstance(tool_result, (dict, list))
                                else tool_result
                            ),
                        }

                    # Add to chat display
                    self.chat_manager.add_special_message(tool_message)

                    # Get follow-up response from model
                    follow_up_messages = self.chat_manager.get_messages_for_api()
                    follow_up_response = OllamaAPI.chat_completion(
                        model=model,
                        messages=follow_up_messages,
                        system=system_prompt,
                        temperature=temperature,
                    )

                    # Handle both old and new response formats
                    if (
                        isinstance(follow_up_response, dict)
                        and "message" in follow_up_response
                    ):
                        # Old format
                        content = follow_up_response["message"]["content"]
                        if content:
                            self.chat_manager.add_message("assistant", content)
                    elif hasattr(follow_up_response, "message") and hasattr(
                        follow_up_response.message, "content"
                    ):
                        # New format
                        content = follow_up_response.message.content
                        if content:
                            self.chat_manager.add_message("assistant", content)
            elif response:
                # Regular response (no tool calls)
                if isinstance(response, dict) and "message" in response:
                    # Old format
                    content = response["message"]["content"]
                    if content:
                        self.chat_manager.add_message("assistant", content)
                elif hasattr(response, "message") and hasattr(
                    response.message, "content"
                ):
                    # New format
                    content = response.message.content
                    if content:
                        self.chat_manager.add_message("assistant", content)
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
