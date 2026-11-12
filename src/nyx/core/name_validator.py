import re
import logging

LOGGER = logging.getLogger(__name__)


class NameValidator:
    """Validates and sanitizes stage object names."""

    STAGE_OBJECT_VALID_PATTERN = re.compile(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*")

    @classmethod
    def get_valid_stage_object_name(cls, name: str) -> str:
        """Convert a name into a valid stage object name.

        Special characters are dropped and whitespace becomes underscores.

        Args:
            name (str): name to sanitize.

        Returns:
            str: valid name (unchanged if already valid).
        """
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
        """Check whether a name is a valid stage object name.

        Args:
            name (str): name to test.

        Returns:
            bool: is valid.
        """
        return bool(cls.STAGE_OBJECT_VALID_PATTERN.fullmatch(name))

    @staticmethod
    def to_address_name(display_name: str) -> str:
        """Derive the address name of a display name.

        The address is what paths are built from: lowercase letters and digits, with
        runs of anything else becoming a single underscore.

        Args:
            display_name (str): name as the user typed it, like "My cool node".

        Returns:
            str: address name, like "my_cool_node". Empty if nothing usable is left.
        """
        return re.sub(r"[^a-z0-9]+", "_", display_name.lower()).strip("_")

    @staticmethod
    def humanize(address_name: str) -> str:
        """Make a display name out of an address name.

        Args:
            address_name (str): address name, like "client_name".

        Returns:
            str: words with their first letter capitalized, like "Client Name".
        """
        words = re.split(r"[_\s]+", address_name.strip())
        return " ".join(word[:1].upper() + word[1:] for word in words if word)
