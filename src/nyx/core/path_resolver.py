import logging
import os
import pathlib

from ..static.vars import ROOT_NODE_PATH

LOGGER = logging.getLogger(__name__)


class StagePathResolver:
    """Helpers for classifying and converting stage object paths."""

    @staticmethod
    def is_absolute_path(path: pathlib.PurePosixPath | str) -> bool:
        """Is given path absolute.

        Args:
            path (pathlib.PurePosixPath | str): path to test

        Returns:
            bool: is absolute

        """
        return pathlib.PurePosixPath(path).is_absolute()

    @staticmethod
    def is_relative_path(path: pathlib.PurePosixPath | str) -> bool:
        """Is given path relative.

        Args:
            path (pathlib.PurePosixPath | str): path to test

        Returns:
            bool: is relative

        """
        return not StagePathResolver.is_absolute_path(path)

    @staticmethod
    def is_node_path(path: pathlib.PurePosixPath | str) -> bool:
        """Is given path a node path.

        Args:
            path (pathlib.PurePosixPath | str): path to test.

        Returns:
            bool: path is inside the stage and has no component suffix.
        """
        path = pathlib.PurePosixPath(path)
        no_suffix = path.suffix == ""
        part_of_stage = path == ROOT_NODE_PATH or ROOT_NODE_PATH in path.parents
        return all([no_suffix, part_of_stage])

    @staticmethod
    def is_node_component_path(path: pathlib.PurePosixPath | str) -> bool:
        """Is given path a node component path.

        Args:
            path (pathlib.PurePosixPath | str): path to test.

        Returns:
            bool: path has a component suffix and its node part is a node path.
        """
        path = pathlib.PurePosixPath(path)
        node_component_name = path.suffix
        if not node_component_name:
            return False

        if StagePathResolver.is_node_path(StagePathResolver.as_node_path(path)):
            return True

    @staticmethod
    def as_node_path(path: pathlib.PurePosixPath | str) -> pathlib.PurePosixPath:
        """Strip the component suffix from a path.

        Args:
            path (pathlib.PurePosixPath | str): node or component path.

        Returns:
            pathlib.PurePosixPath: path of the owning node.
        """
        return pathlib.PurePosixPath(path).with_suffix("")

    @staticmethod
    def compute_relative_path(
        source_path: pathlib.PurePosixPath | str,
        destination_path: pathlib.PurePosixPath | str,
    ) -> pathlib.PurePosixPath:
        """Compute a relative path from source to destination paths.

        Args:
            source_path (pathlib.PurePosixPath | str): start path
            destination_path (pathlib.PurePosixPath | str): target path

        Raises:
            ValueError: source_path is not absolute
            ValueError: destination_path is not absolute

        Returns:
            PurePosixPath: relative path

        """
        if not StagePathResolver.is_absolute_path(source_path):
            raise ValueError(f"Source path is not absolute: {source_path}")
        if not StagePathResolver.is_absolute_path(destination_path):
            raise ValueError(f"Destination path is not absolute: {destination_path}")

        rel_path = os.path.relpath(str(destination_path), str(source_path))
        if "\\" in rel_path:
            rel_path = rel_path.replace("\\", "/")
        if not rel_path.startswith("/"):
            rel_path = "./" + rel_path
        return pathlib.PurePosixPath(rel_path)

    @staticmethod
    def compute_absolute_path(
        anchor_path: pathlib.PurePosixPath | str,
        rel_path: pathlib.PurePosixPath | str,
    ) -> pathlib.PurePosixPath:
        """Compute absolute path from given anchor and relative paths.

        Args:
            anchor_path: anchor path to start computation from
            rel_path: relative path

        Raises:
            ValueError: anchor_path is not absolute
            ValueError: rel_path is not relative

        Returns:
            PurePosixPath: absolute path

        """
        if not StagePathResolver.is_absolute_path(anchor_path):
            raise ValueError(f"Source path is not absolute: {anchor_path}")
        if not StagePathResolver.is_relative_path(rel_path):
            raise ValueError(f"Relative path is not relative: {rel_path}")
        anchor_path = pathlib.PurePosixPath(anchor_path)
        rel_path = pathlib.PurePosixPath(rel_path)

        # Child case
        if not rel_path.as_posix().startswith(".."):
            return anchor_path / rel_path
        # Other node
        new_abs_parts = list(anchor_path.parts)
        for token in rel_path.parts:
            if token == "..":
                new_abs_parts = new_abs_parts[:-1]
            else:
                new_abs_parts.append(token)
        abs_string = new_abs_parts[0] + "/".join(new_abs_parts[1:])
        return pathlib.PurePosixPath(abs_string)
