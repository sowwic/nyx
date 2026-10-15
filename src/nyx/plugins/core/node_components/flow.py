import pathlib

from nyx.api.v1 import (
    Node,
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
)


class FlowComponent(NodeComponent):
    DEFAULT_NAME = "flow"
    EDITOR_QML = "FlowComponentItem"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodeComponents.FLOW

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Flow"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/flow_cpnt"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"logic"}

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        return True

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return (
            NodeComponentFlag.STATIC
            | NodeComponentFlag.WRITABLE
            | NodeComponentFlag.READABLE
        )

    def deserialize_value(self, value: str | None) -> pathlib.PurePosixPath | None:
        if value is None:
            return value
        return pathlib.PurePosixPath(value)

    def get_next_node(self) -> Node | None:
        if self.output_links:
            return self.output_links[0].target_node
        return None
