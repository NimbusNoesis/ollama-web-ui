import re
import time
from typing import Any, Dict, Generator, List, Optional, TypedDict, Union

import ollama
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
        return ErrorHandler.try_execute(
            ollama.list,
            error_context="Failed to fetch models",
            default_return={"models": []},
        ).get("models", [])

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
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> ollama.ChatResponse:
        """
        Generate a chat completion using Ollama

        Args:
            model: The model to use for chat
            messages: List of message objects with role and content
            system: Optional system prompt
            temperature: Temperature for generation (0.0 to 1.0)
            stream: Whether to stream the response
            tools: Optional list of tools to provide to the model
            tool_choice: Optional control for tool selection (auto, none, or specific tool)

        Returns:
            Either a complete response object or a generator of response chunks
        """

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

        # Add request parameters
        request_params = {
            "model": model,
            "messages": processed_messages,
            "options": options,
        }

        # Add tools if provided
        if tools:
            request_params["tools"] = tools

            # Add tool_choice if provided
            if tool_choice:
                request_params["tool_choice"] = tool_choice

        # Call Ollama API
        response = ollama.chat(**request_params)
        return response
