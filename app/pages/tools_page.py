import json
import uuid
import tempfile
import os
import subprocess
from typing import Any, Dict, List

import streamlit as st
from pygments import highlight
from pygments.lexers.python import PythonLexer
from pygments.formatters.html import HtmlFormatter

# Import streamlit_code_editor
from code_editor import code_editor

from app.utils.logger import get_logger
from app.utils.tool_loader import ToolLoader

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

        # Add session state for edited code
        if "edited_code" not in st.session_state:
            st.session_state.edited_code = {}

        # Add session state for lint results
        if "lint_results" not in st.session_state:
            st.session_state.lint_results = {}

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

    def render_combined_tools_list(self):
        """Render installed tools"""
        st.subheader("Your Tools")

        # Get list of installed tools
        installed_tools = ToolLoader.list_available_tools()

        if not installed_tools:
            st.info(
                "No tools are currently installed. Generate and install tools to use them in chats."
            )
        else:
            st.write(
                "The following tools are installed and available for use in chats:"
            )

            for tool_name in installed_tools:
                function, definition = ToolLoader.load_tool_function(tool_name)

                if definition:
                    with st.expander(
                        f"{tool_name}: {definition['function']['description']}"
                    ):
                        st.json(definition)

                        # Add test section
                        st.subheader("Test Tool")
                        parameters = {}
                        properties = definition["function"]["parameters"]["properties"]
                        required = definition["function"]["parameters"].get(
                            "required", []
                        )

                        # Create input fields for each parameter
                        for param_name, param_info in properties.items():
                            param_type = param_info.get("type", "string")
                            param_desc = param_info.get("description", "")

                            if param_type == "string":
                                parameters[param_name] = st.text_input(
                                    f"{param_name} ({param_desc})",
                                    key=f"param_{tool_name}_{param_name}",
                                )
                            elif param_type == "number" or param_type == "integer":
                                parameters[param_name] = st.number_input(
                                    f"{param_name} ({param_desc})",
                                    key=f"param_{tool_name}_{param_name}",
                                )
                            elif param_type == "boolean":
                                parameters[param_name] = st.checkbox(
                                    f"{param_name} ({param_desc})",
                                    key=f"param_{tool_name}_{param_name}",
                                )

                        # Execute button outside of a form
                        if st.button("Execute Tool", key=f"execute_{tool_name}"):
                            # Validate required parameters
                            missing_params = [
                                p for p in required if not parameters.get(p)
                            ]
                            if missing_params:
                                st.error(
                                    f"Missing required parameters: {', '.join(missing_params)}"
                                )
                            else:
                                # Execute the tool
                                with st.spinner("Executing tool..."):
                                    result = ToolLoader.execute_tool(
                                        tool_name, parameters
                                    )
                                st.write("Result:")
                                st.json(result)
                else:
                    st.warning(f"Tool definition for {tool_name} could not be loaded.")

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

    def generate_tool_implementation(self, tool_data: Dict[str, Any]) -> str:
        """
        Generate Python code implementation for a tool

        Args:
            tool_data: The tool definition data

        Returns:
            Python code implementing the tool function
        """
        function_name = tool_data["function"]["name"]
        description = tool_data["function"]["description"]
        parameters = tool_data["function"]["parameters"]["properties"]
        required_params = tool_data["function"]["parameters"].get("required", [])

        # Start building the function
        code = f"def {function_name}("

        # Add parameters
        param_list = []
        for param_name, param_info in parameters.items():
            param_type = param_info.get("type", "Any")

            # Map JSON schema types to Python types
            type_mapping = {
                "string": "str",
                "number": "float",
                "integer": "int",
                "boolean": "bool",
                "array": "List[Any]",
                "object": "Dict[str, Any]",
            }

            python_type = type_mapping.get(param_type, "Any")

            # Add default value None for optional parameters
            if param_name in required_params:
                param_list.append(f"{param_name}: {python_type}")
            else:
                param_list.append(f"{param_name}: Optional[{python_type}] = None")

        code += ", ".join(param_list) + ") -> Any:\n"

        # Add docstring
        code += f'    """{description}\n\n'
        code += f"    Args:\n"
        for param_name, param_info in parameters.items():
            param_desc = param_info.get("description", "")
            code += f"        {param_name}: {param_desc}\n"

        code += '\n    Returns:\n        Result of the tool execution\n    """\n'

        # Add placeholder implementation
        code += "    # TODO: Implement the actual tool functionality\n"

        # Basic implementation based on parameter types
        code += "    try:\n"

        # Add parameter validation for required parameters
        for param_name in required_params:
            code += f"        if {param_name} is None:\n"
            code += f'            raise ValueError(f"{param_name} is required")\n'

        # Add placeholder implementation based on tool type
        if function_name == "web_search":
            code += """        # Example implementation using requests
        import requests

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(
            f"https://api.search.example.com?q={query}",
            headers=headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Search failed with status code {response.status_code}"}
"""
        elif function_name == "calculator":
            code += """        # Example implementation
        import ast
        import operator
        import math

        # Define safe operations
        safe_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.BitXor: operator.xor,
            ast.USub: operator.neg,
            ast.Mod: operator.mod,
        }

        # Define allowed constants
        math_constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
        }

        def safe_eval(expr):
            return eval_(ast.parse(expr, mode='eval').body)

        def eval_(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id in math_constants:
                    return math_constants[node.id]
                raise ValueError(f"Unknown variable: {node.id}")
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type not in safe_operators:
                    raise ValueError(f"Unsupported operation: {node.op.__class__.__name__}")
                return safe_operators[op_type](eval_(node.left), eval_(node.right))
            elif isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type not in safe_operators:
                    raise ValueError(f"Unsupported operation: {node.op.__class__.__name__}")
                return safe_operators[op_type](eval_(node.operand))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                func_name = node.func.id
                if not hasattr(math, func_name):
                    raise ValueError(f"Unknown math function: {func_name}")

                args = [eval_(arg) for arg in node.args]
                return getattr(math, func_name)(*args)
            else:
                raise ValueError(f"Unsupported expression type: {type(node).__name__}")

        result = safe_eval(expression)
        return {"result": result}
"""
        elif function_name == "get_weather":
            code += """        # Example implementation using a weather API
        import requests

        api_key = "YOUR_WEATHER_API_KEY"  # Replace with actual API key
        units_param = "metric" if units == "celsius" else "imperial"

        url = f"https://api.weather.example.com/data/2.5/weather?q={location}&units={units_param}&appid={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            return {
                "location": location,
                "temperature": data["main"]["temp"],
                "conditions": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"]
            }
        else:
            return {"error": f"Failed to get weather data: {response.status_code}"}
"""
        else:
            # Generic implementation for other tool types
            code += """        # Implement your tool logic here
        # This is a placeholder implementation
        result = {
            "status": "success",
            "message": "Tool executed successfully",
            "data": {
"""
            # Add parameters as part of the result
            for param_name in parameters.keys():
                code += f'                "{param_name}": {param_name},\n'

            code += """            }
        }
        return result
"""

        # Add exception handling
        code += """    except Exception as e:
        # Handle exceptions appropriately
        return {"error": str(e)}
"""

        # Add usage example
        code += "\n\n# Example usage:\n"
        example_args = []
        for param_name, param_info in parameters.items():
            param_type = param_info.get("type", "")

            if param_type == "string":
                example_args.append(f'{param_name}="example"')
            elif param_type == "number" or param_type == "integer":
                example_args.append(f"{param_name}=123")
            elif param_type == "boolean":
                example_args.append(f"{param_name}=True")
            elif param_type == "array":
                example_args.append(f'{param_name}=["item1", "item2"]')
            elif param_type == "object":
                example_args.append(f'{param_name}={{"key": "value"}}')
            else:
                example_args.append(f'{param_name}="value"')

        code += f"# result = {function_name}({', '.join(example_args)})\n"

        return code

    def run_pylint(self, code: str) -> List[Dict[str, Any]]:
        """
        Run pylint on the provided code and return the results

        Args:
            code: Python code to lint

        Returns:
            List of lint issues found
        """
        if not code:
            return []

        try:
            # Create a temporary file to store the code
            with tempfile.NamedTemporaryFile(
                suffix=".py", delete=False, mode="w", encoding="utf-8"
            ) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name

            # Run pylint on the temporary file
            try:
                result = subprocess.run(
                    ["pylint", "--output-format=json", temp_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Parse the JSON output if available
                if result.stdout:
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse pylint output: {result.stdout}")
                        return []
                return []
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.error(f"Failed to remove temporary file: {e}")
        except Exception as e:
            logger.error(f"Error running pylint: {e}")
            return []

    def highlight_python_code(self, code: str) -> str:
        """
        Highlight Python code using pygments

        Args:
            code: Python code to highlight

        Returns:
            HTML with highlighted code
        """
        if not code:
            return ""

        formatter = HtmlFormatter(style="colorful")
        highlighted_code = highlight(code, PythonLexer(), formatter)

        # Add the CSS for syntax highlighting
        css = formatter.get_style_defs()
        highlighted_html = f"""
        <style>{css}</style>
        {highlighted_code}
        """

        return highlighted_html

    def render_code_generator(self):
        """Render the code generator section"""
        st.subheader("Tool Implementation Generator")

        # Check both session state tools and installed tools
        installed_tools = ToolLoader.list_available_tools()

        # If there are no tools in session state and no installed tools, show info message
        if not st.session_state.tools and not installed_tools:
            st.info("Create some tools before generating implementation code")
            return

        # Tool selection
        tool_options = ["Select a tool..."]

        # Add tools from session state
        if st.session_state.tools:
            for tool in st.session_state.tools:
                tool_options.append(tool["definition"]["function"]["name"])

        # Add installed tools that are not in the current session
        for tool_name in installed_tools:
            if tool_name not in [
                tool["definition"]["function"]["name"]
                for tool in st.session_state.tools
            ]:
                tool_options.append(f"{tool_name} (installed)")

        selected_tool_name = st.selectbox(
            "Choose a tool to generate implementation for", tool_options
        )

        if selected_tool_name == "Select a tool...":
            st.info("Please select a tool to generate implementation code")
            return

        # Check if this is an installed tool
        is_installed_tool = False
        if " (installed)" in selected_tool_name:
            actual_tool_name = selected_tool_name.replace(" (installed)", "")
            is_installed_tool = True
        else:
            actual_tool_name = selected_tool_name

        # Find or load the selected tool data
        selected_tool_data = None

        if is_installed_tool:
            # Load the tool definition from the installed tool
            _, selected_tool_data = ToolLoader.load_tool_function(actual_tool_name)

            # Load the implementation if we haven't already
            if actual_tool_name not in st.session_state.edited_code:
                tool_code = ToolLoader.get_tool_implementation(actual_tool_name)
                if tool_code:
                    st.session_state.edited_code[actual_tool_name] = tool_code
                    selected_tool_name = actual_tool_name
        else:
            # Find the tool in the session state
            for tool in st.session_state.tools:
                if tool["definition"]["function"]["name"] == actual_tool_name:
                    selected_tool_data = tool["definition"]
                    break

        if selected_tool_data:
            # Generate the implementation code if not already in session state
            if actual_tool_name not in st.session_state.edited_code:
                st.session_state.edited_code[actual_tool_name] = (
                    self.generate_tool_implementation(selected_tool_data)
                )

            col1, col2 = st.columns([1, 3])

            with col1:
                # Add a "Regenerate Code" button to start fresh
                if st.button("Regenerate Code"):
                    st.session_state.edited_code[actual_tool_name] = (
                        self.generate_tool_implementation(selected_tool_data)
                    )
                    # Clear any lint results
                    st.session_state.lint_results[actual_tool_name] = []
                    st.rerun()

            with col2:
                # Display lint results if any
                lint_results = st.session_state.lint_results.get(actual_tool_name, [])
                if lint_results:
                    with st.expander("Lint Results", expanded=True):
                        for issue in lint_results:
                            message_type = issue.get("type", "unknown")
                            line = issue.get("line", 0)
                            message = issue.get("message", "")

                            if message_type == "convention":
                                st.info(f"Line {line}: {message}")
                            elif message_type in ["error", "fatal"]:
                                st.error(f"Line {line}: {message}")
                            elif message_type == "warning":
                                st.warning(f"Line {line}: {message}")
                            else:
                                st.write(f"Line {line}: {message}")

            # Create tabs for editor and highlighted view
            editor_tabs = st.tabs(["Code Editor"])

            with editor_tabs[0]:  # Access the first tab in the list
                # Live code editor
                st.subheader("Edit Implementation")

                # Use a form for the code editor to prevent reloading on every keystroke
                with st.form(key=f"code_form_{actual_tool_name}"):
                    edited_code = code_editor(
                        st.session_state.edited_code.get(actual_tool_name, "")
                    )

                    update_button = st.form_submit_button("Update Code")

                    if update_button:
                        st.session_state.edited_code[actual_tool_name] = edited_code
                        st.success("Code updated successfully!")

            # Syntax validation indicator
            try:
                # Try to compile the code to check for syntax errors
                code_to_check = st.session_state.edited_code.get(actual_tool_name, "")
                if code_to_check:
                    compile(code_to_check, "<string>", "exec")
                    st.success("✓ Code syntax valid")
                else:
                    st.error("Edited code cannot be None")
            except SyntaxError as e:
                st.error(f"Syntax error: {str(e)}")

            # Add download button for the edited version
            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    label="Download Implementation",
                    data=st.session_state.edited_code.get(actual_tool_name, ""),
                    file_name=f"{actual_tool_name}_implementation.py",
                    mime="text/plain",
                )

            with col2:
                if st.button("Save Tool", key=f"install_{actual_tool_name}"):
                    # Try to validate the code first
                    try:
                        code_to_save = st.session_state.edited_code.get(
                            actual_tool_name, ""
                        )
                        if code_to_save:
                            compile(code_to_save, "<string>", "exec")

                        # Save the implementation to the tools directory
                        py_path = ToolLoader.save_tool_implementation(
                            actual_tool_name, code_to_save
                        )

                        # Save the definition to the tools directory
                        json_path = ToolLoader.save_tool_definition(
                            actual_tool_name, selected_tool_data
                        )

                        st.success(f"Installed tool to {py_path} and {json_path}")
                    except SyntaxError as e:
                        st.error(f"Cannot install due to syntax error: {str(e)}")

            # Show integration example
            with st.expander("How to Use This Implementation"):
                st.markdown(
                    f"""
                ### Using the {actual_tool_name} Tool

                1. Save the implementation to a Python file (e.g., `{actual_tool_name}.py`)
                2. Import the function in your code
                3. Use it with Ollama's tool calling feature

                ```python
                from {actual_tool_name} import {actual_tool_name}
                import ollama
                import json

                # Your tool definition
                tools = [{json.dumps(selected_tool_data, indent=2)}]

                # Chat with Ollama using the tool
                response = ollama.chat(
                    model='llama3',  # Use a model that supports tool calling
                    messages=[
                        {{'role': 'user', 'content': 'I need help with something that requires {actual_tool_name}'}}
                    ],
                    tools=tools,
                    tool_choice='auto'
                )

                # Handle tool calls from the model
                if 'tool_calls' in response['message']:
                    for tool_call in response['message']['tool_calls']:
                        if tool_call['function']['name'] == '{actual_tool_name}':
                            # Parse arguments
                            arguments = json.loads(tool_call['function']['arguments'])

                            # Execute the function with the provided arguments
                            result = {actual_tool_name}(**arguments)

                            # Send the result back to the model
                            ollama.chat(
                                model='llama3',
                                messages=[
                                    # Include previous messages...
                                    response['message'],
                                    {{
                                        'role': 'tool',
                                        'tool_call_id': tool_call['id'],
                                        'name': '{actual_tool_name}',
                                        'content': json.dumps(result)
                                    }}
                                ]
                            )
                ```
                """
                )

            # Add an option to test the code if applicable
            with st.expander("Test Code (Experimental)"):
                st.warning(
                    "This will attempt to execute the code in a controlled environment."
                )

                # Create input fields for parameters based on the tool definition
                parameters = {}
                properties = selected_tool_data["function"]["parameters"]["properties"]
                required = selected_tool_data["function"]["parameters"].get(
                    "required", []
                )

                # Create input fields for each parameter
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "string")
                    param_desc = param_info.get("description", "")

                    if param_type == "string":
                        parameters[param_name] = st.text_input(
                            f"{param_name} ({param_desc})",
                            key=f"test_param_{actual_tool_name}_{param_name}",
                        )
                    elif param_type == "number" or param_type == "integer":
                        parameters[param_name] = st.number_input(
                            f"{param_name} ({param_desc})",
                            key=f"test_param_{actual_tool_name}_{param_name}",
                        )
                    elif param_type == "boolean":
                        parameters[param_name] = st.checkbox(
                            f"{param_name} ({param_desc})",
                            key=f"test_param_{actual_tool_name}_{param_name}",
                        )

                # Test execution button
                if st.button("Test Function", key=f"test_exec_{actual_tool_name}"):
                    # Validate required parameters
                    missing_params = [p for p in required if not parameters.get(p)]
                    if missing_params:
                        st.error(
                            f"Missing required parameters: {', '.join(missing_params)}"
                        )
                    else:
                        st.info(
                            "This would execute the function with the provided parameters."
                        )
                        st.code(
                            f"{actual_tool_name}({', '.join([f'{k}={repr(v)}' for k, v in parameters.items()])})"
                        )
                        # Note: Actual execution would require a safe execution environment

    def render(self):
        """Render the tools page"""
        st.title("LLM Tools Generator")
        st.write(
            "Create and manage tools that can be used with Ollama models to extend their capabilities."
        )

        # Layout with tabs - merged Your Tools and Installed Tools into one tab
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Tool Editor", "Your Tools", "Code Generator", "Export"]
        )

        with tab1:
            self.render_tool_editor()
            self.render_integration_help()

        with tab2:
            self.render_combined_tools_list()

        with tab3:
            self.render_code_generator()

        with tab4:
            self.render_tool_export()
