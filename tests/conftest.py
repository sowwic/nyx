import os
import pathlib
import pytest
import logging

from PySide6 import QtWidgets

from nyx.core.logger import NyxLogger
from nyx.application import NyxApplication
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


# Do NOT call app.quit() or app.exit()
@pytest.fixture
def nyx_app():
    """
    Ensure a QApplication exists for tests that require Qt features
    like clipboard, fonts, resources, etc.
    """
    app: NyxApplication | None = QtWidgets.QApplication.instance()

    if app is None:
        app = NyxApplication(
            initialize_plugins=False
        )  # Qt clipboard & global state must remain valid during test session

    yield app


@pytest.fixture(autouse=True, scope="session")
def init_nyx_core():
    try:
        plugin_manager = NyxPluginManager()
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
def make_script(tmp_path):
    def _make_script(content: str, filename: str = "script.py"):
        path = tmp_path / filename
        path.write_text(content)
        return path

    return _make_script
