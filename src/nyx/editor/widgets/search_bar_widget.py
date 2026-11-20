from PySide6 import QtCore, QtGui, QtWidgets

from .nyx_qml_widget import NyxQuickWidget


class SearchBarWidget(NyxQuickWidget):
    """Widget showing a single search bar, the QML bar the palettes have.

    Attributes:
        query_changed: emitted with the text and the tokens of the bar when they change
    """

    QML_MODULE = "NyxEditor.Common"
    QML_COMPONENT = "SearchBar"

    query_changed = QtCore.Signal(str, list)

    def __init__(
        self,
        placeholder_text: str = "Search...",
        token_keys: list[str] | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize SearchBarWidget.

        Args:
            placeholder_text (str): text shown while the bar is empty.
            token_keys (list[str] | None): keys that make a `key:value` token in the
                bar, like the `tokenKeys` of a `TokenFilterModel`.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.setResizeMode(self.ResizeMode.SizeRootObjectToView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setClearColor(self.palette().color(QtGui.QPalette.ColorRole.Window))
        self.setInitialProperties(
            {"placeholderText": placeholder_text, "tokenKeys": list(token_keys or [])}
        )
        self.setSource(self.source_url)

        root = self.rootObject()
        root.queryChanged.connect(self._on_query_changed)
        self.setFixedHeight(int(root.property("implicitHeight")))

    @property
    def text(self) -> str:
        """str: text the bar searches for."""
        root = self.rootObject()
        return root.property("queryText") if root else ""

    @property
    def tokens(self) -> list[str]:
        """list[str]: tokens of the bar, like `tag:logic`."""
        root = self.rootObject()
        # A JavaScript array comes back as a QJSValue
        return list(root.property("queryTokens").toVariant()) if root else []

    def focus_search(self):
        """Give the keyboard focus to the bar."""
        self.setFocus()
        if root := self.rootObject():
            QtCore.QMetaObject.invokeMethod(root, "focusField")

    def clear(self):
        """Empty the bar."""
        if root := self.rootObject():
            QtCore.QMetaObject.invokeMethod(root, "clear")

    def _on_query_changed(self, text: str, tokens: list) -> None:
        """Emit `query_changed`.

        Args:
            text (str): text of the bar.
            tokens (list): tokens of the bar, there are none unless the bar is given
                token keys.
        """
        self.query_changed.emit(text, list(tokens))
