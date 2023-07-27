import os
import typing
import pathlib
from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Stage


LOGGER = get_main_logger()


class Resolver:

    @staticmethod
    def is_absolute_path(path: "pathlib.PurePosixPath | str"):
        """Is given path absolute.

        Args:
            path (pathlib.PurePosixPath | str): path to test

        Returns:
            bool: is absolute
        """
        return os.path.isabs(path)

    @staticmethod
    def is_relative_path(path: "pathlib.PurePosixPath | str"):
        """Is given path relative.

        Args:
            path (pathlib.PurePosixPath | str): path to test

        Returns:
            bool: is relative
        """
        return not Resolver.is_absolute_path(path)

    @staticmethod
    def compute_relative_path(
        source_path: "pathlib.PurePosixPath | str",
        destination_path: "pathlib.PurePosixPath | str"
    ):
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
        if not Resolver.is_absolute_path(source_path):
            raise ValueError(f"Source path is not absolute: {source_path}")
        if not Resolver.is_absolute_path(destination_path):
            raise ValueError(
                f"Destination path is not absolute: {destination_path}")

        rel_path = os.path.relpath(str(destination_path), str(source_path))
        if "\\" in rel_path:
            rel_path = rel_path.replace("\\", "/")
        if not rel_path.startswith("/"):
            rel_path = "./" + rel_path
        return pathlib.PurePosixPath(rel_path)

    @staticmethod
    def computer_absolute_path(
        anchor_path: "pathlib.PurePosixPath | str",
        rel_path: "pathlib.PurePosixPath | str"
    ):
        """Compute absolute path from given anchor and relative paths.

        Args:
            anchor_path (pathlib.PurePosixPath | str): anchor path to start computation from
            rel_path (pathlib.PurePosixPath | str): relative path

        Raises:
            ValueError: anchor_path is not absolute
            ValueError: rel_path is not relative

        Returns:
            PurePosixPath: absolute path
        """
        if not Resolver.is_absolute_path(anchor_path):
            raise ValueError(f"Source path is not absolute: {anchor_path}")
        if not Resolver.is_relative_path(rel_path):
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
