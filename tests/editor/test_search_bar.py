import pytest
from PySide6 import QtCore, QtQml

from nyx.static.paths import PACKAGE_ROOT

SEARCH_BAR_QML = (
    PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "Common" / "SearchBar.qml"
)

_KEEP_ALIVE = []


def as_list(value):
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return list(value)


@pytest.fixture
def search_bar(qapp):
    component = QtQml.QQmlComponent(
        qapp.qml_engine, QtCore.QUrl.fromLocalFile(str(SEARCH_BAR_QML))
    )
    item = component.create()
    assert item is not None, component.errorString()
    _KEEP_ALIVE.append(component)
    item.setProperty("width", 300)
    item.setProperty("tokenKeys", ["tags", "section"])
    queries = []
    item.queryChanged.connect(
        lambda text, tokens: queries.append((text, as_list(tokens)))
    )
    item.queries = queries
    yield item
    item.deleteLater()


def type_text(item, text):
    item.setProperty("text", text)


def test_plain_text_is_the_query(search_bar):
    type_text(search_bar, "branch")

    assert search_bar.property("queryText") == "branch"
    assert as_list(search_bar.property("queryTokens")) == []
    assert search_bar.queries[-1] == ("branch", [])


def test_token_text_filters_before_it_is_committed(search_bar):
    type_text(search_bar, "tags:logic")

    assert search_bar.property("queryText") == ""
    assert as_list(search_bar.property("queryTokens")) == ["tags:logic"]
    assert as_list(search_bar.property("tokens")) == []


def test_unknown_key_stays_text(search_bar):
    type_text(search_bar, "foo:bar")

    assert search_bar.property("queryText") == "foo:bar"
    assert as_list(search_bar.property("queryTokens")) == []


def test_commit_keeps_the_token_and_clears_the_field(search_bar):
    type_text(search_bar, "tags:logic")
    assert search_bar.property("pendingToken") == "tags:logic"

    QtCore.QMetaObject.invokeMethod(
        search_bar, "commitToken", QtCore.Qt.ConnectionType.DirectConnection
    )

    assert as_list(search_bar.property("tokens")) == ["tags:logic"]
    assert search_bar.property("text") == ""
    assert as_list(search_bar.property("queryTokens")) == ["tags:logic"]
    assert search_bar.property("isActive") is True


def test_same_token_is_not_added_twice(search_bar):
    for _ in range(2):
        type_text(search_bar, "tags:logic")
        QtCore.QMetaObject.invokeMethod(
            search_bar, "commitToken", QtCore.Qt.ConnectionType.DirectConnection
        )

    assert as_list(search_bar.property("tokens")) == ["tags:logic"]


def test_tokens_combine_with_text(search_bar):
    type_text(search_bar, "section:core")
    QtCore.QMetaObject.invokeMethod(
        search_bar, "commitToken", QtCore.Qt.ConnectionType.DirectConnection
    )
    type_text(search_bar, "branch")

    assert search_bar.queries[-1] == ("branch", ["section:core"])


def test_remove_token_and_clear(search_bar):
    for token in ("tags:a", "tags:b"):
        type_text(search_bar, token)
        QtCore.QMetaObject.invokeMethod(
            search_bar, "commitToken", QtCore.Qt.ConnectionType.DirectConnection
        )

    QtCore.QMetaObject.invokeMethod(
        search_bar,
        "removeToken",
        QtCore.Qt.ConnectionType.DirectConnection,
        QtCore.Q_ARG("QVariant", 0),
    )
    assert as_list(search_bar.property("tokens")) == ["tags:b"]

    QtCore.QMetaObject.invokeMethod(
        search_bar, "clear", QtCore.Qt.ConnectionType.DirectConnection
    )
    assert as_list(search_bar.property("tokens")) == []
    assert search_bar.property("isActive") is False
