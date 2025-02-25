"""
Helper functions for API operations
"""

from typing import Dict, List, Any, Optional, Callable, Generator, Union
import streamlit as st
from app.utils.logger import get_logger, exception_handler, ErrorHandler


# Get application logger
logger = get_logger()


@exception_handler
def safe_api_call(func: Callable, *args, **kwargs) -> Any:
    """
    Safely call an API function with error handling

    Args:
        func: The API function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the API call, or None if an error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"API call failed: {str(e)}", exc_info=True)
        st.error(f"API call failed: {str(e)}")
        return None


def handle_streaming_response(
    generator: Generator,
    callback: Callable[[Dict[str, Any]], None],
    error_handler: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Handle a streaming API response

    Args:
        generator: The generator yielding API responses
        callback: Function to call for each response chunk
        error_handler: Optional function to call if an error occurs
    """
    try:
        for chunk in generator:
            if "error" in chunk:
                if error_handler:
                    error_handler(chunk["error"])
                else:
                    logger.error(f"API stream error: {chunk['error']}")
                    st.error(f"Error: {chunk['error']}")
                break

            callback(chunk)
    except Exception as e:
        logger.error(f"Error handling streaming response: {str(e)}", exc_info=True)
        st.error(f"Error: {str(e)}")


def parse_model_response(response: Union[Dict[str, Any], List[Dict[str, Any]]]) -> str:
    """
    Parse a model response to extract the content

    Args:
        response: The model response dictionary or list of response chunks

    Returns:
        The extracted content as a string
    """
    # For streaming responses that have been accumulated
    if isinstance(response, list) and len(response) > 0:
        # Try to extract from the last message
        last_msg = response[len(response) - 1]
        if isinstance(last_msg, dict):
            if "message" in last_msg and "content" in last_msg["message"]:
                return last_msg["message"]["content"]

    # For single response objects
    if isinstance(response, dict):
        # Check for OpenAI-like response format
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"]

        # Check for completion-like response format
        if "response" in response:
            return response["response"]

    # Return empty string if we couldn't extract content
    logger.warning(f"Could not parse model response: {response}")
    return ""


def format_model_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format model parameters for API calls, removing None values and defaults

    Args:
        parameters: Dictionary of parameters

    Returns:
        Cleaned up parameters dictionary
    """
    # Default parameter values to exclude if not changed
    defaults = {
        "temperature": 0.7,
        "top_p": 1.0,
        "stream": True,
    }

    # Filter out None values and defaults
    return {
        k: v
        for k, v in parameters.items()
        if v is not None and (k not in defaults or v != defaults[k])
    }
