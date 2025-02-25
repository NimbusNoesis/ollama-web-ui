import json
import os
import logging
import datetime
from typing import List, Dict, Any, Optional, Union
import streamlit as st


class ChatManager:
    """Manages chat conversations, including saving and loading"""

    def __init__(self, chats_dir: str = "app/data/chats"):
        """
        Initialize the chat manager

        Args:
            chats_dir: Directory to store chat files
        """
        self.chats_dir = chats_dir

        # Create directory if it doesn't exist
        os.makedirs(self.chats_dir, exist_ok=True)

        # Initialize session state for chats if needed
        if "current_chat_id" not in st.session_state:
            st.session_state.current_chat_id = None

        if "chats" not in st.session_state:
            st.session_state.chats = {}

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

    def create_new_chat(self, title: Optional[str] = None) -> str:
        """
        Create a new chat session

        Args:
            title: Optional title for the chat

        Returns:
            The ID of the new chat
        """
        chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if not title:
            title = f"Chat {chat_id}"

        st.session_state.chats[chat_id] = {
            "id": chat_id,
            "title": title,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "messages": [],
        }

        st.session_state.current_chat_id = chat_id
        st.session_state.chat_history = []

        return chat_id

    def save_chat(self, chat_id: Optional[str] = None) -> bool:
        """
        Save a chat to disk

        Args:
            chat_id: ID of chat to save, or current chat if None

        Returns:
            True if successful, False otherwise
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id or chat_id not in st.session_state.chats:
            logging.error(f"Invalid chat ID: {chat_id}")
            return False

        chat_data = st.session_state.chats[chat_id]
        chat_data["updated_at"] = datetime.datetime.now().isoformat()

        file_path = os.path.join(self.chats_dir, f"{chat_id}.json")

        try:
            with open(file_path, "w") as f:
                json.dump(chat_data, f, indent=2)
            logging.info(f"Saved chat {chat_id} to {file_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving chat {chat_id}: {str(e)}")
            return False

    def list_saved_chats(self) -> List[Dict[str, Any]]:
        """
        List all saved chats

        Returns:
            List of chat metadata dictionaries
        """
        chats = []

        try:
            for filename in os.listdir(self.chats_dir):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.chats_dir, filename)
                    try:
                        with open(file_path, "r") as f:
                            chat_data = json.load(f)
                            chats.append(
                                {
                                    "id": chat_data.get("id"),
                                    "title": chat_data.get("title"),
                                    "created_at": chat_data.get("created_at"),
                                    "updated_at": chat_data.get("updated_at"),
                                    "message_count": len(chat_data.get("messages", [])),
                                }
                            )
                    except Exception as e:
                        logging.error(f"Error reading chat file {filename}: {str(e)}")
        except Exception as e:
            logging.error(f"Error listing chats: {str(e)}")

        # Sort by updated_at descending
        chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return chats

    def load_chat(self, chat_id: str) -> bool:
        """
        Load a chat from disk

        Args:
            chat_id: ID of chat to load

        Returns:
            True if successful, False otherwise
        """
        file_path = os.path.join(self.chats_dir, f"{chat_id}.json")

        try:
            with open(file_path, "r") as f:
                chat_data = json.load(f)

            st.session_state.chats[chat_id] = chat_data
            st.session_state.current_chat_id = chat_id
            st.session_state.chat_history = chat_data.get("messages", [])

            logging.info(f"Loaded chat {chat_id} from {file_path}")
            return True
        except Exception as e:
            logging.error(f"Error loading chat {chat_id}: {str(e)}")
            return False

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat

        Args:
            chat_id: ID of chat to delete

        Returns:
            True if successful, False otherwise
        """
        file_path = os.path.join(self.chats_dir, f"{chat_id}.json")

        try:
            # Remove from memory
            if chat_id in st.session_state.chats:
                del st.session_state.chats[chat_id]

            # If current chat is being deleted, reset current chat
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = None
                st.session_state.chat_history = []

            # Remove file
            if os.path.exists(file_path):
                os.remove(file_path)

            logging.info(f"Deleted chat {chat_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting chat {chat_id}: {str(e)}")
            return False

    def add_message(
        self, role: str, content: str, chat_id: Optional[str] = None
    ) -> bool:
        """
        Add a message to a chat

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            chat_id: ID of chat to add to, or current chat if None

        Returns:
            True if successful, False otherwise
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id:
            # Create a new chat if none exists
            chat_id = self.create_new_chat()

        if chat_id not in st.session_state.chats:
            logging.error(f"Invalid chat ID: {chat_id}")
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Add to in-memory chat
        st.session_state.chats[chat_id]["messages"].append(message)
        st.session_state.chat_history.append(message)

        # Update timestamp
        st.session_state.chats[chat_id][
            "updated_at"
        ] = datetime.datetime.now().isoformat()

        # Auto-save chat
        self.save_chat(chat_id)

        return True

    def get_messages_for_api(
        self, chat_id: Optional[str] = None
    ) -> List[Dict[str, Union[str, List[Any]]]]:
        """
        Get messages in the format needed for the API

        Args:
            chat_id: ID of chat to get messages for, or current chat if None

        Returns:
            List of message dictionaries with role and content keys
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id or chat_id not in st.session_state.chats:
            return []

        # Convert to format needed for API ({role, content} only)
        messages = []
        for msg in st.session_state.chats[chat_id]["messages"]:
            if msg.get("role") in ["user", "assistant", "system"]:
                # Ensure content can be a list
                content = msg["content"]
                if isinstance(content, str):
                    content = [content]  # Convert string to list
                messages.append({"role": msg["role"], "content": content})

        return messages

    def get_current_chat_title(self) -> str:
        """Get the title of the current chat"""
        chat_id = st.session_state.current_chat_id

        if not chat_id or chat_id not in st.session_state.chats:
            return "New Chat"

        return st.session_state.chats[chat_id].get("title", "Untitled Chat")

    def reset(self):
        """Reset the current chat session"""
        st.session_state.current_chat_id = None
        st.session_state.chat_history = []

    def add_special_message(
        self, message: Dict[str, Any], chat_id: Optional[str] = None
    ) -> bool:
        """
        Add a special message to a chat

        Args:
            message: The special message to add
            chat_id: ID of chat to add to, or current chat if None

        Returns:
            True if successful, False otherwise
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id:
            # Create a new chat if none exists
            chat_id = self.create_new_chat()

        if chat_id not in st.session_state.chats:
            logging.error(f"Invalid chat ID: {chat_id}")
            return False

        # Add to in-memory chat
        st.session_state.chats[chat_id]["messages"].append(message)
        st.session_state.chat_history.append(message)

        # Update timestamp
        st.session_state.chats[chat_id][
            "updated_at"
        ] = datetime.datetime.now().isoformat()

        # Auto-save chat
        self.save_chat(chat_id)

        return True
