import streamlit as st
from .pages.models_page import ModelsPage
from .pages.chat_page import ChatPage
from .pages.comparison_page import ComparisonPage
from .pages.logs_page import LogsPage
from .pages.tools_page import ToolsPage
from .pages.agents_page import AgentsPage
from .utils.logger import get_logger

# Get application logger
logger = get_logger()

# Set page configuration
st.set_page_config(page_title="Ollama UI", page_icon="🤖", layout="wide")


# Initialize app state
def init_app_state():
    """Initialize application state variables"""
    if "page" not in st.session_state:
        st.session_state.page = "Chat"


def set_page(page_name: str):
    """Set the current page"""
    st.session_state.page = page_name


def main():
    """Main application entry point"""
    # Initialize app state
    init_app_state()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    pages = {
        "Chat": ChatPage,
        "Compare Models": ComparisonPage,
        "Models": ModelsPage,
        "Tools": ToolsPage,
        "Agents": AgentsPage,
        "Logs": LogsPage,
    }

    for page_name in pages:
        if st.sidebar.button(page_name, use_container_width=True):
            set_page(page_name)

    # Render the selected page
    page_class = pages[st.session_state.page]
    page = page_class()
    page.render()


if __name__ == "__main__":
    main()
