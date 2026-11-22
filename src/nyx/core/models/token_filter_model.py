import dataclasses
import re

from PySide6 import QtCore

TOKEN_PATTERN = re.compile(r"^(?P<key>[A-Za-z_]+):(?P<value>\S.*)$")


@dataclasses.dataclass(frozen=True)
class SearchToken:
    """Condition of a search written as `key:value`.

    Attributes:
        key: what to look at, one of `TokenFilterModel.TOKEN_ROLES`.
        value: text to look for.
    """

    key: str
    value: str

    def __str__(self) -> str:
        return f"{self.key}:{self.value}"


class TokenFilterModel(QtCore.QSortFilterProxyModel):
    """Filter proxy searching by text and `key:value` tokens, the base of the models
    behind a search bar.

    The text has to be a part of one of the `TEXT_ROLES` of a row. Every token has to
    match too, so `tag:logic` keeps the rows with a tag containing "logic". All
    comparing ignores case.

    Subclasses set `TOKEN_ROLES` and `TEXT_ROLES`. A token whose value isn't stored in a
    role is added by extending `get_token_keys` and `get_token_data`. The search bar
    takes its token keys from `tokenKeys` and calls `setQuery`.
    """

    TOKEN_ROLES: dict[str, int] = {}
    TEXT_ROLES: tuple[int, ...] = (QtCore.Qt.ItemDataRole.DisplayRole,)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        """Initialize TokenFilterModel.

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
        return self.get_token_keys()

    @property
    def text(self) -> str:
        """str: text a row has to contain, lower case."""
        return self._text

    @property
    def tokens(self) -> tuple[SearchToken, ...]:
        """tuple[SearchToken, ...]: tokens every row has to match."""
        return self._tokens

    @property
    def is_active(self) -> bool:
        """bool: True if there is text or a token to search for."""
        return bool(self._text or self._tokens)

    @classmethod
    def get_token_keys(cls) -> list[str]:
        """Get the keys the search understands in a token.

        Returns:
            list[str]: token keys, the keys of `TOKEN_ROLES` by default.
        """
        return list(cls.TOKEN_ROLES)

    def get_token_data(self, index: QtCore.QModelIndex, key: str):
        """Get what a token of a key is compared with.

        Args:
            index (QtCore.QModelIndex): index of the row in the source model.
            key (str): token key.

        Returns:
            Any: a value, or a list of values when a row has several of them.
        """
        return index.data(self.TOKEN_ROLES[key])

    @classmethod
    def parse_token(cls, text: str) -> SearchToken | None:
        """Read a token from text.

        Args:
            text (str): text like `tag:logic`.

        Returns:
            SearchToken | None: the token, None if the text isn't one or the key is
                unknown.
        """
        match = TOKEN_PATTERN.match(text.strip())
        if match is None:
            return None
        key = match.group("key").lower()
        if key not in cls.get_token_keys():
            return None
        return SearchToken(key, match.group("value").strip())

    @QtCore.Slot(str, "QVariantList")
    def setQuery(self, text: str, tokens: list) -> None:
        """Set what to search for.

        Args:
            text (str): part of what the rows show.
            tokens (list): tokens as text like `tag:logic`. The ones that can't be
                read are ignored.
        """
        parsed = (self.parse_token(str(token)) for token in tokens)
        self.beginFilterChange()
        self._text = text.strip().lower()
        self._tokens = tuple(token for token in parsed if token is not None)
        self.endFilterChange()

    def matches_query(self, index: QtCore.QModelIndex) -> bool:
        """Check if a row matches the text and all the tokens.

        Args:
            index (QtCore.QModelIndex): index of the row in the source model.

        Returns:
            bool: True if the row matches, whatever there is to search for.
        """
        if self._text and not any(
            self._text in str(index.data(role) or "").lower() for role in self.TEXT_ROLES
        ):
            return False
        for token in self._tokens:
            data = self.get_token_data(index, token.key)
            candidates = data if isinstance(data, (list, tuple, set)) else [data]
            if not any(token.value.lower() in str(each).lower() for each in candidates):
                return False
        return True

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
        return self.matches_query(index)
