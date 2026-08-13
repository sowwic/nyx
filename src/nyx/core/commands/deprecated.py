import logging
import pathlib
from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from ._base_nyx_command import NyxCommand

LOGGER = logging.getLogger(__name__)


class SetNodeExecStartCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str | None,
        path: pathlib.PurePosixPath | str | Node,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set exec start ->", parent)
        self.node_path = self.stage.node(node).path
        self.path = path
        self.old_exec_path = None
        self.setText(f"Set {self.node_path} exec start -> {self.path}")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_exec_path = node.get_execution_start_path()
        self.stage.set_execution_start_path(node, self.path)
        return super().redo()

    def undo(self) -> None:
        self.stage.set_execution_start_path(self.node_path, self.old_exec_path)
        return super().undo()


class SetStageExecStartCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        path: pathlib.PurePosixPath | str | Node,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set stage exec start -> ", parent)
        self.path = path
        self.old_exec_path = None
        self.setText(f"{self.text()}{self.path}")

    def redo(self) -> None:
        self.old_exec_path = self.stage.get_execution_start_path(None)
        self.stage.set_execution_start_path(None, self.path)
        return super().redo()

    def undo(self) -> None:
        self.stage.set_execution_start_path(None, self.old_exec_path)
        return super().undo()


class ConnectNodeExecCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        output_node: Node | pathlib.PurePosixPath | str,
        input_node: Node | pathlib.PurePosixPath | str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Connect exec", parent)
        self.output_node_path = self.stage.node(output_node).path
        self.input_node_path = self.stage.node(input_node).path
        self.old_output_node_exec_value = None
        self.old_input_node_exec_value = None
        self.setText(f"{self.text()} {self.output_node_path} -> {self.input_node_path}")

    def redo(self) -> None:
        output_node = self.stage.node(self.output_node_path)
        input_node = self.stage.node(self.input_node_path)

        self.old_output_node_exec_value = output_node.get_output_exec_path()
        self.old_input_node_exec_value = input_node.get_input_exec_path()
        input_node.set_input_exec_path(output_node)
        return super().redo()

    def undo(self) -> None:
        output_node = self.stage.node(self.output_node_path)
        input_node = self.stage.node(self.input_node_path)

        output_node.set_output_exec_path(self.old_output_node_exec_value)
        input_node.set_input_exec_path(self.old_input_node_exec_value)
        return super().undo()


class DisconnectNodeInputExecCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Disconnect exec input", parent)
        self.node_path = self.stage.node(node).path
        self.setText(f"{self.text()} ({self.node_path})")
        self.previous_input_exec_path = None

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.previous_input_exec_path = node.get_input_exec_path()
        node.set_input_exec_path(None)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_input_exec_path(self.previous_input_exec_path)
        return super().undo()


class SetNodeCommentCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str | None,
        comment: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Edit comment for", parent)
        self.node_path = self.stage.node(node).path
        self.old_comment = None
        self.new_comment = comment
        self.setText(f"{self.text()} ({self.node_path})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_comment = node.comment()
        node.set_comment(self.new_comment)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_comment(self.old_comment)
        return super().undo()
