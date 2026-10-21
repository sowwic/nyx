"""Functions working with path text. None of them needs the path to exist."""

import pathlib


def join_path(base: str, name: str) -> str:
    """Add a name to the end of a path."""
    return str(pathlib.Path(base) / name)


def file_name(path: str) -> str:
    """Get the last part of a path."""
    return pathlib.Path(path).name


def file_stem(path: str) -> str:
    """Get the file name without its extension."""
    return pathlib.Path(path).stem


def file_extension(path: str) -> str:
    """Get the extension of a file with the dot, empty if there is none."""
    return pathlib.Path(path).suffix


def parent_folder(path: str) -> str:
    """Get the folder a path is in."""
    return str(pathlib.Path(path).parent)


def absolute_path(path: str) -> str:
    """Get the full path from the root, with ~ expanded and symlinks followed."""
    return str(pathlib.Path(path).expanduser().resolve())


def with_name(path: str, name: str) -> str:
    """Replace the last part of a path."""
    return str(pathlib.Path(path).with_name(name))


def with_extension(path: str, extension: str) -> str:
    """Replace the extension of a path, with the dot. Empty removes it."""
    return str(pathlib.Path(path).with_suffix(extension))


def relative_to(path: str, base: str) -> str:
    """Get a path as seen from a base folder, fails if it isn't inside it."""
    return str(pathlib.Path(path).relative_to(base))


def path_parts(path: str) -> list:
    """Get the parts of a path as a list."""
    return list(pathlib.Path(path).parts)


def is_absolute(path: str) -> bool:
    """Check if a path starts from the root."""
    return pathlib.Path(path).is_absolute()


def matches_pattern(path: str, pattern: str) -> bool:
    """Check if a path fits a pattern like "*.py" or "src/*/x.txt"."""
    return pathlib.PurePath(path).match(pattern)


def expand_user(path: str) -> str:
    """Replace a leading ~ with the home folder."""
    return str(pathlib.Path(path).expanduser())
