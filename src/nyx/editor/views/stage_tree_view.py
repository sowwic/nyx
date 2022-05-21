import typing
from collections import deque

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from nyx import get_main_logger
from nyx.core import commands
from nyx.editor.utils import clipboard
from nyx.utils import pyside_fn

if typing.TYPE_CHECKING:
    import pathlib
    from nyx.core import Stage
    from nyx.core import Node
    from nyx.editor.main_window import NyxEditorMainWindow

LOGGER = get_main_logger()


class StageTreeView(QtWidgets.QTreeView):

    selection_changed = QtCore.Signal()
    nodes_selected = QtCore.Signal(list)
    nodes_deselected = QtCore.Signal(list)
    node_doubleclicked = QtCore.Signal(QtGui.QStandardItem)

    def __init__(self, stage=None, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setModel(stage)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)
        self.setEditTriggers(StageTreeView.NoEditTriggers)

        self.create_actions()
        self.create_connections()

    def create_actions(self):
        self.create_new_node_action = QtWidgets.QAction("Create node", self)
        self.create_new_node_action.triggered.connect(self.create_new_node)
        self.delete_selected_node_action = QtWidgets.QAction(pyside_fn.get_standard_icon(self, "SP_DialogDiscardButton"),
                                                             "Delete node",
                                                             self)
        self.delete_selected_node_action.triggered.connect(self.delete_selected_node)
        self.copy_selected_nodes_action = QtWidgets.QAction("Copy", self)
        self.copy_selected_nodes_action.triggered.connect(self.copy_selected_nodes)
        self.cut_selected_nodes_action = QtWidgets.QAction("Cut", self)
        self.cut_selected_nodes_action.triggered.connect(self.cut_selected_nodes)
        self.copy_selected_node_path_action = QtWidgets.QAction("Copy path to selected", self)
        self.copy_selected_node_path_action.triggered.connect(self.copy_selected_node_path)
        self.paste_nodes_action = QtWidgets.QAction("Paste", self)
        self.paste_nodes_action.triggered.connect(self.paste_nodes_from_clipboard)
        self.set_selected_item_as_parents_execution_start_action = QtWidgets.QAction(
            "Set as parent execution start", self)
        self.set_selected_item_as_parents_execution_start_action.triggered.connect(
            self.set_selected_item_as_parents_execution_start)

    def create_connections(self):
        self.doubleClicked.connect(self.__emit_doubledclicked_item)
        self.customContextMenuRequested.connect(self.show_context_menu)

    @property
    def stage(self) -> "Stage":
        return self.model()

    @property
    def main_window(self) -> "NyxEditorMainWindow":
        return QtWidgets.QApplication.instance().main_window()

    @property
    def current_stage_graph(self):
        return self.main_window.current_stage_graph

    def set_stage(self, stage):
        self.setModel(stage)

    def __emit_doubledclicked_item(self, index):
        if not self.stage:
            return
        node = self.stage.itemFromIndex(index)
        self.node_doubleclicked.emit(node)

    def current_node(self) -> "Node":
        if not self.stage:
            return None

        try:
            return self.selected_nodes()[-1]
        except IndexError:
            return None
        except Exception:
            LOGGER.exception("Treeview | Failed to get current item")
            return None

    def selected_nodes(self) -> "deque[Node]":
        nodes = deque()
        for index in self.selectedIndexes():
            nodes.append(self.stage.itemFromIndex(index))

        return nodes

    def select_paths(self, node_paths: "list[pathlib.PurePosixPath]", silent=False):
        if silent:
            self.blockSignals(True)
        indexes = []
        for path in node_paths:
            node = self.stage.node(path)
            if node is None:
                LOGGER.warning("Invalid path selected: {}".format(path))
                continue
            indexes.append(node.index())

        for each_index in indexes:
            self.selectionModel().select(each_index, QtCore.QItemSelectionModel.ClearAndSelect)
        self.blockSignals(False)

    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        super().selectionChanged(selected, deselected)
        selected_items = [self.stage.itemFromIndex(index) for index in selected.indexes()]
        deselected_items = [self.stage.itemFromIndex(index) for index in deselected.indexes()]
        self.nodes_selected.emit(selected_items)
        self.nodes_deselected.emit(deselected_items)
        self.selection_changed.emit()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Delete:
            self.delete_selected_node()
            return

        return super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            if not self.indexAt(event.pos()).isValid():
                self.selectionModel().clear()

        return super().mousePressEvent(event)

    def create_new_node(self):
        parent_path = None
        selected_nodes = self.selected_nodes()
        if selected_nodes:
            parent_path = selected_nodes[-1].path

        view_center_position: QtCore.QPointF = self.current_stage_graph.gr_view.get_center_position()
        create_cmd = commands.CreateNodeCommand(stage=self.stage,
                                                node_name="node",
                                                parent_path=parent_path,
                                                position=view_center_position)
        self.stage.undo_stack.push(create_cmd)

    def delete_selected_node(self):
        if not self.selected_nodes():
            return

        delete_cmd = commands.DeleteNodeCommand(
            self.stage, self.selected_nodes(), command_text=None)
        self.stage.undo_stack.push(delete_cmd)

    def copy_selected_nodes(self):
        selected_nodes = self.selected_nodes()
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=False)
        LOGGER.info("Copied selected nodes")

    def cut_selected_nodes(self):
        selected_nodes = self.selected_nodes()
        if not selected_nodes:
            return

        clipboard.serialize_nodes_to_clipboard(selected_nodes, delete=True)
        LOGGER.info("Cut selected nodes")

    def paste_nodes_from_clipboard(self):
        serialized_nodes = clipboard.get_serialized_nodes_from_clipboard()
        if not serialized_nodes:
            LOGGER.warning("No nodes found in the clipboard!")
            return

        gr_view_center_position = self.current_stage_graph.gr_view.get_center_position()
        parent_node = self.current_node()
        paste_cmd = commands.PasteNodesCommand(stage=self.stage,
                                               serialize_nodes=serialized_nodes,
                                               position=gr_view_center_position,
                                               parent_node=parent_node)
        self.stage.undo_stack.push(paste_cmd)

    def copy_selected_node_path(self):
        selected_node = self.current_node()
        if not selected_node:
            return
        QtWidgets.QApplication.clipboard().setText(selected_node.path.as_posix())
        LOGGER.info(f"Copied node path: {selected_node.path.as_posix()}")

    def set_selected_item_as_parents_execution_start(self):
        current_node = self.current_node()
        if not current_node:
            return

        if current_node.parent():
            set_execution_start_cmd = commands.SetNodeExecStartCommand(stage=current_node.stage,
                                                                       node=current_node.parent(),
                                                                       path=current_node.path)
        else:
            set_execution_start_cmd = commands.SetStageExecStartCommand(stage=current_node.stage,
                                                                        path=current_node.path)

        current_node.stage.undo_stack.push(set_execution_start_cmd)

    def show_context_menu(self, point: QtCore.QPoint):
        menu = QtWidgets.QMenu("", self)
        menu.addAction(self.create_new_node_action)
        if self.current_node():
            menu.addAction(self.set_selected_item_as_parents_execution_start_action)
            menu.addSeparator()
            menu.addAction(self.copy_selected_nodes_action)
            menu.addAction(self.cut_selected_nodes_action)

        menu.addAction(self.paste_nodes_action)

        if self.current_node():
            menu.addSeparator()
            menu.addAction(self.copy_selected_node_path_action)
            menu.addAction(self.delete_selected_node_action)

        menu.exec_(self.mapToGlobal(point))
