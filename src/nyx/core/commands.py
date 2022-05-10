import pathlib
from collections import OrderedDict
from PySide2 import QtWidgets

from nyx.core import Node
from nyx.core import Stage


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
        self.setText(f"{self.text()} '{self.attr_name}' to {self.node_path.as_posix()}")

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
        self.setText(f"{self.text()} '{self.attr_name}' from {self.node_path.as_posix()}")

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
        self.setText(f"{self.text()} '{self.attr_name}' \
            -> '{self.new_attr_name}' on {self.node_path.as_posix()}")

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

    def redo(self) -> None:
        node = self.stage.node(self.node_path)
        self.old_attr_value = node.attr(self.attr_name).get(raw=True)
        node.set_attr(self.attr_name, self.attr_value)
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.node_path)
        node.set_attr(self.attr_name, self.old_attr_value)
        return super().undo()
