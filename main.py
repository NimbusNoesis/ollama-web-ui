import streamlit as st
import pandas as pd
import time
import ollama
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set page configuration
st.set_page_config(page_title="Ollama Model Manager", page_icon="🤖", layout="wide")

# Initialize session state for search results
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "show_model_details" not in st.session_state:
    st.session_state.show_model_details = None
if "search_results_tab" not in st.session_state:
    st.session_state.search_results_tab = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = 0
if "show_download_status" not in st.session_state:
    st.session_state.show_download_status = False
if "download_model_name" not in st.session_state:
    st.session_state.download_model_name = ""
if "download_complete" not in st.session_state:
    st.session_state.download_complete = False
if "download_error" not in st.session_state:
    st.session_state.download_error = None


# Function to get all local models
def get_local_models():
    try:
        models = ollama.list()
        return models.get("models", [])
    except Exception as e:
        st.error(f"Error fetching models: {str(e)}")
        logging.error(f"Failed to fetch models: {str(e)}", exc_info=True)
        return []


# Function to pull a model
def pull_model(model_name, from_sidebar=False):
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

        return True
    except Exception as e:
        error_msg = f"Error preparing to pull model {model_name}: {str(e)}"
        st.error(error_msg)
        logging.error(error_msg, exc_info=True)
        return False


# Function to delete a model
def delete_model(model_name):
    try:
        ollama.delete(model_name)
        return True
    except Exception as e:
        error_msg = f"Error deleting model {model_name}: {str(e)}"
        st.error(error_msg)
        logging.error(error_msg, exc_info=True)
        return False


# Function to get model info
def get_model_info(model_name):
    try:
        model_info = ollama.show(model_name)
        return model_info
    except Exception as e:
        error_msg = f"Error getting info for model {model_name}: {str(e)}"
        st.error(error_msg)
        logging.error(error_msg, exc_info=True)
        return {}


# Function to search for models from Ollama library
def search_models(query):
    try:
        # For now, we'll mock the search since the official ollama library doesn't
        # have a direct search function. In a real application, you might want to
        # query the Ollama registry or use a community API.

        # Common models that match various search terms
        model_catalog = [
            {"name": "llama3", "tags": ["meta", "llama", "large", "general"]},
            {"name": "llama3:8b", "tags": ["meta", "llama", "small", "general"]},
            {"name": "llama3:70b", "tags": ["meta", "llama", "huge", "general"]},
            {"name": "mistral", "tags": ["mistral", "general", "medium"]},
            {"name": "mixtral", "tags": ["mistral", "mixture", "general", "large"]},
            {"name": "phi", "tags": ["microsoft", "small", "general"]},
            {"name": "gemma", "tags": ["google", "general", "medium"]},
            {"name": "gemma:7b", "tags": ["google", "small", "general"]},
            {"name": "codellama", "tags": ["meta", "llama", "code", "programming"]},
            {"name": "vicuna", "tags": ["lmsys", "medium", "general"]},
            {"name": "orca-mini", "tags": ["small", "general"]},
            {"name": "stablelm", "tags": ["stability", "medium"]},
            {"name": "codegemma", "tags": ["google", "code", "programming"]},
            {"name": "deepseek-coder", "tags": ["deepseek", "code", "programming"]},
            {"name": "llava", "tags": ["vision", "multimodal", "image"]},
            {"name": "bakllava", "tags": ["vision", "multimodal", "image"]},
            {"name": "neural-chat", "tags": ["intel", "general", "medium"]},
            {"name": "yi", "tags": ["01ai", "general", "medium"]},
            {"name": "wizard", "tags": ["wizardlm", "general", "medium"]},
            {"name": "falcon", "tags": ["tii", "general", "medium"]},
            {"name": "qwen", "tags": ["alibaba", "general", "medium"]},
            {"name": "nous-hermes", "tags": ["nous", "general", "medium"]},
            {"name": "openhermes", "tags": ["open", "general", "medium"]},
            {"name": "mpt", "tags": ["mosaicml", "general", "medium"]},
            {"name": "dolphin", "tags": ["cognitivecomputations", "general", "medium"]},
            {"name": "command", "tags": ["cohere", "general", "instruction"]},
            {"name": "wizardmath", "tags": ["wizardlm", "math", "specific"]},
            {"name": "orca2", "tags": ["microsoft", "general", "medium"]},
            {"name": "tinyllama", "tags": ["tiny", "small", "efficient"]},
        ]

        # Simple search logic - match against model name or tags
        results = []
        query = query.lower().strip()

        for model in model_catalog:
            # Check if query is in model name or tags
            if query in model["name"].lower() or any(
                query in tag for tag in model["tags"]
            ):
                results.append(
                    {"name": model["name"], "tags": ", ".join(model["tags"])}
                )

        return results
    except Exception as e:
        st.error(f"Error searching models: {str(e)}")
        return []


# Function to check if Ollama is running and accessible
def check_ollama_connection():
    try:
        ollama.list()
        return True
    except Exception as e:
        st.error(f"Unable to connect to Ollama: {str(e)}")
        st.info(
            "Make sure Ollama is running and accessible. Check the installation at https://ollama.com/"
        )
        logging.error(f"Ollama connection failed: {str(e)}", exc_info=True)
        return False


# Function to handle the download process
def perform_download():
    if not st.session_state.show_download_status:
        return

    model_name = st.session_state.download_model_name

    # Create a full-width container at the top level
    overlay_container = st.container()

    with overlay_container:
        with st.status(f"Downloading {model_name}", expanded=True) as status:
            try:
                progress_bar = st.progress(0)

                # Perform the actual download
                for progress in ollama.pull(model_name, stream=True):
                    if "status" in progress:
                        status.update(label=f"Status: {progress['status']}")

                    if "completed" in progress and "total" in progress:
                        percent = progress["completed"] / progress["total"]
                        progress_bar.progress(percent)
                        status.update(
                            label=f"Downloaded: {int(percent * 100)}% of {model_name}"
                        )

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


# Check Ollama connection at startup
if not check_ollama_connection():
    st.stop()


# Main title
st.title("Ollama Model Manager")
st.write("Manage your Ollama models from this dashboard")

# Handle download overlay if active
if st.session_state.show_download_status:
    perform_download()

# Sidebar for actions
with st.sidebar:
    st.header("Model Actions")

    # Search for models section
    st.subheader("Search Models")
    search_query = st.text_input("Search term", placeholder="e.g., code, vision, small")

    if st.button("Search Models", disabled=not search_query):
        with st.spinner("Searching models..."):
            results = search_models(search_query)
            st.session_state.search_results = results
            if not results:
                st.info("No models found matching your search")

    # Display search results if available
    if st.session_state.search_results:
        st.write(f"Found {len(st.session_state.search_results)} models:")
        for i, model in enumerate(st.session_state.search_results):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{model['name']}**")
                    st.caption(f"Tags: {model['tags']}")
                with col2:
                    if st.button("Pull", key=f"pull_search_{i}"):
                        if model["name"] and model["name"].strip():
                            pull_model(model["name"].strip(), from_sidebar=True)
                        else:
                            st.error("Invalid model name")

    # Refresh button
    if st.button("Refresh Model List"):
        st.rerun()

# Main content area
models = get_local_models()

# Replace the tabs system with a radio button group
tab_options = ["📋 Models List", "📊 Model Details", "🔍 Search"]
selected_tab = st.radio(
    "View",
    tab_options,
    index=st.session_state.active_tab,
    horizontal=True,
    label_visibility="collapsed",
)

# Update the active tab in session state when changed
if tab_options.index(selected_tab) != st.session_state.active_tab:
    st.session_state.active_tab = tab_options.index(selected_tab)
    st.rerun()

# Now display content based on the selected tab
if selected_tab == "📋 Models List":
    # Models list content
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
                # Set session state to show details in the second tab
                st.session_state.show_model_details = selected_model
                st.session_state.active_tab = 1  # Set active tab to Model Details
                st.rerun()

        with col2:
            if st.button("Delete Model", key=f"delete_{selected_model}"):
                if st.session_state.get("confirm_delete") != selected_model:
                    st.session_state.confirm_delete = selected_model
                    st.warning(f"Click again to confirm deletion of {selected_model}")
                else:
                    with st.spinner(f"Deleting {selected_model}..."):
                        if delete_model(selected_model):
                            st.success(f"Successfully deleted {selected_model}")
                            st.session_state.confirm_delete = None
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to delete {selected_model}")

elif selected_tab == "📊 Model Details":
    # Model details content
    # Check if we have a model to show details for
    model_to_show = st.session_state.get("show_model_details")

    if model_to_show:
        st.subheader(f"Details for {model_to_show}")

        with st.spinner("Loading model details..."):
            model_info = get_model_info(model_to_show)

            if model_info:
                try:
                    # Basic model information
                    st.write("### Basic Information")

                    # Handle different API response formats
                    if "details" in model_info:
                        # New API format
                        basic_info = {
                            "Model Name": model_to_show,
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
                            "Model Name": model_to_show,
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
                    logging.error(
                        f"Error displaying model information: {str(e)}", exc_info=True
                    )
            else:
                st.info(f"No detailed information available for {model_to_show}")
    else:
        st.info("Select a model from the Models List tab to view its details")

elif selected_tab == "🔍 Search":
    # Search content
    st.subheader("Search for Models")

    search_tab_query = st.text_input(
        "Search term", placeholder="e.g., code, vision, small", key="search_tab_query"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Search", disabled=not search_tab_query):
            with st.spinner("Searching models..."):
                results = search_models(search_tab_query)
                st.session_state.search_results_tab = results

    with col2:
        filter_options = ["All", "Code", "Vision", "Small", "Medium", "Large"]
        selected_filter = st.selectbox("Filter by category", filter_options)

    # Display search results in a nicer format
    if "search_results_tab" in st.session_state and st.session_state.search_results_tab:
        results = st.session_state.search_results_tab

        # Apply filter if selected
        if selected_filter != "All":
            filter_term = selected_filter.lower()
            results = [r for r in results if filter_term in r["tags"].lower()]

        st.write(f"Found {len(results)} models:")

        # Create a grid of cards for search results
        cols = st.columns(3)
        for i, model in enumerate(results):
            with cols[i % 3]:
                with st.container(border=True):
                    st.write(f"**{model['name']}**")
                    st.caption(f"Tags: {model['tags']}")

                    # Check if model is already installed
                    installed = any(m.get("name") == model["name"] for m in models)

                    if installed:
                        st.success("✓ Installed")
                    else:
                        if st.button("Pull Model", key=f"pull_tab_{i}"):
                            if model["name"] and model["name"].strip():
                                pull_model(model["name"].strip(), from_sidebar=False)
                            else:
                                st.error("Invalid model name")
    else:
        st.info("Enter a search term and click 'Search' to find models")

# Footer
st.divider()
st.write("Powered by Ollama - Built with Streamlit")
