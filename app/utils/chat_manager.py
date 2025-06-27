import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import streamlit as st

from .logger import get_logger

logger = get_logger()


class ChatManager:
    """Manages chat conversations, including saving and loading"""

    def __init__(self, chats_dir: str = "app/data/chats"):
        """
        Initialize the chat manager

        Args:
            chats_dir: Directory to store chat files
        """
        self.chats_dir = Path(chats_dir)

        # Create directory if it doesn't exist
        self.chats_dir.mkdir(parents=True, exist_ok=True)

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
        chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not title:
            title = f"Chat {chat_id}"

        st.session_state.chats[chat_id] = {
            "id": chat_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
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
            logger.error("Invalid chat ID: %s", chat_id)
            return False

        chat_data = st.session_state.chats[chat_id]
        chat_data["updated_at"] = datetime.now().isoformat()

        file_path = self.chats_dir / f"{chat_id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(chat_data, f, indent=2)
            logger.info("Saved chat %s to %s", chat_id, file_path)
            return True
        except Exception as e:
            logger.error("Error saving chat %s: %s", chat_id, str(e))
            return False

    def list_saved_chats(self) -> List[Dict[str, Any]]:
        """
        List all saved chats

        Returns:
            List of chat metadata dictionaries
        """
        chats = []

        try:
            for file_path in self.chats_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
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
                    logger.error("Error reading chat file %s: %s", file_path.name, str(e))
        except Exception as e:
            logger.error("Error listing chats: %s", str(e))

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
        file_path = self.chats_dir / f"{chat_id}.json"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                chat_data = json.load(f)

            st.session_state.chats[chat_id] = chat_data
            st.session_state.current_chat_id = chat_id
            st.session_state.chat_history = chat_data.get("messages", [])

            logger.info("Loaded chat %s from %s", chat_id, file_path)
            return True
        except Exception as e:
            logger.error("Error loading chat %s: %s", chat_id, str(e))
            return False

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat

        Args:
            chat_id: ID of chat to delete

        Returns:
            True if successful, False otherwise
        """
        file_path = self.chats_dir / f"{chat_id}.json"

        try:
            # Remove from memory
            if chat_id in st.session_state.chats:
                del st.session_state.chats[chat_id]

            # If current chat is being deleted, reset current chat
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = None
                st.session_state.chat_history = []

            # Remove file
            if file_path.exists():
                file_path.unlink()

            logger.info("Deleted chat %s", chat_id)
            return True
        except Exception as e:
            logger.error("Error deleting chat %s: %s", chat_id, str(e))
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
            logger.error("Invalid chat ID: %s", chat_id)
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        # Add to in-memory chat
        st.session_state.chats[chat_id]["messages"].append(message)
        st.session_state.chat_history.append(message)

        # Update timestamp
        st.session_state.chats[chat_id][
            "updated_at"
        ] = datetime.now().isoformat()

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
                content = msg["content"]
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
        Add a special message (like tool calls) to the chat

        Args:
            message: Complete message object with role and other properties
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
            logger.error("Invalid chat ID: %s", chat_id)
            return False

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()

        # Add to in-memory chat
        st.session_state.chats[chat_id]["messages"].append(message)
        st.session_state.chat_history.append(message)

        # Update timestamp
        st.session_state.chats[chat_id][
            "updated_at"
        ] = datetime.now().isoformat()

        # Auto-save chat
        self.save_chat(chat_id)

        return True

    def prepare_streaming_message(self, chat_id: Optional[str] = None) -> str:
        """
        Prepare a streaming message placeholder in the chat

        Args:
            chat_id: ID of chat to add to, or current chat if None

        Returns:
            ID of the prepared message
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id:
            # Create a new chat if none exists
            chat_id = self.create_new_chat()

        if chat_id not in st.session_state.chats:
            logger.error("Invalid chat ID: %s", chat_id)
            return ""

        # Create a placeholder message
        message_id = f"stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        message = {
            "role": "assistant",
            "content": "",  # Start empty
            "timestamp": datetime.now().isoformat(),
            "id": message_id,
            "is_streaming": True,
        }

        # Add to in-memory chat
        st.session_state.chats[chat_id]["messages"].append(message)
        st.session_state.chat_history.append(message)

        # Update timestamp
        st.session_state.chats[chat_id][
            "updated_at"
        ] = datetime.now().isoformat()

        return message_id

    def finalize_streaming_message(
        self, content: str, message_id: str, chat_id: Optional[str] = None
    ) -> bool:
        """
        Finalize a streaming message with the complete content

        Args:
            content: Final message content
            message_id: ID of the message to update
            chat_id: ID of chat containing the message, or current chat if None

        Returns:
            True if successful, False otherwise
        """
        if not chat_id:
            chat_id = st.session_state.current_chat_id

        if not chat_id:
            logger.error("No active chat found")
            return False

        if chat_id not in st.session_state.chats:
            logger.error("Invalid chat ID: %s", chat_id)
            return False

        # Find the message by ID
        found = False
        for i, message in enumerate(st.session_state.chats[chat_id]["messages"]):
            if message.get("id") == message_id:
                # Update the message content
                st.session_state.chats[chat_id]["messages"][i]["content"] = content
                st.session_state.chats[chat_id]["messages"][i]["is_streaming"] = False
                found = True
                break

        # Also update in chat history
        if found:
            for i, message in enumerate(st.session_state.chat_history):
                if message.get("id") == message_id:
                    st.session_state.chat_history[i]["content"] = content
                    st.session_state.chat_history[i]["is_streaming"] = False
                    break

        # Auto-save chat
        if found:
            self.save_chat(chat_id)
            return True
        else:
            logger.error("Message with ID %s not found in chat %s", message_id, chat_id)
            return False
