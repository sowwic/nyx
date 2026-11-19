from PySide6 import QtCore

from nyx.core.node import Node
from .token_filter_model import TokenFilterModel


class StageFilterModel(TokenFilterModel):
    """Filter proxy over a `Stage`, searching nodes by name and `key:value` tokens.

    The text has to be a part of a name of the node, the one the views show or the
    address name the path is made of. Every token has to match too, so `tag:logic` keeps
    the nodes with a tag containing "logic", and `path:/stage/a` the nodes with that in
    their path. All comparing ignores case.

    The parents of the nodes that match stay, so the matches keep their place in the
    tree. Top level rows (the root node of the stage) always stay.
    """

    TOKEN_ROLES = {
        "type": Node.Roles.TYPE_DISPLAY_NAME,
        "id": Node.Roles.TYPE_ID,
        "tag": Node.Roles.TAGS,
    }
    TEXT_ROLES = (QtCore.Qt.ItemDataRole.DisplayRole, Node.Roles.NAME)
    PATH_TOKEN = "path"

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        """Initialize StageFilterModel.

        Args:
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)

    @classmethod
    def get_token_keys(cls) -> list[str]:
        """Get the keys the search understands in a token.

        Returns:
            list[str]: the keys of `TOKEN_ROLES` and `path`.
        """
        return [*super().get_token_keys(), cls.PATH_TOKEN]

    def get_token_data(self, index: QtCore.QModelIndex, key: str):
        """Get what a token of a key is compared with.

        Args:
            index (QtCore.QModelIndex): index of the row in the source model.
            key (str): token key.

        Returns:
            Any: the value of the role of the key, the path of the node for `path`.
        """
        if key == self.PATH_TOKEN:
            node = self.sourceModel().itemFromIndex(index)
            return node.path.as_posix() if node is not None else ""
        return super().get_token_data(index, key)

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        """Check if a node matches the text and all the tokens.

        Args:
            source_row (int): row in the source model.
            source_parent (QtCore.QModelIndex): parent index in the source model.

        Returns:
            bool: True if the row stays.
        """
        if not self.is_active or not source_parent.isValid():
            return True
        return super().filterAcceptsRow(source_row, source_parent)
