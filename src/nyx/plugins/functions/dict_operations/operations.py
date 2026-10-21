"""Functions working with dictionaries. None of them changes the dictionary it gets."""

import typing


def make_dict(key: typing.Any, value: typing.Any) -> dict:
    """Make a dictionary of one key and its value."""
    return {key: value}


def length(data: dict) -> int:
    """Get the number of keys."""
    return len(data)


def get_value(data: dict, key: typing.Any, default: typing.Any = None) -> typing.Any:
    """Get the value of a key, the default if there is no such key."""
    return data.get(key, default)


def set_value(data: dict, key: typing.Any, value: typing.Any) -> dict:
    """Get a copy of the dictionary with a key set."""
    return {**data, key: value}


def remove_key(data: dict, key: typing.Any) -> dict:
    """Get a copy of the dictionary without a key."""
    return {k: v for k, v in data.items() if k != key}


def has_key(data: dict, key: typing.Any) -> bool:
    """Check if the dictionary has a key."""
    return key in data


def keys(data: dict) -> list:
    """Get the keys."""
    return list(data.keys())


def values(data: dict) -> list:
    """Get the values."""
    return list(data.values())


def items(data: dict) -> list:
    """Get the [key, value] pairs."""
    return [[key, value] for key, value in data.items()]


def from_items(pairs: list) -> dict:
    """Make a dictionary of [key, value] pairs."""
    return {key: value for key, value in pairs}


def merge(a: dict, b: dict) -> dict:
    """Combine two dictionaries, the values of b win."""
    return {**a, **b}


def is_empty(data: dict) -> bool:
    """Check if the dictionary has no keys."""
    return not data


def invert(data: dict) -> dict:
    """Swap the keys and values."""
    return {value: key for key, value in data.items()}


def pick(data: dict, selected_keys: list) -> dict:
    """Get a dictionary of only the given keys that exist."""
    return {key: data[key] for key in selected_keys if key in data}
