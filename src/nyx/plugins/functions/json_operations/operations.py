"""Functions converting to and from JSON."""

import json
import typing


def parse_json(text: str) -> typing.Any:
    """Convert JSON text to a value.

    Args:
        text: JSON text.
    """
    return json.loads(text)


def to_json(value: typing.Any, indent: int = 0) -> str:
    """Convert a value to JSON text, indented if indent is bigger than 0.

    Args:
        value: Value to convert.
        indent: Spaces to indent with, 0 for a single line.
    """
    return json.dumps(value, indent=indent or None, default=str)


def is_valid_json(text: str) -> bool:
    """Check if a string is valid JSON.

    Args:
        text: JSON text.
    """
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def read_json_file(path: str) -> dict:
    """Read a JSON file.

    Args:
        path: File to use.
    """
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def write_json_file(path: str, value: typing.Any, indent: int = 4) -> str:
    """Write a value to a JSON file, get the path of the file.

    Args:
        path: File to use.
        value: Value to convert.
        indent: Spaces to indent with, 0 for a single line.
    """
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, indent=indent or None, default=str)
    return path


def get_json_value(
    value: typing.Any, query: str, default: typing.Any = None
) -> typing.Any:
    """Get a nested value by a dotted query like "user.items.0.name".

    Numbers in the query are list indices when the value there is a list.

    Args:
        value: Value to convert.
        query: Keys and list indices separated by dots, like user.items.0.name.
        default: Value to get if nothing is found.
    """
    for part in query.split("."):
        try:
            if isinstance(value, list):
                value = value[int(part)]
            else:
                value = value[part]
        except (KeyError, IndexError, ValueError, TypeError):
            return default
    return value
