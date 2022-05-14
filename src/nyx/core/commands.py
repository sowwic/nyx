import pathlib
from collections import OrderedDict
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import Node
from nyx.core import Stage


LOGGER = get_main_logger()


class NyxCommand(QtWidgets.QUndoCommand):
    def __init__(self,
                 stage: "Stage",
                 text: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(text, parent_command=parent_command)
        self.stage = stage


class CreateNodeCommand(NyxCommand):
    def __init__(self,
                 stage: Stage,
                 node_name: str = "node",
                 parent_path: str = None,
                 position: "list[float, float]" = None,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage=stage, text="Create Node", parent_command=parent_command)
        self.position = position
        self.parent_path = parent_path
        self.node_name = node_name
        self.node_data: OrderedDict = None

    def redo(self) -> None:
        node = Node(name=self.node_name)
        self.stage.add_node(node, parent=self.parent_path)
        self.node_data = node.serialize()

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.node_data.get("path"))
        self.node_data = None
        return super().undo()


class DeleteNodeCommand(NyxCommand):
    def __init__(self,
                 stage: Stage,
                 node: "Node | pathlib.PurePosixPath | str",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage=stage, text="Delete node", parent_command=parent_command)
        node = self.stage.node(node)
        self.node_data = node.serialize()
        self.setText(f"Delete node ({node.path.as_posix()})")

    def redo(self) -> None:
        self.stage.delete_node(self.node_data.get("path"))
        return super().redo()

    def undo(self) -> None:
        node_path: pathlib.PurePosixPath = pathlib.PurePosixPath(self.node_data.get("path"))
        parent_path = node_path.parent
        new_node = Node()
        self.stage.add_node(new_node, parent=parent_path)
        new_node.deserialize(self.node_data, {}, restore_id=True)
        return super().undo()


class RenameNodeCommand(NyxCommand):
    def __init__(self,
                 stage: Stage,
                 node: "Node | pathlib.PurePosixPath | str",
                 new_name: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage=stage, text="Rename node", parent_command=parent_command)

        node = self.stage.node(node)
        self.new_name = new_name
        self.renamed_node_data: pathlib.PurePosixPath = None
        self.old_name = node.name
        self.node_data = node.serialize()

        self.setText(f"Rename node ({node.path.as_posix()} -> {self.new_name})")

    def redo(self) -> None:
        node = self.stage.node(self.node_data.get("path"))
        node.rename(self.new_name)
        self.renamed_node_data = node.serialize()
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.renamed_node_data.get("path"))
        node.rename(self.old_name)
        return super().undo()


class AddNodeAttributeCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str",
                 attr_name: str,
                 attr_value=None,
                 attr_resolve=True,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Add attr", parent_command)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.attr_resolve = attr_resolve
        self.setText(f"{self.text()} {self.node_path.as_posix()} ({self.attr_name})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        node.add_attr(self.attr_name, value=self.attr_value, resolve=self.attr_resolve)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.delete_attr(self.attr_name)
        return super().undo()


class DeleteNodeAttributeCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str",
                 attr_name: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Delete attr", parent_command)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.attr_serialized = None
        self.setText(f"{self.text()} {self.node_path.as_posix()} ({self.attr_name})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.attr_serialized = node.attr(self.attr_name).serialize()
        node.delete_attr(self.attr_name)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        attr_name = self.attr_serialized["name"]
        node.add_attr(attr_name)
        node.attr(attr_name).deserialize(self.attr_serialized, {}, restore_id=True)
        return super().undo()


class RenameNodeAttributeCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str",
                 attr_name: str,
                 new_attr_name: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Rename attr", parent_command)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.new_attr_name = new_attr_name
        self.setText(
            f"{self.text()} {self.node_path.as_posix()} ({self.attr_name}) -> '{self.new_attr_name}'")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        node.rename_attr(self.attr_name, self.new_attr_name)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.rename_attr(self.new_attr_name, self.attr_name)
        return super().undo()


class SetNodeAttributeCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str",
                 attr_name: str,
                 attr_value=None,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Set attr", parent_command)
        self.node_path = self.stage.node(node).path
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.old_attr_value = None
        self.setText(
            f"{self.text()} {self.node_path.as_posix()} ({self.attr_name}) -> {self.attr_value}")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_attr_value = node.attr(self.attr_name).get(raw=True)
        node.set_attr(self.attr_name, self.attr_value)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_attr(self.attr_name, self.old_attr_value)
        return super().undo()


class ConnectAttribute(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 source_node: "Node | pathlib.PurePosixPath | str",
                 destination_node: "Node | pathlib.PurePosixPath | str",
                 source_attr_name: str,
                 destination_attr_name: str,
                 resolve_on_connect=True,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Connect attr", parent_command)
        self.source_node_path = self.stage.node(source_node).path
        self.destination_node_path = self.stage.node(destination_node).path
        self.source_attr_name = source_attr_name
        self.destination_attr_name = destination_attr_name

        LOGGER.debug(destination_attr_name)

        self.destination_attr_old_value = None
        self.resolve_on_connect = resolve_on_connect
        self.setText(
            f"{self.text()} {self.source_node_path.as_posix()} ({self.source_attr_name}) -> {self.destination_node_path.as_posix()} ({self.destination_attr_name})")  # noqa: E501

    def redo(self) -> None:
        source_node = self.stage.node(self.source_node_path)
        destination_node = self.stage.node(self.destination_node_path)
        self.destination_attr_old_value = destination_node.attr(
            self.destination_attr_name).get(raw=True)
        source_node.attr(self.source_attr_name).connect(
            destination_node.attr(self.destination_attr_name), resolve=self.resolve_on_connect)

        return super().redo()

    def undo(self) -> None:
        destination_node = self.stage.node(self.destination_node_path)
        destination_node.attr(self.destination_attr_name).set(
            self.destination_attr_old_value, resolve=True)
        return super().undo()


class SetNodeExecStartCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 path: "pathlib.PurePosixPath | str | Node",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Set exec start ->", parent_command)
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
    def __init__(self,
                 stage: "Stage",
                 path: "pathlib.PurePosixPath | str | Node",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Set stage exec start -> ", parent_command)
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
    def __init__(self,
                 stage: "Stage",
                 output_node: "Node | pathlib.PurePosixPath | str",
                 input_node: "Node | pathlib.PurePosixPath | str",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Connect exec", parent_command)
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


class EditNodePythonCode(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 new_code: "str",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Edit code", parent_command)
        self.new_code = new_code
        self.old_code = node.get_python_code()
        self.node_path = self.stage.node(node).path
        self.setText(f"Edit code ({self.node_path.as_posix()})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_python_code(self.new_code)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_python_code(self.old_code)
        return super().undo()
