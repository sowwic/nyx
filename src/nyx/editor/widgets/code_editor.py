from PySide2 import QtWidgets


class CodeEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__("", parent)
