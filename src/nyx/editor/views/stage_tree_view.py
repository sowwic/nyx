import typing
from PySide2 import QtCore
from PySide2 import QtWidgets

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.core import Node


class StageTreeView(QtWidgets.QTreeView):

    selection_changed = QtCore.Signal()
    nodes_selected = QtCore.Signal(list)
    nodes_deselected = QtCore.Signal(list)

    def __init__(self, stage=None, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setModel(self.stage)
        self.setHeaderHidden(True)
        self.setEditTriggers(StageTreeView.NoEditTriggers)

    @property
    def stage(self) -> "Stage":
        return self.model()

    def set_stage(self, stage):
        self.setModel(stage)

    def current_item(self) -> "Node":
        return self.stage.itemFromIndex(self.currentIndex())

    def selectionChanged(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection) -> None:
        super().selectionChanged(selected, deselected)
        selected_items = [self.stage.itemFromIndex(index) for index in selected.indexes()]
        deselected_items = [self.stage.itemFromIndex(index) for index in deselected.indexes()]
        self.nodes_selected.emit(selected_items)
        self.nodes_deselected.emit(deselected_items)
        self.selection_changed.emit()
