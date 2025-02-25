import ollama
import logging
import requests
import re
import time
import streamlit as st
from typing import Dict, List, Any, Union, Generator, Optional, TypedDict


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
            logging.error(f"Error searching models: {str(e)}", exc_info=True)
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

        try:
            logging.info("Fetching models from ollama.com/library...")
            models_response = requests.get(
                "https://ollama.com/library", headers=headers, timeout=10
            )
            logging.info(f"Initial response status: {models_response.status_code}")

            if models_response.status_code == 200:
                model_links = re.findall(
                    r'href="/library/([^"]+)', models_response.text
                )
                logging.info(f"Found {len(model_links)} model links")

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
                                f"Tags response status for {name}: {tags_response.status_code}"
                            )

                            if tags_response.status_code == 200:
                                tags = re.findall(
                                    f'{name}:[^"\\s]*', tags_response.text
                                )
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
                                logging.info(f"Successfully processed {name}")
                            else:
                                logging.warning(f"Failed to get tags for {name}")
                        except Exception as e:
                            logging.error(f"Error processing {name}: {str(e)}")
                            continue

                    logging.info(f"Fetched and stored {len(models_data)} models")

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

                    if results:
                        return results

            # Fall back to the local catalog if no results from web
            return OllamaAPI._get_local_model_catalog(query)

        except Exception as e:
            logging.error(f"Error fetching from web: {str(e)}", exc_info=True)
            return OllamaAPI._get_local_model_catalog(query)

    @staticmethod
    def _get_local_model_catalog(query: str) -> List[Dict[str, Any]]:
        """Fall back to local model catalog when web search fails"""
        logging.info("Using local model catalog for search")

        # Enhanced model catalog with a comprehensive list of models
        model_catalog = [
            {"name": "llama3", "tags": ["meta", "llama", "large", "general"]},
            {"name": "llama3:8b", "tags": ["meta", "llama", "small", "general"]},
            {"name": "llama3:70b", "tags": ["meta", "llama", "huge", "general"]},
            {"name": "mistral", "tags": ["mistral", "general", "medium"]},
            {"name": "mixtral", "tags": ["mistral", "mixture", "general", "large"]},
            {"name": "phi", "tags": ["microsoft", "small", "general"]},
            {"name": "gemma", "tags": ["google", "general", "medium"]},
            {"name": "gemma:7b", "tags": ["google", "small", "general"]},
            {"name": "codellama", "tags": ["meta", "llama", "code", "programming"]},
            {"name": "vicuna", "tags": ["lmsys", "medium", "general"]},
            {"name": "orca-mini", "tags": ["small", "general"]},
            {"name": "stablelm", "tags": ["stability", "medium"]},
            {"name": "codegemma", "tags": ["google", "code", "programming"]},
            {"name": "deepseek-coder", "tags": ["deepseek", "code", "programming"]},
            {"name": "llava", "tags": ["vision", "multimodal", "image"]},
            {"name": "bakllava", "tags": ["vision", "multimodal", "image"]},
            {"name": "neural-chat", "tags": ["intel", "general", "medium"]},
            {"name": "yi", "tags": ["01ai", "general", "medium"]},
            {"name": "wizard", "tags": ["wizardlm", "general", "medium"]},
            {"name": "falcon", "tags": ["tii", "general", "medium"]},
            {"name": "qwen", "tags": ["alibaba", "general", "medium"]},
            {"name": "nous-hermes", "tags": ["nous", "general", "medium"]},
            {"name": "openhermes", "tags": ["open", "general", "medium"]},
            {"name": "mpt", "tags": ["mosaicml", "general", "medium"]},
            {"name": "dolphin", "tags": ["cognitivecomputations", "general", "medium"]},
            {"name": "command", "tags": ["cohere", "general", "instruction"]},
            {"name": "wizardmath", "tags": ["wizardlm", "math", "specific"]},
            {"name": "orca2", "tags": ["microsoft", "general", "medium"]},
            {"name": "tinyllama", "tags": ["tiny", "small", "efficient"]},
            # Additional models
            {"name": "llama2", "tags": ["meta", "llama", "general"]},
            {"name": "llama2:7b", "tags": ["meta", "llama", "small", "general"]},
            {"name": "llama2:13b", "tags": ["meta", "llama", "medium", "general"]},
            {"name": "llama2:70b", "tags": ["meta", "llama", "large", "general"]},
            {"name": "mistral:7b", "tags": ["mistral", "small", "general"]},
            {
                "name": "mixtral:8x7b",
                "tags": ["mistral", "mixture", "large", "general"],
            },
            {"name": "phi:3", "tags": ["microsoft", "small", "general"]},
            {"name": "phi:2", "tags": ["microsoft", "small", "general"]},
            {"name": "gemma:2b", "tags": ["google", "tiny", "general"]},
            {
                "name": "codellama:7b",
                "tags": ["meta", "llama", "small", "code", "programming"],
            },
            {
                "name": "codellama:13b",
                "tags": ["meta", "llama", "medium", "code", "programming"],
            },
            {
                "name": "codellama:34b",
                "tags": ["meta", "llama", "large", "code", "programming"],
            },
            {
                "name": "codellama:70b",
                "tags": ["meta", "llama", "huge", "code", "programming"],
            },
            {"name": "wizard:7b", "tags": ["wizardlm", "small", "general"]},
            {"name": "wizard:13b", "tags": ["wizardlm", "medium", "general"]},
            {
                "name": "codegemma:7b",
                "tags": ["google", "small", "code", "programming"],
            },
            {"name": "codegemma:2b", "tags": ["google", "tiny", "code", "programming"]},
            {"name": "yi:6b", "tags": ["01ai", "small", "general"]},
            {"name": "yi:34b", "tags": ["01ai", "large", "general"]},
            {"name": "qwen:7b", "tags": ["alibaba", "small", "general"]},
            {"name": "qwen:14b", "tags": ["alibaba", "medium", "general"]},
            {"name": "qwen:72b", "tags": ["alibaba", "large", "general"]},
            {"name": "qwen2", "tags": ["alibaba", "general"]},
            {"name": "qwen2:7b", "tags": ["alibaba", "small", "general"]},
            {"name": "qwen2:72b", "tags": ["alibaba", "large", "general"]},
            {"name": "wizardcoder", "tags": ["wizardlm", "code", "programming"]},
            {
                "name": "wizardcoder:7b",
                "tags": ["wizardlm", "small", "code", "programming"],
            },
            {
                "name": "wizardcoder:13b",
                "tags": ["wizardlm", "medium", "code", "programming"],
            },
            {
                "name": "wizardcoder:34b",
                "tags": ["wizardlm", "large", "code", "programming"],
            },
            {
                "name": "wizardmath:7b",
                "tags": ["wizardlm", "small", "math", "specific"],
            },
            {
                "name": "wizardmath:13b",
                "tags": ["wizardlm", "medium", "math", "specific"],
            },
            {"name": "openchat", "tags": ["open", "general"]},
            {"name": "openchat:7b", "tags": ["open", "small", "general"]},
            {"name": "nous-hermes:13b", "tags": ["nous", "medium", "general"]},
            {"name": "openhermes:7b", "tags": ["open", "small", "general"]},
            {"name": "openhermes:2.5", "tags": ["open", "general"]},
            {"name": "olmo", "tags": ["allen", "general"]},
            {"name": "olmo:7b", "tags": ["allen", "small", "general"]},
            {"name": "stable-code", "tags": ["stability", "code", "programming"]},
            {
                "name": "stable-code:3b",
                "tags": ["stability", "tiny", "code", "programming"],
            },
            {"name": "command-r", "tags": ["cohere", "general", "instruction"]},
            {
                "name": "command-r:34b",
                "tags": ["cohere", "large", "general", "instruction"],
            },
            {"name": "orca2:7b", "tags": ["microsoft", "small", "general"]},
            {"name": "orca2:13b", "tags": ["microsoft", "medium", "general"]},
            {"name": "falcon:7b", "tags": ["tii", "small", "general"]},
            {"name": "falcon:40b", "tags": ["tii", "large", "general"]},
            {"name": "vicuna:7b", "tags": ["lmsys", "small", "general"]},
            {"name": "vicuna:13b", "tags": ["lmsys", "medium", "general"]},
            {"name": "tinyllama:1.1b", "tags": ["tiny", "very-small", "efficient"]},
            {"name": "solar", "tags": ["upstage", "general"]},
            {"name": "solar:10.7b", "tags": ["upstage", "medium", "general"]},
            {"name": "phi3", "tags": ["microsoft", "general"]},
            {"name": "phi3:medium", "tags": ["microsoft", "medium", "general"]},
            {"name": "phi3:small", "tags": ["microsoft", "small", "general"]},
            {"name": "phi3:mini", "tags": ["microsoft", "tiny", "general"]},
        ]

        # Simple search logic - match against model name or tags
        results = []
        query_lower = query.lower().strip()

        for model in model_catalog:
            # Check if query is in model name or tags
            if query_lower in model["name"].lower() or any(
                query_lower in tag.lower() for tag in model["tags"]
            ):
                results.append(
                    {"name": model["name"], "tags": ", ".join(model["tags"])}
                )

        return results

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

        response = ollama.chat(model=model, messages=processed_messages)
        return response
