import os
import json
from typing import Dict, Any
import subprocess


def file_write_tool(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a file. Overwrites the file if it exists.

    Args:
        file_path (str): The absolute path to the file to write.
        content (str): The content to write to the file.

    Returns:
        Dict[str, Any]: A dictionary containing a success message or an error message.
    """
    try:
        if not os.path.isabs(file_path):
            return {"error": "File path must be absolute."}

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"result": f"File written successfully to {file_path}"}

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = file_write_tool(file_path="/path/to/your/file.txt", content="New content")
# print(result)
