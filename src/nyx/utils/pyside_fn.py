from PySide2 import QtWidgets


def move_window_to_screen_center(window: QtWidgets.QWidget):
    # type: (QtWidgets.QWidget) -> None
    center_position = window.pos() + QtWidgets.QApplication.primaryScreen().geometry().center() - \
        window.geometry().center()
    window.move(center_position)
