import os
import json
from typing import Dict, Any

# Assuming a simple file-based memory implementation

MEMORY_DIR = "memory"  # Define a directory to store memory files


def memory_write_tool(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes to memory.

    Args:
        file_path (str): The path to the memory file to write (relative to the memory directory).
        content (str): The content to write to the file.

    Returns:
        Dict[str, Any]: A dictionary containing a success message or an error message.
    """
    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)  # Ensure memory directory exists
        full_path = os.path.join(MEMORY_DIR, file_path)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {"result": "Memory file saved successfully."}

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = memory_write_tool(file_path="my_note.txt", content="This is a test note.")
# print(result)
