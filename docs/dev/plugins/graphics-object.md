# New graphics object

A **graphics object** is the `QGraphicsItem` that draws something of a stage in the graph
view. Nyx keeps the model (nodes, components, links, util objects) apart from how it is
drawn, and joins them by an id:

```text
stage object type                         graphics object
   get_graphics_object_id()  ──id──▶  NYX_REGISTRY.graphics_objects[id]  ──▶  item
```

The editor builds the item with `create_graphics_object(stage_object, ...)`: it reads
`type(stage_object).get_graphics_object_id()`, finds the class in the registry and calls it.
A type that returns `None` isn't drawn; an id with no registered class logs
`Unknown graphics object ...`.

| Id | Drawn by | Registered by |
| --- | --- | --- |
| `core.node` (`CoreGraphicsObjects.NODE`) | `GraphicsNode` | the editor, always |
| `core.plug` (`PLUG`) | `GraphicsPlug` | the editor, always |
| `core.link` (`LINK`) | `GraphicsLink` | the editor, always |
| `core.note` (`NOTE`) | `GraphicsNote` | the `NyxStdlib` plugin |
| `core.group` (`GROUP`) | `GraphicsGroup` | the `NyxStdlib` plugin |

Most plugins never write one: nodes and components use the standard node and plug
items, and are customized through their data (names, datatypes, plug shapes, QML
editors). Write a graphics object for a new [util object](util-object.md).

!!! warning
    Graphics objects belong to the editor (`nyx.editor`), which is **not** part of
    `nyx.api.v1` and isn't versioned like it. The base class lives in
    `nyx.editor.graphics.graphics_util_object`. The standard library does the same
    (`nyx/stdlib/graphics_objects`), use it as the reference and expect to adjust when the
    editor internals change.

## A complete example: the checklist

```python
# studio_tools/graphics_objects/checklist.py
from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.graphics.graphics_util_object import GraphicsUtilObject
from nyx.editor.graphics.level_of_detail import LevelOfDetail


class GraphicsChecklist(GraphicsUtilObject):
    """Draws a ChecklistObject as a card with its items."""

    RADIUS = 6.0
    PADDING = 8.0
    Z_VALUE = 0.4        # below nodes, notes are at 0.5

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the graphics object is registered with."""
        return "studio.checklist"

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None = None,
    ) -> None:
        """Draw the card and its items.

        Args:
            painter (QtGui.QPainter): painter.
            option (QtWidgets.QStyleOptionGraphicsItem): style options.
            widget (QtWidgets.QWidget | None): painted widget.
        """
        lod = LevelOfDetail.from_painter(painter, text_size=10.0)
        rect = QtCore.QRectF(QtCore.QPointF(), self.item_size)
        painter.setPen(QtGui.QPen(self.color.darker(160), 1.0))
        painter.setBrush(self.color)
        painter.drawRoundedRect(rect, self.RADIUS, self.RADIUS)
        if lod.shows_text:
            painter.setPen(QtGui.QColor("#202020"))
            text = "\n".join(f"- {item}" for item in self.util_object.items)
            painter.drawText(
                rect.adjusted(self.PADDING, self.PADDING, -self.PADDING, -self.PADDING),
                int(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap),
                text,
            )
        self.paint_selection(painter, self.RADIUS)

    def edit(self) -> None:
        """Ask for the items, one per line."""
        text, accepted = QtWidgets.QInputDialog.getMultiLineText(
            self.parent_widget(), "Checklist", "Items:", "\n".join(self.util_object.items)
        )
        if accepted:
            self.push_properties({"items": text.splitlines()}, "Edit checklist")
```

The util object returns this id from `get_graphics_object_id()`
(`"studio.checklist"` in [New util object](util-object.md)), and the plugin lists the class:

```python
plugin.contents.util_objects = [ChecklistObject]
plugin.contents.graphics_objects = [GraphicsChecklist]
```

`color` reads a `color` attribute of the util object; the example has none, so it draws gray.
Add a `color` property (serialized like the note's) for color presets and the color menu.

## What `GraphicsUtilObject` does for you

| Member | Purpose |
| --- | --- |
| `__init__(util_object, parent=None)` | Called by the factory. The item is selectable, takes hover events and calls `refresh`. |
| `util_object`, `uuid` | The model object and its id. |
| `refresh()` | Re-reads size and position from the model, and updates the item. Called when the model changed (undo, redo, paste). Override and call `super()` when you cache anything. |
| `item_size`, `color`, `is_editable` | Current size (follows the mouse while resizing), color and whether the object isn't locked. |
| `paint(...)` | **You implement it.** Draw into `QRectF(QPointF(), item_size)`. |
| `paint_selection(painter, radius)` | Draws the selection outline and the resize grip. Call it last. |
| `edit()` | Called on double click. Implement it to edit the content. |
| `push_properties(properties, text)` | Pushes a `SetUtilObjectPropertiesCommand`, so the change is undoable. **Never change the util object directly.** |
| `set_color(color)` | Pushes a color change. |
| `parent_widget()` | A widget to parent dialogs to. |
| `Z_VALUE`, `COLOR_PRESETS`, `HANDLE_SIZE` | Class attributes to tune. |

Moving and resizing with the mouse is built in: they push commands that set `position` and
`size`, and objects in a locked scope (the contents of a reference) can't be moved.

### Level of detail

`LevelOfDetail.from_painter(painter, text_size=..., shape_size=...)` tells how much is
worth drawing at the current zoom: `MINIMAL` (a flat placeholder), `NO_TEXT` (shapes only)
or `FULL`. Check `lod.shows_text` and `lod.shows_shapes` before expensive drawing, so big
graphs stay fast when zoomed out.

## Registering

- `NyxPluginContents.graphics_objects` takes classes with a `get_type_id` **classmethod**.
  The registry skips (and logs) an id that is already registered.
- Graphics objects are registered when the plugin content is, so they are available when the
  editor builds its first scene.
- Built-in ids are kept when the registry is rebuilt; plugin ones are dropped and
  registered again from the enabled plugins.

## Drawing nodes, plugs or links differently

Node and component types return an id from `get_graphics_object_id()` too (`core.node` and
`core.plug` by default), so a type can point at a different registered item. The standard
items are `GraphicsNode`, `GraphicsPlug` and `GraphicsLink` in `nyx.editor.graphics`. They
are tied closely to the scene, so subclass them and override small pieces instead of writing
an item from scratch. This isn't used by any plugin in the repository yet.
