import time
import threading
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger, exception_handler
from app.utils.session_manager import SessionManager
from app.components.ui_components import (
    create_card,
    status_indicator,
    progress_indicator,
)
from app.components.model_details import ModelDetails
from app.components.model_list import ModelList
from app.components.model_search import ModelSearch

# Get application logger
logger = get_logger()


class ModelsPage:
    """Page for viewing and managing models"""

    def __init__(self):
        """Initialize the models page"""
        # Initialize models-related session state
        SessionManager.init_models_state()

        # Fetch models on initialization
        self.refresh_models()

        # Initialize components
        self.model_details = ModelDetails()
        self.model_list = ModelList()
        self.model_search = ModelSearch()

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

    @exception_handler
    def refresh_models(self):
        """Refresh the list of available models"""
        st.session_state.available_models = OllamaAPI.get_local_models()
        logger.info(f"Loaded {len(st.session_state.available_models)} models")

    def show_model_details(self, model_name: str):
        """
        Show model details for the given model

        Args:
            model_name: Name of the model to display details for
        """
        st.session_state.show_model_details = model_name
        st.rerun()

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model

        Args:
            model_name: Name of the model to delete

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        success = OllamaAPI.delete_model(model_name)
        if success:
            time.sleep(1)
            self.refresh_models()
            st.rerun()
        return success

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
        self.model_search.render_sidebar_search(self.pull_model)

        # Check if we should show model details
        if st.session_state.show_model_details:
            # Use the model details component
            if self.model_details.render():
                # If returned True, it means "back to list" was clicked
                st.rerun()
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
                self.model_list.render(
                    models,
                    on_show_details=self.show_model_details,
                    on_delete=self.delete_model,
                )
            else:
                self.model_search.render_main_search(self.pull_model)
