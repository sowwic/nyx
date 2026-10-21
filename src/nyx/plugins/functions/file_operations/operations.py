"""Functions working with files and folders."""

import os
import shutil


def file_exists(path: str) -> bool:
    """Check if a path is an existing file."""
    return os.path.isfile(path)


def folder_exists(path: str) -> bool:
    """Check if a path is an existing folder."""
    return os.path.isdir(path)


def read_text(path: str, encoding: str = "utf-8") -> str:
    """Read the text of a file."""
    with open(path, encoding=encoding) as file:
        return file.read()


def write_text(path: str, text: str, encoding: str = "utf-8") -> str:
    """Write text to a file, replacing its content. Get the path of the file."""
    with open(path, "w", encoding=encoding) as file:
        file.write(text)
    return path


def append_text(path: str, text: str, encoding: str = "utf-8") -> str:
    """Add text to the end of a file. Get the path of the file."""
    with open(path, "a", encoding=encoding) as file:
        file.write(text)
    return path


def read_lines(path: str, encoding: str = "utf-8") -> list:
    """Read the lines of a file, without line endings."""
    with open(path, encoding=encoding) as file:
        return file.read().splitlines()


def list_folder(path: str) -> list:
    """Get the names of the files and folders in a folder, sorted."""
    return sorted(os.listdir(path))


def make_folder(path: str) -> str:
    """Create a folder with the folders leading to it. Get its path."""
    os.makedirs(path, exist_ok=True)
    return path


def copy_file(source: str, destination: str) -> str:
    """Copy a file. Get the path of the copy."""
    return shutil.copy2(source, destination)


def move_path(source: str, destination: str) -> str:
    """Move a file or folder. Get its new path."""
    return shutil.move(source, destination)


def delete_file(path: str) -> bool:
    """Delete a file. Get if there was a file to delete."""
    if not os.path.isfile(path):
        return False
    os.remove(path)
    return True


def delete_folder(path: str) -> bool:
    """Delete a folder with everything in it. Get if there was a folder to delete."""
    if not os.path.isdir(path):
        return False
    shutil.rmtree(path)
    return True


def file_size(path: str) -> int:
    """Get the size of a file in bytes."""
    return os.path.getsize(path)


def join_path(base: str, name: str) -> str:
    """Add a name to the end of a path."""
    return os.path.join(base, name)


def file_name(path: str) -> str:
    """Get the last part of a path."""
    return os.path.basename(path)


def file_stem(path: str) -> str:
    """Get the file name without its extension."""
    return os.path.splitext(os.path.basename(path))[0]


def file_extension(path: str) -> str:
    """Get the extension of a file with the dot, empty if there is none."""
    return os.path.splitext(path)[1]


def parent_folder(path: str) -> str:
    """Get the folder a path is in."""
    return os.path.dirname(path)


def absolute_path(path: str) -> str:
    """Get the full path from the root, with ~ expanded."""
    return os.path.abspath(os.path.expanduser(path))
