import dataclasses
import re

from PySide6 import QtCore

from .registry_model import RegistryListModel

TOKEN_PATTERN = re.compile(r"^(?P<key>[A-Za-z_]+):(?P<value>\S.*)$")


@dataclasses.dataclass(frozen=True)
class SearchToken:
    """Condition of a search written as `key:value`.

    Attributes:
        key: what to look at, one of `RegistryFilterModel.TOKEN_ROLES`.
        value: text to look for.
    """

    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.key}:{self.value}"


class RegistryFilterModel(QtCore.QSortFilterProxyModel):
    """Filter proxy over a `RegistryListModel`, searching by text and `key:value` tokens.

    The text has to be a part of the display name. Every token has to match too, so
    `tags:logic` keeps the types with a tag containing "logic". All comparing ignores
    case.
    """

    TOKEN_ROLES: dict[str, RegistryListModel.Roles] = {
        "tag": RegistryListModel.Roles.TYPE_TAGS,
        "section": RegistryListModel.Roles.PALETTE_SECTION,
        "id": RegistryListModel.Roles.TYPE_ID,
    }

    def __init__(self, parent=None):
        """Initialize RegistryFilterModel.

        Args:
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._text = ""
        self._tokens: tuple[SearchToken, ...] = ()
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    @QtCore.Property("QStringList", constant=True)
    def tokenKeys(self) -> list[str]:
        """list[str]: keys the search understands in a token."""
        return list(self.TOKEN_ROLES)

    @classmethod
    def parse_token(cls, text: str) -> SearchToken | None:
        """Read a token from text.

        Args:
            text (str): text like `tags:logic`.

        Returns:
            SearchToken | None: the token, None if the text isn't one or the key is
                unknown.
        """
        match = TOKEN_PATTERN.match(text.strip())
        if match is None:
            return None
        key = match.group("key").lower()
        if key not in cls.TOKEN_ROLES:
            return None
        return SearchToken(key, match.group("value").strip())

    @QtCore.Slot(str, "QVariantList")
    def setQuery(self, text: str, tokens: list) -> None:
        """Set what to search for.

        Args:
            text (str): part of the display name.
            tokens (list): tokens as text like `tags:logic`. The ones that can't be
                read are ignored.
        """
        parsed = (self.parse_token(str(token)) for token in tokens)
        self.beginFilterChange()
        self._text = text.strip().lower()
        self._tokens = tuple(token for token in parsed if token is not None)
        self.endFilterChange()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QtCore.QModelIndex
    ) -> bool:
        """Check if a row matches the text and all the tokens.

        Args:
            source_row (int): row in the source model.
            source_parent (QtCore.QModelIndex): parent index in the source model.

        Returns:
            bool: row is shown.
        """
        index = self.sourceModel().index(source_row, 0, source_parent)
        if self._text:
            name = index.data(RegistryListModel.Roles.TYPE_DISPLAY_NAME) or ""
            if self._text not in str(name).lower():
                return False
        for token in self._tokens:
            data = index.data(self.TOKEN_ROLES[token.key])
            candidates = data if isinstance(data, (list, tuple)) else [data]
            if not any(token.value.lower() in str(each).lower() for each in candidates):
                return False
        return True
