def to_camel_case(name: str) -> str:
    first, *rest = name.lower().split("_")
    return first + "".join(word.capitalize() for word in rest)


def enum_to_dict(enum_cls) -> dict[int, bytes]:
    return {
        member.value: to_camel_case(member.name).encode("utf-8") for member in enum_cls
    }
