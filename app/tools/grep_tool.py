import subprocess
from typing import Dict, Any, Optional


def grep_tool(
    pattern: str, path: Optional[str] = None, include: Optional[str] = None
) -> Dict[str, Any]:
    """
    Searches for files containing a specific pattern using grep.

    Args:
        pattern (str): The regular expression pattern to search for.
        path (str, optional): The directory to search in. Defaults to the current working directory.
        include (str, optional): File pattern to include in the search (e.g., "*.js", "*.{ts,tsx}").

    Returns:
        Dict[str, Any]: A dictionary containing the list of filenames or an error message.
    """
    try:
        if path is None:
            search_path = "."  # Current working directory
        else:
            search_path = path

        command = ["grep", "-l", "-i", "-r", pattern, search_path]

        if include:
            command.extend(["--include", include])

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if stderr:
            return {"error": stderr.decode("utf-8")}  # Return any errors

        filenames = stdout.decode("utf-8").strip().split("\n")
        filenames = [f for f in filenames if f]  # Remove empty strings

        return {"filenames": filenames, "num_files": len(filenames)}

    except FileNotFoundError:
        return {
            "error": "Grep command not found. Please ensure it is installed and in your system's PATH."
        }
    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = grep_tool(pattern="your_pattern", path="/path/to/your/directory", include="*.txt")
# print(result)
