from nyx.api.v1 import (
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
    CoreDatatypes,
)


class FileComponent(NodeComponent):
    """Static, editable component holding the path of a file as a string.

    The path can be typed or picked with a file dialog.
    """

    DEFAULT_NAME = "file"
    EDITOR_QML = "FileComponentItem"

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.FILE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "File"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/folder_open"

    @classmethod
    def get_type_default_value(cls) -> str:
        """str: empty file path."""
        return ""

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: the path is kept as a string."""
        return CoreDatatypes.STRING

    @classmethod
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return "Holds the path of a file, typed or picked with a file dialog."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"common", "file", "value"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: static and editable."""
        return NodeComponentFlag.STATIC | NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: file components start expanded."""
        return True
