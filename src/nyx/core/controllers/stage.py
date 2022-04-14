import pathlib
import operator
import functools
from nyx.core.models.stage_model import StageModel
from nyx.utils import file_fn


class Stage:

    ROOT_PATH = pathlib.Path("/")

    def __init__(self, file_path: pathlib.Path = None) -> None:
        self.file_path = file_path
        stage_data = {}
        if file_path:
            stage_data = file_fn.load_json(file_path)

        self.model = StageModel(stage_data)

    @property
    def data(self):
        return self.model.stage_data

    # TODO: Add implementation
    def get_unique_node_name(self, parent_path: pathlib.Path, name: str):
        return name

    def get_data_from_node_path(self, node_path: pathlib.Path):
        if node_path == Stage.ROOT_PATH:
            return self.data
        path_parts = node_path.parts[1:]
        node_data = functools.reduce(operator.getitem, path_parts, self.data)
        return node_data

    def set_data_for_node_path(self, node_path: pathlib.Path, data: dict):
        self.get_data_from_node_path(node_path.parent)[node_path.parts[-1]] = data

    def add_node(self, node):
        self.set_data_for_node_path(node.model.path, node.model.data)
