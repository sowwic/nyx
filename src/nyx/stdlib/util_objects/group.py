import typing
from collections import OrderedDict

from nyx.api.v1 import CoreGraphicsObjects, CoreUtilObjects, UtilObject
from nyx.static.vars import DEFAULT_GROUP_COLOR


class GroupObject(UtilObject):
    """Titled frame drawn behind the nodes it surrounds, to keep them together."""

    GRAPHICS_OBJECT_ID = CoreGraphicsObjects.GROUP
    DEFAULT_SIZE = (360.0, 240.0)
    MIN_SIZE = (80.0, 60.0)
    DEFAULT_TITLE = "Group"
    DEFAULT_COLOR = DEFAULT_GROUP_COLOR

    TITLE_KEY = "title"
    COLOR_KEY = "color"

    def __init__(self, uuid=None):
        """Initialize GroupObject.

        Args:
            uuid (UUID | str | None): object uuid. Generated if omitted.
        """
        super().__init__(uuid=uuid)
        self.title: str = self.DEFAULT_TITLE
        self.color: str = self.DEFAULT_COLOR

    @classmethod
    def get_type_id(cls) -> str:
        """str: util object type id."""
        return CoreUtilObjects.GROUP

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Group"

    @classmethod
    def get_description(cls) -> str:
        """str: what the type does."""
        return "Titled frame around nodes. Moving it moves the nodes inside."

    def serialize_properties(self) -> OrderedDict[str, typing.Any]:
        """OrderedDict[str, typing.Any]: position, size, title and color."""
        properties = super().serialize_properties()
        properties[self.TITLE_KEY] = self.title
        properties[self.COLOR_KEY] = self.color
        return properties

    def apply_properties(self, properties: typing.Mapping[str, typing.Any]) -> None:
        """Set position, size, title and color.

        Args:
            properties (typing.Mapping[str, typing.Any]): values by name.
        """
        super().apply_properties(properties)
        if self.TITLE_KEY in properties:
            self.title = str(properties[self.TITLE_KEY])
        if self.COLOR_KEY in properties:
            self.color = str(properties[self.COLOR_KEY])
