from PySide2 import QtWidgets


class NyxEditorMainWindow(QtWidgets.QMainWindow):

    DEFAULT_TITLE = "Nyx Editor"
    MINIMUM_SIZE = (500, 400)

    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.DEFAULT_TITLE)
        self.setMinimumSize(*self.MINIMUM_SIZE)
