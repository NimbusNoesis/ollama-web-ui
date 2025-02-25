"""
Centralized session state management for the application
"""

import streamlit as st
from typing import Any, Dict, List, Optional


class SessionManager:
    """
    Manages the Streamlit session state across the application
    Eliminates duplicated initialization code
    """

    @staticmethod
    def init_session_if_needed(state_keys: Dict[str, Any]):
        """
        Initialize session state for given keys if they don't exist

        Args:
            state_keys: Dictionary of state keys and their default values
        """
        for key, default_value in state_keys.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def init_chat_state():
        """Initialize chat-related session state variables"""
        chat_state = {
            "messages": [],
            "user_input": "",
            "thinking": False,
            "current_chat_id": None,
            "chats": {},
            "chat_history": [],
            "available_models": [],
            "selected_model": None,
            "chat_temperature": 0.7,
            "system_prompt": "",
            "use_tools": False,
            "tools": [],
            "tool_choice": "auto",
            "use_installed_tools": False,
            "installed_tools": [],
        }
        SessionManager.init_session_if_needed(chat_state)

    @staticmethod
    def init_models_state():
        """Initialize models-related session state variables"""
        models_state = {
            "available_models": [],
            "selected_model": None,
            "model_info": None,
            "model_search_query": "",
            "search_results": [],
            "pull_progress": {},
        }
        SessionManager.init_session_if_needed(models_state)

    @staticmethod
    def init_tools_state():
        """Initialize tools-related session state variables"""
        # Standard templates for common tools
        tool_templates = {
            "Web Search": {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            "Calculator": {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "The mathematical expression to evaluate",
                            }
                        },
                        "required": ["expression"],
                    },
                },
            },
            "Weather Info": {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City or location name",
                            },
                            "units": {
                                "type": "string",
                                "description": "Units for temperature (celsius/fahrenheit)",
                                "enum": ["celsius", "fahrenheit"],
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
        }

        tools_state = {
            "tools": [],
            "selected_tool": None,
            "tool_templates": tool_templates,
        }
        SessionManager.init_session_if_needed(tools_state)

    @staticmethod
    def init_comparison_state():
        """Initialize comparison-related session state variables"""
        comparison_state = {
            "comparison_models": [],
            "comparison_prompt": "",
            "comparison_results": [],
            "comparing": False,
        }
        SessionManager.init_session_if_needed(comparison_state)

    @staticmethod
    def init_logs_state():
        """Initialize logs-related session state variables"""
        logs_state = {
            "log_level": "INFO",
            "log_search_query": "",
            "log_entries": [],
            "auto_refresh_logs": False,
        }
        SessionManager.init_session_if_needed(logs_state)

    @staticmethod
    def init_all():
        """Initialize all session state variables for the application"""
        SessionManager.init_chat_state()
        SessionManager.init_models_state()
        SessionManager.init_tools_state()
        SessionManager.init_comparison_state()
        SessionManager.init_logs_state()

    @staticmethod
    def set_page(page_name: str):
        """
        Set the current page and reset page-specific states

        Args:
            page_name: Name of the page to navigate to
        """
        st.session_state.page = page_name
        # Reset thinking state when navigating away from chat
        if page_name != "chat" and "thinking" in st.session_state:
            st.session_state.thinking = False
