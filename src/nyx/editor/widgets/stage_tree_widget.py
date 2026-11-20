from PySide6 import QtWidgets

from nyx.editor.views.stage_tree_view import StageTreeView
from .search_bar_widget import SearchBarWidget


class StageTreeWidget(QtWidgets.QWidget):
    """Panel content with a search bar above the tree view of the stage.

    The search bar filters the nodes the tree view lists, by name and by tokens like
    `tag:logic`.

    Attributes:
        search_bar: bar to search for node names with
        tree_view: tree view of the nodes
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize StageTreeWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.create_actions()
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_actions(self):
        """Create actions. The widget has none."""
        pass

    def create_widgets(self):
        """Create the search bar and the tree view."""
        self.tree_view = StageTreeView(parent=self)
        self.search_bar = SearchBarWidget(
            "Search nodes...",
            token_keys=self.tree_view.filter_model.tokenKeys,
            parent=self,
        )

    def create_layouts(self):
        """Put the tree view under the search bar."""
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)
        self.main_layout.addWidget(self.search_bar)
        self.main_layout.addWidget(self.tree_view)

    def create_connections(self):
        """Filter the tree view with the search bar."""
        self.search_bar.query_changed.connect(self.tree_view.set_filter)

    def focus_search(self):
        """Give the keyboard focus to the search bar."""
        self.search_bar.focus_search()
