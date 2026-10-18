"""
Houdini in-DCC publisher integration.

Provides automatic context detection from the Houdini environment
and launches the Pipeline Publisher UI parented to the Houdini main window.

Usage:
    HoudiniPublisher.launch()

Context detection flow:
    1. Read PIPELINE_* environment variables (set by launcher)
    2. Fall back to legacy SHOW/SEQ/SHOT/ROLE for backward compatibility
    3. Read current Houdini scene via hou.hipFile.path()
    4. Combine into a context dict → PublisherController → MainWindow
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional, TYPE_CHECKING

# Qt binding: PySide6 is the primary target. Inside Houdini, the
# PySide6/ package at the publisher root (on sys.path) re-exports
# PySide2 behind a PySide6 namespace, so no code changes needed.
if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtCore import Qt

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


class HoudiniPublisher:
    """Manages the Pipeline Publisher lifecycle inside Houdini.

    Handles:
    - Context detection (env vars + Houdini scene file)
    - PublisherController creation
    - MainWindow parenting to hou.qt.mainWindow()
    - Singleton window management (prevent duplicates)

    Class-level _instance tracking ensures only one publisher window
    exists at a time — subsequent launch() calls raise/activate it.
    """

    _instance: Optional[QMainWindow] = None

    # ── Context Detection ──

    @classmethod
    def _detect_context(cls) -> dict:
        """Auto-detect publish context from Houdini environment.

        Priority:
            1. PIPELINE_* environment variables (modern, preferred)
            2. Legacy SHOW/SEQ/SHOT/ROLE (backward compatibility)
            3. hou.hipFile.path() for the current scene file

        Returns:
            dict with keys: project, sequence, shot, department,
            user, dcc, source_path, publish_root, project_root
        """
        ctx = {
            CTX_PROJECT:    os.environ.get(ENV_PROJECT,
                              os.environ.get("SHOW", "")),
            CTX_SEQUENCE:   os.environ.get(ENV_SEQUENCE,
                              os.environ.get("SEQ", "")),
            CTX_SHOT:       os.environ.get(ENV_SHOT,
                              os.environ.get("SHOT", "")),
            # PIPELINE_DEPARTMENT primary, ROLE as fallback
            CTX_DEPARTMENT: os.environ.get(ENV_DEPARTMENT,
                              os.environ.get("ROLE", "")),
            CTX_USER:       os.environ.get(ENV_USER,
                              os.environ.get("USER", "")),
            CTX_DCC:        "houdini",
            CTX_PROJECT_ROOT: os.environ.get(
                              "PROJECT_ROOT",
                              os.environ.get("PROJECT_ROOT", "")),
            CTX_PUBLISH_ROOT: os.environ.get(
                              "PUBLISH_ROOT",
                              os.environ.get("PUBLISH_ROOT", "")),
        }

        # Get source file path from current Houdini scene
        try:
            import hou
            ctx["source_path"] = hou.hipFile.path()
        except Exception:
            ctx["source_path"] = ""

        return ctx

    @classmethod
    def _get_houdini_parent_window(cls):
        """Get the Houdini main window as a Qt parent widget.

        Houdini's hou.qt.mainWindow() returns a PySide2 QWidget.
        The Publisher UI uses PySide6 imports — which resolve to the
        PySide6/ shim package that wraps PySide2. Since both sides
        ultimately use PySide2 objects, the parent is directly compatible.

        Returns:
            QWidget: Houdini's main window

        Raises:
            RuntimeError: If not running inside Houdini
        """
        try:
            import hou
            parent = hou.qt.mainWindow()
            if parent is None:
                raise RuntimeError("hou.qt.mainWindow() returned None")

            # No shiboken bridge needed — qt_compat wraps PySide2,
            # and hou.qt.mainWindow() IS a PySide2 QWidget.
            return parent

        except ImportError:
            raise RuntimeError(
                "Cannot import 'hou' module — not running inside Houdini"
            )
        except AttributeError:
            raise RuntimeError(
                "hou.qt.mainWindow() not available — Houdini version may be too old"
            )

    # ── Window Lifecycle ──

    @classmethod
    def launch(cls) -> QMainWindow:
        """Launch the Pipeline Publisher window inside Houdini.

        If a publisher window already exists and is visible, it is
        raised and activated instead of creating a new one.

        Returns:
            The Pipeline Publisher MainWindow instance.
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

        # --- Step 1: Get Houdini parent window ---
        parent = cls._get_houdini_parent_window()

        # --- Step 2: Detect context ---
        context = cls._detect_context()

        # --- Step 3: Create controller (standalone_mode=False → DCC embed) ---
        controller = PublisherController(standalone_mode=False)

        # Inject detected context into the environment so
        # controller/config picks them up via env var fallback
        env_map = {
            ENV_PROJECT: context.get(CTX_PROJECT, ""),
            ENV_SEQUENCE: context.get(CTX_SEQUENCE, ""),
            ENV_SHOT: context.get(CTX_SHOT, ""),
            ENV_DEPARTMENT: context.get(CTX_DEPARTMENT, ""),
        }
        for key, val in env_map.items():
            if val:
                os.environ.setdefault(key, val)

        # --- Step 4: Create and show MainWindow ---
        from PySide6.QtCore import Qt

        window = MainWindow(
            controller=controller,
            parent=parent,
        )
        window.setAttribute(Qt.WA_DeleteOnClose, True)
        window.setWindowTitle("Pipeline Publisher - Houdini")

        # ── Wire up Houdini pre-publish hook ──
        # Version-up the live scene only when the publish source IS the current
        # session hip. Publishing an external file (e.g. an exported USD cache)
        # must not hijack the chosen source.
        def _pre_publish_guarded():
            try:
                import hou
                src = window.publish_widget.get_source_path()
                if src and os.path.abspath(src) != os.path.abspath(hou.hipFile.path()):
                    print("[Pipeline Publisher] External source — skipping scene version-up.")
                    return None
            except Exception as exc:  # noqa: BLE001
                print(f"[Pipeline Publisher] Pre-publish guard failed: {exc}")
            return cls._houdini_pre_publish()

        window.publish_widget.pre_publish_hook = _pre_publish_guarded

        window.show()

        # Keep reference to prevent garbage collection
        cls._instance = window

        # Clean up reference when window is closed
        window.destroyed.connect(lambda: cls._clear_instance())

        print(f"[Pipeline Publisher] Houdini publisher launched. "
              f"Context: {context.get(CTX_PROJECT)}/"
              f"{context.get(CTX_SEQUENCE)}/"
              f"{context.get(CTX_SHOT)}/"
              f"{context.get(CTX_DEPARTMENT)}")

        return window

    # ── Pre-Publish Hook (Save → Version Up → Publish) ──

    @staticmethod
    def _version_up_path(hip_path: str) -> str:
        """Increment the version number in a Houdini scene file path.

        Patterns matched (in order):
            ``name_v001.hip`` → ``name_v002.hip``
            ``name_v1.hip``   → ``name_v2.hip``
            ``name.hip``      → ``name_v001.hip``  (if no version found)

        Args:
            hip_path: Current scene file path

        Returns:
            File path with incremented version
        """
        p = Path(hip_path)
        stem = p.stem      # e.g. "shot001_v001"
        ext = p.suffix     # e.g. ".hip"

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
    def _houdini_pre_publish(cls) -> Optional[str]:
        """Houdini pre-publish hook: save scene → version up → return new path.

        Called before each publish to ensure:
            1. Current (possibly unsaved) scene is saved
            2. Scene is version-up'ed (v001 → v002)
            3. Houdini switches to the new version file
            4. The new version path is returned as the publish source

        Returns:
            Path to the version-up'ed scene file, or None on failure
        """
        try:
            import hou

            # Step 1: Save current scene (even if unsaved changes)
            current_path = hou.hipFile.path()
            if not current_path:
                raise RuntimeError("Current scene has no file path (unsaved)")

            hou.hipFile.save()
            print(f"[Pipeline Publisher] Saved: {current_path}")

            # Step 2: Version up filename
            new_path = cls._version_up_path(current_path)
            print(f"[Pipeline Publisher] Version up: {new_path}")

            # Step 3: Save as new version (switches Houdini to new path)
            hou.hipFile.save(file_name=new_path)
            print(f"[Pipeline Publisher] Now on: {new_path}")

            return new_path

        except ImportError:
            print("[Pipeline Publisher] Cannot import 'hou' — not in Houdini?")
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

    # ── Internal Helpers ──

    @classmethod
    def _clear_instance(cls) -> None:
        """Clear the singleton window reference (connected to destroyed signal)."""
        cls._instance = None

    @staticmethod
    def _ensure_import_path() -> None:
        """Ensure the publisher package is importable from sys.path.

        Uses the project directory of this file (../../..) to calculate
        the project root, so it works regardless of how Houdini's
        Python environment is configured.
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        root_str = str(project_root)

        if root_str not in sys.path:
            sys.path.insert(0, root_str)
