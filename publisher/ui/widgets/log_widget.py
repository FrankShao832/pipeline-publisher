"""
Log display widget for Pipeline Publisher UI.

Provides a structured log viewer with status display,
color-coded messages, deduplication, and auto-scroll.
"""

import datetime
from typing import Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollBar, QFrame,
)
from PySide6.QtCore import Qt, Signal

from publisher.ui.resources.styles import get_colored_message


class LogWidget(QWidget):
    """
    Log display widget with status bar and activity log.

    Features:
    - Color-coded status display (success/error/warning/info)
    - Timestamped log messages with color coding
    - Message deduplication (prevents repeated messages)
    - Auto-scroll to latest messages
    - Configurable message limit

    Signals:
        status_changed: Emitted when status is updated (message, status_type)
    """

    status_changed = Signal(str, str)

    def __init__(self, parent=None, max_messages: int = 1000):
        """Initialize log widget.

        Args:
            parent: Parent widget
            max_messages: Maximum number of unique message hashes to track
        """
        super().__init__(parent)
        self.max_messages = max_messages
        self._shown_messages: Set[str] = set()

        self.setup_ui()

    def setup_ui(self):
        """Setup the log widget UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Log display frame
        log_frame = QFrame()
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 4px 12px 12px 12px;
            }
        """)

        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(8, 4, 8, 8)

        # Log title
        log_title = QLabel("Activity Log")
        log_title.setStyleSheet(
            "color: #0078d4; font-weight: bold; font-size: 20px;"
            "background: transparent; border: none;"
        )
        log_layout.addWidget(log_title)

        # Log text area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setObjectName("log_display")
        self.log_display.setMinimumHeight(150)
        # Log display stylesheet is applied via global MAIN_WINDOW_STYLE
        log_layout.addWidget(self.log_display)

        log_frame.setLayout(log_layout)
        layout.addWidget(log_frame)

        self.setLayout(layout)

    # ── Public Methods ──

    def log_message(self, message: str, log_type: str = "info"):
        """Add a timestamped, color-coded message to the log display.

        Handles deduplication: identical non-error messages are shown
        only once to prevent log spam.

        Args:
            message: The message text to log
            log_type: 'info', 'success', 'warning', or 'error'
        """
        # Create message hash for deduplication
        message_hash = f"{message}_{log_type}"

        # Skip duplicates for non-error messages
        if log_type != 'error' and message_hash in self._shown_messages:
            return

        # Track message (errors are always shown but not tracked to avoid blocking)
        if log_type != 'error':
            self._shown_messages.add(message_hash)

        # Manage set size - remove oldest entries if limit exceeded
        if len(self._shown_messages) > self.max_messages:
            oldest = list(self._shown_messages)[:100]
            for msg in oldest:
                self._shown_messages.discard(msg)

        # Format with timestamp and color
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        colored = get_colored_message(formatted, log_type)

        # Append and auto-scroll
        self.log_display.append(colored)
        scrollbar = self.log_display.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def clear(self):
        """Clear all log content and reset deduplication tracking."""
        self.log_display.clear()
        self._shown_messages.clear()

    def cleanup(self):
        """Cleanup resources."""
        self.clear()
