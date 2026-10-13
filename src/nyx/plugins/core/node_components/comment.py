from nyx.api.v1 import NodeComponent, CoreNodeComponents, NodeComponentFlag


class CommentComponent(NodeComponent):
    DEFAULT_NAME = "comment"
    EDITOR_QML = "CommentComponentItem.qml"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodeComponents.COMMENT

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Comment"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/comment_cpnt"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"common", "utility"}

    @classmethod
    def get_type_default_value(cls) -> str:
        return ""

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return NodeComponentFlag.EDITABLE | NodeComponentFlag.STATIC

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        return True
