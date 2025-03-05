import os
import glob
from typing import Dict, Any, Optional


def glob_tool(
    pattern: str, path: Optional[str] = None, limit: int = 100, offset: int = 0
) -> Dict[str, Any]:
    """
    Searches for files matching a glob pattern.

    Args:
        pattern (str): The glob pattern to match files against.
        path (str, optional): The directory to search in. Defaults to the current working directory.
        limit (int, optional): The maximum number of files to return. Defaults to 100.
        offset (int, optional): The offset to start from. Defaults to 0.

    Returns:
        Dict[str, Any]: A dictionary containing the list of filenames or an error message.
    """
    try:
        if path is None:
            search_path = "."  # Current working directory
        else:
            search_path = path

        # Expand the glob pattern relative to the search path
        full_pattern = os.path.join(search_path, pattern)

        # Use glob to find files matching the pattern
        files = glob.glob(full_pattern, recursive=True)

        # Apply limit and offset
        truncated = False
        if offset + limit < len(files):
            truncated = True  # Flag to indicate that the file list was truncated

        files = files[offset : offset + limit]

        return {
            "filenames": files,
            "num_files": len(files),
            "truncated": truncated,  # Add the truncated key to return the results to indicate that there might be more results
        }

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = glob_tool(pattern="*.py", path="/path/to/your/directory", limit=5, offset=0)
# print(result)
