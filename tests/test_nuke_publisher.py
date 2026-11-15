"""Nuke publishes what is on screen — the pre-publish save (2026-11-08 bug).

The rehearsal's first comp publish copied a 190-byte template while the artist's
script held 2,573 bytes of nodes, reported success, and the library recorded an
empty v001. Cause: Houdini and Maya hook ``publish_widget.pre_publish_hook`` to
save + version-up before copying; ``publisher/dcc/`` had no nuke package, so the
Nuke menu went straight to the generic shell and the hook never existed.

The facts these tests pin were measured on Nuke 17.0v4 rather than assumed:

* ``nuke.scriptName()`` raises ``RuntimeError`` for a never-saved session.
* ``nuke.scriptSave()`` writes nothing while ``root().modified()`` is False, so
  the save-as to the new version is the write that carries the nodes.
* ``nuke.scriptSaveAs(path, 0)`` refuses to overwrite, hence the free-version
  search before saving.

A fake ``nuke`` module stands in for all of it — the real one is only available
inside Nuke, and these are unit contracts, not integration smoke tests.
"""

from __future__ import annotations

import sys
import types

import pytest

from publisher.dcc.nuke.publisher import NukePublisher


# ── Doubles ─────────────────────────────────────────────────────────────


class FakeNuke:
    """The three Nuke calls the hook makes, recording their order."""

    def __init__(self, script_name=None, save_as_error=None, write_file=True):
        self.calls: list[tuple] = []
        self._script_name = script_name
        self._save_as_error = save_as_error
        self._write_file = write_file

    def scriptName(self):
        if isinstance(self._script_name, BaseException):
            raise self._script_name
        return self._script_name

    def scriptSave(self):
        self.calls.append(("save",))

    def scriptSaveAs(self, path, overwrite=None):
        self.calls.append(("saveAs", path, overwrite))
        if self._save_as_error is not None:
            raise self._save_as_error
        if self._write_file:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("Root {\n inputs 0\n}\n")
        self._script_name = path


class FakePublishWidget:
    """The two widget calls the hook touches."""

    def __init__(self, source: str = ""):
        self.pre_publish_hook = None
        self._source = source

    def get_source_path(self) -> str:
        return self._source

    def set_source_path(self, path: str) -> None:
        self._source = path


def fake_window(source: str = ""):
    return types.SimpleNamespace(
        publish_widget=FakePublishWidget(source),
        isVisible=lambda: False,
        show=lambda: None,
        raise_=lambda: None,
        activateWindow=lambda: None,
        destroyed=types.SimpleNamespace(connect=lambda *_a, **_k: None),
    )


@pytest.fixture
def nuke_module(monkeypatch):
    """Install a fake ``nuke`` in ``sys.modules``; yield a setter for it."""

    installed: dict[str, FakeNuke] = {}

    def install(fake: FakeNuke) -> FakeNuke:
        installed["fake"] = fake
        monkeypatch.setitem(sys.modules, "nuke", fake)
        return fake

    return install


@pytest.fixture(autouse=True)
def reset_singleton():
    """A leaked ``_instance`` would make the next launch return a stale window."""
    NukePublisher._instance = None
    yield
    NukePublisher._instance = None


@pytest.fixture
def script(tmp_path):
    """A saved v001 script, as Hatch leaves it in the shot's department folder."""
    folder = tmp_path / "re_test_001" / "comp"
    folder.mkdir(parents=True)
    path = folder / "re_test_001_v001.nk"
    path.write_text("Root {\n inputs 0\n}\n", encoding="utf-8")
    return path


# ── The save itself ─────────────────────────────────────────────────────


class TestNukePrePublish:
    def test_saves_the_session_then_saves_as_the_next_version(
        self, nuke_module, script
    ):
        fake = nuke_module(FakeNuke(str(script)))

        result = NukePublisher._nuke_pre_publish()

        assert result == str(script.parent / "re_test_001_v002.nk")
        assert [call[0] for call in fake.calls] == ["save", "saveAs"]
        # overwrite=0 → Nuke refuses rather than silently replacing a file
        assert fake.calls[1] == ("saveAs", result, 0)

    def test_the_new_version_is_the_file_that_gets_published(
        self, nuke_module, script
    ):
        """The returned path must exist: it is what ``copy_file`` reads next."""
        nuke_module(FakeNuke(str(script)))

        result = NukePublisher._nuke_pre_publish()

        assert result is not None
        assert open(result, encoding="utf-8").read().startswith("Root {")

    def test_an_existing_next_version_is_skipped(self, nuke_module, script):
        """v002 already on disk → v003. Never overwrite, never prompt."""
        (script.parent / "re_test_001_v002.nk").write_text("x", encoding="utf-8")
        (script.parent / "re_test_001_v003.nk").write_text("x", encoding="utf-8")
        nuke_module(FakeNuke(str(script)))

        result = NukePublisher._nuke_pre_publish()

        assert result == str(script.parent / "re_test_001_v004.nk")

    def test_no_version_in_the_name_starts_at_v001_of_that_stem(
        self, nuke_module, script
    ):
        unversioned = script.parent / "wip.nk"
        unversioned.write_text("Root {\n}\n", encoding="utf-8")
        nuke_module(FakeNuke(str(unversioned)))

        result = NukePublisher._nuke_pre_publish()

        assert result == str(script.parent / "wip_v001.nk")

    def test_an_unsaved_session_raises_instead_of_publishing_nothing(
        self, nuke_module
    ):
        nuke_module(
            FakeNuke(
                RuntimeError("no filename available, have you saved?")
            )
        )

        with pytest.raises(RuntimeError, match="no file path"):
            NukePublisher._nuke_pre_publish()

    def test_a_failed_save_as_does_not_return_a_path(self, nuke_module, script):
        """A path that was not written must never reach the copier."""
        nuke_module(FakeNuke(str(script), save_as_error=OSError("disk full")))

        with pytest.raises(OSError, match="disk full"):
            NukePublisher._nuke_pre_publish()

    def test_without_nuke_it_declines_rather_than_writes(
        self, monkeypatch, script
    ):
        monkeypatch.setitem(sys.modules, "nuke", None)

        assert NukePublisher._nuke_pre_publish() is None


# ── The guard: external files must not hijack the session ───────────────


class TestPrePublishGuard:
    def test_publishes_the_session_when_that_is_the_source(
        self, nuke_module, script
    ):
        fake = nuke_module(FakeNuke(str(script)))
        hook = NukePublisher._pre_publish_guarded(fake_window(str(script)))

        assert hook() == str(script.parent / "re_test_001_v002.nk")
        assert [call[0] for call in fake.calls] == ["save", "saveAs"]

    def test_no_source_chosen_means_the_session_is_the_source(
        self, nuke_module, script
    ):
        fake = nuke_module(FakeNuke(str(script)))

        assert NukePublisher._pre_publish_guarded(fake_window())() is not None
        assert [call[0] for call in fake.calls] == ["save", "saveAs"]

    def test_an_external_source_is_published_untouched(self, nuke_module, script):
        """Publishing a cache or a colleague's script must not version-up ours."""
        fake = nuke_module(FakeNuke(str(script)))
        other = script.parent / "colleague_v009.nk"
        hook = NukePublisher._pre_publish_guarded(fake_window(str(other)))

        assert hook() is None
        assert fake.calls == []

    def test_an_unsaved_session_says_what_to_do(self, nuke_module):
        nuke_module(
            FakeNuke(RuntimeError("no filename available, have you saved?"))
        )
        hook = NukePublisher._pre_publish_guarded(fake_window(""))

        with pytest.raises(RuntimeError, match="save the script once"):
            hook()


# ── Launch wiring ───────────────────────────────────────────────────────


class TestLaunchWiring:
    def test_launch_attaches_the_hook_and_adopts_the_open_script(
        self, nuke_module, script, monkeypatch
    ):
        nuke_module(FakeNuke(str(script)))
        window = fake_window()
        captured: dict[str, object] = {}

        def fake_shell(standalone_mode=False, show=True, title_suffix=None):
            captured["standalone_mode"] = standalone_mode
            captured["title_suffix"] = title_suffix
            return None, window

        monkeypatch.setattr(
            "publisher.dcc.launcher._launch_dcc_shell", fake_shell
        )

        from publisher.dcc.launcher import launch_nuke

        returned = launch_nuke(show=False)

        assert returned == (None, window)
        assert captured == {"standalone_mode": False, "title_suffix": "Nuke"}
        assert callable(window.publish_widget.pre_publish_hook)
        # Source follows the session, not "newest file in the folder".
        assert window.publish_widget.get_source_path() == str(script)

    def test_a_second_launch_raises_the_existing_window(
        self, nuke_module, script, monkeypatch
    ):
        nuke_module(FakeNuke(str(script)))
        window = fake_window()
        window.isVisible = lambda: True
        raised: list[str] = []
        window.raise_ = lambda: raised.append("raised")

        monkeypatch.setattr(
            "publisher.dcc.launcher._launch_dcc_shell",
            lambda **kwargs: (None, window),
        )
        from publisher.dcc.launcher import launch_nuke

        launch_nuke(show=False)          # first: creates
        again = launch_nuke(show=False)  # second: raises, no new window

        assert again == (None, window)
        assert raised == ["raised"]
