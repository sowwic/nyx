import logging

from PySide6 import QtGui

from nyx.editor.widgets.startup_splash import NyxStartupSplash
from nyx.utils import logging_fn, pyside_fn


def test_screen_for_window_geometry_defaults_to_primary(qtbot):
    primary_screen = QtGui.QGuiApplication.primaryScreen()

    assert pyside_fn.screen_for_window_geometry(None, None) is primary_screen
    assert pyside_fn.screen_for_window_geometry((0, 0), None) is primary_screen


def test_screen_for_window_geometry_off_screen_falls_back_to_primary(qtbot):
    primary_screen = QtGui.QGuiApplication.primaryScreen()

    assert pyside_fn.screen_for_window_geometry((-90000, -90000), (10, 10)) is (
        primary_screen
    )


def test_screen_for_window_geometry_finds_screen_of_window_center(qtbot):
    screen = QtGui.QGuiApplication.primaryScreen()
    geometry = screen.geometry()

    found_screen = pyside_fn.screen_for_window_geometry(
        (geometry.x() + 10, geometry.y() + 10), (200, 100)
    )

    assert found_screen is screen


def test_splash_shows_logged_messages(qtbot):
    splash = NyxStartupSplash()
    qtbot.addWidget(splash)
    logger = logging.getLogger("test_startup_splash")
    logger.propagate = False
    signal_handler = logging_fn.QSignalHandler()
    logger.addHandler(signal_handler)
    logger.setLevel(logging.INFO)
    splash.connect_to_logger(signal_handler)

    logger.info("Loading plugin %s", "alpha")

    assert splash.message() == "Loading plugin alpha"

    splash.disconnect_from_logger()
    logger.info("ignored")

    assert splash.message() == "Loading plugin alpha"
