import time
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
                size_gb = round(model.get("size", 0) / (1024**3), 2)
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
            model_info = OllamaAPI.get_model_info(model_name)

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

        if st.sidebar.button("Search Models", disabled=not search_query):
            placeholder = st.sidebar.empty()
            placeholder.info("Searching models...")
            results = OllamaAPI.search_models(search_query)
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
                        if st.button("Pull", key=f"pull_search_{i}"):
                            if model["name"] and model["name"].strip():
                                self.pull_model(model["name"].strip())
                            else:
                                st.error("Invalid model name")

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

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Search", disabled=not search_tab_query):
                with st.spinner("Searching models..."):
                    results = OllamaAPI.search_models(search_tab_query)
                    st.session_state.search_results_tab = results

        with col2:
            filter_options = ["All", "Code", "Vision", "Small", "Medium", "Large"]
            selected_filter = st.selectbox("Filter by category", filter_options)

        # Initialize or get search results
        if "search_results_tab" not in st.session_state:
            with st.spinner("Loading available models..."):
                # Get all models by using an empty search
                st.session_state.search_results_tab = OllamaAPI.search_models("")

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

                        # Check if model is already installed
                        models = OllamaAPI.get_local_models()
                        installed = any(m.get("model") == model["name"] for m in models)

                        if installed:
                            st.success("✓ Installed")
                        else:
                            if st.button("Pull Model", key=f"pull_tab_{i}"):
                                if model["name"] and model["name"].strip():
                                    self.pull_model(model["name"].strip())
                                else:
                                    st.error("Invalid model name")
        else:
            st.info("No models found matching your criteria")

    def render(self):
        """Render the models page"""
        # Handle download overlay if active
        if st.session_state.show_download_status:
            self.download_model()

        st.title("Ollama Model Manager")
        st.write("Manage your Ollama models from this dashboard")

        # Get installed models
        models = OllamaAPI.get_local_models()

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
