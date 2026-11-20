from __future__ import annotations

import typing

from PySide6 import QtCore, QtWidgets

from nyx.api.v1 import CoreInspectorWidgets
from nyx.api.v1.editor_utils import UtilObjectInspectorWidget
from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject

if typing.TYPE_CHECKING:
    from nyx.stdlib.util_objects.group import GroupObject


class GroupInspector(UtilObjectInspectorWidget):
    """Title and color of a group."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the inspector widget."""
        return CoreInspectorWidgets.GROUP

    def _create_form(self, form_layout: QtWidgets.QFormLayout) -> None:
        """Add the title and color rows.

        Args:
            form_layout (QtWidgets.QFormLayout): layout of the form.
        """
        self.title_edit = QtWidgets.QLineEdit()
        self.color_combo = self.create_color_combo(GraphicsUtilObject.COLOR_PRESETS)
        form_layout.addRow("Title", self.title_edit)
        form_layout.addRow("Color", self.color_combo)
        self.title_edit.editingFinished.connect(self.commit_pending_edit)
        self.color_combo.activated.connect(self._on_color_chosen)

    def _show_object(self, group: GroupObject) -> None:
        """Show the title and color of the group.

        Args:
            group (GroupObject): group to show.
        """
        # The refresh after our own command must not reset the field being typed in
        if self.title_edit.text() != group.title:
            with QtCore.QSignalBlocker(self.title_edit):
                self.title_edit.setText(group.title)
        self.show_color(self.color_combo, group.color)

    def clear(self) -> None:
        """Show no group."""
        super().clear()
        with QtCore.QSignalBlocker(self.title_edit):
            self.title_edit.clear()

    def commit_pending_edit(self) -> None:
        """Push the title, if it differs from the one of the group."""
        self.push_properties({"title": self.title_edit.text()}, "Rename group")

    def _on_color_chosen(self, index: int) -> None:
        """Push the color the user chose.

        Args:
            index (int): index of the chosen item.
        """
        self.push_properties({"color": self.color_combo.itemData(index)}, "Change color")
