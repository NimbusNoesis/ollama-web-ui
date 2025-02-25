import logging
import re
import time
from typing import Any, Dict, Generator, List, Optional, TypedDict, Union

import ollama
import requests
import streamlit as st


class ProgressResponse(TypedDict, total=False):
    status: str
    completed: int
    total: int
    error: str


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class OllamaAPI:
    """Class to handle all interactions with the Ollama API"""

    @staticmethod
    def check_connection() -> bool:
        """Check if Ollama is running and accessible"""
        try:
            ollama.list()
            return True
        except Exception as e:
            logging.error(f"Ollama connection failed: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def get_local_models() -> List[Dict[str, Any]]:
        """Get all local models"""
        try:
            models = ollama.list()
            return models.get("models", [])
        except Exception as e:
            logging.error(f"Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def pull_model(model_name: str) -> bool:
        """Prepare to pull a model"""
        try:
            # Validate model name
            if not model_name or not model_name.strip():
                logging.error("Model name cannot be empty")
                return False

            return True
        except Exception as e:
            logging.error(
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
            logging.error(f"Error pulling model {model_name}: {str(e)}", exc_info=True)
            yield {"error": str(e)}

    @staticmethod
    def delete_model(model_name: str) -> bool:
        """Delete a model"""
        try:
            ollama.delete(model_name)
            return True
        except Exception as e:
            logging.error(f"Error deleting model {model_name}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def get_model_info(model_name: str) -> Dict[str, Any]:
        """Get info about a model"""
        try:
            model_info = ollama.show(model_name)
            return dict(model_info)
        except Exception as e:
            logging.error(
                f"Error getting info for model {model_name}: {str(e)}", exc_info=True
            )
            return {}

    @staticmethod
    def search_models(query: str) -> List[Dict[str, Any]]:
        """Search for models from Ollama library"""
        try:
            # Check if we have cached models data and if it's still valid
            if "models_cache" in st.session_state and "cache_time" in st.session_state:
                # Check if cache is less than 1 hour old
                cache_age = time.time() - st.session_state.cache_time
                if cache_age < 3600:  # 3600 seconds = 1 hour
                    logging.info(
                        f"Using cached models data ({int(cache_age)} seconds old)"
                    )
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

                    if results:
                        return results
                    logging.info(
                        "No matches found in cached data, proceeding with fallback"
                    )

            # If no cache or no results from cache, fetch from ollama.com
            return OllamaAPI._fetch_models_from_web(query)
        except Exception as e:
            logging.error("Error searching models: %s", str(e), exc_info=True)
            return []

    @staticmethod
    def _fetch_models_from_web(query: str) -> List[Dict[str, Any]]:
        """Fetch models from ollama.com library"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

        logging.info("Fetching models from ollama.com/library...")
        models_response = requests.get(
            "https://ollama.com/library", headers=headers, timeout=10
        )
        logging.info("Initial response status: %s", models_response.status_code)

        if models_response.status_code == 200:
            model_links = re.findall(r'href="/library/([^"]+)', models_response.text)
            logging.info("Found %d model links", len(model_links))

            if model_links:
                model_names = [link for link in model_links if link]
                logging.info(f"Processing models: {model_names}")

                models_data = []
                for name in model_names:
                    try:
                        logging.info(f"Fetching tags for {name}...")
                        tags_response = requests.get(
                            f"https://ollama.com/library/{name}/tags",
                            headers=headers,
                            timeout=10,
                        )
                        logging.info(
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
                                else "embedding"
                                if "minilm" in name
                                else "text"
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
                            logging.info("Successfully processed %s", name)
                        else:
                            logging.warning("Failed to get tags for %s", name)
                    except Exception as e:
                        logging.error("Error processing %s: %s", name, str(e))
                        continue

                logging.info("Fetched and stored %d models", len(models_data))

                # Cache the models data with current timestamp
                st.session_state.models_cache = models_data
                st.session_state.cache_time = time.time()
                logging.info("Models data cached successfully")

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
    ) -> ollama.ChatResponse:
        """
        Generate a chat completion using Ollama

        Args:
            model: The model to use for chat
            messages: List of message objects with role and content
            system: Optional system prompt
            temperature: Temperature for generation (0.0 to 1.0)
            stream: Whether to stream the response

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

        response = ollama.chat(
            model=model,
            messages=processed_messages,
            options={"temperature": temperature},
        )
        return response
