"""Utility for loading tool implementations from the tools directory."""

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ToolLoader:
    """Utility for loading and managing tool implementations."""

    @staticmethod
    def get_tools_dir() -> str:
        """Get the absolute path to the tools directory."""
        app_dir = Path(__file__).resolve().parents[1]
        tools_dir = app_dir / "tools"
        return str(tools_dir)

    @staticmethod
    def ensure_tools_dir_exists() -> None:
        """Ensure the tools directory exists."""
        tools_dir = Path(ToolLoader.get_tools_dir())
        if not tools_dir.exists():
            tools_dir.mkdir(parents=True)
            # Create an __init__.py file to make it a proper Python package
            init_file = tools_dir / "__init__.py"
            init_file.write_text('"""Tools package for Ollama UI."""\n')

    @staticmethod
    def save_tool_implementation(tool_name: str, code: str) -> str:
        """
        Save a tool implementation to the tools directory.

        Args:
            tool_name: Name of the tool
            code: Python code implementing the tool

        Returns:
            Path to the saved file
        """
        ToolLoader.ensure_tools_dir_exists()
        tools_dir = Path(ToolLoader.get_tools_dir())

        # Sanitize tool name for filename
        sanitized_name = "".join(c if c.isalnum() else "_" for c in tool_name)
        file_path = tools_dir / f"{sanitized_name}.py"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

        logger.info("Saved tool implementation to %s", file_path)
        return str(file_path)

    @staticmethod
    def get_tool_implementation(tool_name: str) -> Optional[str]:
        """
        Get the source code of a tool implementation.

        Args:
            tool_name: Name of the tool

        Returns:
            Source code of the tool implementation or None if not found
        """
        ToolLoader.ensure_tools_dir_exists()
        tools_dir = Path(ToolLoader.get_tools_dir())

        # Sanitize tool name for filename
        sanitized_name = "".join(c if c.isalnum() else "_" for c in tool_name)
        file_path = tools_dir / f"{sanitized_name}.py"

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error("Error reading tool implementation %s: %s", file_path, str(e))
                return None
        else:
            logger.warning("Tool implementation file not found: %s", file_path)
            return None

    @staticmethod
    def save_tool_definition(tool_name: str, tool_definition: Dict[str, Any]) -> str:
        """
        Save a tool definition to the tools directory.

        Args:
            tool_name: Name of the tool
            tool_definition: JSON definition of the tool

        Returns:
            Path to the saved file
        """
        ToolLoader.ensure_tools_dir_exists()
        tools_dir = Path(ToolLoader.get_tools_dir())

        # Sanitize tool name for filename
        sanitized_name = "".join(c if c.isalnum() else "_" for c in tool_name)
        file_path = tools_dir / f"{sanitized_name}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tool_definition, f, indent=2)

        logger.info("Saved tool definition to %s", file_path)
        return str(file_path)

    @staticmethod
    def list_available_tools() -> List[str]:
        """
        List all available tool implementations.

        Returns:
            List of tool names
        """
        ToolLoader.ensure_tools_dir_exists()
        tools_dir = Path(ToolLoader.get_tools_dir())

        tool_files = [
            path.stem
            for path in tools_dir.glob("*.py")
            if path.name != "__init__.py"
        ]

        return tool_files

    @staticmethod
    def load_tool_function(
        tool_name: str,
    ) -> Tuple[Optional[Callable], Optional[Dict[str, Any]]]:
        """
        Load a tool function from a Python file.

        Args:
            tool_name: Name of the tool

        Returns:
            Tuple of (function, definition) or (None, None) if not found
        """
        ToolLoader.ensure_tools_dir_exists()
        tools_dir = Path(ToolLoader.get_tools_dir())

        # Sanitize tool name for filename
        sanitized_name = "".join(c if c.isalnum() else "_" for c in tool_name)
        py_file = tools_dir / f"{sanitized_name}.py"
        json_file = tools_dir / f"{sanitized_name}.json"

        # Check if files exist
        if not py_file.exists():
            logger.warning("Tool implementation file not found: %s", py_file)
            return None, None

        # Load the definition if it exists
        definition = None
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    definition = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in tool definition: %s", json_file)

        # Add the tools directory to the Python path if it's not already there
        if str(tools_dir) not in sys.path:
            sys.path.append(str(tools_dir.parent))  # Add app directory

        try:
            # Import the module dynamically
            module_name = f"app.tools.{sanitized_name}"

            # First, try to import directly
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                # If that fails, try to reload if it's already imported
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    # Try importing with just the filename
                    module = importlib.import_module(sanitized_name)

            # Find the function either by name from definition or first defined function
            function = None

            if (
                definition
                and "function" in definition
                and "name" in definition["function"]
            ):
                function_name = definition["function"]["name"]
                if hasattr(module, function_name):
                    function = getattr(module, function_name)
                    if callable(function):
                        return function, definition

            # If function not found by name, try to find the first defined function
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if name != "__init__":
                    function = obj

                    # If no definition exists, generate one based on function metadata
                    if not definition:
                        from app.api.ollama_api import OllamaAPI

                        definition = OllamaAPI._function_to_tool_definition(function)

                    return function, definition

            logger.error(f"No suitable function found in module: {module_name}")
            return None, None

        except Exception as e:
            logger.error(f"Error loading tool {tool_name}: {str(e)}", exc_info=True)
            return None, None

    @staticmethod
    def load_all_tools() -> List[Union[Dict[str, Any], Callable]]:
        """
        Load all available tools.

        Returns:
            List of tool definitions or function references
        """
        tool_names = ToolLoader.list_available_tools()
        tools = []

        for name in tool_names:
            function, definition = ToolLoader.load_tool_function(name)
            if function:
                # Return the function directly for the new tool calling style
                tools.append(function)
            elif definition:
                # Fall back to definition if function couldn't be loaded
                tools.append(definition)

        return tools

    @staticmethod
    def load_all_tool_functions() -> Dict[str, Callable]:
        """
        Load all available tool functions as a dictionary of function references.

        Returns:
            Dictionary of function name to function reference
        """
        tool_names = ToolLoader.list_available_tools()
        function_map = {}

        for name in tool_names:
            function, definition = ToolLoader.load_tool_function(name)
            if function:
                function_name = function.__name__
                function_map[function_name] = function

        return function_map

    @staticmethod
    def execute_tool(tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a tool function with the given arguments.

        Args:
            tool_name: Name of the tool
            args: Arguments to pass to the tool function

        Returns:
            Result of the tool execution
        """
        function, _ = ToolLoader.load_tool_function(tool_name)
        if function:
            try:
                result = function(**args)
                return result
            except Exception as e:
                logger.error(
                    f"Error executing tool {tool_name}: {str(e)}", exc_info=True
                )
                return {"error": str(e)}
        else:
            return {"error": f"Tool {tool_name} not found or could not be loaded"}
