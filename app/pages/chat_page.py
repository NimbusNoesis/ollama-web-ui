import streamlit as st
import time
from typing import Dict, List, Any, Optional, cast, Union
from app.api.ollama_api import OllamaAPI
from app.components.chat_ui import ChatUI
from app.utils.chat_manager import ChatManager
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

        # Initialize the chat UI
        self.chat_ui = ChatUI(on_message=self.process_message)

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
            if st.session_state.use_tools and st.session_state.tools:
                tools = [tool["definition"] for tool in st.session_state.tools]
                tool_choice = st.session_state.tool_choice

            # Get model response
            response = OllamaAPI.chat_completion(
                model=model,
                messages=messages,
                system=system_prompt,
                temperature=temperature,
                tools=tools,
                tool_choice=tool_choice,
            )

            # Check for tool calls
            if (
                response
                and "message" in response
                and "tool_calls" in response["message"]
            ):
                tool_calls = response["message"]["tool_calls"]

                # Add initial assistant response with tool calls
                self.chat_manager.add_message(
                    "assistant", response["message"]["content"]
                )

                # Process each tool call
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_id = tool_call["id"]
                    arguments = tool_call["function"]["arguments"]

                    # Display tool call to user
                    arg_str = arguments.replace("\n", " ")
                    self.chat_manager.add_message(
                        "system",
                        f"🛠️ **Tool Call**: `{function_name}({arg_str})`\n\n"
                        f"*This is a simulation. In a real application, "
                        f"you would implement the actual function logic and return results.*",
                    )

                    # Simulate a tool response
                    dummy_result = f"Simulated result for {function_name} with arguments: {arguments}"

                    # In a real application, you would:
                    # 1. Parse the arguments (usually JSON)
                    # 2. Call the actual function implementation
                    # 3. Get the real result

                    # Add tool response
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": function_id,
                        "name": function_name,
                        "content": dummy_result,
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

                    if follow_up_response and "message" in follow_up_response:
                        self.chat_manager.add_message(
                            "assistant", follow_up_response["message"]["content"]
                        )
            else:
                # Regular response (no tool calls)
                if response and "message" in response:
                    self.chat_manager.add_message(
                        "assistant", response["message"]["content"]
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
        models = [model["name"] for model in st.session_state.available_models]
        if models:
            selected_idx = 0
            if st.session_state.selected_model in models:
                selected_idx = models.index(st.session_state.selected_model)

            model = st.sidebar.selectbox(
                "Select Model", models, index=selected_idx, key="sidebar_model_select"
            )
            st.session_state.selected_model = model
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
        )
        if temperature != st.session_state.chat_temperature:
            st.session_state.chat_temperature = temperature

        # Tools settings
        st.sidebar.subheader("Tools")
        use_tools = st.sidebar.checkbox(
            "Enable Tools",
            value=st.session_state.use_tools,
            help="Enable tools to allow the AI to call functions",
        )
        if use_tools != st.session_state.use_tools:
            st.session_state.use_tools = use_tools

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
                )
                if tool_choice != st.session_state.tool_choice:
                    st.session_state.tool_choice = tool_choice
            else:
                st.sidebar.warning(
                    "No tools created yet. Go to the Tools page to create tools."
                )

        # Chat actions
        st.sidebar.subheader("Actions")
        if st.sidebar.button("Clear Chat"):
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
