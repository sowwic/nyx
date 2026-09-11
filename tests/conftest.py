import os
import pathlib
import pytest
import logging

from PySide6 import QtWidgets

from nyx.core.logger import NyxLogger
from nyx.application import NyxApplication

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
    output_root = project_root / ".test_output"

    test_file = pathlib.Path(str(request.fspath))
    relative_dir = test_file.parent.relative_to(tests_root)

    module_name = test_file.stem.removeprefix("test_")
    directory = output_root / relative_dir / module_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.fixture
def nyx_app():
    """
    Ensure a QApplication exists for tests that require Qt features
    like clipboard, fonts, resources, etc.
    """
    app: NyxApplication = QtWidgets.QApplication.instance()

    if app is None:
        app = NyxApplication(initialize_plugins=False)

    yield app

    # Do NOT call app.quit() or app.exit()
    # Qt clipboard & global state must remain valid during test session
