# Datatypes

A **datatype** describes the kind of value a component holds. It decides three things:

- how the plug looks (color and shape), so you can read a graph at a glance,
- which components can be linked together,
- how a value is converted when it arrives in or is stored on a component.

Datatypes are provided by plugins and identified by a *type id* with a namespace, such as
`core:int`. The ones below are always available.

## Built-in datatypes

| Type id | Name | Python type | Default | Plug |
| --- | --- | --- | --- | --- |
| `core:object` | Object | any | `None` | blue square matrix |
| `core:type` | Type | `type` | `object` | purple circle |
| `core:bool` | Boolean | `bool` | `False` | red circle |
| `core:string` | String | `str` | `""` | orange circle |
| `core:int` | Integer | `int` | `0` | green-teal circle |
| `core:float` | Float | `float` | `0.0` | light green circle |
| `core:path` | Path | `pathlib.PurePosixPath` | none | light blue circle |
| `core:list` | List | `list` | `[]` | pink bars |
| `core:dict` | Dictionary | `dict` | `{}` | yellow diamond |
| `core:flow` | Flow | none | none | white pentagon |
| `core:stage_object_path` | Object Path | none | none | blue square |

`Flow` and `Object Path` belong to specific component types and can't be picked as the
datatype of a value component. All others can, using the datatype selector of a value
component or the `set_datatype` method.

`Object` is the datatype of values without a hint: whenever a component has no datatype
set (or a plugin that provided it isn't loaded) it is treated as `Object`.

## Which components can be linked

When you drag a link, the target component asks whether it *accepts* the datatype of
the source. The rules, in order:

1. The same datatype is always accepted.
2. A datatype can name others it is compatible with. `Integer` and `Float` accept each
   other, `Object Path` accepts `String`.
3. `Flow` ignores wildcards. A flow component only links to another flow component, and
   a data component can never be linked to flow.
4. Otherwise the link is accepted when **either side is a wildcard**.
   `Object`, `Type`, `Boolean` and `String` are wildcards: they link to
   everything but flow.

| from \ to | Object | Bool | String | Int | Float | Path | List | Dict | Flow |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Object** | yes | yes | yes | yes | yes | yes | yes | yes | no |
| **Bool**, **String**, **Type** | yes | yes | yes | yes | yes | yes | yes | yes | no |
| **Int** | yes | yes | yes | yes | yes | no | no | no | no |
| **Float** | yes | yes | yes | yes | yes | no | no | no | no |
| **Path**, **List**, **Dict** | yes | yes | yes | no | no | same only | same only | same only | no |
| **Flow** | no | no | no | no | no | no | no | no | yes |

Linking is the *permission*; what actually arrives is decided by casting.

## Casting

Every datatype has a **caster**, a function that converts a value to the datatype.
It is applied:

- when a text value is evaluated on a component. The text is first evaluated as a
  Python expression (see [How a graph executes](execution.md)), then the result is
  cast: `3.7` typed into an `Integer` component becomes `3`.
- when a value is pulled through a link. The value of the source is cast to the datatype
  of the target. A value that can't be cast is logged as a warning (naming the component
  and the reason) and passed on unchanged.
- when a Setter node pushes a value into a component, or a Type Cast node converts a value.

A value that can't be cast to the datatype of its own component makes the component
*invalid*: the reason is shown on it.

The casters are the obvious ones: `bool`, `str`, `int`, `float`, `list`, `dict`,
`PurePosixPath` for paths. `Type` also accepts the id of a registered datatype, and a
datatype or any value, from which it takes the Python type.

### Wildcards are not "any value"

A wildcard only means the *link* is allowed. Linking a `String` component to an
`Integer` component works, and at run time `"12"` is cast to `12`, but `"abc"` fails
with a warning and keeps arriving as text. Use a **Type Cast** node when you want the
conversion to be explicit, and **Get Type** to inspect the type of a value.

## Datatypes of function nodes

Function nodes (see the developer guide) pick the datatype of each parameter from its
type hint. `X | None` counts as `X`, and a generic such as `list[str]` as the class it is
made from, `list`. The first registered datatype whose Python type is exactly that class
is used: `int` becomes `Integer`, `list` becomes `List`, and so on. A parameter without a
hint, or with a hint no datatype claims (`pathlib.Path`, a union of several types), is an
`Object`. Datatypes added by plugins take part in this lookup too.

## Inherited datatypes

Some components don't have a datatype of their own. They follow the component they
take their value from. The `value` of a Setter node is an example: it takes the
datatype of what is linked to it, and you can choose one while nothing is linked.
