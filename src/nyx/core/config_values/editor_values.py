import pathlib

from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues
from nyx.static.vars import DEFAULT_UNDO_LIMIT


class NyxEditorBehaviourConfigValues(NyxBaseConfigValues):
    """Editor behaviour config values."""

    new_stage_on_launch: bool = Field(default=True)
    """Create an empty stage at startup."""
    show_splash_screen: bool = Field(default=True)
    """Show a splash screen with the startup progress while the editor launches."""
    show_address_names: bool = Field(default=False)
    """Show the address names of nodes and components, which paths are made of, instead
    of their display names."""
    undo_limit: int = Field(default=DEFAULT_UNDO_LIMIT, ge=0)
    """Number of undoable steps each stage remembers, 0 for no limit.

    Applies to stages opened after the change. A step is one command, or one group of
    commands such as moving several items. Commands that delete or paste nodes keep a
    copy of them, so a high limit costs memory on big stages.
    """


class NyxEditorSessionConfigValues(NyxBaseConfigValues):
    """Editor session config values."""

    recent_files: list[str] = Field(default_factory=list)
    """Recently used stage files, most recent first."""
    max_recent_files: int = Field(default=10)
    """Number of recent files that are kept."""

    def pre_serialize(self) -> None:
        """Drop recent files that no longer exist before saving."""
        self.recent_files = [f for f in self.recent_files if pathlib.Path(f).is_file()]

    def pre_deserialize(self, data: dict) -> dict:
        """Drop recent files that no longer exist while loading.

        Args:
            data (dict): raw config data.

        Returns:
            dict: filtered copy of the data.
        """
        data = dict(data)
        data["recent_files"] = [
            f for f in data.get("recent_files", []) if pathlib.Path(f).is_file()
        ]
        return data
