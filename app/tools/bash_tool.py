import subprocess
from typing import Dict, Any


def bash_tool(command: str, timeout: int = 120000) -> Dict[str, Any]:
    """
    Executes a bash command and returns the output.

    Args:
        command (str): The command to execute.
        timeout (int, optional): Timeout in milliseconds. Defaults to 120000 (2 minutes).

    Returns:
        Dict[str, Any]: A dictionary containing the stdout, stderr, and return code, or an error message.
    """
    process = None
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/bash",  # Specify bash explicitly
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = process.communicate(
            timeout=timeout / 1000
        )  # timeout in seconds

        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()
        return_code = process.returncode

        return {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "return_code": return_code,
        }
    except subprocess.TimeoutExpired:
        if process:
            process.kill()
        return {"error": "Command timed out."}
    except Exception as e:
        return {"error": str(e)}


# Example Usage:
# result = bash_tool(command="ls -l")
# print(result)
