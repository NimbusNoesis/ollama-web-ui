import re
import time
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    TypedDict,
    Union,
    Callable,
    Iterator,
)
import json

import ollama
from ollama import chat
import requests
import streamlit as st

from ..utils.logger import get_logger, exception_handler, ErrorHandler


class ProgressResponse(TypedDict, total=False):
    status: str
    completed: int
    total: int
    error: str


# Get application logger
logger = get_logger()


class OllamaAPI:
    """Class to handle all interactions with the Ollama API"""

    @staticmethod
    @exception_handler
    def check_connection() -> bool:
        """Check if Ollama is running and accessible"""
        try:
            ollama.list()
            return True
        except Exception as e:
            logger.error(f"Ollama connection failed: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def get_local_models() -> List[Dict[str, Any]]:
        """Get all local models"""
        models_response = ErrorHandler.try_execute(
            ollama.list,
            error_context="Failed to fetch models",
            default_return={"models": []},
        )

        # Get the models list
        models = models_response.get("models", [])

        # Convert Model objects to dictionaries and ensure 'name' key exists
        formatted_models = []
        for model in models:
            if hasattr(model, "__dict__"):
                # Convert model object to dict
                model_dict = model.__dict__.copy() if hasattr(model, "__dict__") else {}

                # If it's a modern API response, ensure name compatibility
                if hasattr(model, "model") and not model_dict.get("name"):
                    model_dict["name"] = model.model

                formatted_models.append(model_dict)
            elif isinstance(model, dict):
                # If it's already a dict, ensure name key exists
                if "model" in model and "name" not in model:
                    model["name"] = model["model"]
                formatted_models.append(model)

        return formatted_models

    @staticmethod
    def pull_model(model_name: str) -> bool:
        """Prepare to pull a model"""
        try:
            # Validate model name
            if not model_name or not model_name.strip():
                logger.error("Model name cannot be empty")
                return False

            return True
        except Exception as e:
            logger.error(
                f"Error preparing to pull model {model_name}: {str(e)}", exc_info=True
            )
            return False

    @staticmethod
    def perform_pull(model_name: str) -> Generator[ProgressResponse, None, None]:
        """Actually pull the model and yield progress updates"""
        try:
            for progress in ollama.pull(model_name, stream=True):
                yield ProgressResponse(
                    status=progress.get("status", ""),
                    completed=progress.get("completed", 0),
                    total=progress.get("total", 0),
                )
        except Exception as e:
            error_msg = f"Error pulling model {model_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield {"error": str(e)}

    @staticmethod
    def delete_model(model_name: str) -> bool:
        """Delete a model"""
        return (
            ErrorHandler.try_execute(
                ollama.delete,
                model_name,
                error_context=f"Error deleting model {model_name}",
                default_return=False,
            )
            is not None
        )

    @staticmethod
    def get_model_info(model_name: str) -> Dict[str, Any]:
        """Get info about a model"""
        return ErrorHandler.try_execute(
            ollama.show,
            model_name,
            error_context=f"Error getting info for model {model_name}",
            default_return={},
        )

    @staticmethod
    def search_models(query: str) -> List[Dict[str, Any]]:
        """
        Search for models in the Ollama library

        Args:
            query: Search query

        Returns:
            List of model dictionaries
        """
        # Check if we have cached results
        if (
            "models_cache" in st.session_state
            and "cache_time" in st.session_state
            and time.time() - st.session_state.cache_time < 3600  # 1 hour cache
        ):
            logger.info("Using cached models data")
            models_data = st.session_state.models_cache

            # Filter models based on the search query
            results = []
            query_lower = query.lower().strip()

            for model in models_data:
                if (
                    query_lower in model["name"].lower()
                    or query_lower in model["tags"].lower()
                ):
                    results.append(model)

            return results
        else:
            # Fetch fresh data
            logger.info(f"Fetching models with query: {query}")
            return OllamaAPI._fetch_models_from_web(query)

    @staticmethod
    def _fetch_models_from_web(query: str) -> List[Dict[str, Any]]:
        """Fetch models from ollama.com library"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        logger.info("Fetching models from ollama.com/library...")
        models_response = requests.get(
            "https://ollama.com/library", headers=headers, timeout=10
        )
        logger.info("Initial response status: %s", models_response.status_code)

        if models_response.status_code == 200:
            model_links = re.findall(r'href="/library/([^"]+)', models_response.text)
            logger.info("Found %d model links", len(model_links))

            if model_links:
                model_names = [link for link in model_links if link]
                logger.info(f"Processing models: {model_names}")

                models_data = []
                for name in model_names:
                    try:
                        logger.info(f"Fetching tags for {name}...")
                        tags_response = requests.get(
                            f"https://ollama.com/library/{name}/tags",
                            headers=headers,
                            timeout=10,
                        )
                        logger.info(
                            "Tags response status for %s: %s",
                            name,
                            tags_response.status_code,
                        )

                        if tags_response.status_code == 200:
                            tags = re.findall(f'{name}:[^"\\s]*', tags_response.text)
                            filtered_tags = [
                                tag
                                for tag in tags
                                if not any(x in tag for x in ["text", "base", "fp"])
                                and not re.match(r".*q[45]_[01]", tag)
                            ]

                            model_type = (
                                "vision"
                                if "vision" in name
                                else "embedding" if "minilm" in name else "text"
                            )

                            # Extract tags for display
                            display_tags = OllamaAPI.extract_tags_from_name(name)
                            if model_type == "vision":
                                display_tags.extend(["vision", "multimodal"])
                            elif model_type == "embedding":
                                display_tags.extend(["embedding"])

                            models_data.append(
                                {
                                    "name": name,
                                    "tags": (
                                        ", ".join(display_tags)
                                        if display_tags
                                        else "general"
                                    ),
                                    "variants": filtered_tags,
                                }
                            )
                            logger.info("Successfully processed %s", name)
                        else:
                            logger.warning("Failed to get tags for %s", name)
                    except Exception as e:
                        logger.error("Error processing %s: %s", name, str(e))
                        continue

                logger.info("Fetched and stored %d models", len(models_data))

                # Cache the models data with current timestamp
                st.session_state.models_cache = models_data
                st.session_state.cache_time = time.time()
                logger.info("Models data cached successfully")

                # Filter models based on the search query
                results = []
                query_lower = query.lower().strip()

                for model in models_data:
                    if (
                        query_lower in model["name"].lower()
                        or query_lower in model["tags"].lower()
                    ):
                        results.append(model)

                return results
            else:
                return []
        else:
            return []

    @staticmethod
    def extract_tags_from_name(model_name: str) -> List[str]:
        """Extract tags from model name"""
        tags = []
        model_name = model_name.lower()

        # Extract tags from model name
        if "llama" in model_name:
            tags.append("llama")
            if "3" in model_name:
                tags.append("meta")
            elif "2" in model_name:
                tags.append("meta")
        if "codellama" in model_name:
            tags.append("code")
            tags.append("programming")
            tags.append("meta")
        if "7b" in model_name:
            tags.append("small")
        if "13b" in model_name:
            tags.append("medium")
        if "70b" in model_name:
            tags.append("large")
        if "code" in model_name:
            tags.append("code")
            tags.append("programming")
        if "vision" in model_name or "image" in model_name or "llava" in model_name:
            tags.append("vision")
            tags.append("multimodal")
        if "mistral" in model_name:
            tags.append("mistral")
        if "mixtral" in model_name:
            tags.append("mistral")
            tags.append("mixture")
        if "phi" in model_name:
            tags.append("microsoft")
        if "gemma" in model_name:
            tags.append("google")
        if "wizard" in model_name:
            tags.append("wizardlm")
            if "math" in model_name:
                tags.append("math")
                tags.append("specific")
            if "coder" in model_name:
                tags.append("code")
                tags.append("programming")

        return tags

    @staticmethod
    def chat_completion(
        model: str,
        messages: List[Dict[str, Union[str, List[Any]]]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = True,
        tools: Any = None,
    ) -> Union[ollama.ChatResponse, Iterator[str]]:
        """
        Generate a chat completion using Ollama

        Args:
            model: The model to use for chat
            messages: List of message objects with role and content
            system: Optional system prompt
            temperature: Temperature for generation (0.0 to 1.0)
            stream: Whether to stream the response (ignored if tools are used)
            tools: Optional list of tools to provide to the model - can be function references or tool definitions

        Returns:
            Either a complete response object, a generator of response chunks, or a string iterator for streaming
        """

        # If tools are provided, we can't use streaming as we need to process tool calls
        if tools:
            processed_messages = [
                {
                    "role": msg["role"],
                    "content": (
                        str(msg["content"])
                        if isinstance(msg["content"], list)
                        else msg["content"]
                    ),
                }
                for msg in messages
            ]
            response = chat(
                model=model,
                messages=processed_messages,
                tools=tools,
            )
            return response
        else:
            # If system prompt is provided, add it as a system message at the beginning
            messages_with_system = messages.copy()
            if system:
                # Add system message at the beginning of the list
                messages_with_system.insert(0, {"role": "system", "content": system})
            else:
                content = """
                You are a seasoned software developer. Follow these steps for every response:

                1. First, analyze the question or code carefully
                2. Break down complex problems into smaller components
                3. Think through each step of your solution
                4. Explain your reasoning as you develop the solution
                5. Provide your final implementation or answer, if your answer contains source code, make sure it is complete and fully implemented, and wrapped in markdown code blocks.

                Guidelines:
                - Respond using markdown formatting
                - Include language tags in markdown code blocks
                - When analyzing code, first identify the key components
                - For implementation questions, explain your approach before coding
                - If source code is provided, explicitly reference relevant parts
                - If a question is outside your knowledge, explain why
                - Keep code examples complete and fully implemented

                Remember to maintain context from previous interactions in the conversation.

                Most Important: Always wrap source code in markdown, no exceptions!
                """
                messages_with_system.insert(0, {"role": "system", "content": content})

            # Ensure content of messages is a string
            processed_messages = [
                {
                    "role": msg["role"],
                    "content": (
                        str(msg["content"])
                        if isinstance(msg["content"], list)
                        else msg["content"]
                    ),
                }
                for msg in messages_with_system
            ]

            # Set up options
            options = {"temperature": temperature}

            # Handle streaming vs non-streaming
            if stream:
                return OllamaAPI.stream_chat_completion(
                    model, processed_messages, options
                )
            else:
                response = chat(
                    model=model,
                    messages=processed_messages,
                    options=options,
                )
                return response

    @staticmethod
    def stream_chat_completion(
        model: str, messages: List[Dict[str, str]], options: Dict[str, Any]
    ) -> Iterator[str]:
        """
        Stream chat completion from Ollama

        Args:
            model: The model to use for chat
            messages: Processed messages list
            options: Generation options

        Returns:
            Iterator that yields text chunks as they are generated
        """
        logger.info(f"Starting streaming response with model {model}")

        # Create a generator that yields text chunks
        def message_generator() -> Iterator[str]:
            try:
                # Use ollama's stream feature
                for chunk in chat(
                    model=model,
                    messages=messages,
                    options=options,
                    stream=True,
                ):
                    # Handle different response formats and ensure we always yield strings
                    if hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                        content = chunk.message.content
                        if content:
                            yield str(content)
                    elif (
                        isinstance(chunk, dict)
                        and "message" in chunk
                        and "content" in chunk["message"]
                    ):
                        content = chunk["message"]["content"]
                        if content:
                            yield str(content)
                    else:
                        # Unexpected chunk format, convert to string if possible
                        try:
                            yield str(chunk)
                        except:
                            # If we can't convert it to a string, yield nothing
                            pass
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")
                yield f"\n\n*Error: {str(e)}*"

        return message_generator()

    @staticmethod
    def _function_to_tool_definition(func: Callable) -> Optional[Dict[str, Any]]:
        """
        Convert a Python function to an Ollama tool definition

        Args:
            func: The function to convert

        Returns:
            Tool definition dictionary or None if conversion fails
        """
        try:
            import inspect
            from typing import get_type_hints

            # Get function signature
            sig = inspect.signature(func)

            # Get function name
            func_name = func.__name__

            # Get function docstring
            doc = inspect.getdoc(func) or ""

            # Extract description from docstring (first line)
            description = doc.split("\n")[0] if doc else f"Function {func_name}"

            # Get type hints
            type_hints = get_type_hints(func)

            # Define parameter properties
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Skip self, cls for methods
                if (
                    param_name in ("self", "cls")
                    and param.kind == param.POSITIONAL_OR_KEYWORD
                ):
                    continue

                # Get parameter type
                param_type = type_hints.get(param_name, None)
                json_type = "string"  # Default type

                # Map Python types to JSON Schema types
                if param_type:
                    if param_type in (int, float):
                        json_type = "number"
                    elif param_type is bool:
                        json_type = "boolean"
                    elif param_type in (list, set, tuple):
                        json_type = "array"
                    elif param_type in (dict, object):
                        json_type = "object"

                # Extract parameter description from docstring
                param_desc = ""
                if doc:
                    param_section = (
                        doc.split("Args:")[1].split("Returns:")[0]
                        if "Args:" in doc and "Returns:" in doc
                        else ""
                    )
                    for line in param_section.split("\n"):
                        if line.strip().startswith(param_name + ":"):
                            param_desc = line.split(":", 1)[1].strip()
                            break

                # Add parameter to properties
                properties[param_name] = {
                    "type": json_type,
                    "description": param_desc or f"Parameter {param_name}",
                }

                # Check if parameter is required
                if param.default == param.empty:
                    required.append(param_name)

            # Create tool definition
            tool_def = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            return tool_def
        except Exception as e:
            logger.error(f"Error converting function to tool definition: {str(e)}")
            return None

    @staticmethod
    def process_tool_calls(
        response: Any, available_functions: Dict[str, Callable]
    ) -> Dict[str, Any]:
        """
        Process tool calls from Ollama response

        Args:
            response: Response from Ollama API
            available_functions: Dictionary of function name to function reference

        Returns:
            Dictionary with results from tool calls
        """
        results = {}

        # Check if response has tool calls
        tool_calls = None

        # Handle different response types
        if hasattr(response, "message"):
            msg = getattr(response, "message")
            if hasattr(msg, "tool_calls"):
                tool_calls = getattr(msg, "tool_calls")
        elif isinstance(response, dict) and "message" in response:
            msg_dict = response["message"]
            if "tool_calls" in msg_dict:
                tool_calls = msg_dict["tool_calls"]

        # If we don't have tool calls, return empty results
        if tool_calls is None:
            return results

        # Process each tool call
        for tool_call in tool_calls:
            try:
                # Get function name and arguments
                function_name = ""
                arguments_data = {}
                tool_id = f"tool_{len(results)}"

                # Handle different tool call formats
                if isinstance(tool_call, dict):
                    if "function" in tool_call:
                        func_info = tool_call["function"]
                        if isinstance(func_info, dict):
                            function_name = func_info.get("name", "")
                            arguments_data = func_info.get("arguments", {})
                    if "id" in tool_call:
                        tool_id = tool_call["id"]
                else:
                    # If it's an object
                    if hasattr(tool_call, "function"):
                        func_obj = getattr(tool_call, "function")
                        if hasattr(func_obj, "name"):
                            function_name = getattr(func_obj, "name")
                        if hasattr(func_obj, "arguments"):
                            arguments_data = getattr(func_obj, "arguments")
                    if hasattr(tool_call, "id"):
                        tool_id = getattr(tool_call, "id")

                # Parse arguments
                arguments = {}
                if isinstance(arguments_data, str):
                    try:
                        arguments = json.loads(arguments_data)
                    except json.JSONDecodeError:
                        arguments = {"raw_arguments": arguments_data}
                else:
                    # If it's already a dict or similar object, use it directly
                    arguments = dict(arguments_data) if arguments_data else {}

                # Check if function exists
                if function_name and (
                    function_to_call := available_functions.get(function_name)
                ):
                    # Call the function
                    logger.info(f"Calling function: {function_name}")
                    logger.info(f"Arguments: {arguments}")
                    output = function_to_call(**arguments)
                    results[tool_id] = {
                        "function_name": function_name,
                        "output": output,
                    }
                else:
                    logger.warning(f"Function {function_name} not found")
                    results[tool_id] = {
                        "function_name": function_name,
                        "error": f"Function {function_name} not found",
                    }
            except Exception as e:
                tool_id = getattr(tool_call, "id", f"unknown_{len(results)}")
                logger.error(f"Error processing tool call: {str(e)}")
                results[tool_id] = {"error": str(e)}

        return results

    @staticmethod
    def add_tool_results_to_messages(
        messages: List[Dict[str, Any]],
        response: Any,
        tool_results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Add tool results to messages for further conversation

        Args:
            messages: Original messages list
            response: Response from Ollama API
            tool_results: Results from tool calls

        Returns:
            Updated messages list with tool results
        """
        updated_messages = messages.copy()

        # Get tool calls from response
        tool_calls = None
        assistant_content = ""

        # Handle different response types
        if hasattr(response, "message"):
            msg = getattr(response, "message")
            if hasattr(msg, "tool_calls"):
                tool_calls = getattr(msg, "tool_calls")
            if hasattr(msg, "content"):
                assistant_content = getattr(msg, "content", "")
        elif isinstance(response, dict) and "message" in response:
            msg_dict = response["message"]
            if "tool_calls" in msg_dict:
                tool_calls = msg_dict["tool_calls"]
            if "content" in msg_dict:
                assistant_content = msg_dict.get("content", "")

        # Add assistant message with tool calls
        updated_messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [] if tool_calls is None else tool_calls,
            }
        )

        # Add tool result messages
        if tool_calls is not None:
            for tool_call in tool_calls:
                tool_id = ""

                # Extract tool ID
                if isinstance(tool_call, dict) and "id" in tool_call:
                    tool_id = tool_call["id"]
                elif hasattr(tool_call, "id"):
                    tool_id = getattr(tool_call, "id")
                else:
                    continue  # Skip if no ID

                if tool_id and tool_id in tool_results:
                    result = tool_results[tool_id]
                    updated_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": result.get("function_name", ""),
                            "content": (
                                json.dumps(result.get("output", ""))
                                if isinstance(result.get("output"), (dict, list))
                                else str(result.get("output", ""))
                            ),
                        }
                    )

        return updated_messages
