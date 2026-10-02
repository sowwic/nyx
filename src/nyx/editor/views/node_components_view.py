import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtQuickWidgets import QQuickWidget

from ..controllers.components import ComponentsController
from ...static.paths import QML_DIR

if typing.TYPE_CHECKING:
    from nyx.core.models.components_model import NodeComponentsModel


class NodeComponentsView(QQuickWidget):
    QML_COMPONENT = "NodeComponentsView.qml"

    def __init__(
        self,
        model: NodeComponentsModel | None = None,
        parent: QtWidgets.QWidget | None = None,
    ):
        self._model: NodeComponentsModel | None = None
        self._controller = ComponentsController()

        super().__init__(parent=parent)
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setClearColor(self.palette().color(QtGui.QPalette.ColorRole.Window))
        self.setMinimumWidth(240)

        # Let QML files import siblings
        self.engine().addImportPath(QML_DIR.as_posix())

        self.setModel(model)
        self.setSource(self.source_url)

    @property
    def source_url(self) -> QtCore.QUrl:
        return QtCore.QUrl((QML_DIR / self.QML_COMPONENT).as_posix())

    def setModel(self, model: NodeComponentsModel):
        if self._model == model:
            return

        self._model = model
        self._controller.components_model = model
        self.rootContext().setContextProperty("componentsModel", self._model)
        self.rootContext().setContextProperty("componentsController", self._controller)
