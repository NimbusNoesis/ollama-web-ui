import streamlit as st
from typing import Dict, List, Any, Union, cast
from app.api.ollama_api import OllamaAPI
from app.components.model_comparison import ModelComparison
import re


class ComparisonPage:
    """Page for comparing outputs from multiple models side by side"""

    def __init__(self):
        """Initialize the comparison page"""
        # Initialize session state for comparison results
        if "comparison_results" not in st.session_state:
            st.session_state.comparison_results = {}

        if "selected_comparison_models" not in st.session_state:
            st.session_state.selected_comparison_models = []

        # Initialize the model comparison component
        self.model_comparison = ModelComparison()

    def _process_thinking_tags(self, content: str) -> str:
        """
        Process <think> tags in content and convert them to expandable sections

        Args:
            content: The message content to process

        Returns:
            Processed content with <think> tags converted to expandable sections
        """
        if "<think>" not in content:
            return content

        # Use regex to find all <think> sections
        pattern = r"<think>(.*?)</think>"

        def replacement(match):
            thinking_content = match.group(1).strip()
            # Match the exact HTML structure and styling from chat_ui.py
            return f"""
<details>
    <summary><strong>Thinking</strong> (click to expand)</summary>
    <div class="thinking-content" style="padding: 10px; border-left: 3px solid #ccc; margin: 10px 0;">
        {thinking_content}
    </div>
</details>
<hr style="border: none; border-top: 1px solid rgba(204, 204, 204, 0.4); margin: 10px 0;"/>
"""

        # Replace all <think> tags with expandable sections
        processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        return processed_content

    def run_comparison(self, selected_models: List[str], prompt: str) -> Dict[str, str]:
        """
        Run a comparison across multiple models

        Args:
            selected_models: List of model names to compare
            prompt: The prompt to send to all models

        Returns:
            Dictionary mapping model names to their outputs
        """
        # Store the selected models in session state
        st.session_state.selected_comparison_models = selected_models

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

                    # Extract the response text handling both object and dict formats
                    content = ""
                    if hasattr(response, "message"):
                        msg = getattr(response, "message")
                        if hasattr(msg, "content"):
                            content = str(getattr(msg, "content", ""))
                    elif isinstance(response, dict) and "message" in response:
                        content = str(response["message"].get("content", ""))

                    if not content:
                        content = "Error: No response content"

                    # Process any thinking tags in the response
                    processed_content = self._process_thinking_tags(content)
                    results[model_name] = processed_content

                except Exception as e:
                    results[model_name] = f"Error: {str(e)}"

        # Store results in session state
        st.session_state.comparison_results = results

        return results

    def render(self):
        """Render the comparison page"""
        st.title("Model Comparison")
        st.write("Compare responses from different models side by side")

        # Get list of installed models and ensure it's in the right format
        models = OllamaAPI.get_local_models()
        formatted_models = []

        if models:
            for model in models:
                if isinstance(model, dict):
                    formatted_models.append(model)
                elif isinstance(model, str):
                    formatted_models.append({"name": model})
                else:
                    formatted_models.append({"name": str(model)})

            # Render the comparison component with formatted models
            self.model_comparison.render(formatted_models, self.run_comparison)
        else:
            st.warning(
                "No models installed. Please install models from the Models page first."
            )
