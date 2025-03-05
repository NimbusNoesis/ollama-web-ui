import os
import subprocess
import json
from typing import Dict, Any, List


def ls_tool(path: str = None) -> Dict[str, Any]:
    """
    Lists files and directories in a given path.

    Args:
        path (str, optional): The absolute path to the directory to list. Defaults to the current working directory.

    Returns:
        Dict[str, Any]: A dictionary containing the list of files and directories or an error message.
    """
    try:
        if path is None:
            search_path = "."  # Current working directory
        else:
            search_path = path

        # Check path exists
        if not os.path.exists(search_path):
            return {"error": f"Path '{search_path}' does not exist."}

        # Check if path is a directory
        if not os.path.isdir(search_path):
            return {"error": f"Path '{search_path}' is not a directory."}

        files = os.listdir(search_path)
        # Remove hidden files and directories
        files = [f for f in files if not f.startswith(".")]

        return {"files": files, "num_files": len(files)}

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = ls_tool(path="/path/to/your/directory")
# print(result)
