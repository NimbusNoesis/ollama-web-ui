"""
Reusable component for tool selection and management
"""

import streamlit as st
import json
from typing import List, Dict, Any, Optional, Callable, Union, cast

from app.utils.logger import get_logger
from app.utils.session_manager import SessionManager

# Get application logger
logger = get_logger()


class ToolSelector:
    """Component for selecting and managing tools"""

    def __init__(
        self,
        on_change: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        key_prefix: str = "",
    ):
        """
        Initialize the tool selector component

        Args:
            on_change: Callback when tool selection changes
            key_prefix: Prefix for Streamlit session state keys
        """
        self.on_change = on_change
        self.key_prefix = key_prefix

        # Initialize session state keys for tools
        SessionManager.init_tools_state()

    def get_active_tools(self) -> List[Dict[str, Any]]:
        """
        Get the currently active tools

        Returns:
            List of active tool definitions
        """
        if st.session_state.get("use_tools") and st.session_state.get("tools"):
            return st.session_state.tools
        return []

    def handle_tool_change(self, tools: List[Dict[str, Any]]):
        """
        Handle when tool selection changes

        Args:
            tools: List of selected tools
        """
        # Update session state
        st.session_state.tools = tools

        # Call the callback if provided
        if self.on_change:
            self.on_change(tools)

    def render_tool_selection(self, compact: bool = False):
        """
        Render the tool selection UI

        Args:
            compact: Whether to render in compact mode
        """
        # Header
        if not compact:
            st.subheader("AI Tools")
        else:
            st.sidebar.subheader("AI Tools")

        # Get container based on compact mode
        container = st.sidebar if compact else st

        # Enable/disable tools
        use_tools = container.checkbox(
            "Enable Tools",
            value=st.session_state.get("use_tools", False),
            help="Enable tool usage for the AI assistant",
        )

        # Update session state if changed
        if use_tools != st.session_state.get("use_tools", False):
            st.session_state.use_tools = use_tools
            st.rerun()

        if not use_tools:
            return

        # Get tool templates
        tool_templates = st.session_state.get("tool_templates", {})

        # Select tools to use
        tool_options = list(tool_templates.keys())

        # Tool selection
        selected_tools = container.multiselect(
            "Select Tools",
            options=tool_options,
            default=[],
            help="Select which tools the AI can use",
        )

        # Create tools list based on selection
        tools = []
        for tool_name in selected_tools:
            if tool_name in tool_templates:
                tools.append(tool_templates[tool_name])

        # Update session state and call callback
        if tools != st.session_state.get("tools", []):
            self.handle_tool_change(tools)

        # Tool choice (auto, none, or specific)
        tool_choice_options = ["auto", "none", "required"]
        st.session_state.tool_choice = container.selectbox(
            "Tool Choice",
            options=tool_choice_options,
            index=tool_choice_options.index(
                st.session_state.get("tool_choice", "auto")
            ),
            help="How tools should be used: auto (AI decides), none (no tools), required (must use tools)",
        )

        # Show installed tools option
        use_installed = container.checkbox(
            "Use Installed Tools",
            value=st.session_state.get("use_installed_tools", False),
            help="Use actual tool implementations (when available) instead of simulating",
        )

        if use_installed != st.session_state.get("use_installed_tools", False):
            st.session_state.use_installed_tools = use_installed

        # Show current tool configuration if tools are selected
        if tools and not compact:
            with st.expander("Tool Definitions", expanded=False):
                st.json(tools)

    def render_tool_editor(self):
        """
        Render the tool editor UI for creating and editing custom tools
        """
        st.subheader("Tool Editor")

        # Get tool templates
        tool_templates = st.session_state.get("tool_templates", {})

        # Create tabs for viewing and editing
        tab1, tab2 = st.tabs(["Create New Tool", "Edit Existing Tool"])

        with tab1:
            # New tool form
            with st.form(key="new_tool_form"):
                tool_name = st.text_input(
                    "Tool Name", help="A short, descriptive name for the tool"
                )

                tool_description = st.text_area(
                    "Tool Description",
                    help="Detailed description of what the tool does",
                )

                # Parameters section
                st.subheader("Parameters")
                param_editor = st.text_area(
                    "Parameters JSON",
                    value=json.dumps(
                        {
                            "type": "object",
                            "properties": {
                                "param1": {
                                    "type": "string",
                                    "description": "Description of parameter 1",
                                }
                            },
                            "required": ["param1"],
                        },
                        indent=2,
                    ),
                    height=200,
                    help="JSON schema for the tool parameters",
                )

                submitted = st.form_submit_button("Create Tool")

                if submitted:
                    try:
                        # Validate inputs
                        if not tool_name:
                            st.error("Tool name is required")
                            return

                        # Validate JSON
                        params = json.loads(param_editor)

                        # Create tool definition
                        tool_function_name = (
                            tool_name.lower().replace(" ", "_")
                            if tool_name
                            else "unnamed_tool"
                        )
                        new_tool = {
                            "type": "function",
                            "function": {
                                "name": tool_function_name,
                                "description": tool_description,
                                "parameters": params,
                            },
                        }

                        # Add to templates
                        tool_templates[tool_name] = new_tool
                        st.session_state.tool_templates = tool_templates
                        st.success(f"Tool '{tool_name}' created successfully!")

                    except json.JSONDecodeError:
                        st.error("Invalid JSON for parameters")

        with tab2:
            # Edit existing tool
            if not tool_templates:
                st.info("No tools available to edit. Create a tool first.")
            else:
                tool_to_edit = st.selectbox(
                    "Select Tool to Edit", options=list(tool_templates.keys())
                )

                if tool_to_edit:
                    tool = tool_templates[tool_to_edit]

                    with st.form(key="edit_tool_form"):
                        tool_name = st.text_input("Tool Name", value=tool_to_edit)

                        func = tool.get("function", {})
                        tool_description = st.text_area(
                            "Tool Description", value=func.get("description", "")
                        )

                        # Parameters section
                        st.subheader("Parameters")
                        param_editor = st.text_area(
                            "Parameters JSON",
                            value=json.dumps(func.get("parameters", {}), indent=2),
                            height=200,
                        )

                        submitted = st.form_submit_button("Update Tool")

                        if submitted:
                            try:
                                # Validate inputs
                                if not tool_name:
                                    st.error("Tool name is required")
                                    return

                                # Validate JSON
                                params = json.loads(param_editor)

                                # Update tool definition
                                tool_function_name = (
                                    tool_name.lower().replace(" ", "_")
                                    if tool_name
                                    else "unnamed_tool"
                                )
                                updated_tool = {
                                    "type": "function",
                                    "function": {
                                        "name": tool_function_name,
                                        "description": tool_description,
                                        "parameters": params,
                                    },
                                }

                                # Remove old entry if name changed
                                if tool_name != tool_to_edit:
                                    tool_templates.pop(tool_to_edit)

                                # Add updated tool
                                tool_templates[tool_name] = updated_tool
                                st.session_state.tool_templates = tool_templates
                                st.success(f"Tool '{tool_name}' updated successfully!")

                            except json.JSONDecodeError:
                                st.error("Invalid JSON for parameters")

    def render(self):
        """Render the full tool selector UI"""
        st.title("Tool Management")
        st.write("Configure tools for the AI assistant to use")

        # Render the tool selection UI
        self.render_tool_selection()

        # Render the tool editor
        self.render_tool_editor()
