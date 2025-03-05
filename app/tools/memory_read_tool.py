import os
from typing import Dict, Any, Optional

# Assuming a simple file-based memory implementation

MEMORY_DIR = "memory"  # Define a directory to store memory files


def memory_read_tool(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Reads from memory. If file_path is provided, reads that specific file.
    Otherwise, returns a list of files in memory and the content of the 'index.md' file.

    Args:
        file_path (str, optional): The path to a specific memory file to read. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the content or an error message.
    """
    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)  # Ensure memory directory exists

        if file_path:
            full_path = os.path.join(MEMORY_DIR, file_path)
            if not os.path.exists(full_path):
                return {"error": "Memory file does not exist."}

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return {"content": content}
        else:
            # List files in memory directory and return the content of 'index.md'
            files = [
                f"- {f}"
                for f in os.listdir(MEMORY_DIR)
                if os.path.isfile(os.path.join(MEMORY_DIR, f))
            ]
            index_path = os.path.join(MEMORY_DIR, "index.md")
            index_content = ""

            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    index_content = f.read()

            quotes = "'''"
            content = f"Here are the contents of the root memory file, `{index_path}`: {quotes} {index_content} {quotes} Files in the memory directory: {' '.join(files)}"
            return {"content": content}

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = memory_read_tool(file_path="my_note.txt")
# print(result)
