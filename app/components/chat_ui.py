import time
import re
from typing import Any, Callable, Dict, List, Optional, Iterator

import streamlit as st


class ChatUI:
    """Component for displaying and interacting with the chat interface"""

    def __init__(self, on_message: Callable[[str], None], chat_manager=None):
        """
        Initialize the chat UI

        Args:
            on_message: Callback function to handle new user messages
            chat_manager: Optional chat manager instance for managing chat state
        """
        self.on_message = on_message
        self.chat_manager = chat_manager

        # Initialize session state for messages if needed
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "user_input" not in st.session_state:
            st.session_state.user_input = ""

        if "thinking" not in st.session_state:
            st.session_state.thinking = False

        if "streaming" not in st.session_state:
            st.session_state.streaming = False

        if "stream_container" not in st.session_state:
            st.session_state.stream_container = None

    def _handle_input(self):
        """Handle user input from the chat input box"""
        if st.session_state.user_input and not st.session_state.thinking:
            user_input = st.session_state.user_input

            # Instead of directly modifying session state here, we'll use a callback
            # that will be triggered before the next rerun

            # Process message using the callback
            self.on_message(user_input)

            # We'll clear the input in a separate callback function
            # Set a flag to clear the input on the next rerun
            if "clear_input_flag" not in st.session_state:
                st.session_state.clear_input_flag = True

    def _process_thinking_tags(self, content: str) -> str:
        """
        Process <think> tags in content and convert them to expandable sections

        Args:
            content: The message content to process

        Returns:
            Processed content with <think> tags converted to expandable sections
        """
        if "<think>" not in content:
            return content

        # Use regex to find all <think> sections
        pattern = r"<think>(.*?)</think>"

        def replacement(match):
            thinking_content = match.group(1).strip()
            # Create an expandable details/summary HTML element with a horizontal line after it
            return f"""
            <details>
                <summary><strong>Thinking</strong> (click to expand)</summary>
                <div class="thinking-content">
                    {thinking_content}
                </div>
            </details>
            <hr style="border-top: 1px solid #ccc; margin-top: 10px; margin-bottom: 10px;"/>
            """

        # Replace all <think> tags with expandable sections
        processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        return processed_content

    def render_message(self, message: Dict[str, Any], idx: int):
        """
        Render a single message in the chat

        Args:
            message: The message to render
            idx: Index of the message
        """
        role = message.get("role", "")
        content = message.get("content", "")

        # Process thinking tags for assistant messages
        if role == "assistant" and content:
            content = self._process_thinking_tags(content)

        # Determine avatar and alignment
        if role == "user":
            avatar = "👤"
        elif role == "assistant":
            avatar = "🤖"
        elif role == "system":
            avatar = "🔧"
        else:
            avatar = "❓"

        # Create columns for avatar and message
        col1, col2 = st.columns([1, 9])

        with col1:
            st.write(f"### {avatar}")

        with col2:
            # Apply some styling based on role
            if role == "user":
                header = "User"
            elif role == "assistant":
                header = "Assistant"
            elif role == "system":
                header = "System"
            else:
                header = "Message"

            # Open the styled container
            # st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)
            st.markdown(
                f"<h4>{header}</h4>",
                unsafe_allow_html=True,
            )

            st.markdown(content, unsafe_allow_html=True)

    def render_streaming_message(self, stream_generator: Iterator[str]):
        """
        Render a streaming message in the chat

        Args:
            stream_generator: Iterator that yields text chunks
        """
        # Use write_stream to display the streaming content
        col1, col2 = st.columns([1, 9])

        with col1:
            st.write("### 🤖")

        with col2:
            st.markdown("<h4>Assistant</h4>", unsafe_allow_html=True)

            # Buffer to accumulate chunks and detect <think> tags
            complete_message = ""

            # This generator wraps the stream and detects/processes <think> tags
            def process_stream():
                nonlocal complete_message

                for chunk in stream_generator:
                    if chunk is not None:
                        chunk_str = str(chunk)
                        complete_message += chunk_str

                        # For now, simply yield the chunk for display
                        # We'll process <think> tags after streaming is complete
                        yield chunk_str

                # After streaming is complete, if there are <think> tags,
                # they will be processed when the full message is displayed
                # in render_message after streaming completes

            # Use write_stream to render the streaming content
            st.write_stream(process_stream())

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

    def start_streaming(self):
        """Mark the UI as currently streaming a response"""
        st.session_state.streaming = True

    def stop_streaming(self):
        """Mark the UI as no longer streaming a response"""
        st.session_state.streaming = False

    def remove_thinking_indicator(self):
        """Remove the thinking indicator when the model is done processing"""
        st.session_state.thinking = False

    def render(self, messages: Optional[List[Dict[str, Any]]] = None):
        """
        Render the full chat UI

        Args:
            messages: Optional list of messages to render, if None uses session state
        """
        # Check if we need to clear the input from a previous interaction
        if "clear_input_flag" in st.session_state and st.session_state.clear_input_flag:
            st.session_state.clear_input_flag = False
            # We'll trigger the clear input button click in the next rerun
            st.session_state.trigger_clear_input = True

        if messages is None:
            messages = st.session_state.messages

        messages_to_render: List[Dict[str, Any]] = (
            messages if messages is not None else []
        )

        # Chat messages area with scrolling
        chat_container = st.container()
        with chat_container:
            # Check if we're streaming
            currently_streaming = st.session_state.streaming

            # First render all non-streaming messages
            for idx, message in enumerate(messages_to_render):
                # Skip streaming messages if we're actively streaming
                if currently_streaming and message.get("is_streaming", False):
                    continue
                self.render_message(message, idx)

            # Now handle the thinking indicator
            if st.session_state.thinking and not currently_streaming:
                # Only show thinking spinner when not streaming
                st.spinner("Thinking...")

        # Chat input at the bottom
        st.markdown("---")
        self.render_chat_input()

        # Button row below input
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button(
                "Clear Chat", disabled=st.session_state.thinking, key="btn_clear_chat"
            ):
                # Use chat_manager if available, otherwise reset the messages directly
                if self.chat_manager:
                    self.chat_manager.reset()
                    st.rerun()
                else:
                    st.session_state.messages = []

        with col3:
            # Modified to use a callback for clearing input
            def submit_and_clear():
                if st.session_state.user_input and not st.session_state.thinking:
                    user_input = st.session_state.user_input
                    # Process message using the callback
                    self.on_message(user_input)
                    # Clear input in the next rerun
                    st.session_state.user_input = ""

            if st.button(
                "Submit",
                disabled=st.session_state.thinking,
                on_click=submit_and_clear,
                key="btn_submit",
            ):
                pass
                # The actual submission is handled in the on_click callback
