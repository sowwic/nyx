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

    nodeSpawned = QtCore.Signal(Node)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spawn_position: QtCore.QPointF | None = None

    @property
    def spawn_position(self) -> QtCore.QPointF | None:
        return self._spawn_position

    @spawn_position.setter
    def spawn_position(self, position: QtCore.QPointF | None) -> None:
        if position is None:
            self._spawn_position = None
            return

        if not isinstance(position, QtCore.QPointF):
            raise TypeError(
                f"Spawn position can be of type QPointF or None, got {type(position)}"
            )
        self._spawn_position = position

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
        self.spawn_position = None
        return self.spawnNode(type_id=type_id, position=None)

    @QtCore.Slot(str, result=Node)
    def spawnNode(self, type_id: str, position: QtCore.QPointF | None = None):
        current_editor = self.current_stage_graph
        if current_editor is None:
            return

        position = (
            position
            or self.spawn_position
            or current_editor.gr_view.get_center_position()
        )

        stage = current_editor.stage
        current_scope = self.current_stage_graph.get_scope_path()
        command = CreateNodeCommand(
            stage=self.stage,
            type_id=type_id,
            parent_node=current_scope,
            position=position,
        )
        stage.push_command(command)
        result_node = command.result_node

        self.nodeSpawned.emit(result_node)
        return result_node
