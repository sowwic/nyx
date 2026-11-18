# Value

![Value](../../../_static/images/stdlib/components/value.png)

Holds a typed value that can be edited, linked to other components or pulled by them.

Type id: `core:value`

## How it works

- Static and editable: you can type the value, link another component into it, or have other components pull it.
- Pick its datatype with the datatype selector, see [Datatypes](../../datatypes.md). Without one it is shown with the datatype of the value it holds.
- A dictionary, list, tuple or set value is shown in the Inspector as a scrollable list, key and value for a dictionary, position and value for the others (the first 1000 entries, long values are cut). Select a value in the list to copy it. Double-click the list, or use the edit button, to edit the value as text.
- Most inputs and outputs of the built-in nodes are value components.

## Used by

- [Set](../nodes/set.md)
- [Get](../nodes/get.md)
- [Value](../nodes/value.md)
- [Branch](../nodes/branch.md)
- [Dict](../nodes/dictionary.md)
- [List](../nodes/list.md)
- [For Loop](../nodes/for-loop.md)
- [For Each Loop](../nodes/for-each-loop.md)
- [While Loop](../nodes/while-loop.md)
- [Log](../nodes/log.md)
- [Type Cast](../nodes/type-cast.md)
- [Get Type](../nodes/get-type.md)
- [Remote Client](../nodes/remote-client.md)
- [Remote Action](../nodes/remote-action.md)
- [Launch Process](../nodes/launch-process.md)
