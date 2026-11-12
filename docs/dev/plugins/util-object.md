# New util object

A **util object** is something that sits in the graph of a node but isn't part of the
execution: notes and groups are util objects. It has a position and a size, and
properties of its own. It has no components and no links.

A util object needs two classes:

1. the **util object** (`UtilObject` subclass): the data, which is saved with the stage,
2. a **graphics object** (a `QGraphicsItem`) that draws it, see
   [New graphics object](graphics-object.md).

## A complete example: a checklist

```python
# studio_tools/util_objects/checklist.py
import typing
from collections import OrderedDict

from nyx.api.v1 import UtilObject, CoreGraphicsObjects


class ChecklistObject(UtilObject):
    """A list of to-do items drawn next to the nodes."""

    DEFAULT_SIZE = (240.0, 160.0)

    ITEMS_KEY = "items"

    def __init__(self, uuid=None):
        """Initialize ChecklistObject.

        Args:
            uuid (UUID | str | None): object uuid. Generated if omitted.
        """
        super().__init__(uuid=uuid)
        self.items: list[str] = []

    @classmethod
    def get_type_id(cls) -> str:
        """str: util object type id."""
        return "studio:checklist"

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Checklist"

    @classmethod
    def get_description(cls) -> str:
        """str: what the type does."""
        return "A list of to-do items."

    @classmethod
    def get_graphics_object_id(cls) -> str | None:
        """str | None: id of the graphics object drawing the type."""
        return "studio.checklist"

    def serialize_properties(self) -> OrderedDict[str, typing.Any]:
        """OrderedDict[str, typing.Any]: position, size and the items."""
        properties = super().serialize_properties()
        properties[self.ITEMS_KEY] = list(self.items)
        return properties

    def apply_properties(self, properties: typing.Mapping[str, typing.Any]) -> None:
        """Set position, size and the items.

        Args:
            properties (typing.Mapping[str, typing.Any]): values by name.
        """
        super().apply_properties(properties)
        if self.ITEMS_KEY in properties:
            self.items = [str(item) for item in properties[self.ITEMS_KEY]]
```

Register: `plugin.contents.util_objects = [ChecklistObject]`.

## The contract

| Member | Purpose |
| --- | --- |
| `get_type_id()` | Unique id, `namespace:name`. |
| `get_type_display_name()`, `get_description()` | UI texts. |
| `get_graphics_object_id()` | The id of the graphics object that draws the type. It must be registered by a plugin (or be a built-in one such as `CoreGraphicsObjects.NOTE`). |
| `DEFAULT_SIZE`, `MIN_SIZE` | Size a new object gets, and the smallest size it can be resized to. |
| `position`, `size`, `rect` | Geometry in the scene of the owning node. The size is never smaller than `MIN_SIZE`. |
| `serialize_properties()` | Returns **all** state that can change, as JSON values. Call `super()` and add your own. |
| `apply_properties(properties)` | Sets the state from such a mapping. Missing names are left unchanged. |
| `node`, `stage`, `path`, `is_locked` | The owner and the state: `is_locked` is true inside a locked scope (the content of a reference). |

`serialize_properties` and `apply_properties` are the **whole contract of state**. They are
used for saving, loading, copy and paste, and by the undo commands, which store the
properties before and after a change and apply them on undo and redo. If a piece of state
isn't in them, it is lost on save and can't be undone. Keep attributes (`self.items`) plain
and let the properties mirror them.

## Creating and changing util objects

The editor offers *Create note* and *Create group* in the context menu of the graph. Other
util objects aren't offered in the UI by default: a plugin creates them from code,
or from its own action, with a command (so undo works):

```python
from nyx.api.v1 import commands

command = commands.CreateUtilObjectCommand(
    stage=stage,
    type_id="studio:checklist",
    node=parent_node,                  # defaults to the stage root
    position=(120.0, 40.0),
    properties={"items": ["Export", "Review"]},
)
stage.push_command(command)
checklist = command.result_object
```

To change one, push a `SetUtilObjectPropertiesCommand` with the new properties by object:

```python
stage.push_command(
    commands.SetUtilObjectPropertiesCommand(
        stage, {checklist: {"items": ["Export", "Review", "Publish"]}}, text="Edit checklist"
    )
)
```

The graphics object does that for you when the user moves or resizes it, see below.
`DeleteUtilObjectCommand` removes one.

## Saving

Util objects are written to the `util_objects` list of their node, with their type id and
their properties (`serialize_properties`).

## Rules

- Util objects never take part in execution. If something has to run, make it a node.
- They don't have components, so values can't be linked to them. To show data from the
  graph, use a node.
- A color, text or title is a property of the object, not a config option. Defaults can come
  from the config with `nyx.core.util_object.get_configured_color` as the note does.
