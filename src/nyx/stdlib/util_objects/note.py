import typing
from collections import OrderedDict

from nyx.api.v1 import CoreGraphicsObjects, CoreUtilObjects, UtilObject
from nyx.static.vars import DEFAULT_NOTE_COLOR


class NoteObject(UtilObject):
    """Free text on a sticky note, to document what a node graph does."""

    GRAPHICS_OBJECT_ID = CoreGraphicsObjects.NOTE
    DEFAULT_SIZE = (220.0, 140.0)
    DEFAULT_COLOR = DEFAULT_NOTE_COLOR

    TEXT_KEY = "text"
    COLOR_KEY = "color"

    def __init__(self, uuid=None):
        """Initialize NoteObject.

        Args:
            uuid (UUID | str | None): object uuid. Generated if omitted.
        """
        super().__init__(uuid=uuid)
        self.text: str = ""
        self.color: str = self.DEFAULT_COLOR

    @classmethod
    def get_type_id(cls) -> str:
        """str: util object type id."""
        return CoreUtilObjects.NOTE

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Note"

    @classmethod
    def get_description(cls) -> str:
        """str: what the type does."""
        return "Sticky note with free text."

    def serialize_properties(self) -> OrderedDict[str, typing.Any]:
        """OrderedDict[str, typing.Any]: position, size, text and color."""
        properties = super().serialize_properties()
        properties[self.TEXT_KEY] = self.text
        properties[self.COLOR_KEY] = self.color
        return properties

    def apply_properties(self, properties: typing.Mapping[str, typing.Any]) -> None:
        """Set position, size, text and color.

        Args:
            properties (typing.Mapping[str, typing.Any]): values by name.
        """
        super().apply_properties(properties)
        if self.TEXT_KEY in properties:
            self.text = str(properties[self.TEXT_KEY])
        if self.COLOR_KEY in properties:
            self.color = str(properties[self.COLOR_KEY])
