from typing import Protocol, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class IRegistryEntry(Protocol):
    """Interface for classes stored in the Nyx registry."""

    @classmethod
    @abstractmethod
    def get_type_id(cls) -> str:
        """str: unique type id."""

    @classmethod
    @abstractmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""

    @classmethod
    @abstractmethod
    def get_tags(cls) -> set[str]:
        """set[str]: tags used for filtering."""
