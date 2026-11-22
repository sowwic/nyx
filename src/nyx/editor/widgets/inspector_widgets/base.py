from __future__ import annotations

import typing
import weakref
from uuid import UUID

import shiboken6
from PySide6 import QtWidgets

from nyx.core.exceptions import StageObjectQueryError

if typing.TYPE_CHECKING:
    from nyx.core.stage import Stage
    from nyx.core.stage_object import StageObject


class InspectorWidget(QtWidgets.QWidget):
    """Base of the widgets the inspector shows for a stage object.

    A type picks its widget with `StageObject.get_inspector_widget_id`. Widgets are
    registered by id, built-in ones by the editor and the others by plugins, and the
    inspector creates one when an object of the type is selected. It is created once
    and given every object of its type that is selected after.

    Subclasses implement `get_type_id` and `refresh`, and read the object with
    `stage_object`. They change it by pushing commands to its stage, so edits can be
    undone.
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize InspectorWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._stage_object_uuid: UUID | None = None
        self._stage_ref: weakref.ReferenceType[Stage] | None = None

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the widget, the one types return from `get_inspector_widget_id`."""
        raise NotImplementedError

    @property
    def stage(self) -> Stage | None:
        """Stage | None: stage of the shown object, None if it is gone."""
        stage = self._stage_ref() if self._stage_ref is not None else None
        if stage is None or not shiboken6.isValid(stage):
            return None
        return stage

    @property
    def stage_object(self) -> StageObject | None:
        """StageObject | None: shown object, None if there is none or it was deleted.

        It is looked up by uuid, so a widget never keeps a deleted object alive.
        """
        stage = self.stage
        if stage is None or self._stage_object_uuid is None:
            return None
        try:
            return stage.get_object(self._stage_object_uuid)
        except StageObjectQueryError:
            return None

    def set_stage_object(self, stage_object: StageObject | None) -> None:
        """Show an object.

        Args:
            stage_object (StageObject | None): object to show, None to show none.
        """
        if stage_object is None or stage_object.stage is None:
            self._stage_object_uuid = None
            self._stage_ref = None
            self.clear()
            return
        self._stage_object_uuid = stage_object.uuid
        self._stage_ref = weakref.ref(stage_object.stage)
        self.refresh()

    def refresh(self) -> None:
        """Show the current state of the object again. Subclasses implement it."""
        raise NotImplementedError

    def clear(self) -> None:
        """Show no object. Subclasses implement it."""
        raise NotImplementedError
