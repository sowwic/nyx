import os
import sys
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core.config import Config
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.core import commands

os.environ["QT_MAC_WANTS_LAYER"] = "1"
LOGGER = get_main_logger()


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self.__config = Config.load()
        LOGGER.setLevel(self.config().logging_level)

    def config(self):
        return self.__config

    def reset_config(self):
        """Reset application config."""
        self.__config = self.config().reset()


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        NyxEditorMainWindow.display()
        self.main_window().create_stage_node_graph()

        self.test_commands()

    def main_window(self):
        return NyxEditorMainWindow.instance()

    def test_commands(self):
        stage = self.main_window().current_stage_graph.stage

        # Create 2 nodes
        create_cmd1 = commands.CreateNodeCommand(stage)
        create_cmd2 = commands.CreateNodeCommand(stage, parent_path="/node")
        create_cmd3 = commands.CreateNodeCommand(stage, parent_path="/node")
        create_cmd4 = commands.CreateNodeCommand(stage, node_name="test_custom_name")

        stage.undo_stack.push(create_cmd1)
        stage.undo_stack.push(create_cmd2)
        stage.undo_stack.push(create_cmd3)
        stage.undo_stack.push(create_cmd4)

        # Renamed parent
        rename_cmd1 = commands.RenameNodeCommand(stage, "/node", new_name="parent_node")
        stage.undo_stack.push(rename_cmd1)

        rename_cmd2 = commands.RenameNodeCommand(stage, "/parent_node/node", new_name="child_node")
        stage.undo_stack.push(rename_cmd2)

        # Delete parent
        del_cmd = commands.DeleteNodeCommand(stage, "/parent_node")
        stage.undo_stack.push(del_cmd)
