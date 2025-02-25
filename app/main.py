import streamlit as st
from .api.ollama_api import OllamaAPI
from .pages.models_page import ModelsPage
from .pages.chat_page import ChatPage
from .pages.comparison_page import ComparisonPage
from .pages.logs_page import LogsPage
from .utils.logger import get_logger

# Get application logger
logger = get_logger()

# Set page configuration
st.set_page_config(page_title="Ollama UI", page_icon="��", layout="wide")


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

    if st.sidebar.button("📊 Logs", key="nav_logs"):
        set_page("logs")

    # Check Ollama connection
    if not OllamaAPI.check_connection():
        logger.error("Unable to connect to Ollama service")
        st.error("Unable to connect to Ollama. Make sure it's running and try again.")
        st.info("You can download Ollama from https://ollama.com/")
        return

    # Render the current page
    current_page = st.session_state.page

    try:
        if current_page == "models":
            models_page = ModelsPage()
            models_page.render()
        elif current_page == "chat":
            chat_page = ChatPage()
            chat_page.render()
        elif current_page == "compare":
            comparison_page = ComparisonPage()
            comparison_page.render()
        elif current_page == "logs":
            logs_page = LogsPage()
            logs_page.render()
        else:
            logger.warning(f"Unknown page requested: {current_page}")
            st.error(f"Unknown page: {current_page}")
            set_page("models")
    except Exception as e:
        logger.error(f"Error rendering page {current_page}: {str(e)}", exc_info=True)
        st.error(f"An error occurred while loading the page: {str(e)}")
        if st.button("Reload"):
            st.rerun()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Ollama UI - Built with Streamlit")
    st.sidebar.caption("© 2023-2024")


if __name__ == "__main__":
    main()
