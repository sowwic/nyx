"""Environment files (`.env`), for the `--envfile` command line argument.

This module has no nyx imports so it can run before the rest of the package is imported.
"""

import os
import pathlib


def parse_env_file(text: str) -> dict[str, str]:
    """Parse the content of an environment file.

    Lines are `NAME=value`, optionally after `export`. Blank lines and lines starting
    with `#` are skipped, so are lines without a name or an `=`. A value in single quotes
    is taken as it is, one in double quotes or without quotes gets `$NAME` references
    expanded.

    Args:
        text (str): content of the file.

    Returns:
        dict[str, str]: variables in the order of the file.
    """
    variables = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.removeprefix("export ").lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == "'":
            variables[name] = value[1:-1]
            continue
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        variables[name] = os.path.expandvars(value)
    return variables


def load_env_file(path: pathlib.Path | str) -> dict[str, str]:
    """Set the variables of an environment file in this process.

    Variables are set in order, so a value can refer to one above it.

    Args:
        path (pathlib.Path | str): environment file.

    Returns:
        dict[str, str]: variables that were set.

    Raises:
        OSError: the file can't be read.
    """
    text = pathlib.Path(path).expanduser().read_text(encoding="utf-8")
    variables = {}
    for line in text.splitlines():
        for name, value in parse_env_file(line).items():
            os.environ[name] = variables[name] = value
    return variables
