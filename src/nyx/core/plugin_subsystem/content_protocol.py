from typing import Protocol, runtime_checkable


@runtime_checkable
class PluginContent(Protocol):
    PLUGIN_CONTENT_KIND: str
