from __future__ import annotations

import typing

from PySide6 import QtCore

from nyx.api.v1 import CoreInspectorWidgets
from nyx.api.v1.editor_utils import CommitPlainTextEdit, UtilObjectInspectorWidget
from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject

if typing.TYPE_CHECKING:
    from PySide6 import QtWidgets

    from nyx.stdlib.util_objects.note import NoteObject


class NoteInspector(UtilObjectInspectorWidget):
    """Text and color of a note."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the inspector widget."""
        return CoreInspectorWidgets.NOTE

    def _create_form(self, form_layout: QtWidgets.QFormLayout) -> None:
        """Add the text and color rows.

        Args:
            form_layout (QtWidgets.QFormLayout): layout of the form.
        """
        self.text_edit = CommitPlainTextEdit()
        self.text_edit.setMinimumHeight(120)
        self.color_combo = self.create_color_combo(GraphicsUtilObject.COLOR_PRESETS)
        form_layout.addRow("Text", self.text_edit)
        form_layout.addRow("Color", self.color_combo)
        self.text_edit.editing_finished.connect(self.commit_pending_edit)
        self.color_combo.activated.connect(self._on_color_chosen)

    def _show_object(self, note: NoteObject) -> None:
        """Show the text and color of the note.

        Args:
            note (NoteObject): note to show.
        """
        # The refresh after our own command must not reset the field being typed in
        if self.text_edit.toPlainText() != note.text:
            with QtCore.QSignalBlocker(self.text_edit):
                self.text_edit.setPlainText(note.text)
        self.show_color(self.color_combo, note.color)

    def clear(self) -> None:
        """Show no note."""
        super().clear()
        with QtCore.QSignalBlocker(self.text_edit):
            self.text_edit.clear()

    def commit_pending_edit(self) -> None:
        """Push the text, if it differs from the one of the note."""
        self.push_properties({"text": self.text_edit.toPlainText()}, "Edit note")

    def _on_color_chosen(self, index: int) -> None:
        """Push the color the user chose.

        Args:
            index (int): index of the chosen item.
        """
        self.push_properties({"color": self.color_combo.itemData(index)}, "Change color")
