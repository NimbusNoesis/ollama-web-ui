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

            # Instead of directly modifying session state here, we'll use a callback
            # that will be triggered before the next rerun

            # Process message using the callback
            self.on_message(user_input)

            # We'll clear the input in a separate callback function
            # Set a flag to clear the input on the next rerun
            if "clear_input_flag" not in st.session_state:
                st.session_state.clear_input_flag = True

    def _process_markdown(self, text: str) -> str:
        """
        Process markdown text to HTML

        Args:
            text: The markdown text to process

        Returns:
            HTML representation of the markdown
        """
        # Convert markdown to HTML with syntax highlighting
        html = markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.tables",
                "markdown.extensions.codehilite",
            ],
            extension_configs={
                "markdown.extensions.codehilite": {
                    "linenums": False,
                    "guess_lang": False,
                }
            },
        )
        return html

    def render_message(self, message: Dict[str, Any], idx: int):
        """
        Render a single message in the chat

        Args:
            message: The message to render
            idx: Index of the message
        """
        role = message.get("role", "")
        content = message.get("content", "")

        # Process markdown in content
        processed_content = self._process_markdown(content)

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
                    <div style="color: #333333;">{processed_content}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif role == "assistant":
                st.markdown(
                    f"""
                <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="color: #333333;"><strong>Assistant</strong></p>
                    <div style="color: #333333;">{processed_content}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            elif role == "system":
                st.markdown(
                    f"""
                <div style="background-color: #fdf0d5; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <p style="color: #333333;"><strong>System</strong></p>
                    <div style="color: #333333;"><i>{processed_content}</i></div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(processed_content, unsafe_allow_html=True)

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

        # Define a callback to clear the input after submission
        def clear_input():
            st.session_state.user_input = ""

        # Check if we need to trigger the clear input
        if (
            "trigger_clear_input" in st.session_state
            and st.session_state.trigger_clear_input
        ):
            st.session_state.trigger_clear_input = False
            clear_input()

        st.text_input(
            "Message",
            key="user_input",
            on_change=self._handle_input,
            placeholder="Type your message here...",
            disabled=st.session_state.thinking,
            label_visibility="collapsed",
        )

        # Add a hidden button that will clear the input when clicked
        # We'll use CSS to hide it instead of the style parameter
        st.markdown(
            """
            <style>
            #clear_input_button {
                display: none;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Clear Input",
            key="clear_input_button",
            on_click=clear_input,
        ):
            pass

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

        # Add CSS for syntax highlighting
        st.markdown(
            """
            <style>
            .codehilite .hll { background-color: #ffffcc }
            .codehilite  { background: #f8f8f8; }
            .codehilite .c { color: #408080; font-style: italic } /* Comment */
            .codehilite .err { border: 1px solid #FF0000 } /* Error */
            .codehilite .k { color: #008000; font-weight: bold } /* Keyword */
            .codehilite .o { color: #666666 } /* Operator */
            .codehilite .cm { color: #408080; font-style: italic } /* Comment.Multiline */
            .codehilite .cp { color: #BC7A00 } /* Comment.Preproc */
            .codehilite .c1 { color: #408080; font-style: italic } /* Comment.Single */
            .codehilite .cs { color: #408080; font-style: italic } /* Comment.Special */
            .codehilite .gd { color: #A00000 } /* Generic.Deleted */
            .codehilite .ge { font-style: italic } /* Generic.Emph */
            .codehilite .gr { color: #FF0000 } /* Generic.Error */
            .codehilite .gh { color: #000080; font-weight: bold } /* Generic.Heading */
            .codehilite .gi { color: #00A000 } /* Generic.Inserted */
            .codehilite .go { color: #808080 } /* Generic.Output */
            .codehilite .gp { color: #000080; font-weight: bold } /* Generic.Prompt */
            .codehilite .gs { font-weight: bold } /* Generic.Strong */
            .codehilite .gu { color: #800080; font-weight: bold } /* Generic.Subheading */
            .codehilite .gt { color: #0044DD } /* Generic.Traceback */
            .codehilite .kc { color: #008000; font-weight: bold } /* Keyword.Constant */
            .codehilite .kd { color: #008000; font-weight: bold } /* Keyword.Declaration */
            .codehilite .kn { color: #008000; font-weight: bold } /* Keyword.Namespace */
            .codehilite .kp { color: #008000 } /* Keyword.Pseudo */
            .codehilite .kr { color: #008000; font-weight: bold } /* Keyword.Reserved */
            .codehilite .kt { color: #B00040 } /* Keyword.Type */
            .codehilite .m { color: #666666 } /* Literal.Number */
            .codehilite .s { color: #BA2121 } /* Literal.String */
            .codehilite .na { color: #7D9029 } /* Name.Attribute */
            .codehilite .nb { color: #008000 } /* Name.Builtin */
            .codehilite .nc { color: #0000FF; font-weight: bold } /* Name.Class */
            .codehilite .no { color: #880000 } /* Name.Constant */
            .codehilite .nd { color: #AA22FF } /* Name.Decorator */
            .codehilite .ni { color: #999999; font-weight: bold } /* Name.Entity */
            .codehilite .ne { color: #D2413A; font-weight: bold } /* Name.Exception */
            .codehilite .nf { color: #0000FF } /* Name.Function */
            .codehilite .nl { color: #A0A000 } /* Name.Label */
            .codehilite .nn { color: #0000FF; font-weight: bold } /* Name.Namespace */
            .codehilite .nt { color: #008000; font-weight: bold } /* Name.Tag */
            .codehilite .nv { color: #19177C } /* Name.Variable */
            .codehilite .ow { color: #AA22FF; font-weight: bold } /* Operator.Word */
            .codehilite .w { color: #bbbbbb } /* Text.Whitespace */
            .codehilite .mb { color: #666666 } /* Literal.Number.Bin */
            .codehilite .mf { color: #666666 } /* Literal.Number.Float */
            .codehilite .mh { color: #666666 } /* Literal.Number.Hex */
            .codehilite .mi { color: #666666 } /* Literal.Number.Integer */
            .codehilite .mo { color: #666666 } /* Literal.Number.Oct */
            .codehilite .sa { color: #BA2121 } /* Literal.String.Affix */
            .codehilite .sb { color: #BA2121 } /* Literal.String.Backtick */
            .codehilite .sc { color: #BA2121 } /* Literal.String.Char */
            .codehilite .dl { color: #BA2121 } /* Literal.String.Delimiter */
            .codehilite .sd { color: #BA2121; font-style: italic } /* Literal.String.Doc */
            .codehilite .s2 { color: #BA2121 } /* Literal.String.Double */
            .codehilite .se { color: #AA5D1F; font-weight: bold } /* Literal.String.Escape */
            .codehilite .sh { color: #BA2121 } /* Literal.String.Heredoc */
            .codehilite .si { color: #A45A77; font-weight: bold } /* Literal.String.Interpol */
            .codehilite .sx { color: #008000 } /* Literal.String.Other */
            .codehilite .sr { color: #A45A77 } /* Literal.String.Regex */
            .codehilite .s1 { color: #BA2121 } /* Literal.String.Single */
            .codehilite .ss { color: #19177C } /* Literal.String.Symbol */
            .codehilite .bp { color: #008000 } /* Name.Builtin.Pseudo */
            .codehilite .vc { color: #19177C } /* Name.Variable.Class */
            .codehilite .vg { color: #19177C } /* Name.Variable.Global */
            .codehilite .vi { color: #19177C } /* Name.Variable.Instance */
            .codehilite .il { color: #666666 } /* Literal.Number.Integer.Long */
            </style>
            """,
            unsafe_allow_html=True,
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
            # Modified to use a callback for clearing input
            def submit_and_clear():
                if st.session_state.user_input and not st.session_state.thinking:
                    user_input = st.session_state.user_input
                    # Process message using the callback
                    self.on_message(user_input)
                    # Clear input in the next rerun
                    st.session_state.user_input = ""

            if st.button(
                "Submit", disabled=st.session_state.thinking, on_click=submit_and_clear
            ):
                pass
                # The actual submission is handled in the on_click callback
