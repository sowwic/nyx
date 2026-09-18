from typing import Protocol, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class IRegistryEntry(Protocol):
    @classmethod
    @abstractmethod
    def get_type_id(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_type_display_name(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_tags(cls) -> set[str]: ...
