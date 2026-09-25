from PySide6 import QtWidgets


class NodeComponentsView(QtWidgets.QListView):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent=parent)
