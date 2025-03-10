import time
import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from app.api.ollama_api import OllamaAPI


class ModelsPage:
    """Page for viewing and managing models"""

    def __init__(self):
        """Initialize the models page"""
        # Initialize session state variables
        if "show_model_details" not in st.session_state:
            st.session_state.show_model_details = None

        if "show_download_status" not in st.session_state:
            st.session_state.show_download_status = False

        if "download_model_name" not in st.session_state:
            st.session_state.download_model_name = ""

        if "download_complete" not in st.session_state:
            st.session_state.download_complete = False

        if "download_error" not in st.session_state:
            st.session_state.download_error = None

        if "show_model_variants" not in st.session_state:
            st.session_state.show_model_variants = None

        # Setup cache directory
        self.cache_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "app",
            "data",
            "cache",
        )
        os.makedirs(self.cache_dir, exist_ok=True)

        # Cache TTL in seconds (1 hour)
        self.cache_ttl = 3600

    def _get_cache_path(self, cache_key: str) -> str:
        """
        Get the full path for a cache file

        Args:
            cache_key: Cache identifier

        Returns:
            Path to the cache file
        """
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def _json_serializable(self, obj):
        """
        Convert an object to a JSON serializable format and handle circular references

        Args:
            obj: Object to convert

        Returns:
            JSON serializable version of the object
        """
        if isinstance(obj, datetime):
            return obj.isoformat()

        # Handle ModelDetails or other custom objects by converting to dict
        if hasattr(obj, "__dict__"):
            return self._json_serializable(obj.__dict__)

        # Handle dictionaries (check for circular references)
        if isinstance(obj, dict):
            return {k: self._json_serializable(v) for k, v in obj.items()}

        # Handle lists
        if isinstance(obj, list):
            return [self._json_serializable(item) for item in obj]

        # For other types, just return as is and let JSON handle them
        return obj

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """
        Save data to cache file

        Args:
            cache_key: Cache identifier
            data: Data to cache
        """
        cache_path = self._get_cache_path(cache_key)

        # Make a deep copy of the data to avoid modifying the original
        # and handle possible circular references
        try:
            # Create a safe-to-serialize version of the data
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": self._json_serializable(data),
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            # If serialization fails, log the error but continue execution
            print(f"Error caching data: {str(e)}")

    def _load_from_cache(self, cache_key: str) -> Any:
        """
        Load data from cache if it exists and is not expired

        Args:
            cache_key: Cache identifier

        Returns:
            Cached data or None if cache miss
        """
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if cache is expired (older than TTL)
            timestamp = datetime.fromisoformat(cache_data["timestamp"])
            if datetime.now() - timestamp > timedelta(seconds=self.cache_ttl):
                # Cache expired
                return None

            return cache_data["data"]
        except (json.JSONDecodeError, KeyError, ValueError):
            # Invalid cache file
            return None

    def _get_local_models(self, use_cache=True):
        """
        Get local models with optional caching

        Args:
            use_cache: Whether to use cached results

        Returns:
            List of local models
        """
        # Cache miss, get fresh data
        models = OllamaAPI.get_local_models()

        return models

    def _get_model_info(self, model_name: str, use_cache=True):
        """
        Get model info with optional caching

        Args:
            model_name: Name of the model
            use_cache: Whether to use cached results

        Returns:
            Model information
        """
        cache_key = f"model_info_{model_name}"

        if use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Cache miss, get fresh data
        model_info = OllamaAPI.get_model_info(model_name)

        # Try to cache, but continue even if caching fails
        try:
            self._save_to_cache(cache_key, model_info)
        except Exception as e:
            print(f"Warning: Failed to cache model info: {str(e)}")

        return model_info

    def _search_models(self, search_query: str, use_cache=True):
        """
        Search models with optional caching

        Args:
            search_query: Search term
            use_cache: Whether to use cached results

        Returns:
            Search results
        """
        cache_key = f"search_results_{search_query}"

        if use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Cache miss, get fresh data
        results = OllamaAPI.search_models(search_query)

        # Try to cache, but continue even if caching fails
        try:
            self._save_to_cache(cache_key, results)
        except Exception as e:
            print(f"Warning: Failed to cache search results: {str(e)}")

        return results

    def render_model_list(self, models: List[Dict[str, Any]]):
        """
        Render the models list section

        Args:
            models: List of models to display
        """
        st.subheader("Installed Models")

        if not models:
            st.info("No models found. Use the sidebar to pull models.")
        else:
            # Create a dataframe for better display
            model_data = []
            for model in models:
                # Safely extract size value, handling if it's a dict or other type
                size_value = model.get("size", 0)
                if isinstance(size_value, dict):
                    # Handle nested dictionary - try to extract a numeric value or default to 0
                    size_value = (
                        size_value.get("size", 0) if isinstance(size_value, dict) else 0
                    )

                # Ensure size_value is a number before division
                try:
                    size_gb = (
                        round(float(size_value) / (1024**3), 2) if size_value else 0
                    )
                except (TypeError, ValueError):
                    # If conversion to float fails, default to 0
                    size_gb = 0

                model_data.append(
                    {
                        "Name": model.get("model", "Unknown"),
                        "Size (GB)": size_gb,
                        "Modified": model.get("modified_at", "Unknown"),
                    }
                )

            df = pd.DataFrame(model_data)

            # Display the table
            st.dataframe(df, use_container_width=True)

            # Select a model for actions
            st.subheader("Model Actions")
            selected_model = st.selectbox(
                "Select a model", [m.get("model") for m in models]
            )

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Show Details", key=f"details_{selected_model}"):
                    # Set session state to show details
                    st.session_state.show_model_details = selected_model
                    st.rerun()

            with col2:
                if st.button("Delete Model", key=f"delete_{selected_model}"):
                    if st.session_state.get("confirm_delete") != selected_model:
                        st.session_state.confirm_delete = selected_model
                        st.warning(
                            f"Click again to confirm deletion of {selected_model}"
                        )
                    else:
                        with st.spinner(f"Deleting {selected_model}..."):
                            if selected_model is not None and OllamaAPI.delete_model(
                                str(selected_model)
                            ):
                                st.success(f"Successfully deleted {selected_model}")
                                st.session_state.confirm_delete = None
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Failed to delete {selected_model}")

    def render_model_details(self, model_name: str):
        """
        Render detailed information about a model

        Args:
            model_name: Name of the model to display details for
        """
        st.subheader(f"Details for {model_name}")

        with st.spinner("Loading model details..."):
            # Use cached model info if available
            model_info = self._get_model_info(model_name)

            if model_info:
                try:
                    # Basic model information
                    st.write("### Basic Information")

                    # Handle different API response formats
                    if "details" in model_info:
                        # New API format
                        basic_info = {
                            "Model Name": model_name,
                            "Family": model_info["details"].get("family", "Unknown"),
                            "Parameter Size": model_info["details"].get(
                                "parameter_size", "Unknown"
                            ),
                            "Quantization Level": model_info["details"].get(
                                "quantization_level", "Unknown"
                            ),
                        }
                    else:
                        # Old API format
                        basic_info = {
                            "Model Name": model_name,
                            "Family": model_info.get("family", "Unknown"),
                            "Parameter Size": model_info.get(
                                "parameter_size", "Unknown"
                            ),
                            "Quantization Level": model_info.get(
                                "quantization_level", "Unknown"
                            ),
                        }

                    # Convert to DataFrame for nicer display
                    st.dataframe(pd.DataFrame([basic_info]), use_container_width=True)

                    # System info
                    if "system" in model_info:
                        st.write("### System Prompt")
                        st.code(model_info.get("system", "None"), language="markdown")

                    # Template info
                    if "template" in model_info:
                        st.write("### Template")
                        st.code(model_info.get("template", "None"), language="markdown")

                    # Parameters
                    if "parameters" in model_info:
                        st.write("### Model Parameters")
                        params = model_info.get("parameters", {})
                        if params:
                            # Convert to DataFrame for nicer display
                            params_df = pd.DataFrame([params])
                            st.dataframe(params_df, use_container_width=True)

                    # License
                    if "license" in model_info:
                        st.write("### License")
                        st.code(model_info.get("license", "None"), language="markdown")

                except Exception as e:
                    st.error(f"Error displaying model information: {str(e)}")
            else:
                st.info(f"No detailed information available for {model_name}")

            # Back button
            if st.button("Back to Models List"):
                st.session_state.show_model_details = None
                st.rerun()

    def render_model_variants(self, model_data: Dict[str, Any]):
        """
        Render the model variants selection page

        Args:
            model_data: Model data including variants
        """
        st.subheader(f"Available Variants for {model_data['name']}")

        # Back button at the top
        if st.button("← Back to Search Results", key="back_to_search"):
            st.session_state.show_model_variants = None
            st.rerun()

        st.write(f"**Model:** {model_data['name']}")
        st.write(f"**Tags:** {model_data['tags']}")

        if "variants" in model_data and model_data["variants"]:
            st.write("### Select a Variant to Download")

            # Create a table for better variant comparison
            variant_data = []
            for variant in model_data["variants"]:
                variant_data.append(
                    {
                        "Variant": variant.get(
                            "display_name", variant.get("tag", "Unknown")
                        ),
                        "Tag": variant.get("tag", "Unknown"),
                        "Size": variant.get("size", "Unknown"),
                        "Last Updated": variant.get("last_updated", "Unknown"),
                        "Hash": variant.get("hash", "Unknown"),
                    }
                )

            # Display as a table
            df = pd.DataFrame(variant_data)
            st.dataframe(df, use_container_width=True)

            # Dropdown to select variant
            variant_options = [v.get("tag") for v in model_data["variants"]]
            selected_variant = st.selectbox(
                "Select variant to download",
                variant_options,
                format_func=lambda x: f"{x} ({next((v['size'] for v in model_data['variants'] if v['tag'] == x), 'Unknown')})",
            )

            if st.button("Download Selected Variant", key="download_variant"):
                if selected_variant and selected_variant.strip():
                    self.pull_model(selected_variant.strip())
                else:
                    st.error("Please select a valid variant")
        else:
            st.warning("No variants information available for this model.")

            # Fallback option to download the base model
            if st.button("Download Base Model"):
                if model_data["name"] and model_data["name"].strip():
                    self.pull_model(model_data["name"].strip())
                else:
                    st.error("Invalid model name")

    def download_model(self):
        """Handle downloading a model with progress display"""
        if not st.session_state.show_download_status:
            return

        model_name = st.session_state.download_model_name
        overlay_container = st.container()

        with overlay_container:
            with st.status(f"Downloading {model_name}", expanded=True) as status:
                try:
                    progress_bar = st.progress(0)

                    # Perform the actual download
                    for progress in OllamaAPI.perform_pull(model_name):
                        if "status" in progress:
                            status.update(label=f"Status: {progress['status']}")

                        if "completed" in progress and "total" in progress:
                            # Add safety check for zero division
                            total = progress["total"]
                            if total > 0:  # Only calculate percent if total is positive
                                percent = progress["completed"] / total
                                progress_bar.progress(percent)
                                status.update(
                                    label=f"Downloaded: {int(percent * 100)}% of {model_name}"
                                )
                            else:
                                status.update(label=f"Preparing download: {model_name}")

                    # Mark download as complete
                    progress_bar.progress(1.0)
                    status.update(
                        label=f"Successfully downloaded {model_name}", state="complete"
                    )
                    st.session_state.download_complete = True

                    # Invalidate local models cache after successful download
                    cache_path = self._get_cache_path("local_models")
                    if os.path.exists(cache_path):
                        try:
                            os.remove(cache_path)
                        except Exception:
                            pass

                    if st.button("Close"):
                        st.session_state.show_download_status = False
                        st.rerun()

                except Exception as e:
                    st.session_state.download_error = str(e)
                    status.update(label=f"Error: {str(e)}", state="error")

                    if st.button("Dismiss Error"):
                        st.session_state.show_download_status = False
                        st.rerun()

    def render_search_box(self):
        """Render the model search box in the sidebar"""
        st.sidebar.subheader("Search Models")
        search_query = st.sidebar.text_input(
            "Search term", placeholder="e.g., code, vision, small"
        )

        # Add checkbox for using cache
        use_cache = st.sidebar.checkbox(
            "Use cached results", value=True, key="sidebar_use_cache"
        )

        if st.sidebar.button("Search Models", disabled=not search_query):
            placeholder = st.sidebar.empty()
            placeholder.info("Searching models...")
            results = self._search_models(search_query, use_cache=use_cache)
            st.session_state.search_results = results
            placeholder.empty()
            if not results:
                st.sidebar.info("No models found matching your search")

        # Display search results if available
        if "search_results" in st.session_state and st.session_state.search_results:
            st.sidebar.write(f"Found {len(st.session_state.search_results)} models:")
            for i, model in enumerate(st.session_state.search_results):
                with st.sidebar.container():
                    col1, col2 = st.sidebar.columns([3, 1])
                    with col1:
                        st.write(f"**{model['name']}**")
                        st.caption(f"Tags: {model['tags']}")
                    with col2:
                        if st.button("Details", key=f"details_sidebar_{i}"):
                            st.session_state.show_model_variants = model
                            st.rerun()

    def pull_model(self, model_name: str):
        """
        Prepare to pull a model

        Args:
            model_name: Name of the model to pull
        """
        try:
            # Validate model name
            if not model_name or not model_name.strip():
                st.error("Model name cannot be empty")
                return False

            model_name = model_name.strip()

            # Set session state for download
            st.session_state.show_download_status = True
            st.session_state.download_model_name = model_name
            st.session_state.download_complete = False
            st.session_state.download_error = None

            # Rerun to show the overlay immediately
            st.rerun()
        except Exception as e:
            error_msg = f"Error preparing to pull model {model_name}: {str(e)}"
            st.error(error_msg)
            return False

    def render_search_tab(self):
        """Render the search tab UI with default model listing"""
        st.subheader("Search for Models")

        # Search input and controls
        search_tab_query = st.text_input(
            "Search term",
            placeholder="e.g., code, vision, small",
            key="search_tab_query",
        )

        # Add checkbox for using cache
        use_cache = st.checkbox("Use cached results", value=True, key="tab_use_cache")

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Search", disabled=not search_tab_query):
                with st.spinner("Searching models..."):
                    results = self._search_models(search_tab_query, use_cache=use_cache)
                    st.session_state.search_results_tab = results

        with col2:
            filter_options = ["All", "Code", "Vision", "Small", "Medium", "Large"]
            selected_filter = st.selectbox("Filter by category", filter_options)

        # Initialize or get search results
        if "search_results_tab" not in st.session_state:
            with st.spinner("Loading available models..."):
                # Get all models by using an empty search
                st.session_state.search_results_tab = self._search_models(
                    "", use_cache=use_cache
                )

        results = st.session_state.search_results_tab

        # Apply filter if selected
        if selected_filter != "All":
            filter_term = selected_filter.lower()
            results = [r for r in results if filter_term in r["tags"].lower()]

        if results:
            st.write(f"Found {len(results)} models:")

            # Create a grid of cards for search results
            cols = st.columns(3)
            for i, model in enumerate(results):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.write(f"**{model['name']}**")
                        st.caption(f"Tags: {model['tags']}")

                        # For variant count display
                        variant_count = len(model.get("variants", []))
                        variant_text = f"{variant_count} variant{'s' if variant_count != 1 else ''}"

                        # Check if model is already installed
                        models = self._get_local_models(use_cache=use_cache)
                        installed = any(m.get("model") == model["name"] for m in models)

                        if installed:
                            st.success("✓ Installed")
                        else:
                            st.caption(f"Available: {variant_text}")
                            if st.button("View Details", key=f"view_details_{i}"):
                                st.session_state.show_model_variants = model
                                st.rerun()

        else:
            st.info("No models found matching your criteria")

    def render(self):
        """Render the models page"""
        # Handle download overlay if active
        if st.session_state.show_download_status:
            self.download_model()
            return  # Don't render the rest of the page when downloading

        # Show model variants page if selected
        if st.session_state.show_model_variants:
            self.render_model_variants(st.session_state.show_model_variants)
            return  # Don't render the rest of the page when showing variants

        st.title("Ollama Model Manager")
        st.write("Manage your Ollama models from this dashboard")

        # Add option to clear cache
        with st.expander("Cache Settings"):
            st.write(f"Cache directory: `{self.cache_dir}`")
            st.write(f"Cache TTL: {self.cache_ttl} seconds (1 hour)")
            if st.button("Clear All Cache"):
                try:
                    # Delete all cache files
                    for file in os.listdir(self.cache_dir):
                        if file.endswith(".json"):
                            os.remove(os.path.join(self.cache_dir, file))
                    st.success("Cache cleared successfully")
                except Exception as e:
                    st.error(f"Error clearing cache: {str(e)}")

        # Get installed models (using cache by default)
        try:
            models = self._get_local_models()
        except Exception as e:
            st.error(f"Error loading models: {str(e)}")
            models = []

        # Render search box in sidebar
        self.render_search_box()

        # Check if we should show model details
        if st.session_state.show_model_details:
            self.render_model_details(st.session_state.show_model_details)
        else:
            # Choose between list and search views
            tab_options = ["📋 Models List", "🔍 Search"]
            selected_tab = st.radio(
                "View",
                tab_options,
                index=0,
                horizontal=True,
                label_visibility="collapsed",
            )

            # Display content based on selected tab
            if selected_tab == "📋 Models List":
                self.render_model_list(models)
            else:
                self.render_search_tab()
