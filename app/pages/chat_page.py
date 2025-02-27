import streamlit as st
import time
import json
from typing import Dict, List, Any, Optional, cast, Union, Iterator, TYPE_CHECKING
from app.api.ollama_api import OllamaAPI
from app.components.chat_ui import ChatUI
from app.utils.chat_manager import ChatManager
from app.utils.tool_loader import ToolLoader
from app.utils.logger import get_logger, exception_handler, ErrorHandler

# Get application logger
logger = get_logger()

# Type aliases to help with type checking
ResponseType = Any  # Could be ChatResponse, Iterator[str], or dict


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

        # Initialize streaming related state
        if "use_streaming" not in st.session_state:
            st.session_state.use_streaming = True

        if "full_response" not in st.session_state:
            st.session_state.full_response = ""

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

            # Determine if we can use streaming (only when not using tools)
            use_streaming = (
                st.session_state.use_streaming
                and not st.session_state.use_tools
                and not st.session_state.use_installed_tools
            )

            # Get tools if needed
            tools = None
            tool_choice = None
            available_functions = {}

            if st.session_state.use_tools and st.session_state.tools:
                # User-created tools from the session
                tools = [tool["definition"] for tool in st.session_state.tools]
                tool_choice = st.session_state.tool_choice
                use_streaming = False  # Can't stream with tools
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
                use_streaming = False  # Can't stream with tools

            # Handle streaming separately from non-streaming responses
            if use_streaming:
                self._handle_streaming_response(
                    model, messages, system_prompt, temperature
                )
            else:
                self._handle_normal_response(
                    model,
                    messages,
                    system_prompt,
                    temperature,
                    tools,
                    available_functions,
                    tool_choice,
                )

        except Exception as e:
            logger.error(f"Error getting chat response: {str(e)}", exc_info=True)
            self.chat_manager.add_message(
                "system",
                f"❌ Error: {str(e)}\n\nPlease try again or select a different model.",
            )
        finally:
            # Clear thinking state
            self.chat_ui.remove_thinking_indicator()

    def _handle_streaming_response(self, model, messages, system_prompt, temperature):
        """
        Handle streaming response from model

        Args:
            model: The model to use
            messages: Message history
            system_prompt: System prompt
            temperature: Temperature setting
        """
        logger.info("Using streaming mode for response")
        try:
            # Start streaming mode in UI
            self.chat_ui.start_streaming()

            # Prepare a message placeholder in the chat manager
            message_id = self.chat_manager.prepare_streaming_message()

            # Get streaming response
            response = OllamaAPI.chat_completion(
                model=model,
                messages=messages,
                system=system_prompt,
                temperature=temperature,
                stream=True,
            )

            # Check if we got a streaming iterator or a regular response
            # Use duck typing to determine if it's an iterator without message attribute
            is_iterator = hasattr(response, "__iter__") and not hasattr(
                response, "message"
            )

            if not is_iterator:
                # We got a regular response instead of a streaming iterator
                logger.warning("Expected streaming response but got a regular one")
                # Handle it like a regular response
                content = ""
                if hasattr(response, "message"):
                    msg = getattr(response, "message")
                    if hasattr(msg, "content"):
                        content = str(getattr(msg, "content", ""))
                elif isinstance(response, dict) and "message" in response:
                    content = str(response["message"].get("content", ""))

                if content:
                    # Finalize the message first to remove streaming flag
                    self.chat_manager.finalize_streaming_message(content, message_id)
                    # No need to add another message, we already have one
                return

            # At this point, we're confident we have an iterator
            stream_generator = response

            # Collect the full response for saving later
            full_response = ""

            # Define a wrapper generator that collects the full response
            def collect_stream():
                nonlocal full_response
                for chunk in stream_generator:
                    if chunk is not None:
                        chunk_str = str(chunk)
                        full_response += chunk_str
                        yield chunk_str

            # Create a container below the last non-streaming message
            stream_container = st.container()
            with stream_container:
                # Render the streaming message in the container
                self.chat_ui.render_streaming_message(collect_stream())

            # After streaming completes, save the full response and remove streaming flag
            self.chat_manager.finalize_streaming_message(full_response, message_id)

            # Store full response in session state for reference
            st.session_state.full_response = full_response

            # Request a rerun after streaming is complete to refresh the UI
            # This ensures the message appears in the correct place in the chat history
            st.rerun()

        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            self.chat_manager.add_message(
                "system",
                f"❌ Streaming Error: {str(e)}\n\nPlease try again or disable streaming.",
            )
        finally:
            # Clear streaming state
            self.chat_ui.stop_streaming()

    def _handle_normal_response(
        self,
        model,
        messages,
        system_prompt,
        temperature,
        tools,
        available_functions,
        tool_choice,
    ):
        """
        Handle non-streaming response from model

        Args:
            model: The model to use
            messages: Message history
            system_prompt: System prompt
            temperature: Temperature setting
            tools: Tools to use
            available_functions: Available function references
            tool_choice: Tool choice setting
        """
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
                        stream=False,
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
                        stream=False,
                    )
            else:
                # Regular completion without tools
                response = OllamaAPI.chat_completion(
                    model=model,
                    messages=messages,
                    system=system_prompt,
                    temperature=temperature,
                    stream=False,
                )
        except Exception as e:
            # Final fallback - try minimal parameters
            logger.warning(
                f"Error in chat completion, trying minimal parameters: {str(e)}"
            )
            response = OllamaAPI.chat_completion(
                model=model,
                messages=messages,
                stream=False,
            )

        # Skip response handling if we somehow got a streaming iterator
        is_iterator = hasattr(response, "__iter__") and not hasattr(response, "message")
        if is_iterator:
            logger.warning("Got a streaming response in non-streaming mode")
            # Convert the streaming response to a normal response
            full_text = ""
            try:
                for chunk in response:
                    full_text += str(chunk)
                self.chat_manager.add_message("assistant", full_text)
            except Exception as e:
                logger.error(f"Error processing streaming response: {str(e)}")
            return

        # Add the model's initial response to the chat
        response_content = None
        if hasattr(response, "message"):
            msg = getattr(response, "message")
            if hasattr(msg, "content"):
                response_content = getattr(msg, "content")
                if response_content:
                    self.chat_manager.add_message("assistant", str(response_content))
        elif isinstance(response, dict) and "message" in response:
            msg_dict = response["message"]
            if "content" in msg_dict and msg_dict["content"]:
                self.chat_manager.add_message("assistant", str(msg_dict["content"]))

        # Check for tool calls
        has_tool_calls = False
        tool_calls = None

        if hasattr(response, "message"):
            msg = getattr(response, "message")
            if hasattr(msg, "tool_calls"):
                tool_calls = getattr(msg, "tool_calls")
                has_tool_calls = bool(tool_calls)
        elif isinstance(response, dict) and "message" in response:
            msg_dict = response["message"]
            if "tool_calls" in msg_dict:
                tool_calls = msg_dict["tool_calls"]
                has_tool_calls = bool(tool_calls)

        # Process tool calls if needed
        if has_tool_calls and st.session_state.use_installed_tools:
            # Process tool calls
            try:
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
                    stream=False,
                )

                # Add the follow-up response to chat
                if hasattr(follow_up_response, "message"):
                    msg = getattr(follow_up_response, "message")
                    if hasattr(msg, "content"):
                        content = getattr(msg, "content")
                        if content:
                            self.chat_manager.add_message("assistant", str(content))
                elif (
                    isinstance(follow_up_response, dict)
                    and "message" in follow_up_response
                ):
                    msg_dict = follow_up_response["message"]
                    if "content" in msg_dict and msg_dict["content"]:
                        self.chat_manager.add_message(
                            "assistant", str(msg_dict["content"])
                        )
            except Exception as e:
                logger.error(f"Error processing tool calls: {str(e)}")
                self.chat_manager.add_message(
                    "system",
                    f"❌ **Tool Error**: Failed to process tool calls: {str(e)}",
                )

        elif has_tool_calls and not st.session_state.use_installed_tools:
            # Simulation mode for tool calls - handle both object and dict formats
            tool_calls_list = []

            if tool_calls is not None:
                if isinstance(tool_calls, list):
                    tool_calls_list = tool_calls
                else:
                    # Try to convert to list if possible
                    try:
                        tool_calls_list = list(tool_calls)
                    except:
                        # If conversion fails, use empty list
                        tool_calls_list = []

            for tool_call in tool_calls_list:
                # Extract function info safely for both dict and object formats
                function_name = "unknown_function"
                arguments = "{}"

                if isinstance(tool_call, dict) and "function" in tool_call:
                    function_info = tool_call["function"]
                    if isinstance(function_info, dict):
                        function_name = function_info.get("name", "unknown_function")
                        arguments = function_info.get("arguments", "{}")
                elif hasattr(tool_call, "function"):
                    function_obj = getattr(tool_call, "function")
                    if hasattr(function_obj, "name"):
                        function_name = getattr(function_obj, "name")
                    if hasattr(function_obj, "arguments"):
                        arguments = getattr(function_obj, "arguments")

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
                stream=False,
            )

            # Add the follow-up response to chat
            if hasattr(follow_up_response, "message"):
                msg = getattr(follow_up_response, "message")
                if hasattr(msg, "content"):
                    content = getattr(msg, "content")
                    if content:
                        self.chat_manager.add_message("assistant", str(content))
            elif (
                isinstance(follow_up_response, dict) and "message" in follow_up_response
            ):
                msg_dict = follow_up_response["message"]
                if "content" in msg_dict and msg_dict["content"]:
                    self.chat_manager.add_message("assistant", str(msg_dict["content"]))

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

        # Streaming settings
        st.sidebar.subheader("Response Settings")
        use_streaming = st.sidebar.checkbox(
            "Enable Streaming",
            value=st.session_state.use_streaming,
            help="Stream responses in real-time (disabled when using tools)",
            key="streaming_checkbox",
        )
        if use_streaming != st.session_state.use_streaming:
            st.session_state.use_streaming = use_streaming

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
