# New component

A component is a plug on a node: it holds a value, can be linked, and can run something
when its node executes. Add a new component *type* when several nodes need the same kind of
plug with its own behavior or editor. For a value that only needs another datatype, use a
Value component with that datatype instead ([New datatype](datatype.md)).

## A complete example

A component that holds a color as `#RRGGBB` text and complains about anything else:

```python
# studio_tools/components/color.py
import re

from nyx.api.v1 import (
    NodeComponent,
    CoreNodeComponents,
    CoreDatatypes,
    NodeComponentFlag,
)

HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


class ColorComponent(NodeComponent):
    """Component holding a color as #RRGGBB."""

    DEFAULT_NAME = "color"
    EDITOR_QML = "ColorComponentItem"   # see "New QML for a component"

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return "studio:color"

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Color"

    @classmethod
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return "Holds a color as #RRGGBB."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"value"}

    @classmethod
    def get_type_default_value(cls) -> str:
        """str: initial value of new components."""
        return "#ffffff"

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: the color is kept as text."""
        return CoreDatatypes.STRING

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: flags new components start with."""
        return NodeComponentFlag.EDITABLE | NodeComponentFlag.LITERAL

    @classmethod
    def get_type_enforced_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: always literal, text is never evaluated as an expression."""
        return NodeComponentFlag.LITERAL

    def evaluate(self):
        """Mark the component as invalid when the value isn't a color."""
        value = self.pull_value()
        self.invalid_reason = (
            "" if isinstance(value, str) and HEX_COLOR.fullmatch(value) else
            f"Not a #RRGGBB color: {value!r}"
        )
```

Register it with `plugin.contents.node_components = [ColorComponent]`, and use it from a
node with `self.components_model.create_component("studio:color")`. Users can also add it to
any node from the editor (the "add component" palette lists every registered
component type).

## What a component class defines

### Class attributes

| Attribute | Purpose |
| --- | --- |
| `DEFAULT_NAME` | Address name new components start with. |
| `EDITOR_QML` | Name of the QML file that edits the component, without extension, see [New QML for a component](component-qml.md). Left empty the generic item is used. |
| `VALUE_STORAGE_CLS` | `ValueStorage` subclass that decides how the value is set, evaluated, cast and displayed. Override it to change evaluation (for instance never `eval`, or parse your own syntax). |

### Class methods (the type)

| Method | Purpose |
| --- | --- |
| `get_type_id()` | Unique id stored in files, `namespace:name`. |
| `get_type_display_name()` | Name in the UI. Defaults to the class name. |
| `get_type_icon()` | Resource path of the icon. |
| `get_description()`, `get_tags()` | Palette text and search tags. |
| `get_type_default_value()` | Initial value. |
| `get_type_default_datatype()` | Datatype id new components are hinted with. Default `core:object`. |
| `get_type_default_flags()` | `NodeComponentFlag` set on new components. |
| `get_type_enforced_flags()` | Flags every component of the type has, also when an old file is loaded. Use for rules of the type. |
| `get_default_expanded_state()` | Whether new components start expanded in the node. |
| `get_link_width_multiplier()` | Thickness of the links coming from the component. |
| `get_graphics_object_id()` | Id of the graphics item drawing the plug. Defaults to the standard plug. |

### Instance hooks

| Method | Called |
| --- | --- |
| `evaluate()` | While the node evaluates its components, after the value was evaluated and cast. |
| `execute()` | While the node executes its components. Not called for static or inactive components. Script components run their file here. |
| `evaluation_hook()`, `execution_hook()` | The wrappers that clear the cache, skip inactive and static components, and call the two above. Override only to change those rules. |

Everything in the [node](node.md) properties table applies to components: `readable`,
`writable`, `is_editable`, `is_literal`, `is_static`, `set_datatype`, `pull_value`,
`push_value`.

## Behavior to know about

- **The value is one of three**: raw (as set), cached (evaluated) and display (text). Read
  with `pull_value()`, which follows links; `raw_value` and `cached_value` read this
  component's own.
- **`invalid_reason`** marks a component as not usable and shows the reason in the UI. It is
  not saved. Set it back to `""` when the problem is gone.
- **Flags that are static** (like File, which sets `STATIC | EDITABLE`) are skipped when the
  node executes its components: the value is only data.
- **Serialization**: type id, name, value, default value, datatype, flags and note are
  saved. Override `serialize_value` / `deserialize_value` when the value isn't plain JSON
  (a Python object, a set, a class).
- **The plugin owns the type**: a stage saved with your component can only be opened with
  your plugin loaded. Keep the type id stable.

## Adding a component to a node in code

```python
component = self.components_model.create_component("studio:color")
component.name = "tint"
component.writable = True
self.components_model.add_component(component)
```

Or from a command: `commands.AddNodeComponentCommand(...)`, which supports undo.
