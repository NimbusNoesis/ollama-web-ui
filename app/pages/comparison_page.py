import streamlit as st
from typing import Dict, List, Any, Optional, Union, cast
from app.api.ollama_api import OllamaAPI
from app.components.model_comparison import ModelComparison
from app.utils.logger import get_logger
from app.utils.session_manager import SessionManager
from app.components.ui_components import collapsible_section
import time

# Get application logger
logger = get_logger()


class ComparisonPage:
    """Page for comparing outputs from multiple models side by side"""

    def __init__(self):
        """Initialize the comparison page"""
        # Initialize comparison-related session state
        SessionManager.init_comparison_state()

        # Initialize model comparison component
        self.model_comparison = ModelComparison()

    def run_comparison(self, selected_models: List[str], prompt: str) -> Dict[str, str]:
        """
        Run a comparison across multiple models

        Args:
            selected_models: List of model names to compare
            prompt: The prompt to send to all models

        Returns:
            Dictionary mapping model names to their outputs
        """
        results = {}

        # Create chat message
        messages = [{"role": "user", "content": prompt}]

        # Run each model with the same prompt
        for model_name in selected_models:
            with st.status(f"Running {model_name}..."):
                try:
                    # Non-streaming mode for comparison
                    response = OllamaAPI.chat_completion(
                        model=model_name,
                        messages=cast(List[Dict[str, Union[str, List[Any]]]], messages),
                        stream=False,
                    )

                    # Extract the response text using safe dictionary access
                    results[model_name] = response.get("message", {}).get(
                        "content", "Error: No response content"
                    )

                except Exception as e:
                    results[model_name] = f"Error: {str(e)}"

        # Store results in session state
        st.session_state.comparison_results = results

        return results

    def render(self):
        """Render the comparison page"""
        st.title("Model Comparison")
        st.write("Compare responses from different models side by side")

        # Get list of installed models
        models = OllamaAPI.get_local_models()

        if not models:
            st.warning(
                "No models installed. Please install models from the Models page first."
            )
        else:
            # Render the comparison component
            self.model_comparison.render(models, self.run_comparison)
