import streamlit as st
from typing import List, Dict, Any, Callable, Optional, cast, Union

from app.api.ollama_api import OllamaAPI
from app.utils.logger import get_logger

# Get application logger
logger = get_logger()


class ModelSearch:
    """Component for searching and displaying model search results"""

    def __init__(self):
        """Initialize the model search component"""
        # Initialize session state for search results if needed
        if "search_results" not in st.session_state:
            st.session_state.search_results = []

        if "search_results_tab" not in st.session_state:
            st.session_state.search_results_tab = []

    def render_sidebar_search(self, on_pull_model: Callable[[str], Union[None, bool]]):
        """
        Render the model search box in the sidebar

        Args:
            on_pull_model: Callback when user wants to pull a model
        """
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
                                on_pull_model(model["name"].strip())
                            else:
                                st.error("Invalid model name")

    def render_main_search(self, on_pull_model: Callable[[str], Union[None, bool]]):
        """
        Render the main search tab UI

        Args:
            on_pull_model: Callback when user wants to pull a model
        """
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
                                    on_pull_model(model["name"].strip())
                                else:
                                    st.error("Invalid model name")
        else:
            st.info("No models found matching your criteria")
