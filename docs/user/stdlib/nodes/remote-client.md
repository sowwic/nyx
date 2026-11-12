# Remote Client

![Remote Client](../../../_static/images/stdlib/nodes/remote-client.png)

Waits for an external process to connect to the server, and lets the nodes inside of it run code in that process.

Type id: `core:remote_client`

## Components

| Name | Plug | Datatype | Description |
| --- | --- | --- | --- |
| `flow` | in / out | Flow | Connects the execution flow from one node to the next. |
| `client_name` | in | String | Name of the client to wait for. Empty accepts any, as long as only one client matches. |
| `client_kind` | in | String | Kind of the client to wait for, as it reports itself. Empty accepts any, as long as only one client matches. |
| `timeout` | in | Float | Seconds to wait for the client before failing. 0 or less waits forever. |
| `client` | out | String | Name of the connected client. |

## How it works

- Acts as a scope: the nodes inside of it run code in the process that connects.
- Waits for a client to connect to the bridge server. `client_name` and `client_kind` narrow down which one, empty accepts any as long as only one matches.
- `timeout` of 0 or less waits forever.
- Details: [Remote nodes and the bridge](../../remote-nodes.md).
