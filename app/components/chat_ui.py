import streamlit as st
import markdown
from typing import List, Dict, Any, Optional, Callable
import time


class ChatUI:
    """Component for displaying and interacting with the chat interface"""

    def __init__(self, on_message: Callable[[str], None]):
        """
        Initialize the chat UI

        Args:
            on_message: Callback function to handle new user messages
        """
        self.on_message = on_message

        # Initialize session state for messages if needed
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "user_input" not in st.session_state:
            st.session_state.user_input = ""

        if "thinking" not in st.session_state:
            st.session_state.thinking = False

    def _handle_input(self):
        """Handle user input from the chat input box"""
        if st.session_state.user_input and not st.session_state.thinking:
            user_input = st.session_state.user_input
            st.session_state.user_input = ""

            # Process message using the callback
            self.on_message(user_input)

    def render_message(self, message: Dict[str, Any], idx: int):
        """
        Render a single message in the chat

        Args:
            message: The message to render
            idx: Index of the message
        """
        role = message.get("role", "")
        content = message.get("content", "")

        # Determine avatar and alignment
        if role == "user":
            avatar = "👤"
            is_user = True
        elif role == "assistant":
            avatar = "🤖"
            is_user = False
        elif role == "system":
            avatar = "🔧"
            is_user = False
        else:
            avatar = "❓"
            is_user = False

        # Create columns for avatar and message
        col1, col2 = st.columns([1, 9])

        with col1:
            st.write(f"### {avatar}")

        with col2:
            # Apply some styling based on role
            if role == "user":
                st.markdown(
                    f"""
                <div style="background-color: #e6f7ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="color: #333333;"><strong>User</strong></p>
                    <p style="color: #333333;">{content}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif role == "assistant":
                st.markdown(
                    f"""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="color: #333333;"><strong>Assistant</strong></p>
                    <p style="color: #333333;">{content}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif role == "system":
                st.markdown(
                    f"""
                <div style="background-color: #fdf0d5; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="color: #333333;"><strong>System</strong></p>
                    <p style="color: #333333;"><i>{content}</i></p>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.text(content)

    def render_messages(self, messages: List[Dict[str, Any]]):
        """
        Render all messages in the chat

        Args:
            messages: List of messages to render
        """
        # Render each message
        for idx, message in enumerate(messages):
            self.render_message(message, idx)

    def render_thinking(self):
        """Show a thinking indicator when the model is generating a response"""
        if st.session_state.thinking:
            with st.spinner("Thinking..."):
                # Keep this open until thinking state changes
                while st.session_state.thinking:
                    time.sleep(0.1)
                    # Need to break out of loop after brief time to prevent
                    # spinner from blocking the UI completely
                    break

    def render_chat_input(self):
        """Render the chat input box"""
        st.text_input(
            "Message",
            key="user_input",
            on_change=self._handle_input,
            placeholder="Type your message here...",
            disabled=st.session_state.thinking,
            label_visibility="collapsed",
        )

    def add_thinking_indicator(self):
        """Add a thinking indicator to show the model is processing"""
        st.session_state.thinking = True

    def remove_thinking_indicator(self):
        """Remove the thinking indicator when the model is done processing"""
        st.session_state.thinking = False

    def render(self, messages: Optional[List[Dict[str, Any]]] = None):
        """
        Render the full chat UI

        Args:
            messages: Optional list of messages to render, if None uses session state
        """
        if messages is None:
            messages = st.session_state.messages

        messages_to_render: List[Dict[str, Any]] = (
            messages if messages is not None else []
        )

        # Chat messages area with scrolling
        chat_container = st.container()
        with chat_container:
            self.render_messages(messages_to_render)
            self.render_thinking()

        # Chat input at the bottom
        st.markdown("---")
        self.render_chat_input()

        # Button row below input
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Clear Chat", disabled=st.session_state.thinking):
                st.session_state.messages = []

        with col3:
            if st.button("Submit", disabled=st.session_state.thinking):
                self._handle_input()
