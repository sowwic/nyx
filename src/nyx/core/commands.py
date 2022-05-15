import pathlib
from collections import OrderedDict
from collections import deque
from collections import Sequence
from PySide2 import QtCore
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
        if isinstance(position, (QtCore.QPointF, QtCore.QPoint)):
            position = [position.x(), position.y()]

        self.position = position
        self.parent_path = parent_path
        self.node_name = node_name
        self.node_data: OrderedDict = None

    def redo(self) -> None:
        node = Node(name=self.node_name)
        self.stage.add_node(node, parent=self.parent_path)
        self.node_data = node.serialize()
        if self.position:
            node.set_position(*self.position)

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.node_data.get("path"))
        self.node_data = None
        return super().undo()


class DeleteNodeCommand(NyxCommand):
    def __init__(self,
                 stage: Stage,
                 nodes: "list[Node | pathlib.PurePosixPath | str]",
                 command_text: str = "Delete node",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage=stage, text=command_text, parent_command=parent_command)
        if not isinstance(nodes, Sequence):
            nodes = [nodes]
        self.serialized_nodes = deque()
        for each_node in nodes:
            each_node = self.stage.node(each_node)
            self.serialized_nodes.append(each_node.serialize())
        self.deleted_paths = deque()

        if not command_text:
            if len(nodes) == 1:
                self.setText(f"Delete node ({nodes[-1].path.as_posix()})")
            else:
                self.setText("Deleted nodes")

    def redo(self) -> None:
        self.deleted_paths.clear()
        serialized_paths = [pathlib.PurePosixPath(node_data.get("path"))
                            for node_data in self.serialized_nodes]
        serialized_paths_set = set(serialized_paths)

        # Filter paths to delete, so that only parent paths are deleted.
        for path in serialized_paths:
            if set(path.parents).intersection(serialized_paths_set):
                continue
            self.deleted_paths.append(path)

        self.stage.delete_node(self.deleted_paths)
        return super().redo()

    def undo(self) -> None:
        for node_data in self.serialized_nodes:
            node_path: pathlib.PurePosixPath = pathlib.PurePosixPath(node_data.get("path"))
            if node_path not in self.deleted_paths:
                continue
            parent_path = node_path.parent
            new_node = Node()
            self.stage.add_node(new_node, parent=parent_path)
            new_node.deserialize(node_data, {}, restore_id=True)
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
        new_attr = node.add_attr(self.attr_name, value=self.attr_value, resolve=self.attr_resolve)
        self.attr_name = new_attr.name
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
        self.new_attr_name = node.rename_attr(self.attr_name, self.new_attr_name).name
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


class ConnectAttributeCommand(NyxCommand):
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


class DisconnectNodeInputExecCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Disconnect exec input", parent_command)
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


class EditNodePythonCodeCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 new_code: "str",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Edit code", parent_command)
        self.new_code = new_code
        self.old_code = node.get_python_code()
        self.node_path = self.stage.node(node).path
        self.setText(f"Edit code ({self.node_path})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_python_code(self.new_code)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_python_code(self.old_code)
        return super().undo()


class SetNodeActiveStateCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 state: bool,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Set active state", parent_command)
        self.node_path = self.stage.node(node).path
        self.old_state = None
        self.new_state = state
        self.setText(f"{self.text()} ({self.node_path} -> {self.new_state})")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_state = node.is_active()
        node.set_active(self.new_state)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_active(self.old_state)
        return super().undo()


class SetNodeCommentCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 comment: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Edit comment for", parent_command)
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


class SetNodePositionCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 node: "Node | pathlib.PurePosixPath | str | None",
                 new_position: "tuple(float, float)",
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Set position", parent_command)
        self.node_path = self.stage.node(node).path
        self.new_position = new_position
        self.old_position = None
        self.setText(
            f"{self.text()} ({self.node_path} -> ({self.new_position[0], self.new_position[1]}))")

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_position = node.position()
        node.set_position(*self.new_position)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_position(*self.old_position)
        return super().undo()


class PasteNodesCommand(NyxCommand):
    def __init__(self,
                 stage: "Stage",
                 serialize_nodes: "list[OrderedDict]",
                 position: "tuple(float, float)",
                 parent_node: "Node | pathlib.PurePosixPath | str | None" = None,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(stage, "Paste nodes", parent_command)
        self.serialized_nodes = serialize_nodes
        self.position = position
        self.created_node_paths = deque()
        self.parent_path = None

        parent_node = self.stage.node(parent_node)
        if parent_node:
            self.parent_path = parent_node.path

    def redo(self) -> None:
        self.created_node_paths.clear()

        # Filter child paths
        serialized_paths = [
            pathlib.PurePosixPath(node_data["path"]) for node_data in self.serialized_nodes]
        serialized_paths_set = set(serialized_paths)
        for node_data in self.serialized_nodes:
            node_path = pathlib.PurePosixPath(node_data["path"])
            if set(node_path.parents).intersection(serialized_paths_set):
                LOGGER.debug(f"Skipping paste: {node_path}")
                continue
            # Create new node and store it's path
            new_node = Node(name="pasted_node")
            self.stage.add_node(new_node, parent=self.parent_path)
            new_node.deserialize(node_data, hashmap={}, restore_id=False)
            paste_position = self.get_paste_position(new_node.position())
            new_node.set_position(*paste_position)

            self.created_node_paths.append(new_node.cached_path)
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.created_node_paths)
        return super().undo()

    def get_paste_position(self, serialized_node_position: "list[float ,float]"):
        min_x, max_x, min_y, max_y = 10000000, -10000000, 10000000, -10000000
        pos_x, pos_y = serialized_node_position
        min_x = min(pos_x, min_x)
        max_x = max(pos_x, max_x)
        min_y = min(pos_y, min_y)
        max_y = max(pos_y, max_y)

        new_x = self.position[0] + pos_x - min_x,
        new_y = self.position[1] + pos_y - min_y

        return [new_x, new_y]
