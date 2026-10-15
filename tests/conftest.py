import os
import pathlib
import pytest
import logging
from pytest import MonkeyPatch

from PySide6 import QtWidgets

from nyx.core.logger import NyxLogger
from nyx.application import NyxApplication, NyxEditorApplication
from nyx.api.v1 import NyxPluginManager, NYX_REGISTRY

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
    return app


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
            plugin_manager.initialize_plugins(include=["NyxCore"])
        yield plugin_manager
    except Exception as err:
        pytest.exit(f"NyxCore initialization failed: {err!r}", returncode=2)
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
