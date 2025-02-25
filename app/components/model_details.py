import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ModelDetails:
    """Component for displaying detailed information about a model"""

    def __init__(self):
        """Initialize the model details component"""
        # Initialize session state for showing model details if needed
        if "show_model_details" not in st.session_state:
            st.session_state.show_model_details = None

    def display_model_info(self, model_name: str) -> None:
        """
        Display detailed information about a model

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

    def render(self, model_name: Optional[str] = None) -> bool:
        """
        Render the model details component

        Args:
            model_name: Optional model name to display details for.
                        If None, will use the session state value

        Returns:
            bool: True if going back to model list, False otherwise
        """
        # Use provided model name or get from session state
        display_model = model_name or st.session_state.show_model_details

        if not display_model:
            return False

        # Display model information
        self.display_model_info(display_model)

        # Back button
        if st.button("Back to Models List"):
            st.session_state.show_model_details = None
            return True

        return False
