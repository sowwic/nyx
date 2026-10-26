from nyx.api.v1 import (
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
    CoreDatatypes,
)


class CommentComponent(NodeComponent):
    """Static, editable text component for notes."""

    DEFAULT_NAME = "comment"
    EDITOR_QML = "CommentComponentItem"

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.COMMENT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Comment"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/comment_cpnt"

    @classmethod
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return "Static text for notes. Does not take part in execution."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"common", "utility"}

    @classmethod
    def get_type_default_value(cls) -> str:
        """str: empty text."""
        return ""

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: editable and static."""
        return NodeComponentFlag.EDITABLE | NodeComponentFlag.STATIC

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: comments start expanded."""
        return True

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: comments are strings."""
        return CoreDatatypes.STRING
