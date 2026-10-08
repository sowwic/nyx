import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtQuickWidgets import QQuickWidget

from ..controllers.components import ComponentsController
from ..controllers.components_spawner import NodeComponentSpawner
from ...core.node_component import NodeComponent
from ...core.models.components_filter_model import NodeComponentsFilterModel
from ...core.models.registry_model import RegistryListModel
from ...core.plugin_subsystem.registry import NYX_REGISTRY
from ...static.paths import QML_DIR

if typing.TYPE_CHECKING:
    from nyx.core.models.components_model import NodeComponentsModel


class NodeComponentsView(QQuickWidget):
    QML_COMPONENT = "components_view/NodeComponentsView.qml"

    def __init__(
        self,
        model: NodeComponentsModel | None = None,
        parent: QtWidgets.QWidget | None = None,
    ):
        self._model: NodeComponentsModel | None = None
        self._components_registry_model = RegistryListModel(
            get_items=lambda: NYX_REGISTRY.node_components
        )
        self._filter_proxy_model = NodeComponentsFilterModel()
        self._filter_proxy_model.setFilterRole(NodeComponent.Roles.NAME)
        self._filter_proxy_model.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )
        self._components_registry_filter_model = QtCore.QSortFilterProxyModel()
        self._components_registry_filter_model.setSourceModel(
            self._components_registry_model
        )
        self._components_registry_filter_model.setFilterRole(
            RegistryListModel.Roles.TYPE_DISPLAY_NAME
        )
        self._components_registry_filter_model.setFilterCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive
        )

        # Controllers
        self._controller = ComponentsController(
            components_filter_model=self._filter_proxy_model
        )
        self._component_spawner = NodeComponentSpawner()

        super().__init__(parent=parent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setClearColor(self.palette().color(QtGui.QPalette.ColorRole.Window))
        self.setMinimumWidth(350)

        # Let QML files import siblings
        self.engine().addImportPath(QML_DIR.as_posix())
        self.setInitialProperties(
            {
                "componentsFilterModel": self._filter_proxy_model,
                "componentsRegistryFilterModel": self._components_registry_filter_model,
                "componentsController": self._controller,
                "componentsSpawner": self._component_spawner,
            }
        )
        self.setModel(model)
        self.setSource(self.source_url)

    @property
    def source_url(self) -> QtCore.QUrl:
        return QtCore.QUrl((QML_DIR / self.QML_COMPONENT).as_posix())

    def setModel(self, model: NodeComponentsModel):
        if self._model == model:
            return

        self._model = model
        self._controller.components_model = self._model
