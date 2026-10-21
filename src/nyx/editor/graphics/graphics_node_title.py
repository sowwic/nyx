import typing

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from nyx.core.name_validator import NameValidator
from nyx.editor.graphics.level_of_detail import LevelOfDetail

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsNodeTitle(QtWidgets.QGraphicsTextItem):
    """Title text of a graphics node, editable in place."""

    TITLE_FONT = QtGui.QFont("Zed Mono", 10, QtGui.QFont.Weight.Bold)

    def __init__(self, gr_node: GraphicsNode):
        """Initialize GraphicsNodeTitle.

        Args:
            gr_node (GraphicsNode): graphics node the title belongs to.
        """
        super().__init__(gr_node.node.name, gr_node)
        self.gr_node = gr_node
        self._editor_proxy: QtWidgets.QGraphicsProxyWidget | None = None
        self.setFont(self.TITLE_FONT)

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw the text unless it is too small to read.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        lod = LevelOfDetail.from_painter(painter, text_size=self.TITLE_FONT.pointSizeF())
        if lod.shows_text:
            super().paint(painter, option, widget)

    @property
    def height(self) -> float:
        """float: height of the title text."""
        return self.boundingRect().height()

    @property
    def width(self) -> float:
        """float: width of the title text."""
        return self.boundingRect().width()

    def refresh(self) -> bool:
        """Show the current node name.

        Returns:
            bool: text changed, so the owner needs a new layout.
        """
        name = self.gr_node.node.name
        if name == self.toPlainText():
            return False
        self.setPlainText(name)
        return True

    def edit(self):
        """Show a line edit over the title to rename the node."""
        if self._editor_proxy is not None:
            return
        line_edit = QtWidgets.QLineEdit()
        line_edit.setFont(self.font())
        line_edit.setMaximumWidth(int(self.gr_node.width))
        line_edit.setText(self.toPlainText())

        proxy = QtWidgets.QGraphicsProxyWidget(self)
        proxy.setWidget(line_edit)
        self._editor_proxy = proxy
        line_edit.editingFinished.connect(lambda: self._finish_edit(proxy, line_edit))
        line_edit.setFocus(QtCore.Qt.MouseFocusReason)

    def _finish_edit(
        self, proxy: QtWidgets.QGraphicsProxyWidget, line_edit: QtWidgets.QLineEdit
    ):
        """Close the editor and apply its text. Safe against repeated signals.

        Args:
            proxy (QtWidgets.QGraphicsProxyWidget): proxy holding the editor.
            line_edit (QtWidgets.QLineEdit): the editor.
        """
        if self._editor_proxy is not proxy:
            return
        self._editor_proxy = None
        new_text = line_edit.text()
        proxy.deleteLater()
        self.apply_edit(new_text)

    def apply_edit(self, new_text: str):
        """Rename the node through an undoable command if the name changed.

        Args:
            new_text (str): edited name, sanitized to a valid object name.
        """
        new_text = NameValidator.get_valid_stage_object_name(new_text)
        if not new_text or new_text == self.gr_node.node.name:
            return
        rename_cmd = commands.RenameNodeCommand(
            stage=self.gr_node.node.stage, node=self.gr_node.node, new_name=new_text
        )
        self.gr_node.node.stage.push_command(rename_cmd)
