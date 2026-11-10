from __future__ import annotations

import typing

from PySide6 import QtCore, QtWidgets

from ...static.enums import NodeExecutionStatus
from .dialogs.error_details_dialog import ErrorDetailsDialog

if typing.TYPE_CHECKING:
    from ...core.node import Node


class InspectorErrorBanner(QtWidgets.QFrame):
    """Block showing the error a node raised in its last execution.

    Hidden unless the node failed. The message is one elided line, hovering shows
    all of it and the button opens the full message with the traceback.
    """

    ERROR_COLOR = "#d9534f"

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize InspectorErrorBanner.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._node: Node | None = None
        self._error: BaseException | None = None
        self._summary = ""

        self.setObjectName("InspectorErrorBanner")
        self.setStyleSheet(
            f"#InspectorErrorBanner {{ border: 1px solid {self.ERROR_COLOR}; "
            "border-radius: 4px; }}"
            f"#InspectorErrorBanner QLabel {{ color: {self.ERROR_COLOR}; }}"
        )
        self._label = QtWidgets.QLabel(self)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )
        self._details_button = QtWidgets.QPushButton("Details...", self)
        self._details_button.clicked.connect(self.show_details)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.addWidget(self._label, stretch=1)
        layout.addWidget(self._details_button, stretch=0)
        self.setVisible(False)

    @property
    def node(self) -> Node | None:
        """Node | None: node whose error is shown."""
        return self._node

    @property
    def summary(self) -> str:
        """str: error as shown, `Type: message`, empty when no error is shown."""
        return self._summary

    def set_node(self, node: Node | None) -> None:
        """Show the error of a node.

        Args:
            node (Node | None): node, None to show nothing.
        """
        self._node = node
        self.refresh()

    def refresh(self) -> None:
        """Show the current error of the node, or hide the block if it has none."""
        error = None
        if self._node is not None:
            if self._node.execution_status is NodeExecutionStatus.ERROR:
                error = self._node.raised_exception
        self._error = error
        if error is None:
            self._summary = ""
            self.setVisible(False)
            return
        message = str(error).strip()
        self._summary = (
            f"{type(error).__name__}: {message}" if message else type(error).__name__
        )
        single_line = " ".join(self._summary.split())
        self._label.setToolTip(self._summary)
        self._label.setText(single_line)
        self._elide()
        self.setVisible(True)

    def _elide(self) -> None:
        """Cut the text to the width of the label."""
        single_line = " ".join(self._summary.split())
        self._label.setText(
            self._label.fontMetrics().elidedText(
                single_line,
                QtCore.Qt.TextElideMode.ElideRight,
                max(self._label.width(), 100),
            )
        )

    def resizeEvent(self, event) -> None:
        """Re-elide the text for the new width.

        Args:
            event (QResizeEvent): resize event.
        """
        super().resizeEvent(event)
        if self._error is not None:
            self._elide()

    def show_details(self) -> None:
        """Open the full message and traceback."""
        if self._error is None or self._node is None:
            return
        ErrorDetailsDialog(f"Error | {self._node.path}", self._error, self).exec()
