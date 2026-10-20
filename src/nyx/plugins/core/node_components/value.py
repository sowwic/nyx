from PySide6 import QtGui
from nyx.api.v1 import (
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
    DatatypeColor,
)


class ValueComponent(NodeComponent):
    """Static, editable component holding a value."""

    DEFAULT_NAME = "value"
    EDITOR_QML = "ValueComponentItem"

    VALUE_TYPE_COLOR_MAP = {bool: DatatypeColor.BOOL, str: DatatypeColor.STRING}

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.VALUE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Value"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/value_cpnt"

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"common", "value"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: static and editable."""
        return NodeComponentFlag.STATIC | NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: value components start expanded."""
        return True

    def get_plug_color(self):
        return QtGui.QColor(
            self.VALUE_TYPE_COLOR_MAP.get(
                type(self.cached_value), NodeComponent.DEFAULT_PLUG_COLOR
            )
        )
