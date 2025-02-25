import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Callable, Optional, cast

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ModelList:
    """Component for displaying and managing a list of models"""

    def __init__(self):
        """Initialize the model list component"""
        # Initialize session state for confirmations if needed
        if "confirm_delete" not in st.session_state:
            st.session_state.confirm_delete = None

    def format_model_data(self, models: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Format model data for display

        Args:
            models: List of models to format

        Returns:
            Formatted DataFrame
        """
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

        return pd.DataFrame(model_data)

    def render(
        self,
        models: List[Dict[str, Any]],
        on_show_details: Callable[[str], None],
        on_delete: Callable[[str], bool],
    ):
        """
        Render the models list

        Args:
            models: List of models to display
            on_show_details: Callback when user wants to view model details
            on_delete: Callback when user confirms model deletion
        """
        st.subheader("Installed Models")

        if not models:
            st.info("No models found. Use the sidebar to pull models.")
        else:
            # Create a dataframe for better display
            df = self.format_model_data(models)

            # Display the table
            st.dataframe(df, use_container_width=True)

            # Select a model for actions
            st.subheader("Model Actions")
            model_options = [str(m.get("model", "Unknown")) for m in models]
            selected_model = st.selectbox("Select a model", model_options)

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Show Details", key=f"details_{selected_model}"):
                    # Cast to string to satisfy type checker
                    on_show_details(cast(str, selected_model))

            with col2:
                if st.button("Delete Model", key=f"delete_{selected_model}"):
                    # Cast to string to satisfy type checker
                    model_name = cast(str, selected_model)
                    if st.session_state.get("confirm_delete") != model_name:
                        st.session_state.confirm_delete = model_name
                        st.warning(f"Click again to confirm deletion of {model_name}")
                    else:
                        with st.spinner(f"Deleting {model_name}..."):
                            success = on_delete(model_name)
                            if success:
                                st.success(f"Successfully deleted {model_name}")
                                st.session_state.confirm_delete = None
                            else:
                                st.error(f"Failed to delete {model_name}")
