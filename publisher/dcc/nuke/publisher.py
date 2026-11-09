"""
Nuke in-DCC publisher integration.

Two things make Nuke the odd one out, and they are the same thing twice:

*Nuke has no project switch.* ``-m`` is a render thread count (passing it a path
crashed Nuke 17 on 2026-10-25) and there is no ``$JOB``-style knob; its "project
folder" is the folder of the open script. Pipeline Hatch therefore opens
``<shot>_v001.nk`` on launch, which puts File > Save As in the department folder.
That fixed *where* a save lands.

*It did not fix when.* Publishing copies a file, and Nuke keeps the node graph in
memory until something writes it. On 2026-11-08 the first comp publish copied the
190-byte template while the artist's script held 2,573 bytes of nodes, reported
success, and the library recorded an empty v001. Houdini and Maya have had a
pre-publish hook since v1 (save → version-up → save as); Nuke had none, because
``publisher/dcc/`` had no nuke package at all and the Nuke menu went straight to
the generic standalone shell.

This module gives Nuke the same hook, with the same contract as the other two:
save the session, version the script up, save that new file, and publish it. An
external file picked with Browse never triggers the save — the guard only fires
when the publish source *is* the session script.

Measured on Nuke 17.0v4 (headless), because each of these decides how the hook
is written:

* ``nuke.scriptName()`` **raises** ``RuntimeError('no filename available, have
  you saved?')`` for a never-saved session — "unsaved" is an exception, not an
  empty string.
* ``nuke.scriptSave()`` is a **no-op while** ``nuke.root().modified()`` is False,
  and a terminal-mode session never marks the root dirty — adding a Blur left
  ``modified() == False`` and ``scriptSave()`` wrote nothing (499 B before and
  after). So the flush that matters is the ``scriptSaveAs`` to the new version:
  it wrote the in-memory nodes every time (499 B → 545 B, Blur present). Keeping
  ``scriptSave()`` in the sequence is still right for the GUI session, where the
  artist's unsaved edits are what we are flushing; it just cannot be the only
  write.
* ``nuke.scriptSaveAs(path, 0)`` raises ``... : file exists`` rather than
  overwriting, so the next free version is chosen *before* saving — no modal
  dialog, no silent overwrite of a colleague's v002.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from publisher.core.file_system.path_builder import PathBuilder

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


class NukePublisher:
    """Manages the Pipeline Publisher lifecycle inside Nuke.

    Same contract as :class:`publisher.dcc.houdini.publisher.HoudiniPublisher`:
    one window at a time, context from the launcher-injected ``PIPELINE_*`` env,
    and a pre-publish hook that turns "publish what is on screen" into truth.
    """

    _instance: Optional[Any] = None

    # ── Window Lifecycle ──

    @classmethod
    def launch(cls, show: bool = True) -> "QMainWindow":
        """Launch the Publisher window inside Nuke, hook attached.

        If a publisher window already exists and is visible, it is raised
        instead of creating a second one.

        Args:
            show: Whether to show the window immediately.

        Returns:
            The publisher MainWindow instance.
        """
        if cls._instance is not None and cls._instance.isVisible():
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance

        # The generic DCC shell already detects the environment, builds the
        # controller with standalone_mode=False and titles the window; Nuke only
        # adds the hook and the open-script source below.
        from publisher.dcc.launcher import _launch_dcc_shell

        _, window = _launch_dcc_shell(
            standalone_mode=False, show=False, title_suffix="Nuke"
        )

        window.publish_widget.pre_publish_hook = cls._pre_publish_guarded(window)

        # Publish what is open, not merely what is newest on disk. The auto
        # detection in MainWindow scans the department folder and picks a file;
        # with two scripts sitting there (v001 and v002) that guess can differ
        # from the session the artist is looking at.
        cls._bind_open_script(window)

        if show:
            window.show()
        cls._instance = window
        window.destroyed.connect(lambda: cls._clear_instance())

        print("[Pipeline Publisher] Nuke publisher launched.")
        return window

    @classmethod
    def _clear_instance(cls) -> None:
        """Forget the window so the next launch creates a fresh one."""
        cls._instance = None

    @classmethod
    def _bind_open_script(cls, window: Any) -> None:
        """Adopt the session script as the publish source when none is chosen."""
        try:
            current = cls._current_script()
        except RuntimeError as exc:
            print(f"[Pipeline Publisher] {exc}")
            return
        if window.publish_widget.get_source_path():
            return
        window.publish_widget.set_source_path(current)
        print(f"[Pipeline Publisher] Source: {current}")

    # ── Pre-Publish Hook (Save → Version Up → Publish) ──

    @classmethod
    def _pre_publish_guarded(cls, window: Any):
        """Return the hook, skipping the save when publishing an external file.

        Versioning up the live session must not hijack a publish that is
        deliberately about some other file (an exported cache, a colleague's
        script). Same guard as Houdini's.
        """

        def hook() -> Optional[str]:
            try:
                current = cls._current_script()
            except RuntimeError as exc:
                # Publishing the open-but-never-saved session must fail loudly:
                # there is no file to copy, and a silent skip would publish a
                # stale neighbour instead.
                raise RuntimeError(
                    f"{exc} — save the script once (File > Save As), then publish"
                ) from exc

            source = window.publish_widget.get_source_path()
            if source and os.path.abspath(source) != os.path.abspath(current):
                print(
                    "[Pipeline Publisher] External source — skipping script "
                    f"save/version-up ({source})"
                )
                return None
            return cls._nuke_pre_publish(current)

        return hook

    @classmethod
    def _nuke_pre_publish(cls, current: Optional[str] = None) -> Optional[str]:
        """Save the session, version the script up, and return the new path.

        Args:
            current: Session script path. Read from ``nuke.scriptName()`` when
                omitted.

        Returns:
            Path of the version-up'ed script, which the publisher then copies.

        Raises:
            RuntimeError: ``nuke`` is missing, the session was never saved, or
                the save-as failed. Publishing must stop rather than copy an
                older file and call it a success.
        """
        try:
            import nuke
        except ImportError:
            print("[Pipeline Publisher] Cannot import 'nuke' — skipping save.")
            return None

        current = current or cls._current_script()
        parent = Path(current).parent

        # Flush unsaved edits (a no-op when Nuke does not consider the script
        # dirty — the save-as below is what guarantees the nodes reach disk).
        nuke.scriptSave()
        print(f"[Pipeline Publisher] Saved: {current}")

        target = cls._next_free_version(parent, Path(current).name)
        nuke.scriptSaveAs(target, 0)
        print(f"[Pipeline Publisher] Version up, now on: {target}")

        return target

    @staticmethod
    def _current_script() -> str:
        """Path of the open script, with an actionable error when unsaved.

        Nuke raises (rather than returning ``""``) for a never-saved session, so
        the message is re-raised in pipeline terms.
        """
        import nuke

        try:
            return nuke.scriptName()
        except RuntimeError as exc:
            raise RuntimeError(
                f"Current Nuke script has no file path ({exc})"
            ) from exc

    @staticmethod
    def _next_free_version(parent: Path, filename: str) -> str:
        """First version-up'ed filename in *parent* that does not exist yet.

        ``scriptSaveAs(path, 0)`` refuses to overwrite, so choosing the name
        first keeps a stale v002 from turning into either a modal dialog or a
        failed publish.
        """
        candidate = parent / PathBuilder.version_up_filename(filename)
        guard = 0
        while candidate.exists():
            candidate = parent / PathBuilder.version_up_filename(candidate.name)
            guard += 1
            if guard > 999:
                raise RuntimeError(
                    f"Cannot find a free version next to {filename} in {parent}"
                )
        return str(candidate)
