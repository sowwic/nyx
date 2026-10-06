import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtQuickWidgets import QQuickWidget

from ..controllers.node_spawner import NodeSpawner
from ...core.plugin_subsystem.registry import NYX_REGISTRY
from ...core.models.registry_model import RegistryListModel
from ...static.paths import QML_DIR

if typing.TYPE_CHECKING:
    pass


class NodesPaletteView(QQuickWidget):
    QML_COMPONENT = "NodesPaletteView.qml"

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setClearColor(self.palette().color(QtGui.QPalette.ColorRole.Window))
        self.setMinimumWidth(240)

        self._nodes_registry_model = RegistryListModel(
            get_items=lambda: NYX_REGISTRY.nodes, parent=self
        )
        self._node_spawner = NodeSpawner(self)

        # Let QML files import siblings
        self.engine().addImportPath(QML_DIR.as_posix())

        self.rootContext().setContextProperty(
            "nodesRegistryModel", self._nodes_registry_model
        )
        self.rootContext().setContextProperty("nodeSpawner", self._node_spawner)
        self.setSource(self.source_url)

    @property
    def nodes_spawner(self) -> NodeSpawner:
        return self._node_spawner

    @property
    def source_url(self) -> QtCore.QUrl:
        return QtCore.QUrl((QML_DIR / self.QML_COMPONENT).as_posix())
