import os
import pathlib
import pytest
import logging
from pytest import MonkeyPatch

from PySide6 import QtCore, QtWidgets

from nyx.core.logger import NyxLogger
from nyx.application import NyxApplication, NyxEditorApplication
from nyx.api.v1 import NyxPluginManager, NYX_REGISTRY
from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.main_window import NyxEditorMainWindow

logging.setLoggerClass(NyxLogger)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def output_dir(request: pytest.FixtureRequest) -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    tests_root = pathlib.Path(__file__).parent
    project_root = tests_root.parent
    output_root = project_root / "test_output"

    test_file = pathlib.Path(str(request.fspath))
    relative_dir = test_file.parent.relative_to(tests_root)

    module_name = test_file.stem.removeprefix("test_")
    directory = output_root / relative_dir / module_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def pytest_collection_modifyitems(config, items):
    """Remember whether editor tests are collected (they need the editor app)."""
    editor_dir = pathlib.Path(__file__).parent / "editor"
    config._nyx_needs_editor_app = any(
        editor_dir in pathlib.Path(str(item.fspath)).parents for item in items
    )


def _release_editor_objects(app: QtWidgets.QApplication) -> None:
    """Destroy editor widgets and global actions while Python and Qt are alive.

    Otherwise they are torn down at interpreter exit, after the QApplication, which
    segfaults (exit code 139) on some platforms.
    """
    if not isinstance(app, NyxEditorApplication):
        return

    main_window = NyxEditorMainWindow.instance()
    if main_window is not None:
        main_window.deleteLater()
        NyxEditorMainWindow._INSTANCE = None
    ACTION_REGISTRY.clear()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()


# Do NOT call app.quit() or app.exit()
@pytest.fixture(scope="session")
def qapp(request: pytest.FixtureRequest):
    """Session-wide application, overriding pytest-qt's `qapp`.

    A single QApplication may exist per process, so when editor tests are part of
    the run the full `NyxEditorApplication` (with main window) is created for
    everybody; otherwise a plain `NyxApplication`.
    """
    app = QtWidgets.QApplication.instance()
    if app is None:
        if getattr(request.config, "_nyx_needs_editor_app", False):
            app = NyxEditorApplication()
        else:
            app = NyxApplication(initialize_plugins=False)
    yield app
    _release_editor_objects(app)


@pytest.fixture(autouse=True)
def isolate_user_config(qapp, monkeypatch):
    """Keep tests from persisting anything (e.g. recent files) to the user config."""
    monkeypatch.setattr(qapp.config, "save", lambda *args, **kwargs: None)
    session = qapp.config.values.editor_session
    monkeypatch.setattr(session, "recent_files", [])
    # Tests expect display names, whatever the user toggled in the editor.
    behaviour = qapp.config.values.editor_behaviour
    monkeypatch.setattr(behaviour, "show_address_names", False)


@pytest.fixture
def nyx_app(qapp):
    """Application for tests needing Qt features (clipboard, fonts, resources)."""
    return qapp


@pytest.fixture(autouse=True, scope="session")
def init_nyx_core(qapp):
    try:
        plugin_manager = NyxPluginManager()
        if not isinstance(qapp, NyxEditorApplication):
            # The editor application initializes the plugins itself.
            plugin_manager.initialize_plugins(include=["NyxStdlib"])
        yield plugin_manager
    except Exception as err:
        pytest.exit(f"NyxStdlib initialization failed: {err!r}", returncode=2)
    finally:
        NYX_REGISTRY.clear()


@pytest.fixture(autouse=True)
def with_plugins(request):
    marker = request.node.get_closest_marker("with_plugins")
    if marker is None:
        yield None
        return

    try:
        plugin_manager = NyxPluginManager()
        plugin_manager.initialize_plugins(include=list(marker.args))
    except Exception as err:
        pytest.fail(reason=f"Failed to initialize plugins: {err!r}", pytrace=True)
    finally:
        # TODO: Uninitialize extra plugins
        yield plugin_manager


@pytest.fixture
def make_script(tmp_path: pathlib.Path):
    def _make_script(content: str, filename: str = "script.py"):
        path = tmp_path / filename
        path.write_text(content)
        return path

    return _make_script


@pytest.fixture
def importable_module(tmp_path: pathlib.Path, monkeypatch: MonkeyPatch):
    def _make_module(name: str, content: str):
        module_file = tmp_path / f"{name}.py"
        module_file.write_text(content)
        monkeypatch.syspath_prepend(str(tmp_path))
        return name

    yield _make_module
