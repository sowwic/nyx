import typing

from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxEnvironmentConfigValues(NyxBaseConfigValues):
    """Config values of the environment variables set for the application."""

    source_file: str = Field(default="")
    """Environment file (`NAME=value` lines) to load. Nothing is loaded if empty."""
    vars_overrides: dict[str, str] = Field(default_factory=dict)
    """Variables set after the source file, so they win over it.

    `$NAME` references in a value are expanded. A removed variable stays set until the
    application is restarted.
    """

    def pre_deserialize(self, data: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Move variables saved straight under `environment` to `vars_overrides`.

        Args:
            data: raw values of the section.

        Returns:
            dict[str, Any]: values with every key that is not an option of the
                section taken as a variable.
        """
        options = {"source_file", "vars_overrides"}
        old_variables = {
            name: value for name, value in data.items() if name not in options
        }
        if not old_variables:
            return data
        migrated = {name: value for name, value in data.items() if name in options}
        migrated["vars_overrides"] = {
            **old_variables,
            **migrated.get("vars_overrides", {}),
        }
        return migrated
