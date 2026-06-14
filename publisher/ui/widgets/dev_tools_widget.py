"""
Development tools widget for Pipeline Publisher UI.

Provides debug/development control buttons for admin/developer/TD roles.
Only visible when user has developer-level permissions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
)
from PySide6.QtCore import Qt, Signal

from publisher.ui.resources.styles import get_status_style


class DevToolsWidget(QFrame):
    """
    Development tools panel with debug control buttons.

    Contains 4 debug buttons in a 2x2 grid plus a status display bar.

    Signals:
        show_context_requested: User wants to view context data
        show_config_requested: User wants to view configuration
        init_env_requested: User wants to initialize test environment
        reload_config_requested: User wants to reload configuration
    """

    show_context_requested = Signal()
    show_config_requested = Signal()
    init_env_requested = Signal()
    reload_config_requested = Signal()

    def __init__(self, parent=None, visible: bool = False):
        """Initialize dev tools widget.

        Args:
            parent: Parent widget
            visible: Whether the panel is initially visible
        """
        super().__init__(parent)
        self.setObjectName("controls_frame")

        self.setup_ui()
        self.setVisible(visible)

    def setup_ui(self):
        """Set up the dev tools UI with buttons and status bar."""
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 8, 12, 8)

        # Section title
        title = QLabel("Development Tools")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet(
            "font-weight: bold; color: #0078d4; font-size: 20pt;"
            "background: transparent; border: none; padding: 2px 0px;"
        )
        layout.addWidget(title)

        # Row 1: Show Context + Show Config
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.show_ctx_btn = QPushButton("Show Context")
        self.show_ctx_btn.setObjectName("test_button")
        self.show_ctx_btn.clicked.connect(self.show_context_requested.emit)
        row1.addWidget(self.show_ctx_btn)

        self.show_cfg_btn = QPushButton("Show Config")
        self.show_cfg_btn.setObjectName("test_button")
        self.show_cfg_btn.clicked.connect(self.show_config_requested.emit)
        row1.addWidget(self.show_cfg_btn)

        layout.addLayout(row1)

        # Row 2: Init Test Env + Reload Config
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.init_env_btn = QPushButton("Init Test Env")
        self.init_env_btn.setObjectName("test_button")
        self.init_env_btn.clicked.connect(self.init_env_requested.emit)
        row2.addWidget(self.init_env_btn)

        self.reload_cfg_btn = QPushButton("Reload Config")
        self.reload_cfg_btn.setObjectName("test_button")
        self.reload_cfg_btn.clicked.connect(self.reload_config_requested.emit)
        row2.addWidget(self.reload_cfg_btn)

        layout.addLayout(row2)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #555555; background: transparent;")
        layout.addWidget(sep)

        # Status display bar (moved from LogWidget)
        self.status_display = QLabel("Ready")
        self.status_display.setAlignment(Qt.AlignCenter)
        self.status_display.setFixedHeight(30)
        self.status_display.setObjectName("status_display")
        self.status_display.setStyleSheet(get_status_style('default'))
        layout.addWidget(self.status_display)

        self.setLayout(layout)

    def update_status(self, message: str, status_type: str = "info"):
        """Update the status display with color-coded message.

        Args:
            message: Status message text
            status_type: 'success', 'error', 'warning', 'info', or 'default'
        """
        self.status_display.setText(message)
        self.status_display.setStyleSheet(get_status_style(status_type))
