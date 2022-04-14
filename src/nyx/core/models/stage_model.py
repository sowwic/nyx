import pathlib
from PySide2 import QtCore


class StageModelSignals:
    data_changed = QtCore.Signal(dict)
    name_changed = QtCore.Signal(str)
    path_changed = QtCore.Signal(pathlib.Path)


class StageModel:
    def __init__(self, stage_data: dict) -> None:
        super().__init__()
        self.signals = StageModelSignals()
        self.stage_data = stage_data
