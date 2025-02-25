import streamlit as st
import json
import uuid
from typing import Dict, List, Any, Optional
from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ToolsPage:
    """Page for generating and managing tools for LLM models"""

    def __init__(self):
        """Initialize the tools page"""
        # Initialize session state for tools
        if "tools" not in st.session_state:
            st.session_state.tools = []

        if "selected_tool" not in st.session_state:
            st.session_state.selected_tool = None

        if "tool_templates" not in st.session_state:
            # Initialize with some common tool templates
            st.session_state.tool_templates = {
                "Web Search": {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Search the web for information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                },
                "Calculator": {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": "Perform mathematical calculations",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "expression": {
                                    "type": "string",
                                    "description": "The mathematical expression to evaluate",
                                }
                            },
                            "required": ["expression"],
                        },
                    },
                },
                "Weather Info": {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather information for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "City or location name",
                                },
                                "units": {
                                    "type": "string",
                                    "description": "Units for temperature (celsius/fahrenheit)",
                                    "enum": ["celsius", "fahrenheit"],
                                },
                            },
                            "required": ["location"],
                        },
                    },
                },
            }

    def add_tool(self, tool_data: Dict[str, Any]) -> str:
        """
        Add a new tool to the collection

        Args:
            tool_data: Dictionary containing tool definition

        Returns:
            ID of the created tool
        """
        tool_id = str(uuid.uuid4())
        tool = {"id": tool_id, "definition": tool_data}
        st.session_state.tools.append(tool)
        return tool_id

    def update_tool(self, tool_id: str, tool_data: Dict[str, Any]) -> bool:
        """
        Update an existing tool

        Args:
            tool_id: ID of the tool to update
            tool_data: New tool definition

        Returns:
            True if update was successful, False otherwise
        """
        for i, tool in enumerate(st.session_state.tools):
            if tool["id"] == tool_id:
                st.session_state.tools[i]["definition"] = tool_data
                return True
        return False

    def delete_tool(self, tool_id: str) -> bool:
        """
        Delete a tool

        Args:
            tool_id: ID of the tool to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        for i, tool in enumerate(st.session_state.tools):
            if tool["id"] == tool_id:
                st.session_state.tools.pop(i)
                if st.session_state.selected_tool == tool_id:
                    st.session_state.selected_tool = None
                return True
        return False

    def render_tool_editor(self):
        """Render the tool editor section"""
        st.subheader("Tool Editor")

        # Template selection
        templates = list(st.session_state.tool_templates.keys())
        templates.insert(0, "Custom Tool")
        selected_template = st.selectbox(
            "Choose a template or create custom", templates
        )

        # Start with empty tool or selected template
        if selected_template == "Custom Tool":
            tool_data = {
                "type": "function",
                "function": {
                    "name": "",
                    "description": "",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }
        else:
            tool_data = st.session_state.tool_templates[selected_template].copy()

        # Check if we're editing an existing tool
        editing_existing = st.session_state.selected_tool is not None
        if editing_existing:
            for tool in st.session_state.tools:
                if tool["id"] == st.session_state.selected_tool:
                    tool_data = tool["definition"].copy()
                    break

        # Tool form
        with st.form("tool_editor_form"):
            # Basic tool information
            tool_data["function"]["name"] = st.text_input(
                "Function Name", value=tool_data["function"]["name"]
            )
            tool_data["function"]["description"] = st.text_area(
                "Description", value=tool_data["function"]["description"]
            )

            # Advanced mode toggle for direct JSON editing
            use_advanced_mode = st.checkbox("Advanced Mode (Edit JSON directly)")

            if use_advanced_mode:
                json_str = json.dumps(tool_data, indent=2)
                edited_json = st.text_area("Tool JSON", value=json_str, height=400)
                try:
                    tool_data = json.loads(edited_json)
                except json.JSONDecodeError:
                    st.error("Invalid JSON. Please check your syntax.")
            else:
                # Parameter editor
                st.subheader("Parameters")

                # Get existing parameters
                properties = tool_data["function"]["parameters"]["properties"]
                required_params = tool_data["function"]["parameters"].get(
                    "required", []
                )

                # Parameters UI
                num_params = st.number_input(
                    "Number of Parameters", min_value=0, value=len(properties), step=1
                )

                new_properties = {}
                new_required = []

                if num_params > 0:
                    for i in range(num_params):
                        st.markdown(f"### Parameter {i+1}")

                        # Get existing parameter if available
                        existing_param_name = (
                            list(properties.keys())[i] if i < len(properties) else ""
                        )
                        existing_param = properties.get(existing_param_name, {})

                        # Parameter details
                        param_name = st.text_input(
                            f"Name {i+1}",
                            value=existing_param_name,
                            key=f"param_name_{i}",
                        )
                        param_type = st.selectbox(
                            f"Type {i+1}",
                            ["string", "number", "boolean", "object", "array"],
                            index=[
                                "string",
                                "number",
                                "boolean",
                                "object",
                                "array",
                            ].index(existing_param.get("type", "string")),
                            key=f"param_type_{i}",
                        )
                        param_desc = st.text_input(
                            f"Description {i+1}",
                            value=existing_param.get("description", ""),
                            key=f"param_desc_{i}",
                        )
                        param_required = st.checkbox(
                            f"Required {i+1}",
                            value=existing_param_name in required_params,
                            key=f"param_required_{i}",
                        )

                        # Save parameter if it has a name
                        if param_name:
                            new_properties[param_name] = {
                                "type": param_type,
                                "description": param_desc,
                            }

                            if param_required:
                                new_required.append(param_name)

                # Update parameters in tool data
                tool_data["function"]["parameters"]["properties"] = new_properties
                tool_data["function"]["parameters"]["required"] = new_required

            # Form submission
            submit_label = "Update Tool" if editing_existing else "Create Tool"
            if st.form_submit_button(submit_label):
                if not tool_data["function"]["name"]:
                    st.error("Tool name is required")
                else:
                    if editing_existing:
                        self.update_tool(st.session_state.selected_tool, tool_data)
                        st.success(
                            f"Tool '{tool_data['function']['name']}' updated successfully"
                        )
                    else:
                        tool_id = self.add_tool(tool_data)
                        st.session_state.selected_tool = tool_id
                        st.success(
                            f"Tool '{tool_data['function']['name']}' created successfully"
                        )

                    # Rerun to update the UI
                    st.rerun()

    def render_tool_list(self):
        """Render the list of available tools"""
        st.subheader("Your Tools")

        if not st.session_state.tools:
            st.info(
                "You haven't created any tools yet. Use the tool editor to create one."
            )
            return

        for tool in st.session_state.tools:
            tool_name = tool["definition"]["function"]["name"]
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(
                    f"**{tool_name}**: {tool['definition']['function']['description']}"
                )

            with col2:
                if st.button("Edit", key=f"edit_{tool['id']}"):
                    st.session_state.selected_tool = tool["id"]
                    st.rerun()

            with col3:
                if st.button("Delete", key=f"delete_{tool['id']}"):
                    self.delete_tool(tool["id"])
                    st.rerun()

            st.markdown("---")

    def render_tool_export(self):
        """Render the tool export section"""
        st.subheader("Export Tools")

        if not st.session_state.tools:
            st.info("Create some tools before exporting")
            return

        # Selection method
        selection_method = st.radio(
            "Select tools to export", ["All Tools", "Select Specific Tools"]
        )

        tools_to_export = []

        if selection_method == "All Tools":
            tools_to_export = [tool["definition"] for tool in st.session_state.tools]
        else:
            # Create checkboxes for each tool
            selected_tools = []
            for tool in st.session_state.tools:
                tool_name = tool["definition"]["function"]["name"]
                if st.checkbox(tool_name, key=f"export_{tool['id']}"):
                    selected_tools.append(tool["definition"])

            tools_to_export = selected_tools

        if tools_to_export:
            # Format options
            export_format = st.selectbox("Export Format", ["JSON", "Copy to Clipboard"])

            if export_format == "JSON":
                json_str = json.dumps(tools_to_export, indent=2)
                st.code(json_str, language="json")

                # Download button
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name="ollama_tools.json",
                    mime="application/json",
                )
            else:
                json_str = json.dumps(tools_to_export)
                st.code(json_str, language="json")
                # Note: Actual clipboard functionality requires JavaScript,
                # which is limited in Streamlit. Users will need to manually copy

    def render_integration_help(self):
        """Render help section for integrating tools with Ollama"""
        with st.expander("How to Use Tools with Ollama"):
            st.markdown(
                """
            ### Using Tools with Ollama

            Tools allow you to extend the capabilities of language models by enabling them to call external functions.

            #### Python Example:
            ```python
            import ollama
            import json

            # Load your tools from file
            with open('ollama_tools.json', 'r') as f:
                tools = json.load(f)

            # Set up a conversation with tools
            response = ollama.chat(
                model='llama3',
                messages=[
                    {'role': 'user', 'content': 'What is the weather in New York?'}
                ],
                tools=tools,
                tool_choice='auto'  # Let the model decide when to use tools
            )

            print(response['message']['content'])

            # Handle function calls if any
            if 'tool_calls' in response['message']:
                for tool_call in response['message']['tool_calls']:
                    function_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])

                    # Execute the appropriate function based on function_name
                    # ...

                    # Then send the function result back
                    function_response = "Result from function call"

                    ollama.chat(
                        model='llama3',
                        messages=[
                            {'role': 'user', 'content': 'What is the weather in New York?'},
                            response['message'],
                            {
                                'role': 'tool',
                                'tool_call_id': tool_call['id'],
                                'name': function_name,
                                'content': function_response
                            }
                        ]
                    )
            ```

            #### Important Notes:

            1. Not all models support tool use, particularly older ones.
            2. You need to implement the actual function logic separately.
            3. The model decides when to use tools based on the conversation.
            """
            )

    def render(self):
        """Render the tools page"""
        st.title("LLM Tools Generator")
        st.write(
            "Create and manage tools that can be used with Ollama models to extend their capabilities."
        )

        # Layout with tabs
        tab1, tab2, tab3 = st.tabs(["Tool Editor", "Your Tools", "Export"])

        with tab1:
            self.render_tool_editor()
            self.render_integration_help()

        with tab2:
            self.render_tool_list()

        with tab3:
            self.render_tool_export()
