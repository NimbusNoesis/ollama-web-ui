import os
from typing import Dict, Any, Optional


def file_read_tool(
    file_path: str, offset: int = 1, limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Reads a file from the local filesystem, with optional offset and limit.

    Args:
        file_path (str): The absolute path to the file to read.
        offset (int, optional): The line number to start reading from (1-indexed). Defaults to 1.
        limit (int, optional): The number of lines to read. Defaults to reading the entire file.

    Returns:
        Dict[str, Any]: A dictionary containing the file content or an error message.
    """
    try:
        if not os.path.isabs(file_path):
            return {"error": "File path must be absolute."}

        if not os.path.exists(file_path):
            return {"error": "File does not exist."}

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_line = offset - 1  # Convert to 0-indexed line number
        if start_line < 0:
            start_line = 0  # Ensure start_line is not negative

        if limit is None:
            end_line = len(lines)
        else:
            end_line = start_line + limit

        if start_line >= len(lines):
            return {
                "content": "",
                "num_lines": 0,
                "start_line": offset,
                "total_lines": len(lines),
            }  # Empty content if offset is beyond the file's end

        selected_lines = lines[start_line:end_line]
        content = "".join(selected_lines)

        return {
            "content": content,
            "num_lines": len(selected_lines),
            "start_line": offset,
            "total_lines": len(lines),
        }

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = file_read_tool(file_path="/path/to/your/file.txt", offset=5, limit=10)
# print(result)
