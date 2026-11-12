from nyx.api.v1 import Node, CoreNodes


class BlankNode(Node):
    """Node without components, used as a container and as the stage root."""

    DEFAULT_NAME = "node"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.EMPTY

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Node"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Empty node without components. Groups other nodes inside of it."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"common"}
