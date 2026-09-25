import re
import logging

LOGGER = logging.getLogger(__name__)


class NameValidator:
    STAGE_OBJECT_VALID_PATTERN = re.compile(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*")

    @classmethod
    def get_valid_stage_object_name(cls, name: str) -> str:
        if cls.is_valid_object_name(name):
            return name

        new_name = re.sub(
            r"[^A-Za-z0-9_\s]", "", name
        )  # drop special chars, keep underscores/whitespace
        new_name = re.sub(
            r"\s+", "_", new_name.strip()
        )  # whitespace runs -> single underscore
        new_name = re.sub(r"_+", "_", new_name).strip("_")  # collapse/trim underscores

        LOGGER.warning("Removed invalid characters from %s result: %s", name, new_name)
        return new_name

    @classmethod
    def is_valid_object_name(cls, name: str) -> bool:
        return bool(cls.STAGE_OBJECT_VALID_PATTERN.fullmatch(name))
