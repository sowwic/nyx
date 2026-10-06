import typing
from uuid import UUID

from PySide6 import QtCore, QtGui, QtWidgets

from ...views.nodes_palette_view import NodesPaletteView


if typing.TYPE_CHECKING:
    from ...widgets.stage_graph_editor import StageGraphEditor
    from ....application import NyxEditorApplication


class PopupNodesPalette(QtWidgets.QDialog):
    def __init__(self, scene_pos, parent=None):
        super().__init__(
            parent, QtCore.Qt.WindowType.Dialog | QtCore.Qt.FramelessWindowHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setFixedSize(400, 600)

        self._scene_pos = scene_pos
        self._chosen_node_type_id: UUID | None

        self._create_widgets()
        self._create_layouts()

    def _create_widgets(self):
        self._nodes_palette_view = NodesPaletteView(self)

    def _create_layouts(self):
        self._main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self._main_layout)
        self._main_layout.addWidget(self._nodes_palette_view)

    @classmethod
    def get_current_editor(cls) -> StageGraphEditor | None:
        application: NyxEditorApplication = QtWidgets.QApplication.instance()
        return application.main_window().current_stage_graph

    @classmethod
    def popup(cls):
        current_editor = cls.get_current_editor()
        if current_editor is None:
            return

        stage_graph_view = current_editor.gr_view

        global_pos = QtGui.QCursor.pos()
        scene_pos = stage_graph_view.mapToScene(
            stage_graph_view.mapFromGlobal(global_pos)
        )

        palette = cls(scene_pos, parent=stage_graph_view.window())
        palette.move(global_pos)
        palette.exec()
        return palette
