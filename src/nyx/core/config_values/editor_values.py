import pathlib

from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxEditorBehaviourConfigValues(NyxBaseConfigValues):
    """Editor behaviour config values."""

    new_stage_on_launch: bool = Field(default=True)
    """Create an empty stage at startup."""


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
