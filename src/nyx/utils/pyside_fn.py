import typing

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.main_window import NyxEditorMainWindow


def move_window_to_screen_center(window: QtWidgets.QWidget):
    """Move a window to the center of the primary screen.

    Args:
        window (QtWidgets.QWidget): window to move.
    """
    center_position = (
        window.pos()
        + QtWidgets.QApplication.primaryScreen().geometry().center()
        - window.geometry().center()
    )
    window.move(center_position)


def screen_for_window_geometry(
    position: tuple[int, int] | None, size: tuple[int, int] | None
) -> QtGui.QScreen:
    """Find the screen a window with the given geometry opens on.

    Args:
        position (tuple[int, int] | None): window position, None for the default.
        size (tuple[int, int] | None): window size, None for the default.

    Returns:
        QtGui.QScreen: screen holding the window center, the primary screen if the
            geometry is not set or lies outside every screen.
    """
    primary_screen = QtGui.QGuiApplication.primaryScreen()
    if not position or not size:
        return primary_screen
    window_rect = QtCore.QRect(QtCore.QPoint(*position), QtCore.QSize(*size))
    return QtGui.QGuiApplication.screenAt(window_rect.center()) or primary_screen


def dark_fusion_palette() -> QtGui.QPalette:
    """Build the dark palette.

    Returns:
        QtGui.QPalette: dark palette.
    """
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(208, 208, 208))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    # Stripes of alternating rows, a step lighter than the base
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(34, 34, 34))
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
    """Apply the fusion style with the dark palette.

    Args:
        application (QtWidgets.QApplication): application to style.
    """
    application.setStyle(QtWidgets.QStyleFactory.create("fusion"))
    application.setPalette(dark_fusion_palette())


def min_bounding_rect(rects: list[QtCore.QRect]):
    """Get the rectangle containing all given rectangles.

    Args:
        rects (list[QtCore.QRect]): rectangles, at least one.

    Returns:
        QtCore.QRectF: bounding rectangle.
    """
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
    """Get a style standard icon by name.

    Args:
        widget: widget providing the style.
        icon_name (str): QStyle.StandardPixmap member name.

    Returns:
        QtGui.QIcon: standard icon.
    """
    pixmap = getattr(QtWidgets.QStyle, icon_name)
    icon = widget.style().standardIcon(pixmap)
    return icon


def find_nyx_editor_window() -> NyxEditorMainWindow:
    """Find nyx editor main window.

    Raises:
        RuntimeError: no window found

    Returns:
        NyxEditorMainWindow: editor's main window

    """
    top_widgets = QtWidgets.QApplication.topLevelWidgets()
    for widget in top_widgets:
        if hasattr(widget, "_is_nyx_editor_window"):
            return widget
    else:
        raise RuntimeError("Failed to find nyx editor main window.")


def notify_roles_changed(
    self,
    item_index: QtCore.QModelIndex,
    roles_that_changed: typing.Iterable[int],
) -> None:
    """Emit dataChanged for given roles of an item.

    Args:
        item_index (QtCore.QModelIndex): changed item. Invalid indexes are ignored.
        roles_that_changed (typing.Iterable[int]): changed roles.
    """
    if not item_index.isValid():
        return
    self.dataChanged.emit(
        item_index,
        item_index,
        [int(each_role) for each_role in roles_that_changed],
    )
