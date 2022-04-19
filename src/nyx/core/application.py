import os
import sys
from PySide2 import QtWidgets

from nyx.core import Stage, Node
from nyx.core.config import Config
from nyx.widgets.stage_tree_widget import StageTreeWidget
from nyx.widgets.code_editor import CodeEditor
from nyx import get_main_logger

os.environ["QT_MAC_WANTS_LAYER"] = "1"
LOGGER = get_main_logger()


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)
        self.config = Config.load()
        LOGGER.setLevel(self.config.logging_level)

        stage = Stage()
        self.tree_view = StageTreeWidget(stage)
        self.code_editor = CodeEditor()
        self.code_editor.show()
        self.tree_view.show()

# =================== TESTING AREA ========================== #
        # Add nodes
        for index in range(3):
            base_node = Node("node")
            base_node["count"] = 5
            stage.add_node(base_node)
            for child_index in range(3):
                child_node = Node("child_node", base_node)
                for deep_index in range(3):
                    leaf_node = Node("leaf_node", child_node)
                    leaf_node["count"] = 10

        self.tree_view.selection_changed.connect(self.show_current_code)
        self.code_editor.textChanged.connect(self.set_node_code)
        self.tree_view.selection_changed.connect(
            lambda: print(self.tree_view.current_item().serialize()))

        import pprint
        pprint.pprint(stage.path_map)

    def show_current_code(self):
        current_node = self.tree_view.current_item()
        if current_node:
            self.code_editor.setPlainText(current_node.python_code)

    def set_node_code(self):
        current_node = self.tree_view.current_item()
        if current_node:
            current_node.set_python_code(self.code_editor.toPlainText())

# =================== TESTING AREA ========================== #

    def reset_config(self):
        """Reset application config."""
        self.config = self.config.reset()
