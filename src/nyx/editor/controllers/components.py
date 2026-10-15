import logging
import typing

from PySide6 import QtCore

from ...core.commands import (
    DeleteNodeComponentCommand,
    ReorderNodeComponentCommand,
    SetNodeComponentValueCommand,
    SetNodeComponentActiveStateCommand,
    RenameNodeComponentCommand,
    SetNodeComponentFlagCommand,
)
from ...core.node_component import NodeComponent
from ...static.enums import ItemSelectionMode, NodeComponentFlag


if typing.TYPE_CHECKING:
    from ...core.stage import Stage
    from ...core.models.components_model import NodeComponentsModel

LOGGER = logging.getLogger(__name__)


class ComponentsController(QtCore.QObject):
    """Owns selection state for a components model and keeps it
    consistent across reorders."""

    componentsModelChanged = QtCore.Signal()

    def __init__(
        self,
        components_filter_model: QtCore.QSortFilterProxyModel | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._components_filter_model = components_filter_model
        self._selection_model = QtCore.QItemSelectionModel(
            self._components_filter_model, self
        )
        self._items_selected_before_move = []
        self._current_item_before_move = None

        self._connect_models()

    @property
    def stage(self) -> Stage:
        return self.components_model.node.stage

    @property
    def selection_model(self) -> QtCore.QItemSelectionModel:
        return self._selection_model

    @property
    def components_model(self) -> NodeComponentsModel:
        if self._components_filter_model is None:
            return None
        return self.components_filter_model.sourceModel()

    @property
    def components_filter_model(self) -> QtCore.QSortFilterProxyModel:
        return self._components_filter_model

    @components_model.setter
    def components_model(self, model: NodeComponentsModel) -> None:
        if self.components_model is model:
            return

        if self.components_model is not None:
            self._disconnect_models()
        self.components_filter_model.setSourceModel(model)
        if self.components_model is not None:
            self._connect_models()

    def _connect_models(self):
        if self.components_model is None:
            return

        self.components_model.rowsAboutToBeMoved.connect(self._selection_model.clear)

    def _disconnect_models(self):
        if self.components_model is None:
            return

        self.components_model.rowsAboutToBeMoved.disconnect(self._selection_model.clear)

    def get_component_from_proxy_row(self, row: int) -> NodeComponent:
        proxy_index = self.components_filter_model.index(row, 0)
        source_model_index = self.components_filter_model.mapToSource(proxy_index)
        return self.components_model.itemFromIndex(source_model_index)

    @QtCore.Slot(int, int)
    def selectRow(self, clicked_row: int, selection_mode: ItemSelectionMode):
        model = self.components_filter_model
        if not 0 <= clicked_row < model.rowCount():
            return

        if isinstance(selection_mode, int):
            selection_mode = ItemSelectionMode(selection_mode)

        flags = QtCore.QItemSelectionModel.SelectionFlag
        clicked_index = model.index(clicked_row, 0)
        anchor_index = self._selection_model.currentIndex()

        if selection_mode is ItemSelectionMode.RANGE and anchor_index.isValid():
            first_row, last_row = sorted((anchor_index.row(), clicked_row))
            row_range = QtCore.QItemSelection(
                model.index(first_row, 0),
                model.index(last_row, 0),
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

    @QtCore.Slot()
    def deleteSelectedNodeComponents(self):
        selection = self.selection_model.selection()
        if selection.isEmpty():
            return

        component_names_to_delete = []
        for item_index in self.selection_model.selectedRows():
            source_model_index = self.components_filter_model.mapToSource(item_index)
            component: NodeComponent = self.components_model.itemFromIndex(
                source_model_index
            )
            if component.is_built_in:
                LOGGER.warning("Can't delete built-in component %s", str(component.path))
                return

            component_names_to_delete.append(component.name)

        command = DeleteNodeComponentCommand(
            node=self.components_model.node, component_names=component_names_to_delete
        )
        self.components_model.node.stage.push_command(command)

    @QtCore.Slot(int, bool)
    def setSetComponentActiveState(self, row: int, state: bool):
        component = self.get_component_from_proxy_row(row)
        set_active_command = SetNodeComponentActiveStateCommand(
            stage=component.stage, node_component=component, state=state
        )
        component.stage.push_command(set_active_command)

    @QtCore.Slot(int, int)
    def reorderComponent(self, from_row: int, to_row: int):
        self._selection_model.clear()
        proxy = self.components_filter_model

        from_source = proxy.mapToSource(proxy.index(from_row, 0))
        to_source = proxy.mapToSource(proxy.index(to_row, 0))
        if not from_source.isValid():
            return

        # to_row == rowCount() (drop after last item) gives an invalid index
        to_source_row = (
            to_source.row() if to_source.isValid() else self.components_model.rowCount()
        )

        component = self.components_model.item(from_source.row(), 0)
        self.stage.push_command(
            ReorderNodeComponentCommand(
                stage=self.stage,
                node_component=component,
                to_row=to_source_row,
            )
        )

    @QtCore.Slot(int, str)
    def renameComponent(self, row: int, new_name: str):
        component = self.get_component_from_proxy_row(row)
        self.stage.push_command(
            RenameNodeComponentCommand(
                stage=self.stage, node_component=component, new_name=new_name
            )
        )

    @QtCore.Slot(int, str, bool)
    def setComponentValue(self, row: int, new_value: str, raw: bool):
        component = self.get_component_from_proxy_row(row)
        self.stage.push_command(
            SetNodeComponentValueCommand(
                stage=self.stage, node_component=component, value=new_value, raw=raw
            )
        )

    @QtCore.Slot(int, bool)
    def setComponentReadable(self, row: int, state: bool):
        component = self.get_component_from_proxy_row(row)
        set_flag_command = SetNodeComponentFlagCommand(
            stage=self.stage,
            node_component=component,
            flag=NodeComponentFlag.READABLE,
            role=NodeComponent.Roles.READABLE,
            state=state,
        )
        self.stage.push_command(set_flag_command)

    @QtCore.Slot(int, bool)
    def setComponentWritable(self, row: int, state: bool):
        component = self.get_component_from_proxy_row(row)
        set_flag_command = SetNodeComponentFlagCommand(
            stage=self.stage,
            node_component=component,
            flag=NodeComponentFlag.WRITABLE,
            role=NodeComponent.Roles.WRITABLE,
            state=state,
        )
        self.stage.push_command(set_flag_command)

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
