"""Functions working with regular expressions."""

import re


def _flags(ignore_case: bool, multiline: bool) -> int:
    return (re.IGNORECASE if ignore_case else 0) | (re.MULTILINE if multiline else 0)


def is_match(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> bool:
    """Check if a regular expression matches anywhere in a string.

    Args:
        text: Text to search.
        pattern: Regular expression.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    return re.search(pattern, text, _flags(ignore_case, multiline)) is not None


def is_full_match(text: str, pattern: str, ignore_case: bool = False) -> bool:
    """Check if a regular expression matches the whole string.

    Args:
        text: Text to search.
        pattern: Regular expression.
        ignore_case: Treat upper and lower case as the same.
    """
    return re.fullmatch(pattern, text, _flags(ignore_case, False)) is not None


def find_first(
    text: str,
    pattern: str,
    group: int = 0,
    ignore_case: bool = False,
    multiline: bool = False,
) -> str:
    """Get the first match, or one of its groups, empty if there is no match.

    Args:
        text: Text to search.
        pattern: Regular expression.
        group: Number of the group, 0 for the whole match.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    match = re.search(pattern, text, _flags(ignore_case, multiline))
    if match is None:
        return ""
    return match.group(group) or ""


def find_all(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> list:
    """Get all matches. With groups in the pattern, get what the groups matched.

    Args:
        text: Text to search.
        pattern: Regular expression.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    return re.findall(pattern, text, _flags(ignore_case, multiline))


def groups(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> list:
    """Get what the groups of the first match matched, empty if there is no match.

    Args:
        text: Text to search.
        pattern: Regular expression.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    match = re.search(pattern, text, _flags(ignore_case, multiline))
    return [] if match is None else list(match.groups())


def count_matches(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> int:
    """Count the matches of a regular expression.

    Args:
        text: Text to search.
        pattern: Regular expression.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    return len(list(re.finditer(pattern, text, _flags(ignore_case, multiline))))


def replace(
    text: str,
    pattern: str,
    replacement: str,
    ignore_case: bool = False,
    multiline: bool = False,
) -> str:
    """Replace every match, \\1 in the replacement is the first group.

    Args:
        text: Text to search.
        pattern: Regular expression.
        replacement: Text to put in place, \1 is the first group.
        ignore_case: Treat upper and lower case as the same.
        multiline: ^ and $ match at every line.
    """
    return re.sub(pattern, replacement, text, flags=_flags(ignore_case, multiline))


def split(text: str, pattern: str, ignore_case: bool = False) -> list:
    """Split a string at every match.

    Args:
        text: Text to search.
        pattern: Regular expression to split at.
        ignore_case: Treat upper and lower case as the same.
    """
    return re.split(pattern, text, flags=_flags(ignore_case, False))


def escape(text: str) -> str:
    """Escape the characters of a string that have a meaning in a pattern.

    Args:
        text: Text to search.
    """
    return re.escape(text)


def is_valid_pattern(pattern: str) -> bool:
    """Check if a string is a valid regular expression.

    Args:
        pattern: Regular expression.
    """
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True
