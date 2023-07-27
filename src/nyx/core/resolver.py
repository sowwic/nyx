import os
import typing
import pathlib

if typing.TYPE_CHECKING:
    from nyx.core import Stage


class Resolver:
    def __init__(self, stage: "Stage") -> None:
        self.__stage = stage

    @property
    def stage(self):
        return self.__stage

    @staticmethod
    def compute_relative_path(
        source_path: "pathlib.PurePosixPath | str",
        destination_path: "pathlib.PurePosixPath | str"
    ):
        rel_path = os.path.relpath(str(destination_path), str(source_path))
        if "\\" in rel_path:
            rel_path = rel_path.replace("\\", "/")
        return pathlib.PurePosixPath(rel_path)

    def computer_absolute_path(self, anchor_path, rel_path):
        # TODO: implement
        pass
