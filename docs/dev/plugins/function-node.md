# New function node

The quickest way to add a node: write a normal Python function and register it. Nyx
generates a node class for it (a `FunctionNode` subclass) with a flow component, one
value component per parameter and a `return` component.

## One function

```python
# studio_tools/nyx_plugin.py
import typing

from nyx.api.v1 import NyxPlugin, NyxPluginManager


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Limit a number to a range.

    Args:
        value: The number to limit.
        low: Smallest result.
        high: Largest result.

    Returns:
        The number, not below low and not above high.
    """
    return max(low, min(high, value))


@NyxPluginManager.register_plugin()
class StudioFunctions(NyxPlugin):
    @classmethod
    def get_type_id(cls) -> str:
        return "StudioFunctions"

    @classmethod
    def get_palette_name(cls) -> str:
        return "Studio Functions"

    @classmethod
    def initialize(cls) -> typing.Self:
        plugin = cls()
        plugin.contents.register_function_node(
            clamp, type_id="function:studio.clamp", tags=["math"]
        )
        return plugin
```

`register_function_node(func, type_id=None, tags=())`:

| Argument | Meaning |
| --- | --- |
| `func` | A named function. Lambdas and other callables without a name raise `TypeError`. |
| `type_id` | Node type id. Defaults to `function:<module>.<qualified name>`, which depends on where the function is defined: give an explicit id to keep saved stages working when you move code. |
| `tags` | Tags besides the automatic `function` tag. |

It returns the generated node class and raises `ValueError` if the plugin already
registered a node with that type id.

## A whole module

`register_function_module(module, namespace)` registers every public function of a
module, as `function:<namespace>.<function name>`, tagged with the namespace. This is how
the built-in plugins are written (`nyx/plugins/functions/math_operations`):

```python
# math_operations/nyx_plugin.py
from . import operations

plugin.contents.register_function_module(operations, namespace="math")
```

Public means: defined in that module (not imported into it) and not starting with an
underscore. Put helpers in other modules or prefix them with `_`.

## What is generated

| From the function | Becomes |
| --- | --- |
| Name | The default node name, and the display name with underscores replaced by spaces and capitalized (`floor_divide` becomes "Floor Divide"). |
| Type hints of the parameters | The datatype of each parameter component, see below. |
| Default values | The default and the initial value of the parameter component. |
| First paragraph of the docstring | The node description in the palette. |
| `Args:` section | The tooltips of the parameter components. |
| `Returns:` section (or the first line of the docstring) | The tooltip of the `return` component. |
| Return type hint | The datatype of the `return` component. |

`*args` and `**kwargs` are skipped (with a warning in the log). Positional-only
parameters are passed positionally, the others by keyword.

### Type hints choose the datatypes

The hint is looked up in the registry (`find_datatype_for_type`): `X | None` counts as
`X`, a generic like `list[int]` as `list`, and the first datatype registered for exactly
that Python type wins. No hint, or a type no datatype claims, gives `Object`, which links
to anything. Register your own datatype ([New datatype](datatype.md)) with a
`python_type` to have functions that use that type get properly colored plugs.

### What runs

The node is a flow node. When it executes it pulls every parameter, calls the function and
stores the result in `return` without evaluating it (so a string result isn't run as an
expression). An exception from the function fails the node like any other.

Values are cast to the datatype of the parameter component (see
[Datatypes](../../user/datatypes.md)).

## When a function is not enough

If you need more than the generated shape, for instance flow outputs, a scope or
per-run state, write a [node](node.md) by hand.
