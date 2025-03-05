import os
import json
from typing import Dict, Any
import subprocess


def file_edit_tool(file_path: str, old_string: str, new_string: str) -> Dict[str, Any]:
    """
    Replaces a string in a file with another string.

    Args:
        file_path (str): The absolute path to the file to modify.
        old_string (str): The string to replace.
        new_string (str): The string to replace it with.

    Returns:
        Dict[str, Any]: A dictionary containing a success message, the path, and structured patch.
    """
    try:
        if not os.path.isabs(file_path):
            return {"error": "File path must be absolute."}

        if not os.path.exists(file_path):
            return {"error": "File does not exist."}

        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        if old_string not in file_content:
            return {"error": "String to replace not found in file."}

        new_content = file_content.replace(
            old_string, new_string, 1
        )  # Replace only the first occurrence.

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Generate a structured patch using diff command
        try:
            # Create temporary files for diff
            with open("temp_old_file.txt", "w", encoding="utf-8") as temp_old:
                temp_old.write(file_content)
            with open("temp_new_file.txt", "w", encoding="utf-8") as temp_new:
                temp_new.write(new_content)

            # Run diff command
            diff_command = ["diff", "-u", "temp_old_file.txt", "temp_new_file.txt"]
            diff_process = subprocess.Popen(
                diff_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            diff_output, diff_error = diff_process.communicate()

            if diff_error:
                return {"error": f"Error generating diff: {diff_error.decode('utf-8')}"}

            diff_str = diff_output.decode("utf-8")

        finally:
            # Cleanup - remove temporary files
            if os.path.exists("temp_old_file.txt"):
                os.remove("temp_old_file.txt")
            if os.path.exists("temp_new_file.txt"):
                os.remove("temp_new_file.txt")

        return {
            "file_path": file_path,
            "result": "File edited successfully.",
            "structured_patch": diff_str,
        }

    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = file_edit_tool(file_path="/path/to/your/file.txt", old_string="old content", new_string="new content")
# print(result)
