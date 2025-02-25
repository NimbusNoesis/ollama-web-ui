"""
Reusable component for model selection
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ModelSelector:
    """Reusable component for selecting models"""

    def __init__(
        self,
        on_select: Optional[Callable[[Dict[str, Any]], None]] = None,
        key_prefix: str = "",
    ):
        """
        Initialize the model selector

        Args:
            on_select: Optional callback when a model is selected
            key_prefix: Prefix for Streamlit session state keys
        """
        self.on_select = on_select
        self.key_prefix = key_prefix

        # Construct unique session state keys
        self.selected_key = f"{key_prefix}selected_model"
        self.models_key = f"{key_prefix}available_models"

        # Initialize session state if needed
        if self.models_key not in st.session_state:
            st.session_state[self.models_key] = []

        if self.selected_key not in st.session_state:
            st.session_state[self.selected_key] = None

    def refresh_models(self):
        """Refresh the list of available models"""
        try:
            st.session_state[self.models_key] = OllamaAPI.get_local_models()
            logger.info(f"Loaded {len(st.session_state[self.models_key])} models")
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}", exc_info=True)
            st.error(f"Error loading models: {str(e)}")

    def handle_selection(self, model_info: Dict[str, Any]):
        """
        Handle model selection

        Args:
            model_info: Information about the selected model
        """
        st.session_state[self.selected_key] = model_info

        if self.on_select:
            self.on_select(model_info)

    def render(self, show_refresh: bool = True):
        """
        Render the model selector

        Args:
            show_refresh: Whether to show the refresh button
        """
        # If we have no models, load them
        if not st.session_state[self.models_key]:
            self.refresh_models()

        # Show refresh button if requested
        if show_refresh:
            if st.button("🔄 Refresh Models", key=f"{self.key_prefix}refresh_models"):
                self.refresh_models()

        # Get the list of models
        models = st.session_state[self.models_key]

        if not models:
            st.warning("No models available. Please pull some models first.")
            return

        # Extract model names for the selector
        model_names = [model.get("model", "Unknown") for model in models]

        # Create a selectbox for model selection
        selected_index = st.selectbox(
            "Select Model",
            range(len(model_names)),
            format_func=lambda i: model_names[i],
            key=f"{self.key_prefix}model_selector",
        )

        # Handle selection
        if selected_index is not None:
            selected_model = models[selected_index]

            # Only update if the selection changed
            current = st.session_state.get(self.selected_key)
            if current is None or current.get("model") != selected_model.get("model"):
                self.handle_selection(selected_model)

        # Display the currently selected model
        if st.session_state[self.selected_key]:
            model_info = st.session_state[self.selected_key]
            st.markdown(f"**Selected:** {model_info}")

            # Show some basic model info
            with st.expander("Model Details", expanded=False):
                st.json(model_info)

        return st.session_state[self.selected_key]
