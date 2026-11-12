# Remote nodes and the bridge

Some work can only be done inside another application: build a scene in Maya, export
a mesh from Blender, call an API that only exists in a DCC's Python. Nyx doesn't import
those applications. It sends code to them over the **bridge** and takes the results back
into the graph.

## The concept

```text
┌──────────────────────────┐         TCP          ┌───────────────────────────┐
│ Nyx (server)             │ ◀──────────────────  │ Maya / Blender / any      │
│  BridgeServer            │   client connects    │ Python (client)           │
│  Remote Client node      │ ──── code ─────────▶ │  NyxClient                │
│   └ Remote Action nodes  │ ◀─── result ──────── │  runs it on the app's     │
└──────────────────────────┘                      │  main thread              │
                                                  └───────────────────────────┘
```

- **Nyx is the server; the external process is the client and connects out.** The
  process that executes code never opens a port.
- **One server per application.** Many clients can be connected at once, each with a
  *name* and a *kind* (`maya`, `blender`, `python`, ...).
- **Clients find the server through an address file**, `bridge.json` in the Nyx user
  directory, which holds the host, port and a token. On the same machine nothing needs
  to be configured. A client can also be given the address and token directly, or
  through the environment variables `NYX_BRIDGE_ADDRESS`, `NYX_BRIDGE_TOKEN` and
  `NYX_BRIDGE_ADDRESS_FILE`.
- **A token protects the server.** Whoever has the token can run code in a connected
  client, so the server listens on `127.0.0.1` by default and generates a random token
  at every launch (unless you set `bridge.token`). The address file is readable by its
  owner only where the system supports it.

The protocol, the server and the client base class live in a separate package,
[`nyx-bridge`](https://github.com/sowwic/nyx-bridge). It has no dependencies and does
not import Nyx or Qt, so it installs into the Python of a DCC. The DCC specific parts are
separate repositories:

| Repository | What it adds |
| --- | --- |
| [`nyx-bridge-maya`](https://github.com/sowwic/nyx-bridge-maya) | A Maya client (plug-in and Python API) and a Nyx plugin with Maya nodes. |
| [`nyx-bridge-blender`](https://github.com/sowwic/nyx-bridge-blender) | A Blender add-on client and a Nyx plugin with Blender nodes. |

Install the client half into the DCC following the README of the repository, and the
Nyx half by adding the plugin folder to `plugin_paths` or `NYX_PLUGIN_PATH`
(see [Customization](customization.md)).

## Starting the server

The server starts with the application when `bridge.enabled` is `true` (the default).
The **Bridge dock** of the editor shows its address, the connected clients, and lets you
start, stop and copy the address or token. With `nyx stage run` the server starts too,
unless `--no-bridge` is given, so a headless run can reach clients as well.
`bridge.port` fixes the port (`--port N` overrides it for one headless run); when it is
`null` the default port is tried first and then the ones after it.

## The nodes

### Remote Client

A **scope node**. It waits until a matching client has connected, then runs the nodes
**inside** it with that client available to them.

| Component | Purpose |
| --- | --- |
| `client_name` | Name of the client to wait for. Empty accepts any. |
| `client_kind` | Kind of the client (`maya`, `blender`, ...). Empty accepts any. |
| `timeout` | Seconds to wait for a client before failing, `30` by default. `0` or less waits forever. |
| `client` (output) | Name of the connected client. |

If more than one connected client matches, the node **fails** instead of picking one, so
code never goes to the wrong application. Set the name or kind to choose. If no client
connects in time it fails with a message naming the address it waited on.

The wait doesn't freeze the editor and can be cancelled.

### Remote Action

A **flow node** that must be placed inside a Remote Client (its scope), because it
asks that scope for the client. It sends a script to the client and waits for the answer.

| Component | Purpose |
| --- | --- |
| `script` | A Python file, or an entry point `module:function`. |
| `args` | A dictionary of values the script can use by name. |
| `timeout` | Seconds to wait for the answer, `30` by default. `0` or less waits forever. |
| `response` (output) | The value the script assigned to `result`. |

How the script is run depends on what `script` holds:

- **A file.** The file is read in Nyx and its source is sent. The entries of `args` are
  variables in the script. To send something back, assign it to `result`:

    ```python
    # export_selection.py, runs inside Maya
    # `args` entries are variables: `path`
    cmds.file(path, exportSelected=True, type="mayaAscii")
    result = cmds.ls(selection=True)
    ```

- **An entry point**, `package.module:function`. The module must be importable in the
  client. It is imported there and called with the entries of `args` as keyword
  arguments, and its return value becomes the `result`. The part before the colon can go
  through attributes, like `bpy.ops.mesh:primitive_cube_add`.

Everything crossing the bridge has to be JSON data: numbers, strings, booleans, lists,
dictionaries and `None`. Anything else arrives as its `repr`. Standard output and
standard error of the script are written to the Nyx log. An exception in the client is
raised in the Remote Action node as a `RemoteExecutionError` with the traceback of the
client, so the node fails like any other. The code runs on the **main thread** of the
application, as the DCC requires.

Plugins can subclass Remote Action to build the script and its arguments themselves, so
that a node for a DCC doesn't need you to write one, see the developer guide.

### Launch Process

Optional. A scope node that **starts** the external process instead of waiting for you to
start it, for example a headless Blender, and stops it when the nodes inside are done.

| Component | Purpose |
| --- | --- |
| `command` | Command line to run. `$NAME` and `${NAME}` are replaced by environment variables, those of `env` included. |
| `env` | Dictionary of environment variables added to the application's. |
| `working_directory` | Folder to run in. Empty uses the current one. |
| `client_name` | Name the process connects as. Empty makes one up. |
| `wait_for_client` | Wait until the process has connected before the nodes inside run. |
| `timeout` | Seconds to wait for it to connect, `30` by default. |
| `client`, `process_id` (outputs) | Name the process connects as, and its process id. |

The process gets `NYX_BRIDGE_ADDRESS`, `NYX_BRIDGE_TOKEN` and a client name in its
environment, so a client started in it connects to this server without any setup. Its
output is written to the log line by line, and the last lines are kept for the error
message if it fails.

A Remote Client placed **inside** a Launch Process waits for the process that was
started, unless you give it a name or kind of its own.

## A complete example

```text
Flow Start ─▶ Launch Process ("blender --background --python start_client.py")
               └─ Remote Client (kind = blender)
                   └─ Flow Start ─▶ Remote Action (bpy.ops.mesh:primitive_cube_add)
                                       ─▶ Remote Action (export.py, args = {"path": "cube.fbx"})
               ─▶ Log (response of the export)
```

When this stage runs: Blender starts and connects, the Remote Client finds it, the
actions run in it one after another, then Blender is stopped and the flow goes on to the
Log node.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `The bridge server is not running` | The server is disabled (`bridge.enabled`), failed to start (see the log), or the stage was run with `--no-bridge`. |
| `No matching client connected to host:port within Ns` | The client didn't start, got the wrong address or token, or its name or kind doesn't match. Check the Bridge dock for connected clients. |
| `N connected clients match, set the client name or kind` | Several clients are connected. Fill `client_name` or `client_kind`. |
| The Remote Action fails with a client traceback | The code raised in the external process. Fix the script, the stack trace is the client's. |
| The action doesn't find a client | It isn't inside a Remote Client. |
