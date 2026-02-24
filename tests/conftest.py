import os
import pathlib
import pytest
import logging
from PySide6 import QtWidgets

from nyx.core.logger import NyxLogger
from nyx.application import NyxApplication

logging.setLoggerClass(NyxLogger)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def output_dir() -> pathlib.Path:
    """Output directory for tests.

    Returns:
        pathlib.Path: path to test output directory.

    """
    out_dir = pathlib.Path.cwd() / ".test_output"
    out_dir.mkdir(exist_ok=True)
    return out_dir


@pytest.fixture
def nyx_app():
    """
    Ensure a QApplication exists for tests that require Qt features
    like clipboard, fonts, resources, etc.
    """
    app: NyxApplication = QtWidgets.QApplication.instance()

    if app is None:
        app = NyxApplication()

    yield app

    # Do NOT call app.quit() or app.exit()
    # Qt clipboard & global state must remain valid during test session
