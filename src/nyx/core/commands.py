import pathlib
from collections import OrderedDict
from PySide2 import QtWidgets

from nyx.core import Node
from nyx.core import Stage


class NyxCommand(QtWidgets.QUndoCommand):
    def __init__(self, text: str, parent: QtWidgets.QUndoCommand = None) -> None:
        super().__init__(text, parent)


class CreateNodeCommand(NyxCommand):
    def __init__(self, stage: Stage, parent_path=None, position=None, parent_command=None) -> None:
        super().__init__("Create Node", parent=parent_command)
        self.stage = stage
        self.position = position
        self.parent_path = parent_path
        self.node_data: OrderedDict = None

    def redo(self) -> None:
        node = Node()
        self.stage.add_node(node, parent=self.parent_path)
        self.node_data = node.serialize()

        self.setText(f"Create node ({node.path.as_posix()})")
        return super().redo()

    def undo(self) -> None:
        self.stage.delete_node(self.node_data.get("path"))
        self.node_data = None
        return super().undo()


class DeleteNodeCommand(NyxCommand):
    def __init__(self, stage: Stage,
                 node: "Node | pathlib.PurePosixPath | str",
                 parent: QtWidgets.QUndoCommand = None) -> None:
        super().__init__("Delete node", parent)
        self.stage = stage
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
    def __init__(self, stage: Stage,
                 node: "Node | pathlib.PurePosixPath | str",
                 new_name: str,
                 parent_command: QtWidgets.QUndoCommand = None) -> None:
        super().__init__("Rename node", parent=parent_command)
        self.stage = stage

        node = self.stage.node(node)
        self.new_name = new_name
        self.renamed_node_data: pathlib.PurePosixPath = None
        self.old_name = node.name
        self.node_data = node.serialize()

        self.setText(f"Rename node ({self.old_name} -> {self.new_name})")

    def redo(self) -> None:
        node = self.stage.node(self.node_data.get("path"))
        node.rename(self.new_name)
        self.renamed_node_data = node.serialize()
        return super().redo()

    def undo(self) -> None:
        node = self.stage.node(self.renamed_node_data.get("path"))
        node.rename(self.old_name)
        return super().undo()
