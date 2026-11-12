"""Functions working with lists. None of them changes the list it gets."""

import typing


def make_list(a: typing.Any, b: typing.Any) -> list:
    """Make a list of two values.

    Args:
        a: First item.
        b: Second item.
    """
    return [a, b]


def length(items: list) -> int:
    """Get the number of items.

    Args:
        items: List to use.
    """
    return len(items)


def get_item(items: list, index: int) -> typing.Any:
    """Get the item at an index, negative ones count from the end.

    Args:
        items: List to use.
        index: Position in the list, negative counts from the end.
    """
    return items[index]


def first(items: list) -> typing.Any:
    """Get the first item.

    Args:
        items: List to use.
    """
    return items[0]


def last(items: list) -> typing.Any:
    """Get the last item.

    Args:
        items: List to use.
    """
    return items[-1]


def append(items: list, item: typing.Any) -> list:
    """Get a copy of the list with an item added at the end.

    Args:
        items: List to use.
        item: Item to use.
    """
    return [*items, item]


def insert(items: list, index: int, item: typing.Any) -> list:
    """Get a copy of the list with an item inserted at an index.

    Args:
        items: List to use.
        index: Position to insert at.
        item: Item to use.
    """
    result = list(items)
    result.insert(index, item)
    return result


def remove_at(items: list, index: int) -> list:
    """Get a copy of the list without the item at an index.

    Args:
        items: List to use.
        index: Position in the list, negative counts from the end.
    """
    result = list(items)
    del result[index]
    return result


def remove_item(items: list, item: typing.Any) -> list:
    """Get a copy of the list without the first occurrence of an item.

    Args:
        items: List to use.
        item: Item to use.
    """
    result = list(items)
    result.remove(item)
    return result


def set_item(items: list, index: int, item: typing.Any) -> list:
    """Get a copy of the list with the item at an index replaced.

    Args:
        items: List to use.
        index: Position in the list, negative counts from the end.
        item: Item to use.
    """
    result = list(items)
    result[index] = item
    return result


def extend(items: list, other: list) -> list:
    """Get a list of the items followed by the items of another list.

    Args:
        items: List to start with.
        other: List to add.
    """
    return [*items, *other]


def slice_list(items: list, start: int, end: int = -1) -> list:
    """Get the items from start up to end, the rest of the list if end is -1.

    Args:
        items: List to use.
        start: Index of the first item.
        end: Index to stop before, -1 for the end.
    """
    return items[start:] if end == -1 else items[start:end]


def index_of(items: list, item: typing.Any) -> int:
    """Get the index of the first occurrence of an item, -1 if there is none.

    Args:
        items: List to use.
        item: Item to use.
    """
    return items.index(item) if item in items else -1


def count(items: list, item: typing.Any) -> int:
    """Count the occurrences of an item.

    Args:
        items: List to use.
        item: Item to use.
    """
    return items.count(item)


def contains(items: list, item: typing.Any) -> bool:
    """Check if the list has an item.

    Args:
        items: List to use.
        item: Item to use.
    """
    return item in items


def is_empty(items: list) -> bool:
    """Check if the list has no items.

    Args:
        items: List to use.
    """
    return not items


def reverse(items: list) -> list:
    """Get the items in reverse order.

    Args:
        items: List to use.
    """
    return items[::-1]


def sort(items: list, descending: bool = False) -> list:
    """Get the items in order.

    Args:
        items: List to use.
        descending: Biggest first.
    """
    return sorted(items, reverse=descending)


def unique(items: list) -> list:
    """Get the items without duplicates, in order of first appearance.

    Args:
        items: List to use.
    """
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def minimum(items: list) -> typing.Any:
    """Get the smallest item.

    Args:
        items: List to use.
    """
    return min(items)


def maximum(items: list) -> typing.Any:
    """Get the biggest item.

    Args:
        items: List to use.
    """
    return max(items)


def total(items: list) -> float:
    """Add up the items.

    Args:
        items: List to use.
    """
    return sum(items)


def flatten(items: list) -> list:
    """Get the items of the lists in a list as one list.

    Args:
        items: List to use.
    """
    return [element for item in items for element in item]


def repeat_list(items: list, count: int) -> list:
    """Repeat the items a number of times.

    Args:
        items: Items to repeat.
        count: How many times to repeat the items.
    """
    return items * count


def number_range(start: int, stop: int, step: int = 1) -> list:
    """Get the integers from start up to, not including, stop.

    Args:
        start: First number.
        stop: Number to stop before.
        step: Difference between numbers.
    """
    return list(range(start, stop, step))


def zip_lists(a: list, b: list) -> list:
    """Pair up the items of two lists, as long as the shorter one.

    Args:
        a: First list.
        b: Second list.
    """
    return [list(pair) for pair in zip(a, b)]
