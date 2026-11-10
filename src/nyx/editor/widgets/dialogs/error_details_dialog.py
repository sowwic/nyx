import traceback

from PySide6 import QtGui, QtWidgets


class ErrorDetailsDialog(QtWidgets.QDialog):
    """Dialog showing the full message and traceback of an error."""

    def __init__(
        self,
        title: str,
        error: BaseException,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize ErrorDetailsDialog.

        Args:
            title (str): window title, e.g. the path of the node that failed.
            error (BaseException): error to show.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 620)

        self.text_edit = QtWidgets.QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        )
        self.text_edit.setPlainText("".join(traceback.format_exception(error)).rstrip())

        copy_button = QtWidgets.QPushButton("Copy", self)
        copy_button.clicked.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(
                self.text_edit.toPlainText()
            )
        )
        close_button = QtWidgets.QPushButton("Close", self)
        close_button.clicked.connect(self.accept)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(copy_button)
        buttons.addWidget(close_button)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        layout.addLayout(buttons)
