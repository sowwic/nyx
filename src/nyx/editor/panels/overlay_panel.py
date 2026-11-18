from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .panel_registry import PanelArea


class _ResizeGrip(QtWidgets.QWidget):
    """Thin strip on the inner edge of a panel that the user drags to resize it."""

    SIZE = 5

    dragged = QtCore.Signal(int)

    def __init__(self, area: PanelArea, parent: QtWidgets.QWidget) -> None:
        """Initialize _ResizeGrip.

        Args:
            area (PanelArea): edge the panel is attached to.
            parent (QtWidgets.QWidget): panel.
        """
        super().__init__(parent)
        self._area = area
        self._drag_origin: int | None = None
        self._size_at_drag_start = 0
        horizontal = area is not PanelArea.BOTTOM
        self.setCursor(
            QtCore.Qt.CursorShape.SizeHorCursor
            if horizontal
            else QtCore.Qt.CursorShape.SizeVerCursor
        )

    def _coordinate(self, event: QtGui.QMouseEvent) -> int:
        point = event.globalPosition().toPoint()
        return point.y() if self._area is PanelArea.BOTTOM else point.x()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Start a drag.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return
        self._drag_origin = self._coordinate(event)
        panel = self.parentWidget()
        self._size_at_drag_start = (
            panel.height() if self._area is PanelArea.BOTTOM else panel.width()
        )

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Emit the size the drag asks for.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        if self._drag_origin is None:
            return
        delta = self._coordinate(event) - self._drag_origin
        # The panel grows away from the edge it is attached to
        if self._area is not PanelArea.LEFT:
            delta = -delta
        self.dragged.emit(self._size_at_drag_start + delta)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """End the drag.

        Args:
            event (QtGui.QMouseEvent): event.
        """
        self._drag_origin = None


class OverlayPanel(QtWidgets.QFrame):
    """Titled panel that floats over the graph area.

    Attributes:
        close_requested: emitted when the close button is clicked.
        size_requested: emitted with the width (height for the bottom area) the user
            dragged the panel to.
    """

    close_requested = QtCore.Signal()
    size_requested = QtCore.Signal(int)

    def __init__(
        self,
        title: str,
        area: PanelArea,
        content: QtWidgets.QWidget,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize OverlayPanel.

        Args:
            title (str): title shown in the header.
            area (PanelArea): edge of the graph area the panel is attached to.
            content (QtWidgets.QWidget): widget shown below the header.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._area = area
        self._title = title
        self._content = content
        self.setObjectName(f"overlay_panel_{area.value}")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)

        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    @property
    def area(self) -> PanelArea:
        """PanelArea: edge of the graph area the panel is attached to."""
        return self._area

    @property
    def content(self) -> QtWidgets.QWidget:
        """QtWidgets.QWidget: widget shown below the header."""
        return self._content

    def _create_widgets(self) -> None:
        """Create child widgets."""
        self._title_label = QtWidgets.QLabel(self._title, self)
        font = self._title_label.font()
        font.setBold(True)
        self._title_label.setFont(font)

        self._close_button = QtWidgets.QToolButton(self)
        self._close_button.setAutoRaise(True)
        self._close_button.setText("✕")
        self._close_button.setToolTip("Close")

        self._grip = _ResizeGrip(self._area, self)
        self._content.setParent(self)

    def _create_layouts(self) -> None:
        """Create layouts."""
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(8, 4, 4, 4)
        header_layout.addWidget(self._title_label, stretch=1)
        header_layout.addWidget(self._close_button)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self._content, stretch=1)
        self._content.show()

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self._close_button.clicked.connect(self.close_requested)
        self._grip.dragged.connect(self.size_requested)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Keep the grip on the inner edge.

        Args:
            event (QtGui.QResizeEvent): event.
        """
        super().resizeEvent(event)
        grip_size = _ResizeGrip.SIZE
        if self._area is PanelArea.LEFT:
            self._grip.setGeometry(self.width() - grip_size, 0, grip_size, self.height())
        elif self._area is PanelArea.RIGHT:
            self._grip.setGeometry(0, 0, grip_size, self.height())
        else:
            self._grip.setGeometry(0, 0, self.width(), grip_size)
        self._grip.raise_()
