from nyx.api.v1 import Node, CoreNodes


class BlankNode(Node):
    DEFAULT_NAME = "node"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.EMPTY

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Node"
