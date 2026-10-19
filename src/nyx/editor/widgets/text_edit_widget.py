from PySide6 import QtCore, QtWidgets


class NyxTextEdit(QtWidgets.QTextEdit):
    """A TextEdit editor that sends editingFinished events
    when the text was changed and focus is lost.
    """

    editingFinished = QtCore.Signal()
    receivedFocus = QtCore.Signal()

    def __init__(self, text="", parent=None):
        """Initialize NyxTextEdit.

        Args:
            text (str): initial text.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(text, parent)
        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

    def focusInEvent(self, event):
        """Emit `receivedFocus` when focus is gained.

        Args:
            event (QtGui.QFocusEvent): event.
        """
        super().focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        """Emit `editingFinished` on focus loss if the text changed.

        Args:
            event (QtGui.QFocusEvent): event.
        """
        if self._changed:
            self.editingFinished.emit()
        super().focusOutEvent(event)

    def _handle_text_changed(self):
        """Remember that the text changed."""
        self._changed = True

    def set_text_changed(self, state=True):
        """Set the text changed flag.

        Args:
            state (bool): whether the text counts as changed.
        """
        self._changed = state
