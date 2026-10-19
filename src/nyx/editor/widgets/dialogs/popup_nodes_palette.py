import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from ...views.nodes_palette_view import NodesPaletteView


if typing.TYPE_CHECKING:
    from ....core.node import Node
    from ...widgets.stage_graph_editor import StageGraphEditor
    from ....application import NyxEditorApplication


# TODO: Potentially a singleton?
class PopupNodesPalette(QtWidgets.QDialog):
    """Frameless popup with the nodes palette, closing once a node is created."""

    def __init__(self, scene_pos, parent=None):
        """Initialize PopupNodesPalette.

        Args:
            scene_pos (QtCore.QPointF): scene position the node is created at.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(
            parent, QtCore.Qt.WindowType.Dialog | QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFixedSize(400, 500)

        self._scene_pos = scene_pos
        self._chosen_node_type_id: UUID | None

        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    def _create_widgets(self):
        """Create the palette view."""
        self._nodes_palette_view = NodesPaletteView(drag_enabled=False, parent=self)

    def _create_layouts(self):
        """Lay out the palette view."""
        self._main_layout = QtWidgets.QVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._main_layout)
        self._main_layout.addWidget(self._nodes_palette_view)

    def _create_connections(self):
        """Close the popup when a node is spawned."""
        self._nodes_palette_view.nodes_spawner.nodeSpawned.connect(self.deleteLater)

    @staticmethod
    def clamp_to_bounds(
        top_left: QtCore.QPoint, size: QtCore.QSize, bounds: QtCore.QRect
    ) -> QtCore.QPoint:
        """Move a rectangle inside bounds, keeping its top left corner visible.

        Args:
            top_left (QtCore.QPoint): wanted top left corner.
            size (QtCore.QSize): size of the rectangle.
            bounds (QtCore.QRect): area the rectangle has to stay in.

        Returns:
            QtCore.QPoint: top left corner that keeps the rectangle in bounds. A
                rectangle bigger than the bounds is aligned to their top left.
        """
        x = min(top_left.x(), bounds.right() - size.width() + 1)
        y = min(top_left.y(), bounds.bottom() - size.height() + 1)
        return QtCore.QPoint(max(x, bounds.left()), max(y, bounds.top()))

    def move_within_screen(
        self, top_left: QtCore.QPoint, anchor: QtCore.QPoint | None = None
    ):
        """Move the palette so it is fully inside the usable area of a screen.

        Args:
            top_left (QtCore.QPoint): wanted global top left corner.
            anchor (QtCore.QPoint | None): global point choosing the screen, such as
                the cursor. Defaults to the top left corner.
        """
        screen = (
            QtGui.QGuiApplication.screenAt(anchor or top_left)
            or QtGui.QGuiApplication.primaryScreen()
        )
        if screen is None:
            self.move(top_left)
            return
        self.move(
            self.clamp_to_bounds(top_left, self.size(), screen.availableGeometry())
        )

    def set_spawner_position(self, position: QtCore.QPointF):
        """Set the position nodes are created at.

        Args:
            position (QtCore.QPointF): scene position.
        """
        self._nodes_palette_view.nodes_spawner.spawn_position = position

    @classmethod
    def get_current_editor(cls) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        application: NyxEditorApplication = QtWidgets.QApplication.instance()
        return application.main_window().current_stage_graph

    @classmethod
    def popup_centered(cls, spawn_position: QtCore.QPointF | None = None):
        """Show the palette modally, centered over the main window."""
        current_editor = cls.get_current_editor()
        if current_editor is None:
            return

        window = current_editor.window()
        palette = cls(spawn_position, parent=window)
        if spawn_position is not None:
            palette.set_spawner_position(QtCore.QPointF(spawn_position))
        center = window.geometry().center()
        palette.move_within_screen(center - palette.rect().center(), anchor=center)
        palette.exec()
        return palette

    @classmethod
    def popup(cls, on_node_spawned: typing.Callable[[Node], None] | None = None):
        """Show the palette at the cursor, creating nodes at that scene position.

        Args:
            on_node_spawned (Callable[[Node], None] | None): called with the node
                created by the palette.
        """
        current_editor = cls.get_current_editor()
        if current_editor is None:
            return

        stage_graph_view = current_editor.gr_view

        global_pos = QtGui.QCursor.pos()
        scene_pos = stage_graph_view.mapToScene(
            stage_graph_view.mapFromGlobal(global_pos)
        )

        palette = cls(scene_pos, parent=stage_graph_view.window())
        palette.set_spawner_position(QtCore.QPointF(scene_pos.x(), scene_pos.y()))
        if on_node_spawned is not None:
            palette._nodes_palette_view.nodes_spawner.nodeSpawned.connect(
                on_node_spawned
            )
        palette.move_within_screen(global_pos)
        palette.exec()
        return palette
