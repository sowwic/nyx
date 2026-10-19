def to_camel_case(name: str) -> str:
    """Convert a snake or upper case name to camel case.

    Args:
        name (str): name to convert.

    Returns:
        str: camel case name.
    """
    first, *rest = name.lower().split("_")
    return first + "".join(word.capitalize() for word in rest)


def enum_to_dict(enum_cls) -> dict[int, bytes]:
    """Map enum values to camel case member names, as expected for Qt role names.

    Args:
        enum_cls: enum class.

    Returns:
        dict[int, bytes]: utf-8 encoded names by value.
    """
    return {
        member.value: to_camel_case(member.name).encode("utf-8") for member in enum_cls
    }
