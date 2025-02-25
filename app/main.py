import streamlit as st
import logging
from .api.ollama_api import OllamaAPI
from .pages.models_page import ModelsPage
from .pages.chat_page import ChatPage
from .pages.comparison_page import ComparisonPage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set page configuration
st.set_page_config(page_title="Ollama UI", page_icon="🤖", layout="wide")


# Initialize app state
def init_app_state():
    """Initialize application state variables"""
    if "page" not in st.session_state:
        st.session_state.page = "models"


def set_page(page_name: str):
    """Set the current page"""
    st.session_state.page = page_name
    # Reset other states that should be cleared on page change
    if page_name != "chat" and "thinking" in st.session_state:
        st.session_state.thinking = False


def main():
    """Main application entry point"""
    # Initialize app state
    init_app_state()

    # Title and navigation in the sidebar
    st.sidebar.title("Ollama UI")

    # Navigation links
    st.sidebar.header("Navigation")
    if st.sidebar.button("📋 Models", key="nav_models"):
        set_page("models")

    if st.sidebar.button("💬 Chat", key="nav_chat"):
        set_page("chat")

    if st.sidebar.button("🔄 Compare Models", key="nav_compare"):
        set_page("compare")

    # Check Ollama connection
    if not OllamaAPI.check_connection():
        st.error("Unable to connect to Ollama. Make sure it's running and try again.")
        st.info("You can download Ollama from https://ollama.com/")
        return

    # Render the current page
    current_page = st.session_state.page

    if current_page == "models":
        models_page = ModelsPage()
        models_page.render()
    elif current_page == "chat":
        chat_page = ChatPage()
        chat_page.render()
    elif current_page == "compare":
        comparison_page = ComparisonPage()
        comparison_page.render()
    else:
        st.error(f"Unknown page: {current_page}")
        set_page("models")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Ollama UI - Built with Streamlit")
    st.sidebar.caption("© 2023-2024")


if __name__ == "__main__":
    main()
