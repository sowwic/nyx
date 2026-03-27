import logging
import pathlib
from PySide6 import QtGui

from nyx.core import Node
from nyx.core import Stage
from ._base_nyx_command import NyxCommand

LOGGER = logging.getLogger(__name__)


class AddNodeAttributeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        attr_name: str,
        attr_value=None,
        attr_resolve=True,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Add attr", parent)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.attr_resolve = attr_resolve
        self.setText(f"{self.text()} {self.node_path.as_posix()} ({self.attr_name})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        new_attr = node.add_attr(
            self.attr_name, value=self.attr_value, resolve=self.attr_resolve
        )
        self.attr_name = new_attr.name
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.delete_attr(self.attr_name)
        return super().undo()


class DeleteNodeAttributeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        attr_names: list[str],
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Delete attrs", parent)
        self.node_path = self.stage.node(node).path
        self.attr_names = attr_names
        self.attrs_serialized = []
        self.setText(f"{self.text()} {self.node_path.as_posix()} {self.attr_names}")

    def redo(self) -> None:
        self.attrs_serialized.clear()
        node = self.stage.node(self.node_path)
        self.attrs_serialized = [node.attr(name).serialize() for name in self.attr_names]
        for name in self.attr_names:
            node.delete_attr(name)

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        for attr_data in self.attrs_serialized:
            attr_name = attr_data["name"]
            node.add_attr(attr_name)
            node.attr(attr_name).deserialize(attr_data)
        return super().undo()


class RenameNodeAttributeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        attr_name: str,
        new_attr_name: str,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Rename attr", parent)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.new_attr_name = new_attr_name
        self.setText(
            f"{self.text()} {self.node_path.as_posix()} "
            f"({self.attr_name}) -> '{self.new_attr_name}'"
        )

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.new_attr_name = node.rename_attr(self.attr_name, self.new_attr_name).name
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.rename_attr(self.new_attr_name, self.attr_name)
        return super().undo()


class SetNodeAttributeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        node: Node | pathlib.PurePosixPath | str,
        attr_name: str,
        attr_value=None,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Set attr", parent)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.old_attr_value = None
        self.setText(
            f"{self.text()} {self.node_path.as_posix()} "
            f"({self.attr_name}) -> {self.attr_value}"
        )

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_attr_value = node.attr(self.attr_name).get(raw=True)
        node.set_attr(self.attr_name, self.attr_value)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_attr(self.attr_name, self.old_attr_value)
        return super().undo()


class ConnectAttributeCommand(NyxCommand):
    def __init__(
        self,
        stage: Stage,
        source_node: Node | pathlib.PurePosixPath | str,
        destination_node: Node | pathlib.PurePosixPath | str,
        source_attr_name: str,
        destination_attr_name: str,
        resolve_on_connect=True,
        parent: QtGui.QUndoCommand | None = None,
    ) -> None:
        super().__init__(stage, "Connect attr", parent)
        self.source_node_path = self.stage.node(source_node).path
        self.destination_node_path = self.stage.node(destination_node).path
        self.source_attr_name = source_attr_name
        self.destination_attr_name = destination_attr_name

        LOGGER.debug(destination_attr_name)

        self.destination_attr_old_value = None
        self.resolve_on_connect = resolve_on_connect
        self.setText(
            f"{self.text()} {self.source_node_path.as_posix()} "
            f"({self.source_attr_name}) -> {self.destination_node_path.as_posix()} "
            f"({self.destination_attr_name})"
        )

    def redo(self) -> None:
        source_node = self.stage.node(self.source_node_path)
        destination_node = self.stage.node(self.destination_node_path)
        self.destination_attr_old_value = destination_node.attr(
            self.destination_attr_name
        ).get(raw=True)
        source_node.attr(self.source_attr_name).connect(
            destination_node.attr(self.destination_attr_name),
            resolve=self.resolve_on_connect,
        )

        return super().redo()

    def undo(self) -> None:
        destination_node = self.stage.node(self.destination_node_path)
        destination_node.attr(self.destination_attr_name).set(
            self.destination_attr_old_value, resolve=True
        )
        return super().undo()


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
