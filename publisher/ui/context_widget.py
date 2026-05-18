"""
Context information widget for Pipeline Publisher.

Displays project, sequence, shot, and role information.
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QFrame, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor


class ContextWidget(QWidget):
    """
    Widget displaying pipeline context information.
    
    Shows project, sequence, shot, role, user, DCC information
    with real-time updates and status indicators.
    """
    
    # Signals for context changes
    context_changed = Signal(dict)
    status_changed = Signal(str, str)  # (message, status_type)
    
    def __init__(self, parent=None):
        """Initialize context widget."""
        super().__init__(parent)
        
        self.context_data = {}
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_context)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        self.setup_ui()
        self.update_context()
    
    def setup_ui(self):
        """Setup UI components."""
        self.setup_styles()
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # Create header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Create context group
        context_group = self.create_context_group()
        main_layout.addWidget(context_group)
        
        # Create status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)
        
        self.setLayout(main_layout)
    
    def setup_styles(self):
        """Setup widget styles."""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border-radius: 6px;
            }
            
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: #2b2b2b;
                color: #0078d4;
            }
            
            QLabel {
                color: #cccccc;
                font-size: 10pt;
            }
            
            QLabel#header_label {
                font-size: 12pt;
                font-weight: bold;
                color: #0078d4;
            }
            
            QLabel#context_value {
                color: #ffffff;
                font-weight: normal;
            }
            
            QLabel#status_value {
                color: #4caf50;
                font-weight: bold;
            }
            
            QLabel#status_warning {
                color: #ff9800;
                font-weight: bold;
            }
            
            QLabel#status_error {
                color: #f44336;
                font-weight: bold;
            }
            
            QFrame {
                background-color: #444444;
                border: none;
                border-radius: 2px;
            }
        """)
    
    def create_header(self) -> QLabel:
        """Create header label."""
        header = QLabel("📍 Context Information")
        header.setObjectName("header_label")
        header.setAlignment(Qt.AlignCenter)
        return header
    
    def create_context_group(self) -> QGroupBox:
        """Create context information group."""
        group = QGroupBox("Pipeline Context")
        layout = QFormLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Project information
        self.project_label = QLabel("Not set")
        self.project_label.setObjectName("context_value")
        layout.addRow("Project:", self.project_label)
        
        # Sequence information
        self.sequence_label = QLabel("Not set")
        self.sequence_label.setObjectName("context_value")
        layout.addRow("Sequence:", self.sequence_label)
        
        # Shot information
        self.shot_label = QLabel("Not set")
        self.shot_label.setObjectName("context_value")
        layout.addRow("Shot:", self.shot_label)
        
        # Role information
        self.role_label = QLabel("Not set")
        self.role_label.setObjectName("context_value")
        layout.addRow("Role:", self.role_label)
        
        # User information
        self.user_label = QLabel("Not set")
        self.user_label.setObjectName("context_value")
        layout.addRow("User:", self.user_label)
        
        # DCC information
        self.dcc_label = QLabel("Not detected")
        self.dcc_label.setObjectName("context_value")
        layout.addRow("DCC:", self.dcc_label)
        
        # DCC version
        self.dcc_version_label = QLabel("N/A")
        self.dcc_version_label.setObjectName("context_value")
        layout.addRow("Version:", self.dcc_version_label)
        
        group.setLayout(layout)
        return group
    
    def create_status_bar(self) -> QFrame:
        """Create status bar with context validity indicator."""
        status_frame = QFrame()
        status_frame.setFixedHeight(40)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        
        # Status text
        self.status_text = QLabel("Checking context...")
        self.status_text.setObjectName("status_value")
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_text)
        layout.addStretch()
        
        status_frame.setLayout(layout)
        return status_frame
    
    def update_context(self):
        """Update context information from environment and DCC."""
        # Get environment variables
        self.context_data = {
            'project': os.getenv('SHOW', 'Not set'),
            'sequence': os.getenv('SEQ', 'Not set'),
            'shot': os.getenv('SHOT', 'Not set'),
            'role': os.getenv('ROLE', 'Not set'),
            'user': self.get_user(),
            'dcc': self.detect_dcc(),
            'dcc_version': self.get_dcc_version(),
            'project_root': os.getenv('PROJECT_ROOT', 'Not set'),
            'publish_root': os.getenv('PUBLISH_ROOT', 'Not set'),
        }
        
        # Update UI
        self.update_ui()
        
        # Emit context changed signal
        self.context_changed.emit(self.context_data)
        
        # Validate context
        self.validate_context()
    
    def get_user(self) -> str:
        """Get current user name."""
        return os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    
    def detect_dcc(self) -> str:
        """Detect current DCC application."""
        try:
            import maya.cmds as cmds
            return "Maya"
        except ImportError:
            pass
        
        try:
            import hou
            return "Houdini"
        except ImportError:
            pass
        
        try:
            import nuke
            return "Nuke"
        except ImportError:
            pass
        
        return "Standalone"
    
    def get_dcc_version(self) -> str:
        """Get DCC version information."""
        dcc = self.detect_dcc()
        
        try:
            if dcc == "Maya":
                import maya.cmds as cmds
                return cmds.about(version=True)
            elif dcc == "Houdini":
                import hou
                return hou.applicationVersionString()
            elif dcc == "Nuke":
                import nuke
                return nuke.NUKE_VERSION_STRING
        except Exception:
            pass
        
        return "N/A"
    
    def update_ui(self):
        """Update UI labels with current context data."""
        self.project_label.setText(self.context_data['project'])
        self.sequence_label.setText(self.context_data['sequence'])
        self.shot_label.setText(self.context_data['shot'])
        self.role_label.setText(self.context_data['role'])
        self.user_label.setText(self.context_data['user'])
        self.dcc_label.setText(self.context_data['dcc'])
        self.dcc_version_label.setText(self.context_data['dcc_version'])
    
    def validate_context(self):
        """Validate context and update status indicators."""
        required_fields = ['project', 'sequence', 'shot', 'role']
        missing_fields = []
        
        for field in required_fields:
            if self.context_data.get(field) == 'Not set':
                missing_fields.append(field)
        
        if not missing_fields:
            # All required fields present
            self.status_text.setText("✓ Context complete")
            self.status_text.setObjectName("status_value")
            self.status_text.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.status_indicator.setStyleSheet("color: #4caf50;")
            self.status_changed.emit("Context validation passed", "success")
        else:
            # Missing required fields
            self.status_text.setText(f"✗ Missing: {', '.join(missing_fields)}")
            self.status_text.setObjectName("status_warning")
            self.status_text.setStyleSheet("color: #ff9800; font-weight: bold;")
            self.status_indicator.setStyleSheet("color: #ff9800;")
            self.status_changed.emit(f"Missing context: {', '.join(missing_fields)}", "warning")
    
    def get_context_data(self) -> dict:
        """Get current context data."""
        return self.context_data.copy()
    
    def is_context_valid(self) -> bool:
        """Check if context is valid for publishing."""
        required_fields = ['project', 'sequence', 'shot', 'role']
        return all(self.context_data.get(field) != 'Not set' for field in required_fields)
    
    def manual_refresh(self):
        """Manually trigger context refresh."""
        self.update_context()
    
    def cleanup(self):
        """Cleanup resources."""
        self.update_timer.stop()