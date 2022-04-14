import pathlib
from nyx.core.models.stage_model import StageModel
from nyx.utils import file_fn


class Stage:
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
