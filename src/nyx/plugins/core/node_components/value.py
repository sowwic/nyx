from nyx.api.v1 import NodeComponent, CoreNodeComponents, NodeComponentFlag


class ValueComponent(NodeComponent):
    DEFAULT_NAME = "value"
    EDITOR_QML = "ValueComponentItem.qml"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodeComponents.VALUE

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Value"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/value_cpnt"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"common", "value"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return NodeComponentFlag.STATIC | NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        return True
