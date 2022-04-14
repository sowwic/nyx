import typing
import pathlib

from nyx.core.models.node_model import NodeModel


class Node:

    def __init__(self, stage, name: str = "node", parent_path: typing.Union[pathlib.Path, str] = "/") -> None:
        self.stage = stage
        name = stage.get_unique_node_name(parent_path, name)
        parent_path = parent_path if isinstance(
            parent_path, pathlib.Path) else pathlib.Path(parent_path)

        self.model = NodeModel(parent_path / name)
