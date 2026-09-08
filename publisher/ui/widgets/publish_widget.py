"""
Publish widget for Pipeline Publisher.

Provides the publish operation UI including file selection,
publish type selection, notes, and execution.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QLineEdit,
    QFileDialog, QFrame, QGroupBox,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from publisher.core.models.enums import PublishType
from publisher.core.services.publish_service import PublishService, PublishRequest, PublishResult


class PublishWidget(QWidget):
    """
    Publish operation widget.

    Provides a complete publish interface:
    - Source file path selection with Browse button
    - Publish type dropdown (from PublishType enum)
    - Publish notes input
    - Publish button with status feedback
    - Version display

    Signals:
        publish_requested: Emitted when user clicks Publish (dict = PublishRequest data)
        publish_completed: Emitted when publish finishes (dict = PublishResult data)
    """

    publish_requested = Signal(dict)
    publish_completed = Signal(dict)
    publish_readiness_changed = Signal(bool)  # emitted when source path changes

    def __init__(self, parent: Optional[QWidget] = None,
                 publish_service: Optional[PublishService] = None,
                 save_before_publish: bool = False,
                 pre_publish_hook=None):
        """Initialize publish widget.

        Args:
            parent: Parent widget
            publish_service: Optional PublishService for direct execution.
                            If not provided, emits publish_requested signal instead.
            save_before_publish: If True, version-up the source file before publishing
                                (standalone/Save & Publish mode).
            pre_publish_hook: Optional callable() -> Optional[str]. Called before
                             publish to do DCC-specific prep (e.g. save Houdini scene
                             and version up). If it returns a string, the source path
                             is updated to that value and used for the publish.
        """
        super().__init__(parent)
        self.publish_service = publish_service
        self.save_before_publish = save_before_publish
        self.pre_publish_hook = pre_publish_hook
        self._current_version: Optional[str] = None
        self._last_result: Optional[PublishResult] = None

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the publishing widget UI."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # ── Header ──
        header = QLabel("Publish")
        header.setStyleSheet("""
            QLabel {
                font-size: 20pt;
                font-weight: bold;
                color: #0078d4;
                background-color: transparent;
                border: none;
                padding: 4px 0px;
            }
        """)
        main_layout.addWidget(header)

        # ── Publish Form Group ──
        form_group = QGroupBox()
        form_group.setStyleSheet("""
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
            QGroupBox QLabel {
                font-size: 14pt;
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }
            QLineEdit, QComboBox, QTextEdit {
                font-size: 14pt;
                background-color: #2b2b2b;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #ffffff;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
        """)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(12, 20, 12, 12)

        # Source file path with Browse button
        source_layout = QHBoxLayout()
        source_layout.setSpacing(4)

        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("Select source file or auto-detect...")
        self.source_path_edit.setReadOnly(False)
        source_layout.addWidget(self.source_path_edit)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 13pt;
                font-weight: bold;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
        """)
        source_layout.addWidget(self.browse_btn)

        form_layout.addRow("Source:", source_layout)

        # Publish type dropdown
        self.publish_type_combo = QComboBox()
        for pt in PublishType:
            self.publish_type_combo.addItem(pt.display_name() if hasattr(pt, 'display_name') else pt.value.upper(), pt.value)
        # Set default to SCRIPT
        script_idx = self.publish_type_combo.findData(PublishType.SCRIPT.value)
        if script_idx >= 0:
            self.publish_type_combo.setCurrentIndex(script_idx)
        form_layout.addRow("Type:", self.publish_type_combo)

        # Version display (read-only)
        self.version_label = QLabel("—")
        self.version_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14pt;
                color: #4caf50;
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }
        """)
        form_layout.addRow("Version:", self.version_label)

        # Publish notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Optional publish notes...")
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("Notes:", self.notes_edit)

        # Status display (inside form group, under Notes)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                font-weight: normal;
                font-size: 14pt;
                color: #cccccc;
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }
        """)
        form_layout.addRow("Status:", self.status_label)

        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)

        # ── Publish Button (layout managed externally) ──
        self.publish_btn = QPushButton("▶ Publish")
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 21pt;
                font-weight: bold;
                min-height: 36px;
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
        """)
        self.publish_btn.setEnabled(False)
        main_layout.addWidget(self.publish_btn)

        self.setLayout(main_layout)

    def connect_signals(self):
        """Connect UI signals to handlers."""
        self.browse_btn.clicked.connect(self._on_browse)
        self.publish_btn.clicked.connect(self._on_publish_clicked)
        self.source_path_edit.textChanged.connect(self._on_source_changed)

    # ── Public Methods ──

    def set_source_path(self, path: str):
        """Set the source file path programmatically.

        Args:
            path: Absolute path to the source file
        """
        self.source_path_edit.setText(path)

    def get_source_path(self) -> str:
        """Get the current source file path."""
        return self.source_path_edit.text().strip()

    def set_publish_type(self, publish_type: PublishType):
        """Set the publishing type dropdown."""
        idx = self.publish_type_combo.findData(publish_type.value)
        if idx >= 0:
            self.publish_type_combo.setCurrentIndex(idx)

    def get_publish_type(self) -> PublishType:
        """Get the selected publishing type."""
        data = self.publish_type_combo.currentData()
        return PublishType(data)

    def set_version(self, version: Optional[str]):
        """Set the displayed version number.

        Args:
            version: Version string like 'v001' or None to show '—'
        """
        self._current_version = version
        if version:
            self.version_label.setText(version)
            self.version_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14pt;
                    color: #4caf50;
                    background-color: transparent;
                    border: none;
                    padding: 2px 4px;
                }
            """)
        else:
            self.version_label.setText("—")
            self.version_label.setStyleSheet("""
                QLabel {
                    font-weight: normal;
                    font-size: 14pt;
                    color: #888888;
                    background-color: transparent;
                    border: none;
                    padding: 2px 4px;
                }
            """)

    def set_status(self, message: str, status_type: str = "info"):
        """Update the status label with color-coded message.

        Args:
            message: Status text to display
            status_type: 'info', 'success', 'warning', or 'error'
        """
        colors = {
            "info": "#cccccc",
            "success": "#4caf50",
            "warning": "#ff9800",
            "error": "#f44336",
        }
        color = colors.get(status_type, "#cccccc")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-weight: normal;
                font-size: 14pt;
                color: {color};
                background-color: transparent;
                border: none;
                padding: 2px 4px;
            }}
        """)
        self.status_label.setText(message)

    def set_publish_service(self, publish_service: PublishService):
        """Set or update the publish service.

        Args:
            publish_service: PublishService instance
        """
        self.publish_service = publish_service

    def get_publish_request(self) -> Optional[dict]:
        """Build a publish request dict from current UI state.

        Returns:
            Dict with source_path, publish_type, note fields,
            or None if source path is empty.
        """
        source_path = self.get_source_path()
        if not source_path:
            return None

        return {
            'source_path': source_path,
            'publish_type': self.get_publish_type(),
            'note': self.notes_edit.toPlainText().strip(),
        }

    def trigger_publish(self):
        """Programmatically trigger a publish (called from external button)."""
        self._on_publish_clicked()

    def reset(self):
        """Reset the widget to initial state."""
        self.source_path_edit.clear()
        self.notes_edit.clear()
        self.set_version(None)
        self.set_status("Ready", "info")
        self.publish_btn.setEnabled(False)
        self._last_result = None

    # ── Slots ──

    @Slot()
    def _on_browse(self):
        """Open file browser dialog for source file selection.

        Start directory priority:
            1. directory of the source path already filled in the field
            2. $JOB (hatch launches DCCs with JOB = <seq>/<shot>/<task> workdir)
            3. current working directory, then home as a last resort
        """
        current = self.get_source_path()
        start_dir = os.path.dirname(current) if current else ""
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.getenv("JOB", "")
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.getcwd()
        if not os.path.isdir(start_dir):
            start_dir = str(Path.home())

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Source File",
            start_dir,
            "All Files (*)",
        )
        if file_path:
            self.source_path_edit.setText(file_path)

    @Slot()
    def _on_publish_clicked(self):
        """Handle publish button click."""
        source_path = self.get_source_path()
        if not source_path:
            self.set_status("✗ No source file selected", "warning")
            return

        # ── Pre-publish hook (DCC-specific: save scene, version up, etc.) ──
        if self.pre_publish_hook:
            try:
                new_source = self.pre_publish_hook()
                if new_source:
                    self.set_source_path(new_source)
                    source_path = new_source
            except Exception as e:
                self.set_status(f"✗ Pre-publish failed: {e}", "error")
                self.publish_btn.setEnabled(True)
                self.publish_readiness_changed.emit(True)
                self.publish_btn.setText("▶ Publish")
                return

        # Build publish request data
        request_data = self.get_publish_request()
        if not request_data:
            return

        # Disable button during publish
        self.publish_btn.setEnabled(False)
        self.publish_readiness_changed.emit(False)
        self.publish_btn.setText("Publishing...")
        self.set_status("Publishing...", "info")

        if self.publish_service:
            # Direct execution mode
            context = self._build_context()
            if not context:
                self.set_status("✗ Missing publish context", "error")
                self.publish_btn.setEnabled(True)
                self.publish_readiness_changed.emit(True)
                self.publish_btn.setText("▶ Publish")
                return

            request = PublishRequest(
                source_path=source_path,
                publish_type=self.get_publish_type(),
                context=context,
                note=request_data.get('note', ''),
                save_before_publish=self.save_before_publish,
            )
            result = self.publish_service.execute_publish(request)
            self._handle_result(result)
        else:
            # Signal mode - emit for parent to handle
            self.publish_requested.emit(request_data)

    @Slot(str)
    def _on_source_changed(self, text: str):
        """Enable/disable publish button based on source path."""
        ready = bool(text.strip())
        self.publish_btn.setEnabled(ready)
        self.publish_readiness_changed.emit(ready)

    # ── Internal Helpers ──

    def _handle_result(self, result: PublishResult):
        """Handle publish result.

        Args:
            result: PublishResult from PublishService
        """
        self._last_result = result
        self.publish_btn.setEnabled(True)
        self.publish_readiness_changed.emit(True)
        self.publish_btn.setText("▶ Publish")

        if result.success:
            self.set_version(result.version)
            self.set_status(f"✓ Published: {result.version}", "success")
        else:
            self.set_status(f"✗ {result.message}", "error")

        # Emit completion signal
        self.publish_completed.emit({
            'success': result.success,
            'message': result.message,
            'version': result.version,
            'publish_path': result.publish_path,
            'error': result.error,
        })

    def _build_context(self) -> Optional[dict]:
        """
        Build context dict from parent widget or environment.
        
        Attempts to get context from a parent ContextWidget,
        or falls back to environment variables.
        
        Returns:
            Context dict or None if context is incomplete
        """
        # Try to find ContextWidget in parent hierarchy
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'context_widget') and hasattr(parent.context_widget, 'get_context_data'):
                context_data = parent.context_widget.get_context_data()
                return {
                    'project': context_data.get('project', 'Not set'),
                    'sequence': context_data.get('sequence', 'Not set'),
                    'shot': context_data.get('shot', 'Not set'),
                    'department': context_data.get('department', 'Not set').lower(),
                    'publish_root': context_data.get('publish_root', 'Not set'),
                }
            parent = parent.parent()

        # Fallback to environment variables
        import os
        return {
            'project': os.getenv('SHOW', 'Not set'),
            'sequence': os.getenv('SEQ', 'Not set'),
            'shot': os.getenv('SHOT', 'Not set'),
            'department': os.getenv('PIPELINE_DEPARTMENT', os.getenv('ROLE', 'Not set')).lower(),
            'publish_root': os.getenv('PUBLISH_ROOT', 'Not set'),
        }

    def cleanup(self):
        """Cleanup resources."""
        pass
