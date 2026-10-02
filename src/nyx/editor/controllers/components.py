import logging
import typing

from PySide6 import QtCore, QtGui

from ...static.enums import ItemSelectionMode


if typing.TYPE_CHECKING:
    from ...core.models.components_model import NodeComponentsModel

LOGGER = logging.getLogger(__name__)


class ComponentsController(QtCore.QObject):
    """Owns selection state for a components model and keeps it
    consistent across reorders."""

    componentsModelChanged = QtCore.Signal()

    def __init__(self, components_model: NodeComponentsModel | None = None, parent=None):
        super().__init__(parent)
        self._components_model = components_model
        self._selection_model = QtCore.QItemSelectionModel(components_model, self)
        self._items_selected_before_move = []
        self._current_item_before_move = None

        self._connect_models()

    @property
    def selection_model(self) -> QtCore.QItemSelectionModel:
        return self._selection_model

    @property
    def components_model(self) -> NodeComponentsModel:
        return self._components_model

    @components_model.setter
    def components_model(self, model: NodeComponentsModel) -> None:
        if model is self._components_model:
            return

        self._disconnect_models()
        self._components_model = model
        self._selection_model.setModel(model)
        self._connect_models()
        self.componentsModelChanged.emit()

    def _connect_models(self):
        if self._components_model is None:
            return

        self._components_model.rowsAboutToBeMoved.connect(self._selection_model.clear)

    def _disconnect_models(self):
        if self._components_model is None:
            return

        self._components_model.rowsAboutToBeMoved.disconnect(self._selection_model.clear)

    @QtCore.Slot(int, int)
    def selectRow(self, clicked_row: int, selection_mode: ItemSelectionMode):
        if not 0 <= clicked_row < self._components_model.rowCount():
            return

        if isinstance(selection_mode, int):
            selection_mode = ItemSelectionMode(selection_mode)

        flags = QtCore.QItemSelectionModel.SelectionFlag
        clicked_index = self._components_model.index(clicked_row, 0)
        anchor_index = self._selection_model.currentIndex()

        if selection_mode is ItemSelectionMode.RANGE and anchor_index.isValid():
            first_row, last_row = sorted((anchor_index.row(), clicked_row))
            row_range = QtCore.QItemSelection(
                self._components_model.index(first_row, 0),
                self._components_model.index(last_row, 0),
            )
            self._selection_model.select(row_range, flags.ClearAndSelect | flags.Rows)
        elif selection_mode is ItemSelectionMode.TOGGLE:
            self._selection_model.select(clicked_index, flags.Toggle | flags.Rows)
            self._selection_model.setCurrentIndex(clicked_index, flags.NoUpdate)
        else:
            self._selection_model.select(
                clicked_index, flags.ClearAndSelect | flags.Rows
            )
            self._selection_model.setCurrentIndex(clicked_index, flags.NoUpdate)

    selectionModel = QtCore.Property(
        QtCore.QObject,
        fget=selection_model.fget,
        fset=selection_model.fset,
        constant=True,
    )
    componentsModel = QtCore.Property(
        QtCore.QObject,
        fget=components_model.fget,
        fset=components_model.fset,
        notify=componentsModelChanged,
    )
