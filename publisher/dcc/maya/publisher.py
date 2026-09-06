"""
Maya in-DCC publisher integration.

Provides automatic context detection from the Maya environment
and launches the Pipeline Publisher UI parented to the Maya main window.

Usage:
    MayaPublisher.launch()

Context detection flow:
    1. Read PIPELINE_* environment variables (set by launcher)
    2. Fall back to legacy SHOW/SEQ/SHOT/ROLE for backward compatibility
    3. Read current Maya scene via cmds.file()
    4. Combine into a context dict → PublisherController → MainWindow
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

from publisher.core.constants import (
    ENV_PROJECT,
    ENV_SEQUENCE,
    ENV_SHOT,
    ENV_DEPARTMENT,
    ENV_USER,
    CTX_PROJECT,
    CTX_SEQUENCE,
    CTX_SHOT,
    CTX_DEPARTMENT,
    CTX_USER,
    CTX_DCC,
    CTX_PUBLISH_ROOT,
    CTX_PROJECT_ROOT,
)


class MayaPublisher:
    """Manages the Pipeline Publisher lifecycle inside Maya.

    Handles:
    - Context detection (env vars + Maya scene file)
    - PublisherController creation
    - MainWindow parenting to Maya's main window
    - Singleton window management (prevent duplicates)

    Class-level _instance tracking ensures only one publisher window
    exists at a time — subsequent launch() calls raise/activate it.
    """

    _instance: Optional["QMainWindow"] = None

    # ── Context Detection ──────────────────────────────────

    @classmethod
    def _detect_context(cls) -> dict:
        """Auto-detect publish context from Maya environment.

        Priority:
            1. PIPELINE_* environment variables (modern, preferred)
            2. Legacy SHOW/SEQ/SHOT/ROLE (backward compatibility)
            3. cmds.file() for the current scene file

        Returns:
            dict with keys: project, sequence, shot, department,
            user, dcc, source_path, publish_root, project_root
        """
        ctx = {
            CTX_PROJECT: os.environ.get(
                ENV_PROJECT, os.environ.get("SHOW", "")
            ),
            CTX_SEQUENCE: os.environ.get(
                ENV_SEQUENCE, os.environ.get("SEQ", "")
            ),
            CTX_SHOT: os.environ.get(
                ENV_SHOT, os.environ.get("SHOT", "")
            ),
            CTX_DEPARTMENT: os.environ.get(
                ENV_DEPARTMENT, os.environ.get("ROLE", "")
            ),
            CTX_USER: os.environ.get(
                ENV_USER, os.environ.get("USER", "")
            ),
            CTX_DCC: "maya",
            CTX_PROJECT_ROOT: os.environ.get("PROJECT_ROOT", ""),
            CTX_PUBLISH_ROOT: os.environ.get("PUBLISH_ROOT", ""),
        }

        # Get source file path from current Maya scene
        try:
            import maya.cmds as cmds
            ctx["source_path"] = cmds.file(query=True, sceneName=True) or ""
        except Exception:
            ctx["source_path"] = ""

        return ctx

    @classmethod
    def _get_maya_parent_window(cls):
        """Get the Maya main window as a Qt parent widget.

        Uses Maya's MQtUtil + shiboken6 to bridge C++ → PySide6 QWidget.
        """
        try:
            import maya.OpenMayaUI as omui
            import shiboken6
            from PySide6 import QtWidgets

            ptr = omui.MQtUtil.mainWindow()
            if ptr is None:
                raise RuntimeError("MQtUtil.mainWindow() returned None")

            parent = shiboken6.wrapInstance(int(ptr), QtWidgets.QWidget)
            return parent

        except ImportError as e:
            raise RuntimeError(
                "Cannot import Maya modules — not running inside Maya"
            ) from e

    # ── Window Lifecycle ───────────────────────────────────

    @classmethod
    def launch(cls):
        """Launch the Pipeline Publisher window inside Maya.

        If a publisher window already exists and is visible, it is
        raised and activated instead of creating a new one.
        """
        # Prevent duplicate windows — raise existing one
        if cls._instance is not None and cls._instance.isVisible():
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance

        # Add project root to sys.path if needed
        cls._ensure_import_path()

        from publisher.ui.main_window import MainWindow
        from publisher.core.controller import PublisherController
        from PySide6.QtCore import Qt

        # Step 1: Get Maya parent window
        parent = cls._get_maya_parent_window()

        # Step 2: Detect context
        context = cls._detect_context()

        # Step 3: Create controller
        controller = PublisherController(standalone_mode=False)

        # Inject detected context into the environment
        env_map = {
            ENV_PROJECT: context.get(CTX_PROJECT, ""),
            ENV_SEQUENCE: context.get(CTX_SEQUENCE, ""),
            ENV_SHOT: context.get(CTX_SHOT, ""),
            ENV_DEPARTMENT: context.get(CTX_DEPARTMENT, ""),
        }
        for key, val in env_map.items():
            if val:
                os.environ.setdefault(key, val)

        # Step 4: Create and show MainWindow
        window = MainWindow(controller=controller, parent=parent)
        window.setAttribute(Qt.WA_DeleteOnClose, True)
        window.setWindowTitle("Pipeline Publisher - Maya")

        # Wire up Maya pre-publish hook
        window.publish_widget.pre_publish_hook = cls._maya_pre_publish

        window.show()

        # Keep reference
        cls._instance = window
        window.destroyed.connect(lambda: cls._clear_instance())

        print(
            f"[Pipeline Publisher] Maya publisher launched. "
            f"Context: {context.get(CTX_PROJECT)}/"
            f"{context.get(CTX_SEQUENCE)}/"
            f"{context.get(CTX_SHOT)}/"
            f"{context.get(CTX_DEPARTMENT)}"
        )

        return window

    # ── Pre-Publish Hook (Save → Version Up → Publish) ──────

    @staticmethod
    def _version_up_path(scene_path: str) -> str:
        """Increment the version number in a Maya scene file path.

        Patterns matched (in order):
            ``name_v001.ma`` → ``name_v002.ma``
            ``name_v1.mb``   → ``name_v2.mb``
            ``name.ma``      → ``name_v001.ma``  (if no version found)

        Args:
            scene_path: Current scene file path

        Returns:
            File path with incremented version
        """
        p = Path(scene_path)
        stem = p.stem      # e.g. "shot001_v001"
        ext = p.suffix     # e.g. ".ma" or ".mb"

        # Match _v followed by digits at the end of the stem
        match = re.search(r"_v(\d+)$", stem)
        if match:
            num = int(match.group(1)) + 1
            pad = len(match.group(1))
            new_stem = stem[:match.start()] + f"_v{num:0{pad}d}"
            return str(p.parent / f"{new_stem}{ext}")
        else:
            # No version — start at v001
            return str(p.parent / f"{stem}_v001{ext}")

    @classmethod
    def _maya_pre_publish(cls) -> Optional[str]:
        """Maya pre-publish hook: save scene → version up → return new path.

        Called before each publish to ensure:
            1. Current (possibly unsaved) scene is saved
            2. Scene is version-up'ed (v001 → v002)
            3. Maya switches to the new version file
            4. The new version path is returned as the publish source

        Returns:
            Path to the version-up'ed scene file, or None on failure
        """
        try:
            import maya.cmds as cmds

            # Step 1: Get current scene path
            current_path = cmds.file(query=True, sceneName=True)
            if not current_path:
                raise RuntimeError(
                    "Current scene has no file path (unsaved)"
                )

            # Step 2: Save current scene
            cmds.file(save=True, force=True)
            print(f"[Pipeline Publisher] Saved: {current_path}")

            # Step 3: Version up filename
            new_path = cls._version_up_path(current_path)
            print(f"[Pipeline Publisher] Version up: {new_path}")

            # Step 4: Save as new version (switches Maya to new path)
            cmds.file(rename=new_path)
            cmds.file(save=True, force=True)
            print(f"[Pipeline Publisher] Now on: {new_path}")

            return new_path

        except ImportError:
            print(
                "[Pipeline Publisher] Cannot import 'maya.cmds' — "
                "not in Maya?"
            )
            return None
        except Exception as e:
            print(f"[Pipeline Publisher] Pre-publish hook failed: {e}")
            raise

    @classmethod
    def close(cls) -> None:
        """Close the publisher window if open."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None

    # ── Internal Helpers ───────────────────────────────────

    @classmethod
    def _clear_instance(cls) -> None:
        """Clear the singleton window reference."""
        cls._instance = None

    @staticmethod
    def _ensure_import_path() -> None:
        """Ensure the publisher package is importable from sys.path."""
        project_root = Path(__file__).resolve().parent.parent.parent
        root_str = str(project_root)

        if root_str not in sys.path:
            sys.path.insert(0, root_str)
