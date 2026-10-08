import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtQuickWidgets import QQuickWidget

from ..controllers.node_spawner import NodeSpawner
from ...core.plugin_subsystem.registry import NYX_REGISTRY
from ...core.models.registry_model import RegistryListModel
from ...static.paths import QML_DIR
from ...static.vars import NODE_TYPE_MIME

if typing.TYPE_CHECKING:
    pass


class NodesPaletteView(QQuickWidget):
    QML_COMPONENT = "nodes_palette/NodesPaletteView.qml"

    def __init__(
        self,
        drag_enabled: bool = False,
        parent: QtWidgets.QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setClearColor(self.palette().color(QtGui.QPalette.ColorRole.Window))
        self.setMinimumWidth(240)

        self._drag_enabled = drag_enabled
        self._nodes_registry_model = RegistryListModel(
            get_items=lambda: NYX_REGISTRY.nodes, parent=self
        )
        self._filter_proxy_model = QtCore.QSortFilterProxyModel()
        self._filter_proxy_model.setFilterRole(QtCore.Qt.ItemDataRole.DisplayRole)
        self._filter_proxy_model.setSourceModel(self._nodes_registry_model)
        self._filter_proxy_model.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )

        self._node_spawner = NodeSpawner(self)

        # Let QML files import siblings
        self.engine().addImportPath(QML_DIR.as_posix())
        self.setInitialProperties(
            {
                "nodesRegistryFilterModel": self._filter_proxy_model,
                "nodeSpawner": self._node_spawner,
                "dragEnabled": self._drag_enabled,
                "nodeMimeType": NODE_TYPE_MIME,
            }
        )

        self.setSource(self.source_url)

    def on_node_dropped(self, type_id: str, position: QtCore.QPointF):
        self.nodes_spawner.spawn_position = position
        self.nodes_spawner.spawnNode(type_id)

    @property
    def drag_enabled(self) -> bool:
        return self._drag_enabled

    @drag_enabled.setter
    def drag_enabled(self, state: bool) -> None:
        self._drag_enabled = state
        if root := self.rootObject():
            root.setProperty("dragEnabled", state)

    @property
    def nodes_spawner(self) -> NodeSpawner:
        return self._node_spawner

    @property
    def source_url(self) -> QtCore.QUrl:
        return QtCore.QUrl((QML_DIR / self.QML_COMPONENT).as_posix())
