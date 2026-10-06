import logging
import typing

from PySide6 import QtCore, QtWidgets

from ...core.node import Node
from ...core.commands import CreateNodeCommand


if typing.TYPE_CHECKING:
    from ...core.stage import Stage
    from ...application import NyxEditorApplication
    from ..widgets.stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class NodeSpawner(QtCore.QObject):
    """Owns selection state for a components model and keeps it
    consistent across reorders."""

    def __init__(self, parent=None):
        super().__init__(parent)

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        application: NyxEditorApplication = QtWidgets.QApplication.instance()
        return application.main_window().current_stage_graph

    @property
    def stage(self) -> Stage | None:
        current_editor = self.current_stage_graph
        if current_editor is None:
            return None
        return current_editor.stage

    @QtCore.Slot(str, result=Node)
    def spawnNodeAtCenter(self, type_id: str) -> Node:
        return self.spawnNode(type_id=type_id, position=None)

    @QtCore.Slot(str, QtCore.QPointF, result=Node)
    def spawnNode(self, type_id: str, position: QtCore.QPointF | None = None):
        current_editor = self.current_stage_graph
        if current_editor is None:
            return

        if position is None:
            position = current_editor.gr_view.get_center_position()

        stage = current_editor.stage
        current_scope = self.current_stage_graph.get_scope_path()
        command = CreateNodeCommand(
            stage=self.stage,
            type_id=type_id,
            parent_node=current_scope,
            position=position,
        )
        stage.push_command(command)
        return command.result_node
