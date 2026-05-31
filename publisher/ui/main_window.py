"""
Main window for Y Publisher.

Provides the primary user interface for the publishing tool.
Minimal version with ContextWidget for testing and validation.
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QFrame, QApplication, QTextEdit)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from .context_widget import ContextWidget
from publisher.core.version import get_version_info
from .ui_utils import center_window_on_screen
from publisher.core.config.settings import ConfigManager
from publisher.core.services import PublishService, PublishRequest
from publisher.core.models.enums import PublishType
from publisher.core.file_system.path_builder import PathBuilder
from publisher.core.file_system.file_manager import FileManager
from publisher.core.file_system.test_env import ensure_test_environment


class MainWindow(QMainWindow):
    """
    Main window for Pipeline Publisher application.
    
    Minimal version with ContextWidget for testing and validation.
    """
    
    # Signals
    window_ready = Signal()
    test_completed = Signal(bool, str)
    
    def __init__(self, standalone_mode: bool = True):
        """Initialize main window."""
        super().__init__()
        
        self.standalone_mode = standalone_mode
        self.context_data = {}
        self.shown_log_messages = set()
        self.max_log_messages = 1000
        
        # User info
        self.user_name = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
        # Frank is Admin by default; others controlled by PUBLISHER_ROLE env var
        default_role = 'admin' if self.user_name.lower() == 'frank' else 'artist'
        self.user_role = os.getenv('PUBLISHER_ROLE', default_role).lower()
        self.is_developer = self.user_role in ('admin', 'developer', 'td')
        
        # Configuration and publish service
        self.config_manager = ConfigManager()
        self.publish_service = PublishService(
            file_manager=FileManager(),
            path_builder=PathBuilder(),
            enable_database=self.config_manager.get_config().enable_database,
        )
        
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()
        self.setup_window()
    
    def setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Y Publisher")
        self.setMinimumSize(400, 840)
        self.resize(500, 1020)
        
        # Center window on screen
        self.center_window()
    
    def setup_ui(self):
        """Setup user interface components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header
        # header = self.create_header()
        # main_layout.addWidget(header)
        
        # Context widget (includes user info in header)
        self.context_widget = ContextWidget(
            self,
            user_name=self.user_name,
            user_role=self.user_role,
        )
        main_layout.addWidget(self.context_widget)
        
        # Development tools (only visible for admin/developer/TD roles)
        self.controls_frame = self.create_test_controls()
        self.controls_frame.setVisible(self.is_developer)
        main_layout.addWidget(self.controls_frame)
        
        # Status display
        self.status_display = QLabel("Ready")
        self.status_display.setAlignment(Qt.AlignCenter)
        self.status_display.setFixedHeight(30)
        self.status_display.setObjectName("status_display")
        main_layout.addWidget(self.status_display)
        
        # Log display
        log_frame = self.create_log_display()
        main_layout.addWidget(log_frame)
        
        # Publish bar (Validate + Publish) - at the bottom
        publish_bar = self.create_publish_bar()
        main_layout.addWidget(publish_bar)
        
        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        central_widget.setLayout(main_layout)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.context_widget.context_changed.connect(self.on_context_changed)
        self.context_widget.status_changed.connect(self.on_status_changed)
        
        # Log startup
        self.log_message("Y Publisher started", "info")
    
    def setup_styles(self):
        """Setup window styles."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QLabel#header_label {
                font-size: 18pt;
                font-weight: bold;
                color: #0078d4;
                padding: 8px;
                background-color: #2b2b2b;
                border-radius: 4px;
            }
            
            QLabel#footer_label {
                font-size: 13pt;
                color: #666666;
                padding: 8px;
            }
            
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 14pt;
                min-height: 32px;
            }
            
            QPushButton:hover {
                background-color: #1084d8;
            }
            
            QPushButton:pressed {
                background-color: #005a9e;
            }
            
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
            
            /* Test control buttons - gray style */
            QPushButton#test_button {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
            }
            
            QPushButton#test_button:hover {
                background-color: #5a5a5a;
                border-color: #666666;
            }
            
            QPushButton#test_button:pressed {
                background-color: #3a3a3a;
                border-color: #444444;
            }
            
            QLabel#status_display {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 6px;
                font-size: 14pt;
                color: #cccccc;
            }
            
            QTextEdit#log_display {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #cccccc;
                font-family: 'Courier New', monospace;
                font-size: 14pt;
                padding: 8px;
            }
            
            QFrame#controls_frame {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px;
            }
        """)
    
    # def create_header(self) -> QLabel:
    #     """Create header label."""
    #     header = QLabel("Y Publisher - Test Environment")
    #     header.setObjectName("header_label")
    #     header.setAlignment(Qt.AlignCenter)
    #     return header
    
    def create_test_controls(self) -> QFrame:
        """Create debug/development control buttons (4 buttons, 2 rows)."""
        frame = QFrame()
        frame.setObjectName("controls_frame")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Section title - left aligned, 16pt (1pt larger than buttons)
        title = QLabel("Development Tools")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-weight: bold; color: #0078d4; font-size: 16pt; background: transparent; border: none; padding: 2px 0px;")
        layout.addWidget(title)
        
        # Row 1: Show Context + Show Config
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        show_ctx_btn = QPushButton("Show Context")
        show_ctx_btn.setObjectName("test_button")
        show_ctx_btn.clicked.connect(self.show_context_data)
        row1.addWidget(show_ctx_btn)
        
        show_cfg_btn = QPushButton("Show Config")
        show_cfg_btn.setObjectName("test_button")
        show_cfg_btn.clicked.connect(self.show_config)
        row1.addWidget(show_cfg_btn)
        
        layout.addLayout(row1)
        
        # Row 2: Init Test Env + Reload Config
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        init_env_btn = QPushButton("Init Test Env")
        init_env_btn.setObjectName("test_button")
        init_env_btn.clicked.connect(self.init_test_environment)
        row2.addWidget(init_env_btn)
        
        reload_cfg_btn = QPushButton("Reload Config")
        reload_cfg_btn.setObjectName("test_button")
        reload_cfg_btn.clicked.connect(self.reload_config)
        row2.addWidget(reload_cfg_btn)
        
        layout.addLayout(row2)
        
        frame.setLayout(layout)
        return frame
    
    def create_publish_bar(self) -> QFrame:
        """Create publish action bar (Validate + Publish) at the bottom."""
        frame = QFrame()
        frame.setObjectName("controls_frame")
        frame.setStyleSheet("""
            QFrame#controls_frame {
                background-color: #2b2b2b;
                border: 2px solid #0078d4;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Validate button (left) - equal split with Publish
        self.validate_btn = QPushButton("✓ Validate")
        self.validate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 15pt;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        self.validate_btn.clicked.connect(self.validate_and_publish)
        layout.addWidget(self.validate_btn)
        
        # Publish button (right) - prominent blue, equal split
        self.publish_btn = QPushButton("▶ Publish")
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 15pt;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.publish_btn.clicked.connect(self.execute_publish)
        layout.addWidget(self.publish_btn)
        
        frame.setLayout(layout)
        return frame
    
    def create_log_display(self) -> QFrame:
        """Create log display widget."""
        log_frame = QFrame()
        log_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Log title
        log_title = QLabel("Activity Log")
        log_title.setStyleSheet(
            "color: #0078d4; font-weight: bold; font-size: 16pt;"
        )
        layout.addWidget(log_title)
        
        # Log text area
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setObjectName("log_display")
        self.log_display.setMinimumHeight(150)
        layout.addWidget(self.log_display)
        
        log_frame.setLayout(layout)
        return log_frame
    
    def create_footer(self) -> QLabel:
        """Create footer label with dynamic version info."""
        info = get_version_info()
        footer = QLabel(
            f"Y Publisher V {info['publisher_version']} - "
            f"Python {info['python_version']} | {info['pyside6_version']}"
        )
        footer.setObjectName("footer_label")
        footer.setAlignment(Qt.AlignCenter)
        return footer
    
    def center_window(self):
        """Center window on screen using ui_utils."""
        center_window_on_screen(self)
    
    # Slot methods
    @Slot(dict)
    def on_context_changed(self, context: dict):
        """Handle context changes."""
        # Only log if significant change occurred (not just periodic updates)
        old_project = self.context_data.get('project', 'Not set')
        new_project = context.get('project', 'Not set')
        
        if old_project != new_project:
            self.context_data = context
            self.log_message(f"Context changed: {new_project}", "info")
        else:
            self.context_data = context  # Update data without logging
    
    @Slot(str, str)
    def on_status_changed(self, message: str, status_type: str):
        """Handle status changes."""
        self.update_status(f"Context Status: {message}", status_type)
        self.log_message(f"[{status_type.upper()}] {message}", status_type)
    
    # ---- Dev/Debug Button Handlers ----
    
    def show_context_data(self):
        """Display current context data (from env vars)."""
        context = self.context_widget.get_context_data()
        
        result = "Current Context Data:\n" + "=" * 50 + "\n"
        for key, value in context.items():
            result += f"{key:15}: {value}\n"
        
        self.log_message(result, "info")
        print(result)
        self.update_status("Context data displayed", "success")
    
    def show_config(self):
        """Display current YAML configuration."""
        config = self.config_manager.get_config()
        
        result = "Current Configuration:\n" + "=" * 50 + f"""
Config source: {self.config_manager._config_path or '(defaults)'}
enable_database: {config.enable_database}
publish_root:    {config.publish_root or '(not set)'}
project_root:    {config.project_root or '(not set)'}
DB host:         {config.database.host}
DB port:         {config.database.port}
Log level:       {config.logging.level}
"""
        self.log_message(result, "info")
        print(result)
        self.update_status("Config displayed", "success")
    
    def init_test_environment(self):
        """Initialize test environment (create dirs + set default env vars)."""
        config = self.config_manager.get_config()
        project_root = Path(config.project_root) if config.project_root else None
        publish_root = Path(config.publish_root) if config.publish_root else None
        
        ensure_test_environment(project_root, publish_root)
        self.context_widget.manual_refresh()
        
        self.log_message("Test environment initialized", "success")
        self.update_status("Test environment ready", "success")
    
    def reload_config(self):
        """Reload YAML configuration and update publish service."""
        self.config_manager.reload()
        config = self.config_manager.get_config()
        self.publish_service.enable_database = config.enable_database
        
        self.log_message(
            f"Config reloaded (db={'on' if config.enable_database else 'off'})",
            "info",
        )
        self.update_status("Configuration reloaded", "success")
    
    # ---- Publish Bar Handlers ----
    
    def validate_and_publish(self):
        """Validate context, then execute publish if valid."""
        if not self.context_widget.is_context_valid():
            self.update_status("✗ Validation failed: missing context fields", "error")
            self.log_message("✗ Cannot publish: context validation failed", "error")
            return
        
        # Context is valid, proceed to publish
        self.execute_publish()
    
    def execute_publish(self):
        """Execute publish using PublishService with current context."""
        context = self.context_widget.get_context_data()
        config = self.config_manager.get_config()
        
        # Get publish root from config (with env var fallback)
        publish_root = (
            config.publish_root
            or os.getenv('PUBLISH_ROOT')
            or '/Volumes/Projects/y_pipeline_publish/Test'
        )
        
        # Build context dict for PublishService
        service_context = {
            'project': context.get('project', 'Not set'),
            'sequence': context.get('sequence', 'Not set'),
            'shot': context.get('shot', 'Not set'),
            'role': context.get('role', 'Not set').lower(),
            'publish_root': publish_root,
        }
        
        # Find source file in project root
        project_root = (
            config.project_root
            or os.getenv('PROJECT_ROOT')
            or '/Volumes/Projects/y_pipeline_projects/Test'
        )
        
        # Try to find a source file matching the current DCC role
        role = service_context['role']
        source_dir = Path(project_root) / context.get('project', '') / context.get('sequence', '') / context.get('shot', '') / role
        
        source_files = {
            'maya': '*.ma',
            'houdini': '*.hip',
            'nuke': '*.nk',
        }
        
        source_path = None
        pattern = source_files.get(role, '*')
        if source_dir.exists():
            matches = list(source_dir.glob(pattern))
            if matches:
                source_path = str(matches[0])
        
        if not source_path:
            self.update_status(f"✗ No source file found in {source_dir}", "error")
            self.log_message(f"✗ No source file found matching role '{role}'", "error")
            return
        
        # Execute publish
        request = PublishRequest(
            source_path=source_path,
            publish_type=PublishType.SCRIPT,
            context=service_context,
            note="Published from standalone mode",
        )
        
        result = self.publish_service.execute_publish(request)
        
        if result.success:
            self.update_status(
                f"✓ Published v{result.version}: {Path(source_path).name}",
                "success",
            )
            self.log_message(
                f"✓ Published: {Path(source_path).name} → {result.publish_path} [{result.version}]",
                "success",
            )
        else:
            self.update_status(f"✗ Publish failed: {result.message}", "error")
            self.log_message(f"✗ Publish failed: {result.message}", "error")
    
    # Helper methods
    def update_status(self, message: str, status_type: str = "info"):
        """Update status display."""
        color_map = {
            'success': '#4caf50',
            'error': '#f44336',
            'warning': '#ff9800',
            'info': '#2196f3',
            'default': '#666666'  # Gray for regular status
        }
        
        color = color_map.get(status_type, '#666666')
        self.status_display.setText(message)
        self.status_display.setStyleSheet(f"""
            QLabel#status_display {{
                background-color: #3a3a3a;
                border: 1px solid {color};
                border-radius: 4px;
                padding: 6px;
                font-size: 14pt;
                color: {color};
                font-weight: normal;
            }}
        """)
    
    def log_message(self, message: str, log_type: str = "info"):
        """Add message to log display."""
        import datetime
        
        # Create message hash for deduplication
        message_hash = f"{message}_{log_type}"
        
        # Skip if this exact message was already shown (except for critical errors)
        if message_hash in self.shown_log_messages and log_type in ['info', 'success', 'warning']:
            return  # Skip duplicate messages
        
        # For errors, always show, but for other types, prevent repeats
        if log_type != 'error':
            self.shown_log_messages.add(message_hash)
        
        # Manage log size - remove old messages if too many
        if len(self.shown_log_messages) > self.max_log_messages:
            # Remove oldest messages (FIFO)
            oldest_messages = list(self.shown_log_messages)[:100]
            for old_msg in oldest_messages:
                self.shown_log_messages.discard(old_msg)
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Add color based on log type
        color_map = {
            'info': '#2196f3',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336'
        }
        
        color = color_map.get(log_type, '#2196f3')
        colored_message = f'<span style="color: {color}">{formatted_message}</span>'
        
        self.log_display.append(colored_message)
        # Auto-scroll to bottom
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
    
    def show(self):
        """Show window and emit ready signal."""
        super().show()
        # Re-center after layout is finalized
        self.center_window()
        self.window_ready.emit()
    
    def cleanup(self):
        """Cleanup resources."""
        self.context_widget.cleanup()


def test_main_window():
    """Test main window functionality."""
    app = QApplication(sys.argv)
    app.setApplicationName("Y Publisher")
    app.setOrganizationName("Frank")
    
    window = MainWindow(standalone_mode=True)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    test_main_window()