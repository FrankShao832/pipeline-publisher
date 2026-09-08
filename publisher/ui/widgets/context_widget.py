"""
Context information widget for Pipeline Publisher.

Displays project, sequence, shot, department, user, and DCC information.
"""

import os
import re
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QFrame, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor

from publisher.dcc.dcc_detector import DCCDetector


class ContextWidget(QWidget):
    """
    Widget displaying pipeline context information.
    
    Shows project, sequence, shot, department, user, DCC information
    with real-time updates and status indicators.
    """
    
    # Signals for context changes
    context_changed = Signal(dict)
    status_changed = Signal(str, str)  # (message, status_type)
    
    def __init__(self, parent=None, user_name: str = "unknown", user_role: str = "artist"):
        """Initialize context widget."""
        super().__init__(parent)
        
        self.user_name = user_name
        self.user_role = user_role
        self.is_developer = user_role.lower() in ('admin', 'developer', 'td')
        self.context_data = {}
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_context)
        self.update_timer.start(10000)
        
        self.setup_ui()
        self.update_context()
    
    def setup_ui(self):
        """Setup UI components."""
        # Remove fixed width to allow auto-resize
        # Component will automatically fill available width
        # Center alignment is handled by parent layout
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to match other components width
        main_layout.setSpacing(8)
        
        # Create header with individual styling
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Create context group with individual styling
        context_group = self.create_context_group()
        main_layout.addWidget(context_group)
        
        # Create status bar with individual styling
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)
        
        self.setLayout(main_layout)
    
    def create_header(self) -> QWidget:
        """Create header with 'Context' on the left and user info on the right."""
        role_display = self.user_role.capitalize()

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # "Context" title on the left
        context_title = QLabel("Context")
        context_title.setStyleSheet("""
            QLabel {
                font-size: 20pt;
                font-weight: bold;
                color: #0078d4;
                background-color: transparent;
                border: none;
                padding: 8px;
            }
        """)
        layout.addWidget(context_title)

        layout.addStretch()

        # User info on the right
        user_label = QLabel(f"User: {self.user_name}  [ {role_display} ]")
        user_label.setStyleSheet("""
            QLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #0078d4;
                background-color: transparent;
                border: none;
                padding: 8px;
            }
        """)
        layout.addWidget(user_label)

        header_widget.setLayout(layout)
        return header_widget
    
    def create_context_group(self) -> QGroupBox:
        """Create context information group with individual styling."""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: transparent;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: transparent;
                color: #0078d4;
            }
            
            /* Form label (left column) - match value label font size */
            QGroupBox QLabel {
                font-size: 15pt;
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }
        """)
        
        layout = QFormLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(16, 24, 16, 16)
        
        # Project information with individual styling
        self.project_label = self._create_context_value_label("Not set")
        layout.addRow("Project:", self.project_label)
        
        # Sequence information with individual styling
        self.sequence_label = self._create_context_value_label("Not set")
        layout.addRow("Sequence:", self.sequence_label)
        
        # Shot information with individual styling
        self.shot_label = self._create_context_value_label("Not set")
        layout.addRow("Shot:", self.shot_label)
        
        # File version (extracted from source filename)
        self.version_label = self._create_context_value_label("N/A")
        layout.addRow("Version:", self.version_label)
        
        # Role information with individual styling
        self.department_label = self._create_context_value_label("Not set")
        layout.addRow("Department:", self.department_label)
        
        # User information with individual styling
        self.user_label = self._create_context_value_label("Not set")
        layout.addRow("User:", self.user_label)
        
        # DCC information with individual styling
        self.dcc_label = self._create_context_value_label("Not detected")
        layout.addRow("DCC:", self.dcc_label)
        
        group.setLayout(layout)
        return group
    
    def _create_context_value_label(self, text: str) -> QLabel:
        """Create context value label with individual styling."""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                font-weight: normal;
                font-size: 15pt;
                color: #ffffff;
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }
        """)
        return label
    
    def create_status_bar(self) -> QFrame:
        """Create status bar with context validity indicator and individual styling."""
        status_frame = QFrame()
        status_frame.setFixedHeight(40)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #444444;
                border: none;
                border-radius: 2px;
                padding: 0px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Status indicator with individual styling
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("""
            QLabel {
                font-size: 16pt;
                color: #888888;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        # Status text with individual styling
        self.status_text = QLabel("Checking context...")
        self.status_text.setStyleSheet("""
            QLabel {
                font-size: 16pt;
                color: #4caf50;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_text)
        layout.addStretch()
        
        status_frame.setLayout(layout)
        return status_frame
    
    def update_context(self):
        """Update context information from environment and DCC."""
        # Get environment variables (PIPELINE_* with legacy SHOW/SEQ/SHOT fallback)
        self.context_data = {
            'project': os.getenv('PIPELINE_PROJECT',
                        os.getenv('SHOW', 'Not set')),
            'sequence': os.getenv('PIPELINE_SEQUENCE',
                         os.getenv('SEQ', 'Not set')),
            'shot': os.getenv('PIPELINE_SHOT',
                     os.getenv('SHOT', 'Not set')),
            'department': os.getenv('PIPELINE_DEPARTMENT',
                          os.getenv('ROLE', 'Not set')),
            'user': self.get_user(),
            'dcc': self.detect_dcc(),
            'file_version': self.detect_file_version(),
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
        """Get current username."""
        return os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    
    def detect_dcc(self) -> str:
        """Detect current DCC application using DCCDetector."""
        return DCCDetector.detect().display_name
    
    def get_dcc_version(self) -> str:
        """Get DCC version information using DCCDetector."""
        dcc_type = DCCDetector.detect()
        info = DCCDetector.get_dcc_info(dcc_type)
        return info.get('version', 'N/A')
    
    def detect_file_version(self) -> str:
        """
        Detect file version from source filename in the project workspace.
        
        Looks for source files in {project_root}/{project}/{seq}/{shot}/{department}/
        and extracts version from filename pattern like _v001, _v002, etc.
        
        Returns:
            Version string (e.g., 'v001') or 'N/A' if not found.
        """
        project = self.context_data.get('project', '')
        sequence = self.context_data.get('sequence', '')
        shot = self.context_data.get('shot', '')
        department = self.context_data.get('department', '')
        project_root = os.getenv('PROJECT_ROOT', '')
        
        if not all([project, sequence, shot, department, project_root]):
            return 'N/A'
        
        dept_dir = Path(project_root) / project / sequence / shot / department
        if not dept_dir.exists():
            return 'N/A'
        
        # Determine DCC from department and get extension patterns
        from publisher.core.constants import get_dcc_for_department, get_extensions_for_dcc
        dcc = get_dcc_for_department(department)
        patterns = get_extensions_for_dcc(dcc)

        files = []
        for pat in patterns:
            files.extend(f for f in dept_dir.glob(pat) if f.is_file())
        if not files:
            files = [f for f in dept_dir.iterdir() if f.is_file()]

        if not files:
            return 'N/A'

        # Highest numeric version wins (glob/iterdir order is not sorted).
        best_num = -1
        best_pad = 3
        for f in files:
            version_match = re.search(r'_v(\d+)', f.stem, re.IGNORECASE)
            if version_match:
                num = int(version_match.group(1))
                if num > best_num:
                    best_num = num
                    best_pad = len(version_match.group(1))
        if best_num < 0:
            return 'N/A'
        return f"v{str(best_num).zfill(best_pad)}"

    
    def update_ui(self):
        """Update UI labels with current context data."""
        self.project_label.setText(self.context_data['project'])
        self.sequence_label.setText(self.context_data['sequence'])
        self.shot_label.setText(self.context_data['shot'])
        self.department_label.setText(self.context_data['department'])
        self.user_label.setText(self.context_data['user'])
        self.dcc_label.setText(self.context_data['dcc'])
        self.version_label.setText(self.context_data['file_version'])
    
    def validate_context(self):
        """Validate context and update status indicators."""
        required_fields = ['project', 'sequence', 'shot', 'department']
        missing_fields = []
        
        for field in required_fields:
            if self.context_data.get(field) == 'Not set':
                missing_fields.append(field)
        
        if not missing_fields:
            # All required fields present
            self.status_text.setText("✓ Context complete")
            self.status_text.setStyleSheet("""
                QLabel {
                    font-size: 16pt;
                    color: #4caf50;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16pt;
                    color: #4caf50;
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.status_changed.emit("Context validation passed", "success")
        else:
            # Missing required fields
            self.status_text.setText(f"✗ Missing: {', '.join(missing_fields)}")
            self.status_text.setStyleSheet("""
                QLabel {
                    font-size: 16pt;
                    color: #ff9800;
                    font-weight: bold;
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.status_indicator.setStyleSheet("""
                QLabel {
                    font-size: 16pt;
                    color: #ff9800;
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                }
            """)
            self.status_changed.emit(f"Missing context: {', '.join(missing_fields)}", "warning")
    
    def get_context_data(self) -> dict:
        """Get current context data."""
        return self.context_data.copy()
    
    def is_context_valid(self) -> bool:
        """Check if context is valid for publishing."""
        required_fields = ['project', 'sequence', 'shot', 'department']
        return all(self.context_data.get(field) != 'Not set' for field in required_fields)
    
    def manual_refresh(self):
        """Manually trigger context refresh."""
        self.update_context()
    
    def cleanup(self):
        """Cleanup resources."""
        self.update_timer.stop()