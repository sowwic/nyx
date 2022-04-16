from PySide2 import QtWidgets


class StageTreeWidget(QtWidgets.QTreeView):
    def __init__(self, stage, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.stage = stage
        self.setModel(self.stage)
        self.setHeaderHidden(True)

    def current_item(self):
        self.stage.itemFromIndex(self.currentIndex())
