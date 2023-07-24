from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets


def move_window_to_screen_center(window: QtWidgets.QWidget):
    center_position = window.pos() + QtWidgets.QApplication.primaryScreen().geometry().center() - \
        window.geometry().center()
    window.move(center_position)


def dark_fusion_palette() -> QtGui.QPalette:
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(45, 45, 48))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.Highlight, QtCore.Qt.gray)

    return palette


def set_dark_fusion_palette(application: QtWidgets.QApplication):
    application.setStyle(QtWidgets.QStyleFactory.create("fusion"))
    application.setPalette(dark_fusion_palette())


def min_bounding_rect(rects: "list[QtCore.QRect]"):
    min_x = rects[0].left()
    min_y = rects[0].top()
    max_x = rects[0].right()
    max_y = rects[0].bottom()

    for k in range(1, len(rects)):
        min_x = min(min_x, rects[k].left())
        min_y = min(min_y, rects[k].top())
        max_x = max(max_x, rects[k].right())
        max_y = max(max_y, rects[k].bottom())

    return QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y)


def get_standard_icon(widget, icon_name: str):
    pixmap = getattr(QtWidgets.QStyle, icon_name)
    icon = widget.style().standardIcon(pixmap)
    return icon
