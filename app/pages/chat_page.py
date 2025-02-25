import streamlit as st
import time
import json
from typing import Dict, List, Any, Optional, cast, Union
from app.api.ollama_api import OllamaAPI
from app.api.api_helpers import parse_model_response, handle_streaming_response
from app.components.chat_ui import ChatUI
from app.components.model_selector import ModelSelector
from app.components.tool_selector import ToolSelector
from app.utils.chat_manager import ChatManager
from app.utils.tool_loader import ToolLoader
from app.utils.logger import get_logger, exception_handler, ErrorHandler
from app.utils.session_manager import SessionManager
from app.components.ui_components import status_indicator, collapsible_section

# Get application logger
logger = get_logger()


class ChatPage:
    """Page for chatting with LLM models"""

    def __init__(self):
        """Initialize the chat page"""
        # Initialize all chat-related session state
        SessionManager.init_chat_state()

        # Initialize chat manager
        self.chat_manager = ChatManager()

        # Initialize the chat UI
        self.chat_ui = ChatUI(on_message=self.process_message)

        # Initialize the model selector
        self.model_selector = ModelSelector(on_select=self.handle_model_selected)

        # Initialize the tool selector
        self.tool_selector = ToolSelector(on_change=self.handle_tools_changed)

    def handle_model_selected(self, model_info: Dict[str, Any]):
        """
        Handle when a model is selected

        Args:
            model_info: Information about the selected model
        """
        # Update the session state with the selected model
        st.session_state.selected_model = model_info.get("name")
        logger.info(f"Selected model: {model_info.get('name')}")

    def handle_tools_changed(self, tools: List[Any]):
        """
        Handle when selected tools change

        Args:
            tools: List of active tools
        """
        logger.info(f"Active tools changed: {len(tools)} tools")

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

            # Get active tools from the tool selector
            tools = self.tool_selector.get_active_tools()
            tool_choice = st.session_state.tool_choice
            available_functions = {}

            if tools and st.session_state.use_installed_tools:
                # For installed tools, load function references
                try:
                    available_functions = ToolLoader.load_all_tool_functions()
                    logger.info(
                        f"Loaded {len(available_functions)} available functions"
                    )
                except Exception as e:
                    logger.error(f"Error loading tool functions: {str(e)}")

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
        st.sidebar.subheader("Model Selection")

        # Render the model selector in the sidebar
        self.model_selector.render()

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

        # Render the tool selector in compact mode
        self.tool_selector.render_tool_selection(compact=True)

        # Chat actions
        st.sidebar.subheader("Actions")
        if st.sidebar.button("Clear Chat", key="sidebar_clear_chat"):
            self.chat_manager.reset()
            st.rerun()

    def render(self):
        """Render the chat page"""
        st.title("Ollama Chat")
        st.write("Chat with your installed Ollama models")

        # Render the sidebar
        self.render_sidebar()

        # Display the chat title
        st.subheader(self.chat_manager.get_current_chat_title())

        # Handle model response if thinking
        self.handle_model_response()

        # Render the chat UI with current messages
        self.chat_ui.render(self.chat_manager.get_messages_for_api())
