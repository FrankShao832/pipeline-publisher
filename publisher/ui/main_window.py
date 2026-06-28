"""
Main window for Y Publisher.

Provides the primary user interface for the publishing tool.
Assembles all widget components and manages signal wiring.
Designed as a thin view layer, receiving dependencies via
PublisherController and delegating logic to specialized widgets.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QLabel,
)
from PySide6.QtCore import Qt, Signal, Slot

from .widgets.context_widget import ContextWidget
from .widgets.publish_widget import PublishWidget
from .widgets.log_widget import LogWidget
from .widgets.dev_tools_widget import DevToolsWidget
from publisher.core.controller import PublisherController
from publisher.core.version import get_version_info
from publisher.core.file_system.test_env import ensure_test_environment
from .utils.ui_utils import center_window_on_screen
from .utils.source_detector import detect_source_file
from .resources.styles import MAIN_WINDOW_STYLE


class MainWindow(QMainWindow):
    """
    Main window for Pipeline Publisher application.

    Assembles ContextWidget, PublishWidget, LogWidget, and DevToolsWidget
    into a cohesive interface. Handles cross-component communication
    and delegates business logic to PublisherController.

    Dependencies are injected via PublisherController, making this
    a pure view-layer component.
    """

    # Signals
    window_ready = Signal()
    test_completed = Signal(bool, str)

    def __init__(self, controller: PublisherController, parent=None):
        """Initialize main window with injected controller.

        Args:
            controller: PublisherController managing config, services, and user info
            parent: Optional parent widget (e.g. hou.qt.mainWindow() for Houdini embed)
        """
        super().__init__(parent)
        self.controller = controller
        self.context_data = {}

        self.setup_ui()
        self.setup_connections()

        # ── Force immediate context refresh ──
        # ContextWidget.__init__ calls update_context() (and emits context_changed)
        # BEFORE setup_connections() wires the signal → first emission is lost.
        # Manual refresh ensures the signal fires after connections are live,
        # so PublishWidget gets source_path + version populated immediately.
        self.context_widget.manual_refresh()

    # ── Setup Methods ──

    def setup_ui(self):
        """Assemble all widget components into the main layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Context widget
        self.context_widget = ContextWidget(
            self,
            user_name=self.controller.user.name,
            user_role=self.controller.user.role,
        )
        layout.addWidget(self.context_widget)

        # Development tools (admin/developer/TD only)
        self.dev_tools = DevToolsWidget(
            self,
            visible=self.controller.user.is_developer,
        )
        layout.addWidget(self.dev_tools)

        # Publish widget
        self.publish_widget = PublishWidget(
            self,
            publish_service=self.controller.publish_service,
            save_before_publish=self.controller.standalone_mode,
        )
        layout.addWidget(self.publish_widget)

        # Log widget
        self.log_widget = LogWidget(self)
        layout.addWidget(self.log_widget)

        # Footer
        info = get_version_info()
        footer = QLabel(
            f"Y Publisher V {info['publisher_version']} - "
            f"Python {info['python_version']} | {info['pyside6_version']}"
        )
        footer.setObjectName("footer_label")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        central_widget.setLayout(layout)

    def setup_connections(self):
        """Wire signals between components and window properties."""
        # Context → auto-detect source file
        self.context_widget.context_changed.connect(self._on_context_changed)
        self.context_widget.status_changed.connect(self._on_context_status)

        # Publish → log results
        self.publish_widget.publish_completed.connect(self._on_publish_completed)

        # DevTools → handlers
        self.dev_tools.show_context_requested.connect(self._on_dev_show_context)
        self.dev_tools.show_config_requested.connect(self._on_dev_show_config)
        self.dev_tools.init_env_requested.connect(self._on_dev_init_env)
        self.dev_tools.reload_config_requested.connect(self._on_dev_reload_config)

        # Window properties
        self.setWindowTitle("Y Publisher")
        self.setMinimumSize(400, 1008)
        self.resize(500, 1224)
        self.setStyleSheet(MAIN_WINDOW_STYLE)

        self.log_widget.log_message("Y Publisher started", "info")

    # ── Context Handlers ──

    @Slot(dict)
    def _on_context_changed(self, context: dict):
        """Handle context changes and auto-detect source file."""
        old_project = self.context_data.get('project', 'Not set')
        new_project = context.get('project', 'Not set')

        if old_project != new_project:
            self.log_widget.log_message(f"Context changed: {new_project}", "info")

        self.context_data = context

        # Auto-detect source file from work directory
        project_root = self.controller.get_project_root()
        result = detect_source_file(context, project_root)
        if result:
            source_path, version = result
            current_source = self.publish_widget.get_source_path()
            if current_source != source_path:
                self.publish_widget.set_source_path(source_path)
                if version:
                    self.publish_widget.set_version(version)

    @Slot(str, str)
    def _on_context_status(self, message: str, status_type: str):
        """Forward context status to log widget."""
        self.log_widget.log_message(
            f"[{status_type.upper()}] {message}", status_type
        )

    # ── PublishWidget Handlers ──

    @Slot(dict)
    def _on_publish_completed(self, result: dict):
        """Log publish results to activity log."""
        if result.get('success'):
            self.log_widget.log_message(
                f"✓ Published: {result.get('publish_path', '')} "
                f"[{result.get('version', '')}]",
                "success",
            )
        else:
            self.log_widget.log_message(
                f"✗ Publish failed: {result.get('message', '')}",
                "error",
            )

    # ── DevTools Handlers ──

    @Slot()
    def _on_dev_show_context(self):
        """Display current context data in activity log."""
        context = self.context_widget.get_context_data()
        result = "Current Context Data:\n" + "=" * 50 + "\n"
        for key, value in context.items():
            result += f"{key:15}: {value}\n"

        self.log_widget.log_message(result, "info")
        print(result)
        self.dev_tools.update_status("Context data displayed", "success")

    @Slot()
    def _on_dev_show_config(self):
        """Display current YAML configuration in activity log."""
        config = self.controller.config_manager.get_config()
        result = (
            "Current Configuration:\n" + "=" * 50 + f"""
Config source: {self.controller.config_manager._config_path or '(defaults)'}
enable_database: {config.enable_database}
publish_root:    {config.publish_root or '(not set)'}
project_root:    {config.project_root or '(not set)'}
DB host:         {config.database.host}
DB port:         {config.database.port}
Log level:       {config.logging.level}
"""
        )
        self.log_widget.log_message(result, "info")
        print(result)
        self.dev_tools.update_status("Config displayed", "success")

    @Slot()
    def _on_dev_init_env(self):
        """Initialize test environment directories."""
        config = self.controller.config_manager.get_config()
        project_root = Path(config.project_root) if config.project_root else None
        publish_root = Path(config.publish_root) if config.publish_root else None

        ensure_test_environment(project_root, publish_root)
        self.context_widget.manual_refresh()

        self.log_widget.log_message("Test environment initialized", "success")
        self.dev_tools.update_status("Test environment ready", "success")

    @Slot()
    def _on_dev_reload_config(self):
        """Reload YAML configuration and update publish service."""
        self.controller.reload_config()
        self.log_widget.log_message(
            "Config reloaded "
            f"(db={'on' if self.controller.publish_service.enable_database else 'off'})",
            "info",
        )
        self.dev_tools.update_status("Configuration reloaded", "success")

    # ── Window Lifecycle ──

    def show(self):
        """Show window, center on screen, and emit ready signal."""
        super().show()
        center_window_on_screen(self)
        self.window_ready.emit()

    def cleanup(self):
        """Cleanup resources on application shutdown."""
        self.context_widget.cleanup()
        self.log_widget.cleanup()
        self.controller.cleanup()

    def closeEvent(self, event):
        """Handle window close — cleanup database pool and other resources."""
        self.cleanup()
        super().closeEvent(event)


def test_main_window():
    """Launch main window in standalone test mode."""
    app = QApplication([])
    app.setApplicationName("Y Publisher")
    app.setOrganizationName("Frank")

    controller = PublisherController(standalone_mode=True)
    window = MainWindow(controller)
    window.show()

    return app.exec()


if __name__ == "__main__":
    import sys
    sys.exit(test_main_window())
