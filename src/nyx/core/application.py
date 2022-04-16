import os
import sys
from PySide2 import QtWidgets

from nyx.core import Stage, Node
from nyx.widgets.stage_tree_widget import StageTreeWidget
from nyx import get_main_logger

os.environ["QT_MAC_WANTS_LAYER"] = "1"
LOGGER = get_main_logger()


class NyxApplication(QtWidgets.QApplication):
    def __init__(self) -> None:
        super().__init__(sys.argv)

        stage = Stage()
        self.tree_view = StageTreeWidget(stage)
        self.tree_view.show()

        # Add nodes
        for index in range(1, 5):
            base_node = Node(f"node{index}")
            stage.add_node(base_node)
            for child_index in range(1, 6):
                child_node = Node(f"child_node{child_index}")
                stage.add_node(child_node, base_node)
                for deep_index in range(1, 4):
                    leaf_node = Node(f"leaf_node{deep_index}")
                    stage.add_node(leaf_node, child_node)
