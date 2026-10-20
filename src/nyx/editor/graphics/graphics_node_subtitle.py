import typing

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_node import GraphicsNode


class GraphicsNodeSubtitle(QtWidgets.QGraphicsSimpleTextItem):
    """Extra text under the title of a graphics node. Not editable.

    Long text is elided in the middle, so a path keeps both of its ends, and the full
    text is shown as a tooltip. The item takes no room while it has no text.
    """

    SUBTITLE_FONT = QtGui.QFont("Zed Mono", 8)
    COLOR = QtGui.QColor("#9A9A9A")
    MAX_WIDTH = 240.0
    # The title item keeps a margin around its text. The subtitle tucks into it by this
    # much, and adds this much less than its own height to the header. Lower values
    # leave more space between the title and the subtitle.
    TITLE_OVERLAP = 2.0
    HEADER_PADDING = 4.0

    def __init__(self, gr_node: GraphicsNode):
        """Initialize GraphicsNodeSubtitle.

        Args:
            gr_node (GraphicsNode): graphics node the subtitle belongs to.
        """
        super().__init__(gr_node)
        self.gr_node = gr_node
        self._full_text = ""
        self.setFont(self.SUBTITLE_FONT)
        self.setBrush(QtGui.QBrush(self.COLOR))
        self.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.setVisible(False)

    @property
    def full_text(self) -> str:
        """str: the text as given, before eliding."""
        return self._full_text

    @property
    def height(self) -> float:
        """float: height the subtitle adds to the header, 0 without text."""
        if not self._full_text:
            return 0.0
        return self.boundingRect().height() - self.TITLE_OVERLAP + self.HEADER_PADDING

    @property
    def width(self) -> float:
        """float: width of the shown text, 0 without text."""
        if not self._full_text:
            return 0.0
        return self.boundingRect().width()

    def refresh(self, text: str) -> bool:
        """Show a text.

        Args:
            text (str): subtitle of the node, empty for none.

        Returns:
            bool: text changed, so the owner needs a new layout.
        """
        if text == self._full_text:
            return False
        self._full_text = text
        shown = QtGui.QFontMetricsF(self.font()).elidedText(
            text, QtCore.Qt.TextElideMode.ElideMiddle, self.MAX_WIDTH
        )
        self.setText(shown)
        self.setToolTip(text if shown != text else "")
        self.setVisible(bool(text))
        return True
