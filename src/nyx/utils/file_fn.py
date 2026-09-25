"""Common file operations"""

import abc
import json
import pathlib


class DirectoryStruct(abc.ABC):
    def make_dirs(self, exist_ok=True):
        """Create directory for each path field.

        Args:
            exist_ok: Skip directory if already exists

        """
        for dir_path in self.list_dirs():
            dir_path.mkdir(exist_ok=exist_ok)

    def list_dirs(self) -> list[pathlib.Path]:
        """List paths to directories in this struct.

        Returns:
            list[pathlib.Path]: list of directories paths.

        """
        return [
            path
            for path in vars(self).values()
            if isinstance(path, pathlib.Path) and not path.suffix
        ]


def write_json(
    path: pathlib.Path | str,
    data: dict,
    as_string=False,
    sort_keys=True,
    indent=4,
):
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
    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)

    with path.open("w") as json_file:
        if as_string:
            json_file.write(
                json.dumps(data, sort_keys=sort_keys, indent=4, separators=(",", ":"))
            )
        else:
            json.dump(data, json_file, indent=indent)
    return path


def load_json(
    path: pathlib.Path | str | None = None,
    input_str: str | None = None,
    object_pairs_hook=None,
):
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
            data = json.load(json_file, object_pairs_hook=object_pairs_hook)
    return data


def is_jsonable(obj):
    try:
        json.dumps(obj)
        return True
    except TypeError, OverflowError:
        return False
