"""Text functions."""


def concatenate(a: str, b: str) -> str:
    """Join two strings.

    Args:
        a: Text that comes first.
        b: Text that comes second.
    """
    return a + b


def join(items: list, separator: str = ", ") -> str:
    """Join the items of a list into a string, put the separator between them.

    Args:
        items: Items to join, they are turned into text.
        separator: Text put between the items.
    """
    return separator.join(str(item) for item in items)


def split(text: str, separator: str = " ") -> list:
    """Split a string into a list at every separator.

    Args:
        text: Text to use.
        separator: Text to split at.
    """
    return text.split(separator)


def replace(text: str, old: str, new: str) -> str:
    """Replace every occurrence of old with new.

    Args:
        text: Text to use.
        old: Text to look for.
        new: Text to put in its place.
    """
    return text.replace(old, new)


def format_text(template: str, values: dict) -> str:
    """Fill the {names} of a template with the values of a dictionary.

    Args:
        template: Text with {names} to fill.
        values: Dictionary of the values for the names.
    """
    return template.format(**values)


def to_upper(text: str) -> str:
    """Convert a string to upper case.

    Args:
        text: Text to use.
    """
    return text.upper()


def to_lower(text: str) -> str:
    """Convert a string to lower case.

    Args:
        text: Text to use.
    """
    return text.lower()


def to_title(text: str) -> str:
    """Capitalize the first letter of every word.

    Args:
        text: Text to use.
    """
    return text.title()


def strip(text: str, characters: str = "") -> str:
    """Remove characters from both ends, whitespace if none are given.

    Args:
        text: Text to use.
        characters: Characters to remove, whitespace if empty.
    """
    return text.strip(characters or None)


def starts_with(text: str, prefix: str) -> bool:
    """Check if a string starts with a prefix.

    Args:
        text: Text to use.
        prefix: Beginning to look for.
    """
    return text.startswith(prefix)


def ends_with(text: str, suffix: str) -> bool:
    """Check if a string ends with a suffix.

    Args:
        text: Text to use.
        suffix: Ending to look for.
    """
    return text.endswith(suffix)


def contains(text: str, part: str) -> bool:
    """Check if a string contains another one.

    Args:
        text: Text to use.
        part: Text to look for.
    """
    return part in text


def find(text: str, part: str) -> int:
    """Get the index of the first occurrence of a part, -1 if there is none.

    Args:
        text: Text to use.
        part: Text to look for.
    """
    return text.find(part)


def length(text: str) -> int:
    """Get the number of characters in a string.

    Args:
        text: Text to use.
    """
    return len(text)


def substring(text: str, start: int, end: int = -1) -> str:
    """Get the characters from start up to end, the rest of the string if end is -1.

    Args:
        text: Text to use.
        start: Index of the first character.
        end: Index to stop before, -1 for the end.
    """
    return text[start:] if end == -1 else text[start:end]


def repeat(text: str, count: int) -> str:
    """Repeat a string a number of times.

    Args:
        text: Text to use.
        count: How many times to repeat the text.
    """
    return text * count


def pad_left(text: str, width: int, fill: str = " ") -> str:
    """Add fill characters on the left until the string is width long.

    Args:
        text: Text to use.
        width: Length the text should have.
        fill: Character to add.
    """
    return text.rjust(width, fill)


def pad_right(text: str, width: int, fill: str = " ") -> str:
    """Add fill characters on the right until the string is width long.

    Args:
        text: Text to use.
        width: Length the text should have.
        fill: Character to add.
    """
    return text.ljust(width, fill)


def to_int(text: str) -> int:
    """Convert a string to an integer.

    Args:
        text: Text to use.
    """
    return int(text)


def to_float(text: str) -> float:
    """Convert a string to a float.

    Args:
        text: Text to use.
    """
    return float(text)


def to_string(value: object) -> str:
    """Convert any value to a string.

    Args:
        value: Any value.
    """
    return str(value)
