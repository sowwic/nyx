from PySide6 import QtCore, QtWidgets, QtQuickWidgets

from ...core.plugin_subsystem.registry import NYX_REGISTRY
from ..utils.common import get_application_qml_engine


class NyxQuickWidget(QtQuickWidgets.QQuickWidget):
    """Base class for widgets showing a QML component from a registered plugin.

    Subclasses set `QML_MODULE` and `QML_COMPONENT`.
    """

    QML_MODULE: str = ""
    QML_COMPONENT: str = ""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        """Initialize NyxQuickWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(get_application_qml_engine(), parent)

    @property
    def source_url(self) -> QtCore.QUrl:
        """QtCore.QUrl: url of the QML component file."""
        qml_file = NYX_REGISTRY.resolve_qml_source(
            qml_module_uri=self.QML_MODULE, qml_type_name=self.QML_COMPONENT
        )
        return QtCore.QUrl.fromLocalFile(str(qml_file))
