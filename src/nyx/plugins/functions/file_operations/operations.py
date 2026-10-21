"""Functions working with files and folders."""

import pathlib
import shutil


def create_file(
    path: str, mode: int = 0o666, exists_ok: bool = False, parent_dirs: bool = True
) -> bool:
    """Create an empty file.

    Args:
        path: file to create.
        mode: permissions of the file.
        exists_ok: leave the file as it is if it exists, instead of failing.
        parent_dirs: create the folders leading to the file too.

    Returns:
        bool: file was created, false if it was there already.
    """
    file_path = pathlib.Path(path)
    if file_path.exists() and not exists_ok:
        raise ValueError(f"File already exists: {file_path}")

    created = not file_path.exists()
    file_path.parent.mkdir(parents=parent_dirs, exist_ok=True)
    file_path.touch(mode=mode, exist_ok=True)
    return created


def file_exists(path: str) -> bool:
    """Check if a path is an existing file.

    Args:
        path: Path of the file or folder.
    """
    return pathlib.Path(path).is_file()


def folder_exists(path: str) -> bool:
    """Check if a path is an existing folder.

    Args:
        path: Path of the file or folder.
    """
    return pathlib.Path(path).is_dir()


def read_text(path: str, encoding: str = "utf-8") -> str:
    """Read the text of a file.

    Args:
        path: Path of the file or folder.
        encoding: Text encoding of the file.
    """
    return pathlib.Path(path).read_text(encoding=encoding)


def write_text(path: str, text: str, encoding: str = "utf-8") -> str:
    """Write text to a file, replacing its content. Get the path of the file.

    Args:
        path: Path of the file or folder.
        text: Text to write.
        encoding: Text encoding of the file.
    """
    pathlib.Path(path).write_text(text, encoding=encoding)
    return path


def append_text(path: str, text: str, encoding: str = "utf-8") -> str:
    """Add text to the end of a file. Get the path of the file.

    Args:
        path: Path of the file or folder.
        text: Text to add.
        encoding: Text encoding of the file.
    """
    with pathlib.Path(path).open("a", encoding=encoding) as file:
        file.write(text)
    return path


def read_lines(path: str, encoding: str = "utf-8") -> list:
    """Read the lines of a file, without line endings.

    Args:
        path: Path of the file or folder.
        encoding: Text encoding of the file.
    """
    return pathlib.Path(path).read_text(encoding=encoding).splitlines()


def list_folder(path: str) -> list:
    """Get the names of the files and folders in a folder, sorted.

    Args:
        path: Path of the file or folder.
    """
    return sorted(child.name for child in pathlib.Path(path).iterdir())


def make_folder(path: str) -> str:
    """Create a folder with the folders leading to it. Get its path.

    Args:
        path: Path of the file or folder.
    """
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    return path


def copy_file(source: str, destination: str) -> str:
    """Copy a file. Get the path of the copy.

    Args:
        source: File to copy.
        destination: Path of the copy.
    """
    return str(shutil.copy2(pathlib.Path(source), pathlib.Path(destination)))


def move_path(source: str, destination: str) -> str:
    """Move a file or folder. Get its new path.

    Args:
        source: File or folder to move.
        destination: Path to move to.
    """
    return str(shutil.move(pathlib.Path(source), pathlib.Path(destination)))


def delete_file(path: str) -> bool:
    """Delete a file. Get if there was a file to delete.

    Args:
        path: Path of the file or folder.
    """
    file_path = pathlib.Path(path)
    if not file_path.is_file():
        return False
    file_path.unlink()
    return True


def delete_folder(path: str) -> bool:
    """Delete a folder with everything in it. Get if there was a folder to delete.

    Args:
        path: Path of the file or folder.
    """
    folder_path = pathlib.Path(path)
    if not folder_path.is_dir():
        return False
    shutil.rmtree(folder_path)
    return True


def file_size(path: str) -> int:
    """Get the size of a file in bytes.

    Args:
        path: Path of the file or folder.
    """
    return pathlib.Path(path).stat().st_size
