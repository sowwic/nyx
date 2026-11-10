from PySide6 import QtGui
from nyx.api.v1 import (
    NYX_REGISTRY,
    Datatype,
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
)


class ValueComponent(NodeComponent):
    """Static, editable component holding a value."""

    DEFAULT_NAME = "value"
    EDITOR_QML = "ValueComponentItem"

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
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return (
            "Holds a typed value that can be edited, linked to other components or "
            "pulled by them."
        )

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

    def get_shown_datatype(self) -> Datatype:
        """Get the datatype the component is shown with.

        Returns:
            Datatype: the datatype hint, or for an unhinted component the datatype
                of the current value.
        """
        if not self.datatype.is_wildcard:
            return self.datatype
        return NYX_REGISTRY.infer_datatype(self.cached_value)

    def get_plug_color(self) -> QtGui.QColor:
        """QtGui.QColor: color of the shown datatype."""
        if self._providers.plug_color is not None:
            return self._providers.plug_color()
        return QtGui.QColor(self.get_shown_datatype().color)
