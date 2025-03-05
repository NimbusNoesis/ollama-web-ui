file_read_tool_prompt = """
Reads a file from the local filesystem. The file_path parameter must be an absolute path, not a relative path.
By default, it reads the entire file. You can optionally specify a line offset and limit (especially handy for long files).
"""

glob_tool_prompt = """
Searches for files matching a glob pattern. Supports patterns like "**/*.py" or "src/**/*.txt".
Returns a list of matching file paths. Use this tool when you need to find files by name patterns.
"""

grep_tool_prompt = """
Searches file contents using regular expressions. Supports full regex syntax (e.g., "log.*Error").
Filter files by pattern with the include parameter (e.g., "*.js", "*.{ts,tsx}").
Returns matching file paths. Use this tool when you need to find files containing specific patterns.
"""

bash_tool_prompt = """
Executes a given bash command with an optional timeout.
Ensure proper quoting and handling of shell metacharacters.
Avoid using search commands like `find` and read tools like `cat`. Use glob and grep instead.
"""

memory_read_tool_prompt = """
Reads from memory. If file_path is provided, reads that specific file.
Otherwise, returns a list of files in memory and the content of the 'index.md' file.
"""

memory_write_tool_prompt = """
Writes to memory. The file is saved relative to the memory directory.
"""

file_write_tool_prompt = """
Writes content to a file. Overwrites the file if it exists. The file_path parameter must be an absolute path not a relative path.
"""

file_edit_tool_prompt = """
Replaces a string in a file with another string. The file_path parameter must be an absolute path, not a relative path.
The tool will replace ONE occurrence of old_string with new_string in the specified file.
The old_string MUST uniquely identify the specific instance you want to change.
"""

think_tool_prompt = """
Logs a thought. This tool doesn't perform any action but records the thought.
"""

ls_tool_prompt = """
Lists files and directories in a given path.
The path parameter must be an absolute path, not a relative path.
"""

sticker_request_tool_prompt = """
This tool should be used whenever a user expresses interest in receiving stickers.
It simulates displaying a shipping form for the user to enter their mailing address and contact details.
Please tell the user that they will receive stickers in the mail.
"""

# Example Usage:
# print(file_read_tool_prompt)