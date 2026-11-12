# Nodes

The nodes of the standard library. Most have **flow** components that connect them to the execution flow. Nodes without any provide values and run when something pulls from them.

## Structure and flow control

| Name | What it does |
| --- | --- |
| [Node](node.md) | Empty node without components. Groups other nodes inside of it. |
| [Flow Start](flow-start.md) | Marks where the execution flow of the parent scope begins. |
| [Action](action.md) | Runs its components when the flow reaches it. A general purpose step with a flow input and output. |
| [Branch](branch.md) | Continues through the true or false flow output depending on the condition value. |
| [Sequence](sequence.md) | Continues through all of its flow outputs one after another, in order. |
| [Reference](reference.md) | Stands for a stage file, with the components of its top node. |

## Loops

| Name | What it does |
| --- | --- |
| [For Loop](for-loop.md) | Runs the loop body for every index from the first to the last index, then continues with completed. |
| [For Each Loop](for-each-loop.md) | Runs the loop body for every element of an iterable, optionally in reverse, then continues with completed. |
| [While Loop](while-loop.md) | Runs the loop body for as long as the condition is true, then continues with completed. |

## Values and data

| Name | What it does |
| --- | --- |
| [Value](value.md) | Provides a value that can be edited and linked to other nodes. |
| [Set](set.md) | Sets the value of a component of another node when the flow reaches it. |
| [Get](get.md) | Provides the value of a component of another node. |
| [Dict](dictionary.md) | Collects value components and creates a dictionary result. |
| [List](list.md) | Collects value components and creates a list result. |
| [Type Cast](type-cast.md) | Converts an object to the given type when the flow reaches it, e.g. a string to an int. |
| [Get Type](get-type.md) | Finds the type of an object when the flow reaches it. |

## Logging

| Name | What it does |
| --- | --- |
| [Log](log.md) | Writes a message to the log with the chosen level. |

## Bridge and processes

| Name | What it does |
| --- | --- |
| [Remote Client](remote-client.md) | Waits for an external process to connect to the server, and lets the nodes inside of it run code in that process. |
| [Remote Action](remote-action.md) | Runs code in the external process of the Remote Client it is inside of and outputs the value the code assigned to `result`. |
| [Launch Process](launch-process.md) | Starts a process that connects to the bridge server, like a headless application, waits for it and stops it when the nodes inside are done. |
