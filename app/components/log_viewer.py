"""
Reusable component for viewing and filtering log files
"""

import os
import re
import base64
import streamlit as st
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Callable, Any
from collections import Counter
from app.utils.logger import get_logger, LOGS_DIR

# Get application logger
logger = get_logger()


class LogViewer:
    """Reusable component for viewing and filtering log files"""

    def __init__(self, logs_dir: str = LOGS_DIR, key_prefix: str = ""):
        """
        Initialize the log viewer

        Args:
            logs_dir: Directory containing log files
            key_prefix: Prefix for Streamlit session state keys
        """
        self.logs_dir = logs_dir
        self.key_prefix = key_prefix

        # Construct unique session state keys
        self.selected_file_key = f"{key_prefix}selected_log_file"
        self.filter_key = f"{key_prefix}log_filter"
        self.search_key = f"{key_prefix}log_full_text_search"
        self.level_key = f"{key_prefix}log_level_filter"
        self.error_type_key = f"{key_prefix}error_type_filter"

        # Initialize session state if needed
        if self.selected_file_key not in st.session_state:
            st.session_state[self.selected_file_key] = None

        if self.filter_key not in st.session_state:
            st.session_state[self.filter_key] = ""

        if self.search_key not in st.session_state:
            st.session_state[self.search_key] = ""

        if self.level_key not in st.session_state:
            st.session_state[self.level_key] = "All"

        if self.error_type_key not in st.session_state:
            st.session_state[self.error_type_key] = "All"

    def get_log_files(self) -> List[Tuple[str, datetime]]:
        """
        Get all log files with their creation timestamps

        Returns:
            List of tuples containing (filename, timestamp)
        """
        log_files = []

        try:
            # Ensure logs directory exists
            if not os.path.exists(self.logs_dir):
                logger.warning(f"Logs directory does not exist: {self.logs_dir}")
                return []

            # Get all log files
            for filename in os.listdir(self.logs_dir):
                if filename.endswith(".log"):
                    file_path = os.path.join(self.logs_dir, filename)
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
            file_path = os.path.join(self.logs_dir, filename)
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

    def render_sidebar_options(self, log_files: List[Tuple[str, datetime]]):
        """
        Render the sidebar for logs options

        Args:
            log_files: List of log files
        """
        st.sidebar.header("Logs Settings")

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
            key=f"{self.key_prefix}log_selector",
        )

        # Extract the filename from the selected option
        selected_filename = filenames[log_options.index(selected_option)]
        st.session_state[self.selected_file_key] = selected_filename

        # Filter options
        st.sidebar.subheader("Filter Options")

        # Text filter
        st.session_state[self.filter_key] = st.sidebar.text_input(
            "Quick Filter",
            value=st.session_state[self.filter_key],
            help="Filter logs containing this text (simple substring match)",
            key=f"{self.key_prefix}quick_filter",
        )

        # Full text search
        st.session_state[self.search_key] = st.sidebar.text_input(
            "Full Text Search",
            value=st.session_state[self.search_key],
            help="Search for logs containing all these words (space-separated)",
            key=f"{self.key_prefix}full_search",
        )

        # Log level filter
        st.session_state[self.level_key] = st.sidebar.selectbox(
            "Log Level",
            options=["All", "INFO", "WARNING", "ERROR", "DEBUG"],
            index=["All", "INFO", "WARNING", "ERROR", "DEBUG"].index(
                st.session_state[self.level_key]
            ),
            key=f"{self.key_prefix}level_filter",
        )

        # Error type filter
        # First read the log file to extract error types
        if st.session_state[self.selected_file_key]:
            log_lines = self.read_log_file(st.session_state[self.selected_file_key])
            error_types = self.extract_error_types(log_lines)

            # Create options list with "All" as the first option
            error_type_options = ["All"] + sorted(list(error_types))

            # Error type filter
            st.session_state[self.error_type_key] = st.sidebar.selectbox(
                "Error Type",
                options=error_type_options,
                index=(
                    error_type_options.index(st.session_state[self.error_type_key])
                    if st.session_state[self.error_type_key] in error_type_options
                    else 0
                ),
                help="Filter logs by specific error type",
                key=f"{self.key_prefix}error_type_filter",
            )

        # Refresh button
        if st.sidebar.button("Refresh Logs", key=f"{self.key_prefix}refresh_logs"):
            st.rerun()

        # Delete log file button
        if st.sidebar.button("Delete Selected Log", key=f"{self.key_prefix}delete_log"):
            selected_filename = st.session_state[self.selected_file_key]
            try:
                file_path = os.path.join(self.logs_dir, selected_filename)
                os.remove(file_path)
                logger.info(f"Deleted log file: {selected_filename}")
                st.session_state[self.selected_file_key] = None
                st.rerun()
            except Exception as e:
                logger.error(
                    f"Error deleting log file {selected_filename}: {str(e)}",
                    exc_info=True,
                )
                st.sidebar.error(f"Error deleting log file: {str(e)}")

    def render(self):
        """Render the log viewer"""
        # Get all log files
        log_files = self.get_log_files()

        # Render sidebar options
        self.render_sidebar_options(log_files)

        # Display the selected log file
        if st.session_state[self.selected_file_key]:
            st.subheader(f"Log File: {st.session_state[self.selected_file_key]}")

            # Add download button
            log_path = os.path.join(
                self.logs_dir, st.session_state[self.selected_file_key]
            )
            if os.path.exists(log_path):
                with open(log_path, "rb") as file:
                    contents = file.read()
                    b64 = base64.b64encode(contents).decode()
                    download_button_str = f"""
                        <a href="data:file/txt;base64,{b64}" download="{st.session_state[self.selected_file_key]}">
                            <button style="background-color:#4CAF50;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;">
                                Download Log File
                            </button>
                        </a>
                    """
                    st.markdown(download_button_str, unsafe_allow_html=True)

            # Read log file
            log_lines = self.read_log_file(st.session_state[self.selected_file_key])

            # Generate and display statistics
            stats = self.get_log_statistics(log_lines)
            self.render_statistics(stats)

            # Apply filters
            filtered_lines = self.filter_log_lines(
                log_lines,
                st.session_state[self.filter_key],
                st.session_state[self.level_key],
                st.session_state[self.error_type_key],
                st.session_state[self.search_key],
            )

            # Display filter information
            active_filters = []
            if st.session_state[self.filter_key]:
                active_filters.append(
                    f"Quick filter: '{st.session_state[self.filter_key]}'"
                )
            if st.session_state[self.search_key]:
                active_filters.append(
                    f"Full text: '{st.session_state[self.search_key]}'"
                )
            if st.session_state[self.level_key] != "All":
                active_filters.append(f"Level: {st.session_state[self.level_key]}")
            if st.session_state[self.error_type_key] != "All":
                active_filters.append(
                    f"Error type: {st.session_state[self.error_type_key]}"
                )

            if active_filters:
                st.info(f"Filtered by: {', '.join(active_filters)}")
                st.write(
                    f"Showing {len(filtered_lines)} of {len(log_lines)} log entries"
                )

                # Add export filtered logs button
                if filtered_lines and len(filtered_lines) < len(log_lines):
                    filtered_content = "".join(filtered_lines)
                    b64_filtered = base64.b64encode(filtered_content.encode()).decode()

                    # Generate a filename for the filtered logs
                    base_name = os.path.splitext(
                        st.session_state[self.selected_file_key]
                    )[0]
                    filtered_filename = f"{base_name}_filtered.log"

                    export_button_str = f"""
                        <a href="data:file/txt;base64,{b64_filtered}" download="{filtered_filename}">
                            <button style="background-color:#2196F3;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer;margin-top:10px;">
                                Export Filtered Logs
                            </button>
                        </a>
                    """
                    st.markdown(export_button_str, unsafe_allow_html=True)

                    # Add option to save filtered logs to disk
                    if st.button(
                        "Save Filtered Logs to Disk",
                        key=f"{self.key_prefix}save_filtered",
                    ):
                        try:
                            filtered_path = os.path.join(
                                self.logs_dir, filtered_filename
                            )
                            with open(filtered_path, "w") as f:
                                f.write(filtered_content)
                            logger.info(f"Saved filtered logs to {filtered_filename}")
                            st.success(f"Filtered logs saved to {filtered_filename}")
                        except Exception as e:
                            logger.error(
                                f"Error saving filtered logs: {str(e)}", exc_info=True
                            )
                            st.error(f"Error saving filtered logs: {str(e)}")

            # Display log content
            if filtered_lines:
                # If using full text search, highlight the search terms
                if st.session_state[self.search_key]:
                    search_terms = st.session_state[self.search_key].split()

                    # Create HTML with highlighted terms
                    highlighted_lines = [
                        self.highlight_search_terms(line, search_terms)
                        for line in filtered_lines
                    ]

                    # Join lines and display as HTML
                    highlighted_content = "<br>".join(highlighted_lines)
                    st.markdown(
                        f"""<div style="background-color: #1E1E1E; color: #D4D4D4; padding: 10px;
                        font-family: monospace; white-space: pre-wrap;
                        height: 500px; overflow-y: auto; border-radius: 5px;
                        font-size: 14px; line-height: 1.5;">{highlighted_content}</div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    # Display as regular text area
                    log_content = "".join(filtered_lines)
                    st.text_area("Log Content", log_content, height=500)
            else:
                st.warning("No log entries match the current filters")
        else:
            st.info("Select a log file from the sidebar to view its contents")
