from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxBridgeConfigValues(NyxBaseConfigValues):
    """Config values of the server external processes (Blender, Maya...) connect to."""

    enabled: bool = Field(default=True)
    """Start the server when the application launches. It can be started later."""
    host: str = Field(default="127.0.0.1")
    """Interface to listen on. Anyone holding the token can run code in a client."""
    port: int | None = Field(default=None, ge=0, le=65535)
    """Port to listen on. None tries the default port and the ones after it."""
    token: str = Field(default="")
    """Secret clients have to present. Random on every launch if empty."""
