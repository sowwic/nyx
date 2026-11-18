from __future__ import annotations

import typing

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core import commands
from .base import InspectorWidget

if typing.TYPE_CHECKING:
    from nyx.core.util_object import UtilObject


class UtilObjectInspectorWidget(InspectorWidget):
    """Base of the inspector widgets of util objects.

    Shows the type and path of the object above a form that subclasses add rows to in
    `_create_form`. The form is read only while the object is locked. Edits go through
    `push_properties`, so they can be undone.
    """

    COLOR_SWATCH_SIZE = 14

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize UtilObjectInspectorWidget.

        Args:
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._create_widgets()
        self._create_layouts()
        self._create_form(self.form_layout)

    def _create_widgets(self) -> None:
        """Create the header widgets."""
        self.icon_label = QtWidgets.QLabel()
        self.type_label = QtWidgets.QLabel()
        font = self.type_label.font()
        font.setBold(True)
        self.type_label.setFont(font)
        self.path_label = QtWidgets.QLabel()
        self.path_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.locked_label = QtWidgets.QLabel("Locked: the object can't be changed.")
        self.locked_label.setVisible(False)
        self.form_container = QtWidgets.QWidget()
        self.form_layout = QtWidgets.QFormLayout(self.form_container)

    def _create_layouts(self) -> None:
        """Lay out the header above the form."""
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.type_label, stretch=1)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.path_label)
        main_layout.addWidget(self.locked_label)
        main_layout.addWidget(self.form_container)
        main_layout.addStretch(1)

    def _create_form(self, form_layout: QtWidgets.QFormLayout) -> None:
        """Add the rows editing the object. Subclasses implement it.

        Args:
            form_layout (QtWidgets.QFormLayout): layout of the form.
        """
        raise NotImplementedError

    def _show_object(self, util_object: UtilObject) -> None:
        """Show the properties of the object in the form. Subclasses implement it.

        Args:
            util_object (UtilObject): object to show.
        """
        raise NotImplementedError

    def commit_pending_edit(self) -> None:
        """Push what the user typed but did not finish yet. Subclasses implement it.

        Called before the widget shows another object, because the focus can leave the
        field after the selection changed, and the edit would be lost.
        """

    def set_stage_object(self, stage_object) -> None:
        """Show an object, after committing the edit of the one shown before.

        Args:
            stage_object (StageObject | None): object to show, None to show none.
        """
        new_uuid = None if stage_object is None else stage_object.uuid
        if new_uuid != self._stage_object_uuid:
            self.commit_pending_edit()
        super().set_stage_object(stage_object)

    def refresh(self) -> None:
        """Show the object, or nothing if it is gone."""
        util_object: UtilObject | None = self.stage_object
        if util_object is None:
            self.clear()
            return
        icon = QtGui.QIcon(util_object.get_type_icon())
        self.icon_label.setPixmap(icon.pixmap(24, 24))
        self.type_label.setText(util_object.get_type_display_name())
        self.path_label.setText(str(util_object.path))
        self.locked_label.setVisible(util_object.is_locked)
        self.form_container.setEnabled(not util_object.is_locked)
        self._show_object(util_object)

    def clear(self) -> None:
        """Show no object."""
        self.icon_label.clear()
        self.type_label.clear()
        self.path_label.clear()
        self.locked_label.setVisible(False)
        self.form_container.setEnabled(False)

    def push_properties(self, properties: dict[str, typing.Any], text: str) -> None:
        """Change properties of the shown object with an undoable command.

        Args:
            properties (dict[str, typing.Any]): new values by property name.
            text (str): undo stack text.
        """
        util_object = self.stage_object
        if util_object is None or util_object.is_locked:
            return
        current = util_object.serialize_properties()
        changed = {
            name: value
            for name, value in properties.items()
            if current.get(name) != value
        }
        if not changed:
            return
        stage = util_object.stage
        stage.push_command(
            commands.SetUtilObjectPropertiesCommand(
                stage, {util_object: changed}, text=text
            )
        )

    def create_color_combo(
        self, color_presets: typing.Mapping[str, str]
    ) -> QtWidgets.QComboBox:
        """Create a combo box choosing a color from presets.

        The color of the object is added as "Custom" when it is not a preset.

        Args:
            color_presets (typing.Mapping[str, str]): color names and values.

        Returns:
            QtWidgets.QComboBox: combo box, its items hold the colors as data.
        """
        combo = QtWidgets.QComboBox()
        for name, color in color_presets.items():
            combo.addItem(self._color_icon(color), name, color)
        return combo

    def show_color(self, combo: QtWidgets.QComboBox, color: str) -> None:
        """Select a color in a combo box made by `create_color_combo`.

        Args:
            combo (QtWidgets.QComboBox): combo box.
            color (str): color value to select.
        """
        index = combo.findData(color)
        custom_index = combo.findText("Custom")
        if index < 0:
            if custom_index < 0:
                combo.addItem(self._color_icon(color), "Custom", color)
                custom_index = combo.count() - 1
            else:
                combo.setItemData(custom_index, color)
                combo.setItemIcon(custom_index, self._color_icon(color))
            index = custom_index
        elif custom_index >= 0 and index != custom_index:
            combo.removeItem(custom_index)
            index = combo.findData(color)
        combo.setCurrentIndex(index)

    def _color_icon(self, color: str) -> QtGui.QIcon:
        """Get a small square filled with a color.

        Args:
            color (str): color value, such as "#5b8def".

        Returns:
            QtGui.QIcon: icon.
        """
        pixmap = QtGui.QPixmap(self.COLOR_SWATCH_SIZE, self.COLOR_SWATCH_SIZE)
        pixmap.fill(QtGui.QColor(color))
        return QtGui.QIcon(pixmap)
