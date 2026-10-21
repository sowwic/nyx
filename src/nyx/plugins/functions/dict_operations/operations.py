"""Functions working with dictionaries. None of them changes the dictionary it gets."""

import typing


def make_dict(key: typing.Any, value: typing.Any) -> dict:
    """Make a dictionary of one key and its value.

    Args:
        key: The key.
        value: The value of the key.
    """
    return {key: value}


def length(data: dict) -> int:
    """Get the number of keys.

    Args:
        data: Dictionary to use.
    """
    return len(data)


def get_value(data: dict, key: typing.Any, default: typing.Any = None) -> typing.Any:
    """Get the value of a key, the default if there is no such key.

    Args:
        data: Dictionary to use.
        key: Key to use.
        default: Value to get if there is no such key.
    """
    return data.get(key, default)


def set_value(data: dict, key: typing.Any, value: typing.Any) -> dict:
    """Get a copy of the dictionary with a key set.

    Args:
        data: Dictionary to use.
        key: Key to use.
        value: Value to use.
    """
    return {**data, key: value}


def remove_key(data: dict, key: typing.Any) -> dict:
    """Get a copy of the dictionary without a key.

    Args:
        data: Dictionary to use.
        key: Key to use.
    """
    return {k: v for k, v in data.items() if k != key}


def has_key(data: dict, key: typing.Any) -> bool:
    """Check if the dictionary has a key.

    Args:
        data: Dictionary to use.
        key: Key to use.
    """
    return key in data


def keys(data: dict) -> list:
    """Get the keys.

    Args:
        data: Dictionary to use.
    """
    return list(data.keys())


def values(data: dict) -> list:
    """Get the values.

    Args:
        data: Dictionary to use.
    """
    return list(data.values())


def items(data: dict) -> list:
    """Get the [key, value] pairs.

    Args:
        data: Dictionary to use.
    """
    return [[key, value] for key, value in data.items()]


def from_items(pairs: list) -> dict:
    """Make a dictionary of [key, value] pairs.

    Args:
        pairs: List of [key, value] pairs.
    """
    return {key: value for key, value in pairs}


def merge(a: dict, b: dict) -> dict:
    """Combine two dictionaries, the values of b win.

    Args:
        a: First dictionary.
        b: Second dictionary, its values win.
    """
    return {**a, **b}


def is_empty(data: dict) -> bool:
    """Check if the dictionary has no keys.

    Args:
        data: Dictionary to use.
    """
    return not data


def invert(data: dict) -> dict:
    """Swap the keys and values.

    Args:
        data: Dictionary to use.
    """
    return {value: key for key, value in data.items()}


def pick(data: dict, selected_keys: list) -> dict:
    """Get a dictionary of only the given keys that exist.

    Args:
        data: Dictionary to use.
        selected_keys: Keys to keep.
    """
    return {key: data[key] for key in selected_keys if key in data}
