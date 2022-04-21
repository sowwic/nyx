import pathlib
from collections import deque

from nyx import get_main_logger

LOGGER = get_main_logger()


def get_absolute_path_from_relative(anchor_path: pathlib.PurePosixPath, relative_path: pathlib.PurePosixPath):
    if isinstance(relative_path, str):
        relative_path = pathlib.PurePosixPath(relative_path)

    steps_back = relative_path.parts.count("..")
    forward_parts = [part for part in relative_path.parts if part != ".."]

    parent_paths = deque(anchor_path.parents)
    parent_paths.rotate()

    if steps_back:
        resolved_path = parent_paths[steps_back].joinpath(*forward_parts)
    else:
        resolved_path = anchor_path.joinpath(*forward_parts)

    LOGGER.debug(f"Resolved path: {resolved_path} (anchor: {anchor_path} + rel: {relative_path})")
    return resolved_path
