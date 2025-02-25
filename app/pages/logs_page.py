import os
import streamlit as st
import base64
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import Counter
import time
import logging
import pandas as pd

from app.utils.logger import get_logger, LOGS_DIR
from app.utils.session_manager import SessionManager
from app.components.ui_components import collapsible_section, status_indicator
from app.components.log_viewer import LogViewer

# Get application logger
logger = get_logger()


class LogsPage:
    """Page for viewing application logs"""

    def __init__(self):
        """Initialize the logs page"""
        # Initialize logs-related session state
        SessionManager.init_logs_state()

        # Initialize the log viewer
        self.log_viewer = LogViewer()

    def get_log_files(self) -> List[Tuple[str, datetime]]:
        """
        Get all log files with their creation timestamps

        Returns:
            List of tuples containing (filename, timestamp)
        """
        log_files = []

        try:
            # Ensure logs directory exists
            if not os.path.exists(LOGS_DIR):
                logger.warning(f"Logs directory does not exist: {LOGS_DIR}")
                return []

            # Get all log files
            for filename in os.listdir(LOGS_DIR):
                if filename.endswith(".log"):
                    file_path = os.path.join(LOGS_DIR, filename)
                    # Get file creation time
                    timestamp = datetime.fromtimestamp(os.path.getctime(file_path))
                    log_files.append((filename, timestamp))

            # Sort by timestamp (newest first)
            log_files.sort(key=lambda x: x[1], reverse=True)

        except Exception as e:
            logger.error(f"Error getting log files: {str(e)}", exc_info=True)

        return log_files

    def read_log_file(self, filename: str) -> List[str]:
        """
        Read the contents of a log file

        Args:
            filename: Name of the log file to read

        Returns:
            List of log lines
        """
        try:
            file_path = os.path.join(LOGS_DIR, filename)
            with open(file_path, "r") as f:
                return f.readlines()
        except Exception as e:
            logger.error(f"Error reading log file {filename}: {str(e)}", exc_info=True)
            return [f"Error reading log file: {str(e)}"]

    def extract_error_types(self, lines: List[str]) -> Set[str]:
        """
        Extract unique error types from log lines

        Args:
            lines: List of log lines

        Returns:
            Set of unique error types
        """
        error_types = set()

        # Regular expression to match error types
        error_pattern = r"Error: ([A-Za-z0-9_]+Error|Exception)"
        exception_pattern = r"Exception: ([A-Za-z0-9_]+Error|Exception)"
        type_pattern = r'"type": "([A-Za-z0-9_]+Error|Exception)"'

        for line in lines:
            # Check for error types in different formats
            for pattern in [error_pattern, exception_pattern, type_pattern]:
                matches = re.findall(pattern, line)
                error_types.update(matches)

            # Also check for common error keywords
            if "Error in" in line and ":" in line:
                parts = line.split("Error in")[1].split(":", 1)
                if len(parts) > 1:
                    error_part = parts[1].strip()
                    if (
                        error_part and len(error_part) < 50
                    ):  # Avoid capturing entire error messages
                        error_types.add(error_part)

        return error_types

    def filter_log_lines(
        self,
        lines: List[str],
        filter_text: str,
        level_filter: str,
        error_type_filter: str,
        full_text_search: str,
    ) -> List[str]:
        """
        Filter log lines based on filter criteria

        Args:
            lines: List of log lines
            filter_text: Text to filter by
            level_filter: Log level to filter by
            error_type_filter: Error type to filter by
            full_text_search: Full text search query

        Returns:
            Filtered list of log lines
        """
        if (
            not filter_text
            and level_filter == "All"
            and error_type_filter == "All"
            and not full_text_search
        ):
            return lines

        filtered_lines = []
        for line in lines:
            # Check if line contains the filter text
            if filter_text and filter_text.lower() not in line.lower():
                continue

            # Check if line matches the log level
            if level_filter != "All":
                # Extract log level from line (format: timestamp - name - LEVEL - message)
                parts = line.split(" - ")
                if len(parts) >= 3:
                    line_level = parts[2].strip()
                    if line_level != level_filter:
                        continue

            # Check if line contains the error type
            if error_type_filter != "All" and error_type_filter not in line:
                continue

            # Check if line matches the full text search query
            if full_text_search:
                # Split the search query into words for more flexible matching
                search_terms = full_text_search.lower().split()
                if not all(term in line.lower() for term in search_terms):
                    continue

            filtered_lines.append(line)

        return filtered_lines

    def highlight_search_terms(self, text: str, search_terms: List[str]) -> str:
        """
        Highlight search terms in text using HTML

        Args:
            text: Text to highlight in
            search_terms: List of terms to highlight

        Returns:
            HTML-formatted text with highlights
        """
        if not search_terms:
            return text

        # Escape HTML special characters
        escaped_text = (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

        # Highlight each term
        for term in search_terms:
            if not term:
                continue

            # Case-insensitive replacement with HTML highlight
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            escaped_text = pattern.sub(
                f'<span style="background-color: #FFFF00; color: #000000; font-weight: bold;">{term}</span>',
                escaped_text,
            )

        return escaped_text

    def get_log_statistics(self, lines: List[str]) -> Dict:
        """
        Generate statistics about the log file

        Args:
            lines: List of log lines

        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_lines": len(lines),
            "log_levels": Counter(),
            "error_types": Counter(),
            "timestamp_range": {"first": None, "last": None},
            "common_messages": Counter(),
        }

        # Regular expression for timestamp extraction
        timestamp_pattern = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"

        for line in lines:
            # Count log levels
            parts = line.split(" - ")
            if len(parts) >= 3:
                level = parts[2].strip()
                stats["log_levels"][level] += 1

                # Extract message part for common messages
                if len(parts) >= 4:
                    # Get just the beginning of the message (first 50 chars)
                    message = parts[3].strip()[:50]
                    if message:
                        stats["common_messages"][message] += 1

            # Extract timestamp
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                    if (
                        stats["timestamp_range"]["first"] is None
                        or timestamp < stats["timestamp_range"]["first"]
                    ):
                        stats["timestamp_range"]["first"] = timestamp
                    if (
                        stats["timestamp_range"]["last"] is None
                        or timestamp > stats["timestamp_range"]["last"]
                    ):
                        stats["timestamp_range"]["last"] = timestamp
                except ValueError:
                    pass

            # Count error types
            if "ERROR" in line:
                # Extract error types using the same patterns as in extract_error_types
                error_pattern = r"Error: ([A-Za-z0-9_]+Error|Exception)"
                exception_pattern = r"Exception: ([A-Za-z0-9_]+Error|Exception)"
                type_pattern = r'"type": "([A-Za-z0-9_]+Error|Exception)"'

                for pattern in [error_pattern, exception_pattern, type_pattern]:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        stats["error_types"][match] += 1

        return stats

    def render_statistics(self, stats: Dict):
        """
        Render statistics about the log file

        Args:
            stats: Dictionary of statistics
        """
        with st.expander("Log Statistics", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("General")
                st.write(f"Total lines: {stats['total_lines']}")

                if (
                    stats["timestamp_range"]["first"]
                    and stats["timestamp_range"]["last"]
                ):
                    first = stats["timestamp_range"]["first"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    last = stats["timestamp_range"]["last"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    duration = (
                        stats["timestamp_range"]["last"]
                        - stats["timestamp_range"]["first"]
                    )
                    st.write(f"Time range: {first} to {last}")
                    st.write(f"Duration: {duration}")

                st.subheader("Log Levels")
                for level, count in sorted(
                    stats["log_levels"].items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (count / stats["total_lines"]) * 100
                    st.write(f"{level}: {count} ({percentage:.1f}%)")

            with col2:
                if stats["error_types"]:
                    st.subheader("Error Types")
                    for error_type, count in stats["error_types"].most_common(10):
                        st.write(f"{error_type}: {count}")

                st.subheader("Common Messages")
                for message, count in stats["common_messages"].most_common(5):
                    if count > 1:  # Only show repeated messages
                        st.write(f"'{message}...' - {count} occurrences")

    def render_sidebar(self):
        """Render the sidebar for logs options"""
        st.sidebar.header("Logs Settings")

        # Get all log files
        log_files = self.get_log_files()

        if not log_files:
            st.sidebar.warning("No log files found")
            return

        # Create a list of log file options with timestamps
        log_options = [
            f"{filename} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
            for filename, timestamp in log_files
        ]

        # Get filenames only for internal use
        filenames = [filename for filename, _ in log_files]

        # Select log file
        selected_option = st.sidebar.selectbox(
            "Select Log File",
            options=log_options,
            index=0,  # Default to the most recent log file
        )

        # Extract the filename from the selected option
        selected_filename = filenames[log_options.index(selected_option)]
        st.session_state.selected_log_file = selected_filename

        # Filter options
        st.sidebar.subheader("Filter Options")

        # Text filter
        st.session_state.log_filter = st.sidebar.text_input(
            "Quick Filter",
            value=st.session_state.log_filter,
            help="Filter logs containing this text (simple substring match)",
        )

        # Full text search
        st.session_state.log_full_text_search = st.sidebar.text_input(
            "Full Text Search",
            value=st.session_state.log_full_text_search,
            help="Search for logs containing all these words (space-separated)",
        )

        # Log level filter
        st.session_state.log_level_filter = st.sidebar.selectbox(
            "Log Level",
            options=["All", "INFO", "WARNING", "ERROR", "DEBUG"],
            index=["All", "INFO", "WARNING", "ERROR", "DEBUG"].index(
                st.session_state.log_level_filter
            ),
        )

        # Error type filter
        # First read the log file to extract error types
        if st.session_state.selected_log_file:
            log_lines = self.read_log_file(st.session_state.selected_log_file)
            error_types = self.extract_error_types(log_lines)

            # Create options list with "All" as the first option
            error_type_options = ["All"] + sorted(list(error_types))

            # Error type filter
            st.session_state.error_type_filter = st.sidebar.selectbox(
                "Error Type",
                options=error_type_options,
                index=(
                    error_type_options.index(st.session_state.error_type_filter)
                    if st.session_state.error_type_filter in error_type_options
                    else 0
                ),
                help="Filter logs by specific error type",
            )

        # Refresh button
        if st.sidebar.button("Refresh Logs"):
            st.rerun()

        # Delete log file button
        if st.sidebar.button("Delete Selected Log"):
            try:
                file_path = os.path.join(LOGS_DIR, selected_filename)
                os.remove(file_path)
                logger.info(f"Deleted log file: {selected_filename}")
                st.session_state.selected_log_file = None
                st.rerun()
            except Exception as e:
                logger.error(
                    f"Error deleting log file {selected_filename}: {str(e)}",
                    exc_info=True,
                )
                st.sidebar.error(f"Error deleting log file: {str(e)}")

    def render(self):
        """Render the logs page"""
        st.title("Application Logs")
        st.write("View and manage application log files")

        # Render the log viewer
        self.log_viewer.render()
