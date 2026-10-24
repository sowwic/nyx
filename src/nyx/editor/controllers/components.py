import logging
import pathlib
import typing

from PySide6 import QtCore, QtWidgets

from ...core.commands import (
    DeleteNodeComponentCommand,
    ReorderNodeComponentCommand,
    SetNodeComponentValueCommand,
    SetNodeComponentDatatypeCommand,
    SetNodeComponentNoteCommand,
    SetNodeComponentActiveStateCommand,
    RenameNodeComponentCommand,
    SetNodeComponentFlagCommand,
)
from ...core.node_component import NodeComponent
from ...core.plugin_subsystem.registry import NYX_REGISTRY
from ...static.enums import ItemSelectionMode, NodeComponentFlag, NoteFormat


if typing.TYPE_CHECKING:
    from ...core.stage import Stage
    from ...core.models.components_model import NodeComponentsModel

LOGGER = logging.getLogger(__name__)


class ComponentsController(QtCore.QObject):
    """Owns selection state for a components model and keeps it
    consistent across reorders."""

    componentsModelChanged = QtCore.Signal()
    structureEditableChanged = QtCore.Signal()

    def __init__(
        self,
        components_filter_model: QtCore.QSortFilterProxyModel | None = None,
        parent=None,
    ):
        """Initialize ComponentsController.

        Args:
            components_filter_model (QtCore.QSortFilterProxyModel): proxy model
                exposed to the view.
            parent (QtCore.QObject | None): parent object.
        """
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
        """Stage: stage of the node whose components are shown."""
        return self.components_model.node.stage

    @property
    def selection_model(self) -> QtCore.QItemSelectionModel:
        """QtCore.QItemSelectionModel: selection of the component rows."""
        return self._selection_model

    @property
    def components_model(self) -> NodeComponentsModel:
        """NodeComponentsModel | None: source model behind the filter model."""
        if self._components_filter_model is None:
            return None
        return self.components_filter_model.sourceModel()

    @property
    def components_filter_model(self) -> QtCore.QSortFilterProxyModel:
        """QtCore.QSortFilterProxyModel: proxy model exposed to the view."""
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
        self.structureEditableChanged.emit()

    @property
    def structure_editable(self) -> bool:
        """bool: components can be added to and removed from the node shown."""
        model = self.components_model
        if model is None or model.node is None:
            return True
        node = model.node
        return node.ALLOWS_STRUCTURE_CHANGES and not node.is_in_locked_scope

    def _connect_models(self):
        """Clear the selection before rows are moved."""
        if self.components_model is None:
            return

        self.components_model.rowsAboutToBeMoved.connect(self._selection_model.clear)

    def _disconnect_models(self):
        """Undo the connections made by _connect_models."""
        if self.components_model is None:
            return

        self.components_model.rowsAboutToBeMoved.disconnect(self._selection_model.clear)

    def get_component_from_proxy_row(self, row: int) -> NodeComponent:
        """Get the component at a row of the proxy model.

        Args:
            row (int): proxy row.

        Returns:
            NodeComponent: component at that row.
        """
        proxy_index = self.components_filter_model.index(row, 0)
        source_model_index = self.components_filter_model.mapToSource(proxy_index)
        return self.components_model.itemFromIndex(source_model_index)

    @QtCore.Slot(int, int)
    def selectRow(self, clicked_row: int, selection_mode: ItemSelectionMode):
        """Select a row following the clicked selection mode.

        Args:
            clicked_row (int): proxy row that was clicked.
            selection_mode (ItemSelectionMode): single, toggle or range selection.
        """
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
        """Delete the selected components. Nothing is deleted if one is built-in."""
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
        """Set the active state of a component through an undoable command.

        Args:
            row (int): proxy row.
            state (bool): new active state.
        """
        component = self.get_component_from_proxy_row(row)
        set_active_command = SetNodeComponentActiveStateCommand(
            stage=component.stage, node_component=component, state=state
        )
        component.stage.push_command(set_active_command)

    @QtCore.Slot(int, int)
    def reorderComponent(self, from_row: int, to_row: int):
        """Move a component to another row through an undoable command.

        Args:
            from_row (int): proxy row of the component.
            to_row (int): proxy row to move to. May equal the row count to move to the
                end.
        """
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
        """Rename a component through an undoable command.

        Args:
            row (int): proxy row.
            new_name (str): new component name.
        """
        component = self.get_component_from_proxy_row(row)
        self.stage.push_command(
            RenameNodeComponentCommand(
                stage=self.stage, node_component=component, new_name=new_name
            )
        )

    @QtCore.Slot(int, str, bool)
    def setComponentValue(self, row: int, new_value: str, raw: bool):
        """Set a component value through an undoable command.

        Args:
            row (int): proxy row.
            new_value (str): new value.
            raw (bool): set the value without evaluating it.
        """
        component = self.get_component_from_proxy_row(row)
        self.stage.push_command(
            SetNodeComponentValueCommand(
                stage=self.stage, node_component=component, value=new_value, raw=raw
            )
        )

    @QtCore.Slot(int, str, str)
    def setComponentNote(self, row: int, text: str, note_format: str):
        """Set the note of a component through an undoable command.

        Args:
            row (int): proxy row.
            text (str): new note, empty to remove it.
            note_format (str): how the note is written, a `NoteFormat` value.
        """
        component = self.get_component_from_proxy_row(row)
        if component.note == text and component.note_format == note_format:
            return
        self.stage.push_command(
            SetNodeComponentNoteCommand(
                stage=self.stage,
                node_component=component,
                text=text,
                note_format=note_format,
            )
        )

    @QtCore.Slot(result="QVariantList")
    def noteFormats(self) -> list[dict[str, str]]:
        """Get the formats a note can be written in.

        Returns:
            list[dict[str, str]]: `id` and `name` of every note format.
        """
        return [
            {"id": str(note_format), "name": note_format.name.title()}
            for note_format in NoteFormat
        ]

    @QtCore.Slot(int, str)
    def setComponentDatatype(self, row: int, datatype_id: str):
        """Set the datatype hint of a component through an undoable command.

        Args:
            row (int): proxy row.
            datatype_id (str): type id of the datatype.
        """
        component = self.get_component_from_proxy_row(row)
        if component.datatype_id == datatype_id:
            return
        self.stage.push_command(
            SetNodeComponentDatatypeCommand(
                stage=self.stage, node_component=component, datatype_id=datatype_id
            )
        )

    @QtCore.Slot(result="QVariantList")
    def availableDatatypes(self) -> list[dict[str, str]]:
        """Get the datatypes a component can be hinted with.

        Returns:
            list[dict[str, str]]: `id` and `name` of every selectable datatype.
        """
        return [
            {"id": str(datatype.type_id), "name": datatype.display_name}
            for datatype in NYX_REGISTRY.iter_datatypes()
            if datatype.selectable
        ]

    @QtCore.Slot(str, str, str, result=str)
    def selectFile(self, title: str, name_filters: str, start_path: str) -> str:
        """Ask for an existing file with a file dialog of the editor window.

        A widget dialog is used on purpose: the QML `FileDialog` falls back to a
        window of its own when it is shown from a `QQuickWidget`.

        Args:
            title (str): dialog title.
            name_filters (str): filters separated by ";;", like "Python (*.py);;All (*)".
            start_path (str): file or folder to start at. Anything else, like an
                entry point, starts at the default folder.

        Returns:
            str: chosen file, empty if the dialog was cancelled.
        """
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            QtWidgets.QApplication.activeWindow(),
            title,
            self._dialog_start_path(start_path),
            name_filters,
        )
        return file_path

    @staticmethod
    def _dialog_start_path(path: str) -> str:
        """Get where a file dialog should start for some text.

        Args:
            path (str): text that may be the path of a file or folder.

        Returns:
            str: the path if it is a file or folder, otherwise an empty string.
        """
        if not path:
            return ""
        try:
            candidate = pathlib.Path(path)
            return path if candidate.is_file() or candidate.is_dir() else ""
        except (OSError, ValueError):
            return ""

    @QtCore.Slot(int, bool)
    def setComponentReadable(self, row: int, state: bool):
        """Set the readable flag of a component through an undoable command.

        Args:
            row (int): proxy row.
            state (bool): whether the component produces output.
        """
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
        """Set the writable flag of a component through an undoable command.

        Args:
            row (int): proxy row.
            state (bool): whether the component accepts input.
        """
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
    structureEditable = QtCore.Property(
        bool,
        fget=structure_editable.fget,
        notify=structureEditableChanged,
    )
    componentsModel = QtCore.Property(
        QtCore.QObject,
        fget=components_model.fget,
        fset=components_model.fset,
        notify=componentsModelChanged,
    )
