"""
Main window for Pipeline Publisher.

Provides the primary user interface for the publishing tool.
Minimal version with ContextWidget for testing and validation.
"""

import sys
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QLabel, QFrame, QApplication, QTextEdit)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from .context_widget import ContextWidget


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
        
        self.setup_window()
        self.setup_ui()
        self.setup_connections()
        self.setup_styles()
    
    def setup_window(self):
        """Setup window properties."""
        self.setWindowTitle("Pipeline Publisher - Test Mode")
        self.setMinimumSize(400, 600)
        self.resize(500, 700)
        
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
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Context widget
        self.context_widget = ContextWidget(self)
        main_layout.addWidget(self.context_widget)
        
        # Test controls
        controls_frame = self.create_test_controls()
        main_layout.addWidget(controls_frame)
        
        # Status display
        self.status_display = QLabel("Ready for testing")
        self.status_display.setAlignment(Qt.AlignCenter)
        self.status_display.setFixedHeight(30)
        self.status_display.setObjectName("status_display")
        main_layout.addWidget(self.status_display)
        
        # Log display
        log_frame = self.create_log_display()
        main_layout.addWidget(log_frame)
        
        # Spacer
        main_layout.addStretch()
        
        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)
        
        central_widget.setLayout(main_layout)
    
    def setup_connections(self):
        """Setup signal connections."""
        self.context_widget.context_changed.connect(self.on_context_changed)
        self.context_widget.status_changed.connect(self.on_status_changed)
        
        # Log startup
        self.log_message("Pipeline Publisher started", "info")
    
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
                font-size: 14pt;
                font-weight: bold;
                color: #0078d4;
                padding: 8px;
                background-color: #2b2b2b;
                border-radius: 4px;
            }
            
            QLabel#footer_label {
                font-size: 9pt;
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
                font-size: 10pt;
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
                font-size: 10pt;
                color: #cccccc;
            }
            
            QFrame#controls_frame {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 12px;
            }
            
            QTextEdit#log_display {
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #cccccc;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                padding: 8px;
            }
        """)
    
    def create_header(self) -> QLabel:
        """Create header label."""
        header = QLabel("🚀 Pipeline Publisher - Test Environment")
        header.setObjectName("header_label")
        header.setAlignment(Qt.AlignCenter)
        return header
    
    def create_test_controls(self) -> QFrame:
        """Create test control buttons."""
        frame = QFrame()
        frame.setObjectName("controls_frame")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Title
        title = QLabel("Test Controls")
        title.setStyleSheet("font-weight: bold; color: #0078d4; font-size: 11pt;")
        layout.addWidget(title)
        
        # Button row 1
        button_layout_1 = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh Context")
        refresh_btn.setObjectName("test_button")
        refresh_btn.clicked.connect(self.refresh_context)
        button_layout_1.addWidget(refresh_btn)
        
        validate_btn = QPushButton("✓ Validate Context")
        validate_btn.setObjectName("test_button")
        validate_btn.clicked.connect(self.validate_context)
        button_layout_1.addWidget(validate_btn)
        
        layout.addLayout(button_layout_1)
        
        # Button row 2
        button_layout_2 = QHBoxLayout()
        
        test_env_btn = QPushButton("🧪 Test Environment")
        test_env_btn.setObjectName("test_button")
        test_env_btn.clicked.connect(self.test_environment)
        button_layout_2.addWidget(test_env_btn)
        
        show_data_btn = QPushButton("📋 Show Context Data")
        show_data_btn.setObjectName("test_button")
        show_data_btn.clicked.connect(self.show_context_data)
        button_layout_2.addWidget(show_data_btn)
        
        layout.addLayout(button_layout_2)
        
        # Button row 3
        button_layout_3 = QHBoxLayout()
        
        set_env_btn = QPushButton("⚙️ Set Test Environment")
        set_env_btn.setObjectName("test_button")
        set_env_btn.clicked.connect(self.set_test_environment)
        button_layout_3.addWidget(set_env_btn)
        
        clear_env_btn = QPushButton("🗑️ Clear Environment")
        clear_env_btn.setObjectName("test_button")
        clear_env_btn.clicked.connect(self.clear_environment)
        button_layout_3.addWidget(clear_env_btn)
        
        layout.addLayout(button_layout_3)
        
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
        log_title = QLabel("📋 Activity Log")
        log_title.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 11pt;")
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
        """Create footer label."""
        footer = QLabel("Pipeline Publisher v1.0.0 - Test Mode | Python 3.11 | PySide6")
        footer.setObjectName("footer_label")
        footer.setAlignment(Qt.AlignCenter)
        return footer
    
    def center_window(self):
        """Center window on screen."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        
        self.move(x, y)
    
    # Slot methods
    @Slot(dict)
    def on_context_changed(self, context: dict):
        """Handle context changes."""
        self.context_data = context
        self.log_message(f"Context changed: {context.get('project', 'N/A')}", "info")
    
    @Slot(str, str)
    def on_status_changed(self, message: str, status_type: str):
        """Handle status changes."""
        self.update_status(f"Context Status: {message}", status_type)
        self.log_message(f"[{status_type.upper()}] {message}", status_type)
    
    # Button handlers
    def refresh_context(self):
        """Refresh context information."""
        self.context_widget.manual_refresh()
        self.update_status("Context refreshed successfully", "success")
        self.log_message("Context refreshed manually", "info")
    
    def validate_context(self):
        """Validate context data."""
        if self.context_widget.is_context_valid():
            self.update_status("✓ Context validation passed", "success")
            self.log_message("✓ Context validation passed", "success")
            self.test_completed.emit(True, "Context validation passed")
        else:
            self.update_status("✗ Context validation failed", "error")
            self.log_message("✗ Context validation failed", "error")
            self.test_completed.emit(False, "Context validation failed")
    
    def test_environment(self):
        """Test environment setup."""
        dcc = self.context_widget.detect_dcc()
        version = self.context_widget.get_dcc_version()
        user = self.context_widget.get_user()
        
        result = f"""
Environment Test Results:
├─ DCC: {dcc}
├─ DCC Version: {version}
├─ User: {user}
├─ Python: {sys.version.split()[0]}
└─ Standalone Mode: {self.standalone_mode}
        """.strip()
        
        self.log_message(result, "info")
        print(result)
        self.update_status("Environment test completed", "success")
    
    def show_context_data(self):
        """Display current context data."""
        context = self.context_widget.get_context_data()
        
        result = "Current Context Data:\n" + "=" * 50 + "\n"
        for key, value in context.items():
            result += f"{key:15}: {value}\n"
        
        self.log_message(result, "info")
        print(result)
        self.update_status("Context data displayed", "success")
    
    def set_test_environment(self):
        """Set test environment variables."""
        test_data = {
            'SHOW': 'test_project',
            'SEQ': 'seq001',
            'SHOT': 'shot001',
            'ROLE': 'test_role',
            'PROJECT_ROOT': '/test/project_root',
            'PUBLISH_ROOT': '/test/publish_root'
        }
        
        for key, value in test_data.items():
            os.environ[key] = value
        
        self.context_widget.manual_refresh()
        self.update_status("Test environment variables set", "success")
        self.log_message(f"Set test environment: {test_data['SHOW']}", "info")
    
    def clear_environment(self):
        """Clear test environment variables."""
        env_vars = ['SHOW', 'SEQ', 'SHOT', 'ROLE', 'PROJECT_ROOT', 'PUBLISH_ROOT']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        self.context_widget.manual_refresh()
        self.update_status("Environment variables cleared", "success")
        self.log_message("Environment variables cleared", "warning")
    
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
                font-size: 10pt;
                color: {color};
                font-weight: normal;
            }}
        """)
    
    def log_message(self, message: str, log_type: str = "info"):
        """Add message to log display."""
        import datetime
        
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
        self.window_ready.emit()
    
    def cleanup(self):
        """Cleanup resources."""
        self.context_widget.cleanup()


def test_main_window():
    """Test main window functionality."""
    app = QApplication(sys.argv)
    app.setApplicationName("Pipeline Publisher")
    app.setOrganizationName("Pipeline Team")
    
    window = MainWindow(standalone_mode=True)
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    test_main_window()