import pathlib

from nyx import get_main_logger

LOGGER = get_main_logger()


def get_absolute_path_from_relative(anchor_path: pathlib.PurePosixPath, relative_path: pathlib.PurePosixPath):
    if isinstance(relative_path, str):
        relative_path = pathlib.PurePosixPath(relative_path)
    anchor_parts = list(anchor_path.parts)
    steps_back = relative_path.parts.count("..")
    forward_parts = [part for part in relative_path.parts if part != ".."]

    parent_parts = anchor_parts
    parent_parts.reverse()
    parent_parts = parent_parts[steps_back:]
    parent_parts.reverse()

    full_parts = parent_parts + forward_parts
    resolved_path = pathlib.PurePosixPath(*full_parts)
    LOGGER.debug(f"Resolved path: {resolved_path}(achor: {anchor_path} + rel: {relative_path})")
    return resolved_path
