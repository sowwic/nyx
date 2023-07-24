from PySide2 import QtCore
from PySide2 import QtWidgets


class NyxTextEdit(QtWidgets.QTextEdit):
    """
    A TextEdit editor that sends editingFinished events
    when the text was changed and focus is lost.
    """

    editingFinished = QtCore.Signal()
    receivedFocus = QtCore.Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super().focusOutEvent(event)

    def _handle_text_changed(self):
        self._changed = True

    def set_text_changed(self, state=True):
        self._changed = state
