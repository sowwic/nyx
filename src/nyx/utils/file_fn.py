"""Common file operations"""
import abc
import json
import sys
import pathlib
import typing


class DirectoryStruct(abc.ABC):
    def make_dirs(self, exist_ok=True):
        """Create directory for each path field.

        Args:
            exist_ok (bool, optional): Skip directory if already exists. Defaults to True.
        """
        for dir_path in self.list_dirs():
            dir_path.mkdir(exist_ok=exist_ok)

    def list_dirs(self) -> typing.List[pathlib.Path]:
        """List paths to directories in this struct.

        Returns:
            list[pathlib.Path]: list of directories paths.
        """
        return [path for path in vars(self).values() if isinstance(path, pathlib.Path) and not path.suffix]


def write_json(path: typing.Union[pathlib.Path, str], data: dict, as_string=False, sort_keys=True, indent=4):
    """Write json file.

    Args:
        path (pathlib.Path | str): path to json file.
        data (dict): data to write.
        as_string (bool, optional): write data as json string. Defaults to False.
        sort_keys (bool, optional): sort data keys. Defaults to True.
        indent (int, optional): indentation inside written file. Defaults to 4.

    Returns:
        pathlib.Path: path to written file.
    """
    with path.open("w") as json_file:
        if as_string:
            json_file.write(json.dumps(data, sort_keys=sort_keys, indent=4, separators=(",", ":")))
        else:
            json.dump(data, json_file, indent=indent)
    return path


def load_json(path: typing.Union[pathlib.Path, str] = None, input_str: str = None):
    """Load json data from file or string.

    Args:
        path (pathlib.Path | str, optional): path to json file. Defaults to None.
        input_str (str, optional): json string. Defaults to None.

    Raises:
        ValueError: If no file path or string were provided.

    Returns:
        dict: loaded json data.
    """
    if path is None and input_str is None:
        raise ValueError("Invalid parameters: neither path or json string were given.")

    if input_str:
        data = json.loads(input_str)
    else:
        path = pathlib.Path(path) if not isinstance(path, pathlib.Path) else path
        with path.open("r") as json_file:
            data = json.load(json_file)
    return data


# Directory
def get_data_dir() -> pathlib.Path:
    """Get user data direcotory for current machine OS.

    Returns:
        pathlib.Path: user app data directory path.
    """
    home = pathlib.Path.home()
    if sys.platform == "win32":
        return home / "AppData/Roaming"
    elif sys.platform == "linux":
        return home / ".local/share"
    elif sys.platform == "darwin":
        return home / "Library/Application Support"
