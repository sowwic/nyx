from typing import Protocol, runtime_checkable
from abc import abstractmethod

from nyx.static.enums import PluginContentKind


@runtime_checkable
class PluginContent(Protocol):
    @classmethod
    @abstractmethod
    def get_type_id(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_type_display_name(cls) -> str: ...

    @classmethod
    @abstractmethod
    def get_plugin_content_kind(cls) -> PluginContentKind: ...

    @classmethod
    @abstractmethod
    def get_tags(cls) -> set[str]: ...
