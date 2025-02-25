import streamlit as st
from typing import List, Dict, Any, Optional, Callable


class ModelComparison:
    """Component for displaying outputs from multiple models side by side"""

    def __init__(self):
        """Initialize the model comparison component"""
        # Initialize session state for model outputs if needed
        if "model_outputs" not in st.session_state:
            st.session_state.model_outputs = {}

        if "selected_models" not in st.session_state:
            st.session_state.selected_models = []

        if "comparison_prompt" not in st.session_state:
            st.session_state.comparison_prompt = ""

    def select_models(self, available_models: List[Dict[str, Any]]) -> List[str]:
        """
        Let the user select models to compare

        Args:
            available_models: List of available models

        Returns:
            List of selected model names
        """
        # Convert models to options for multiselect
        model_options = [
            model.get("model", model.get("name", "")) for model in available_models
        ]

        # Let the user select models
        selected_models = st.multiselect(
            "Select models to compare",
            options=model_options,
            default=(
                st.session_state.selected_models
                if st.session_state.selected_models
                else None
            ),
        )

        # Update session state
        st.session_state.selected_models = selected_models

        return selected_models

    def input_prompt(self) -> str:
        """
        Get the prompt for model comparison

        Returns:
            The prompt text
        """
        # Get the prompt from the user
        prompt = st.text_area(
            "Enter your prompt",
            value=st.session_state.comparison_prompt,
            height=100,
            placeholder="Enter the prompt you want to compare across models...",
        )

        # Update session state
        st.session_state.comparison_prompt = prompt if prompt is not None else ""
        return st.session_state.comparison_prompt

    def display_outputs(self, outputs: Dict[str, str]):
        """
        Display outputs from multiple models side by side

        Args:
            outputs: Dict mapping model names to their outputs
        """
        # Update session state
        st.session_state.model_outputs = outputs

        # Determine the number of columns based on output count
        num_outputs = len(outputs)

        if num_outputs == 0:
            st.info("No model outputs to display. Run a comparison first.")
            return

        if num_outputs == 1:
            # Just one model, use full width
            for model_name, output in outputs.items():
                st.subheader(f"Output from {model_name}")
                st.markdown(f"```\n{output}\n```")
        else:
            # Multiple models, create columns
            cols = st.columns(min(num_outputs, 3))  # Max 3 columns

            # Display each output in its own column
            for idx, (model_name, output) in enumerate(outputs.items()):
                col_idx = idx % len(cols)  # Wrap around if more than 3 outputs
                with cols[col_idx]:
                    st.subheader(f"{model_name}")
                    st.markdown(f"```\n{output}\n```")

                # Start a new row after every 3 models
                if col_idx == len(cols) - 1 and idx < num_outputs - 1:
                    st.markdown("---")
                    cols = st.columns(min(num_outputs - idx - 1, 3))

    def render(self, available_models: List[Dict[str, Any]], on_compare: Callable[[List[str], str], Dict[str, str]]):
        """
        Render the full comparison UI

        Args:
            available_models: List of available models
            on_compare: Callback function when the compare button is clicked
        """
        st.header("Model Comparison")

        # Model selection
        selected_models = self.select_models(available_models)

        # Prompt input
        prompt = self.input_prompt()

        # Run comparison button
        if st.button("Compare Models", disabled=not selected_models or not prompt):
            # Call the callback with selected models and prompt
            outputs = on_compare(selected_models, prompt)

            # Display the results
            self.display_outputs(outputs)
        else:
            # Display existing results if any
            if st.session_state.model_outputs:
                self.display_outputs(st.session_state.model_outputs)
