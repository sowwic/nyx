import pytest
from PySide6 import QtCore, QtQml

from nyx.static.paths import PACKAGE_ROOT

QML = PACKAGE_ROOT / "editor" / "qml" / "NyxEditor" / "Common" / "CollapsibleFrame.qml"
_KEEP_ALIVE = []


@pytest.fixture
def frame(qapp):
    component = QtQml.QQmlComponent(qapp.qml_engine, QtCore.QUrl.fromLocalFile(str(QML)))
    item = component.create()
    assert item is not None, component.errorString()
    _KEEP_ALIVE.append(component)
    yield item
    item.deleteLater()


def styled(frame, title):
    return QtCore.QMetaObject.invokeMethod(
        frame,
        "styledTitle",
        QtCore.Qt.ConnectionType.DirectConnection,
        QtCore.Q_RETURN_ARG("QVariant"),
        QtCore.Q_ARG("QVariant", title),
    )


def test_title_in_parentheses_is_dimmed(frame):
    result = styled(frame, "Links (in: 2 | out: 1)")

    assert result.startswith("Links<font color=")
    assert result.endswith(" (in: 2 | out: 1)</font>")


def test_plain_title_is_left_alone(frame):
    assert styled(frame, "Links") == "Links"


def test_title_is_escaped(frame):
    assert styled(frame, "<b>x</b> (a&b)").startswith("&lt;b&gt;x&lt;/b&gt;<font")
    assert styled(frame, "(only)") == "(only)"
