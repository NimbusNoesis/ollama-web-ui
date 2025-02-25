import streamlit as st
import time
from typing import Dict, List, Any, Optional, cast, Union
from app.api.ollama_api import OllamaAPI
from app.components.chat_ui import ChatUI
from app.utils.chat_manager import ChatManager


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
        """Handle model response when thinking state is active"""
        if not st.session_state.thinking:
            return

        try:
            # Get the model and messages
            model = st.session_state.selected_model
            messages = self.chat_manager.get_messages_for_api()
            system = (
                st.session_state.system_prompt
                if st.session_state.system_prompt.strip()
                else None
            )
            temperature = st.session_state.chat_temperature

            # Get model response
            response_text = ""

            result = OllamaAPI.chat_completion(
                model=model,
                messages=cast(List[Dict[str, Union[str, List[Any]]]], messages),
                system=system,
                temperature=temperature,
                stream=True,
            )

            # Parse the assistant's message from the model response
            if result and "message" in result:
                # Extract just the content field from the message
                if "content" in result["message"]:
                    response_text = result["message"]["content"]
                else:
                    response_text = str(result["message"])
            else:
                response_text = str(result)

            # Add the response to chat history
            self.chat_manager.add_message("assistant", response_text)

        except Exception as e:
            # Add error message to chat
            error_message = f"Error: {str(e)}"
            self.chat_manager.add_message("system", error_message)

        finally:
            # Remove thinking indicator
            self.chat_ui.remove_thinking_indicator()

    def render_sidebar(self):
        """Render the sidebar for chat options"""
        st.sidebar.header("Chat Settings")

        # Model selection
        models = OllamaAPI.get_local_models()
        model_options = [m.get("model", "") for m in models]

        # Store available models for later use
        st.session_state.available_models = models

        if model_options:
            # Select model
            selected_model = st.sidebar.selectbox(
                "Select Model",
                options=model_options,
                index=(
                    0
                    if st.session_state.selected_model is None
                    else (
                        model_options.index(st.session_state.selected_model)
                        if st.session_state.selected_model in model_options
                        else 0
                    )
                ),
            )

            # Update selected model in session state
            st.session_state.selected_model = selected_model
        else:
            st.sidebar.warning("No models available. Please install models first.")
            st.session_state.selected_model = None

        # Temperature slider
        st.session_state.chat_temperature = st.sidebar.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.chat_temperature,
            step=0.1,
            help="Higher values make output more random, lower values more deterministic",
        )

        # System prompt
        st.session_state.system_prompt = st.sidebar.text_area(
            "System Prompt",
            value=st.session_state.system_prompt,
            help="Optional instructions to guide the model's behavior",
        )

        # Chat management section
        st.sidebar.header("Chat Management")

        # New chat button
        if st.sidebar.button("New Chat"):
            self.chat_manager.create_new_chat()
            st.rerun()

        # Saved chats
        st.sidebar.subheader("Saved Chats")
        saved_chats = self.chat_manager.list_saved_chats()

        if not saved_chats:
            st.sidebar.info("No saved chats yet")
        else:
            # Display saved chats
            for chat in saved_chats:
                col1, col2 = st.sidebar.columns([3, 1])

                with col1:
                    st.write(f"**{chat['title']}**")
                    st.caption(f"{chat['message_count']} messages")

                with col2:
                    if st.button("Load", key=f"load_{chat['id']}"):
                        self.chat_manager.load_chat(chat["id"])
                        st.rerun()
                    if st.button("Delete", key=f"delete_{chat['id']}"):
                        self.chat_manager.delete_chat(chat["id"])
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
