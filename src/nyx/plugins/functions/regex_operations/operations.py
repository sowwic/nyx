"""Functions working with regular expressions."""

import re


def _flags(ignore_case: bool, multiline: bool) -> int:
    return (re.IGNORECASE if ignore_case else 0) | (re.MULTILINE if multiline else 0)


def is_match(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> bool:
    """Check if a regular expression matches anywhere in a string."""
    return re.search(pattern, text, _flags(ignore_case, multiline)) is not None


def is_full_match(text: str, pattern: str, ignore_case: bool = False) -> bool:
    """Check if a regular expression matches the whole string."""
    return re.fullmatch(pattern, text, _flags(ignore_case, False)) is not None


def find_first(
    text: str,
    pattern: str,
    group: int = 0,
    ignore_case: bool = False,
    multiline: bool = False,
) -> str:
    """Get the first match, or one of its groups, empty if there is no match."""
    match = re.search(pattern, text, _flags(ignore_case, multiline))
    if match is None:
        return ""
    return match.group(group) or ""


def find_all(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> list:
    """Get all matches. With groups in the pattern, get what the groups matched."""
    return re.findall(pattern, text, _flags(ignore_case, multiline))


def groups(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> list:
    """Get what the groups of the first match matched, empty if there is no match."""
    match = re.search(pattern, text, _flags(ignore_case, multiline))
    return [] if match is None else list(match.groups())


def count_matches(
    text: str, pattern: str, ignore_case: bool = False, multiline: bool = False
) -> int:
    """Count the matches of a regular expression."""
    return len(list(re.finditer(pattern, text, _flags(ignore_case, multiline))))


def replace(
    text: str,
    pattern: str,
    replacement: str,
    ignore_case: bool = False,
    multiline: bool = False,
) -> str:
    """Replace every match, \\1 in the replacement is the first group."""
    return re.sub(pattern, replacement, text, flags=_flags(ignore_case, multiline))


def split(text: str, pattern: str, ignore_case: bool = False) -> list:
    """Split a string at every match."""
    return re.split(pattern, text, flags=_flags(ignore_case, False))


def escape(text: str) -> str:
    """Escape the characters of a string that have a meaning in a pattern."""
    return re.escape(text)


def is_valid_pattern(pattern: str) -> bool:
    """Check if a string is a valid regular expression."""
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True
