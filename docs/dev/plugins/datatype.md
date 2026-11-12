# New datatype

A datatype tells Nyx what kind of value a component holds: how the plug is drawn, which
components it can link to, and how a value is converted. A datatype is **data, not a
class**: an instance of the frozen dataclass `Datatype`.

## A complete example

```python
# studio_tools/datatypes.py
from nyx.api.v1 import Datatype, GraphicsPlugShape


def cast_to_vector3(value) -> tuple[float, float, float]:
    """Convert a sequence of three numbers.

    Args:
        value: Anything that can be iterated for three numbers.

    Raises:
        ValueError: There aren't three values.

    Returns:
        The vector.
    """
    x, y, z = (float(each) for each in value)
    return (x, y, z)


VECTOR3 = Datatype(
    type_id="studio:vector3",
    display_name="Vector3",
    color="#FF8A5B",
    caster=cast_to_vector3,
    python_type=tuple,
    plug_shape=GraphicsPlugShape.TRIANGLE,
    default_factory=lambda: (0.0, 0.0, 0.0),
)
```

Register it in `initialize` and use it in a node:

```python
plugin.contents.datatypes = [VECTOR3]

# in a node's setup()
self.position_cpnt.set_datatype("studio:vector3")
```

A value component with that datatype now shows an orange triangle plug, starts at
`(0.0, 0.0, 0.0)`, and anything pulled into it through a link is cast with `cast_to_vector3`.

## Fields

| Field | Meaning |
| --- | --- |
| `type_id` | Unique id, `namespace:name`. Stored in stage files. |
| `display_name` | Name in the UI (the datatype selector). |
| `color` | Plug color as hex. |
| `caster` | Function that converts an evaluated value. **Must raise** when it can't; Nyx wraps the error in a `DatatypeCastError`. Defaults to returning the value as it is. |
| `python_type` | Exact Python type of the values. Used to infer the datatype of a value and to choose the datatype for a type hint of a function node. Leave `None` if there isn't one. |
| `plug_shape` | `GraphicsPlugShape`: `CIRCLE`, `TRIANGLE`, `PENTAGON`, `SQUARE`, `SQUARE_MATRIX`, `BARS`, `DIAMOND`. Circles are the default, pick another shape to tell types apart without color. |
| `default_factory` | Creates the starting value. Called for every new value, so mutable defaults aren't shared. Default gives `None`. |
| `is_wildcard` | Links to every datatype (but ones that ignore wildcards). |
| `ignores_wildcards` | Links only to itself and what `compatible_with` lists. Flow uses it. |
| `compatible_with` | `frozenset` of type ids it can link to besides itself. Declare it on both datatypes if the compatibility goes both ways, as Integer and Float do. |
| `selectable` | `False` hides it from the datatype selector. For datatypes that belong to one component type. |

The behavior, in detail:

- `accepts(other)` is what decides if a link is allowed: same id, or listed in
  `compatible_with`, then wildcards (unless one side ignores them), see
  [Datatypes](../../user/datatypes.md).
- `cast(value)` runs the caster and raises `DatatypeCastError` with a message including the
  value and the reason.
- `matches(value)` is true only for the **exact** type (`type(value) is python_type`), so a
  `bool` doesn't count as an `int`.

## Design advice

- **Be strict in the caster, loose in `compatible_with`.** The caster should refuse what
  it can't understand. The warning that follows names the component and the reason.
- **One Python type, one datatype.** `infer_datatype` and function node hints pick the first
  registered datatype for a Python type. If two plugins claim `tuple`, the one registered
  first wins. Use a distinct `python_type` (a small class) if your values need to be told
  apart.
- **Avoid wildcards.** Wildcards make links between unrelated things possible, which hides
  mistakes. Use `compatible_with` to name the few types you really want to interoperate with.
- **The value is saved as JSON.** A component writes its value to the stage file as JSON, so
  a tuple becomes a list there. Make the caster accept the shapes JSON gives (lists, dicts,
  strings, numbers). If the value is something else, the component type needs
  `serialize_value` and `deserialize_value`.
- **An unknown datatype becomes Object.** A stage saved with your datatype and opened
  without the plugin warns `Unknown datatype ...` and falls back to `Object`.

## Using a datatype in components

- In `setup()` of a node: `component.set_datatype("studio:vector3")`.
- For a new component type: return the id from `get_type_default_datatype()`, see
  [New component](component.md).
- In functions: annotate parameters with the Python type (`def move(offset: tuple): ...`).
  See [New function node](function-node.md).
