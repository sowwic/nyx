from nyx.api.v1 import NodeComponent, CoreNodeComponents


class ValueComponent(NodeComponent):
    DEFAULT_NAME = "value"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodeComponents.VALUE

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Value"

    @classmethod
    def get_tags(self) -> set[str]:
        return {"common", "value"}
