import logging
import os
import sys
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

# Type variable for the decorator
F = TypeVar("F", bound=Callable[..., Any])

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure log file path with timestamp
LOG_FILENAME = f"ollama_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE_PATH = os.path.join(LOGS_DIR, LOG_FILENAME)

# Get log level from environment variable (default to INFO if not set)
LOG_LEVEL_ENV = os.environ.get("OLLAMA_UI_LOG_LEVEL", "INFO").upper()
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
LOG_LEVEL = LOG_LEVELS.get(LOG_LEVEL_ENV, logging.INFO)

# Configure logging
logger = logging.getLogger("ollama_ui")
logger.setLevel(LOG_LEVEL)

# Create file handler
file_handler = logging.FileHandler(LOG_FILE_PATH)
file_handler.setLevel(LOG_LEVEL)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(LOG_LEVEL)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Log the current configuration
logger.info(f"Logger initialized with level: {LOG_LEVEL_ENV}")
if LOG_LEVEL == logging.DEBUG:
    logger.debug("Debug logging is enabled")


def get_logger() -> logging.Logger:
    """Get the application logger"""
    return logger


def set_log_level(level: str) -> None:
    """
    Set the log level for the application logger

    Args:
        level: The log level to set (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_upper = level.upper()
    if level_upper in LOG_LEVELS:
        numeric_level = LOG_LEVELS[level_upper]
        logger.setLevel(numeric_level)
        for handler in logger.handlers:
            handler.setLevel(numeric_level)
        logger.info(f"Log level changed to: {level_upper}")
    else:
        logger.warning(f"Invalid log level: {level}. Using current level.")


def log_exception(e: Exception, context: str = "") -> str:
    """
    Log an exception with traceback and return a formatted error message

    Args:
        e: The exception to log
        context: Additional context about where the exception occurred

    Returns:
        A formatted error message
    """
    error_msg = f"{context}: {str(e)}" if context else str(e)
    logger.error(error_msg)
    logger.error(traceback.format_exc())
    return error_msg


def exception_handler(func: F) -> F:
    """
    Decorator to handle exceptions in functions

    Args:
        func: The function to decorate

    Returns:
        The decorated function
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get function name for context
            func_name = func.__qualname__
            # Log the exception
            error_msg = log_exception(e, f"Error in {func_name}")
            # Re-raise the exception with the logged message
            raise type(e)(error_msg) from e

    return cast(F, wrapper)


class ErrorHandler:
    """
    Class to handle errors in a standardized way across the application
    """

    @staticmethod
    def handle_error(
        e: Exception, context: str = "", raise_error: bool = False
    ) -> Dict[str, str]:
        """
        Handle an error, log it, and return a standardized error response

        Args:
            e: The exception to handle
            context: Additional context about where the exception occurred
            raise_error: Whether to re-raise the exception after handling

        Returns:
            A dictionary with error information
        """
        error_msg = log_exception(e, context)

        error_response = {
            "status": "error",
            "message": error_msg,
            "type": e.__class__.__name__,
        }

        if raise_error:
            raise e

        return error_response

    @staticmethod
    def try_execute(
        func: Callable[..., Any],
        *args: Any,
        error_context: str = "",
        default_return: Any = None,
        raise_error: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Try to execute a function and handle any exceptions

        Args:
            func: The function to execute
            *args: Arguments to pass to the function
            error_context: Context for error messages
            default_return: Value to return if an exception occurs
            raise_error: Whether to re-raise the exception after handling
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The function result or default_return if an exception occurs
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_error(e, error_context, raise_error)
            return default_return
