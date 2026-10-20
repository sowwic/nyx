from json_config.api import ConfigValues
from pydantic import ConfigDict


class NyxBaseConfigValues(ConfigValues):
    """Base of the nyx config values.

    The docstring under a field is its description, so write it right below the field.
    """

    model_config = ConfigDict(use_attribute_docstrings=True)
