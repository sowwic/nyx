import sys
import logging
from PySide6 import QtGui, QtWidgets

import nyx.resources.resources_rc  # noqa: F401
from nyx.version import __version__
from nyx.core.config import Config
from nyx.editor.main_window import NyxEditorMainWindow
from nyx.core import commands
from nyx.utils import pyside_fn


LOGGER = logging.getLogger(__name__)


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self.setApplicationDisplayName("Nyx")
        self.setWindowIcon(QtGui.QIcon(":/icons/nyx.png"))
        self.setApplicationVersion(__version__)
        self._config = Config.load()
        LOGGER.setLevel(self.config().logging_level)

    def config(self):
        return self._config

    def reset_config(self):
        """Reset application config."""
        self._config = self.config().reset()


class NyxEditorApplication(NyxApplication):
    def __init__(self) -> None:
        super().__init__()
        if self.config().dark_mode:
            pyside_fn.set_dark_fusion_palette(self)

        NyxEditorMainWindow.display()
        self.main_window().on_stage_new()

        self.test_commands()

    def main_window(self):
        return NyxEditorMainWindow.instance()

    def test_commands(self):
        stage = self.main_window().current_stage_graph.stage

        # Create 2 nodes
        create_cmd1 = commands.CreateNodeCommand(stage)
        create_cmd2 = commands.CreateNodeCommand(stage, parent_path="/node")
        create_cmd3 = commands.CreateNodeCommand(stage, parent_path="/node")
        create_cmd4 = commands.CreateNodeCommand(stage, node_name="test_node")
        create_cmd5 = commands.CreateNodeCommand(
            stage, node_name="test_child", parent_path="/test_node"
        )

        stage.push_command(create_cmd1)
        stage.push_command(create_cmd2)
        stage.push_command(create_cmd3)
        stage.push_command(create_cmd4)
        stage.push_command(create_cmd5)

        # Renamed parent
        rename_cmd1 = commands.RenameNodeCommand(stage, "/node", new_name="parent_node")
        stage.push_command(rename_cmd1)

        rename_cmd2 = commands.RenameNodeCommand(
            stage, "/parent_node/node", new_name="child_node"
        )
        stage.push_command(rename_cmd2)

        # Attributes
        add_attr_cmd1 = commands.AddNodeAttributeCommand(
            stage, node="/test_node", attr_name="test_attr", attr_value=5
        )
        set_attr_cmd = commands.SetNodeAttributeCommand(
            stage, node="/test_node", attr_name="test_attr", attr_value=10
        )
        add_attr_cmd2 = commands.AddNodeAttributeCommand(
            stage, node="/test_node/test_child", attr_name="child_attr"
        )
        stage.push_command(add_attr_cmd1)
        stage.push_command(set_attr_cmd)
        stage.push_command(add_attr_cmd2)

        conn_attr_cmd = commands.ConnectAttributeCommand(
            stage,
            source_node="/test_node",
            destination_node="/test_node/test_child",
            source_attr_name="test_attr",
            destination_attr_name="child_attr",
        )
        stage.push_command(conn_attr_cmd)

        rename_attr_cmd = commands.RenameNodeAttributeCommand(
            stage,
            node="/test_node/test_child",
            attr_name="child_attr",
            new_attr_name="new_attr",
        )
        stage.push_command(rename_attr_cmd)

        # Exec starts
        stage_exec_start_cmd = commands.SetStageExecStartCommand(stage, "/test_node")
        stage.push_command(stage_exec_start_cmd)

        node_exec_start_cmd = commands.SetNodeExecStartCommand(
            stage, node="/parent_node", path="/parent_node/node1"
        )
        stage.push_command(node_exec_start_cmd)

        # Node exec connections
        child_node_to_node1_exec_cmd = commands.ConnectNodeExecCommand(
            stage, output_node="/parent_node/child_node", input_node="/parent_node/node1"
        )
        stage.push_command(child_node_to_node1_exec_cmd)
        # Deletions
        # del_attr_cmd = commands.DeleteNodeAttributeCommand(
        #     stage, node="/test_node/test_child", attr_name="new_attr",)
        # stage.push_command(del_attr_cmd)

        # LOGGER.debug(stage.describe())
        # Delete parent
        # del_cmd = commands.DeleteNodeCommand(stage, "/parent_node")
        # stage.push_command(del_cmd)
