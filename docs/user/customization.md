# Customization

Nyx keeps its settings in one JSON file, the **user config**. The editor reads it at
startup, and saves it when it exits normally, with state such as the window layout and
the recent files. Edit it by hand to change options, or to prepare a machine. Close the
editor first, or it overwrites your edit when it exits.

## Where the files are

All user files live in one directory:

| Platform | Directory |
| --- | --- |
| Linux, macOS | `$XDG_CONFIG_HOME/nyx`, `~/.config/nyx` when the variable is not set |
| Windows | `%LOCALAPPDATA%\sowwic\nyx` |

| File | Content |
| --- | --- |
| `user_config.json` | The config described on this page |
| `session.nyxsession` | Stages that were open when the editor closed |
| `bridge.json` | Address and token of the running bridge server, see [Remote nodes](remote-nodes.md) |
| `logs/` | Log files |
| `profiling/` | `.pstats` files, see the developer guide |

`make config-file` prints the path of the config file. A missing file or key falls back
to the default, so the file only has to hold what you change. A stage run with
`nyx stage run` reads the config but never saves it.

## Environment variables

| Variable | Effect |
| --- | --- |
| `NYX_PLUGIN_PATH` | Extra directories to search for plugins, in addition to the `plugin_paths` config value. Separated by `:` on Linux and macOS, `;` on Windows. |
| `NYX_DEBUG` | `1` logs at debug level and shows the model roles as a tooltip on nodes and plugs. |
| `NYX_PROFILING` | `1` writes profiler files for the profiled steps, see the developer guide. |
| `XDG_CONFIG_HOME` | Moves the user directory (Linux, macOS). |

## Config reference

The file is a tree of sections. Defaults are shown; paths such as
`editor_widgets.graphics_stage.link_style` mean nested objects.

```json
{
    "bridge": { "enabled": true, "host": "127.0.0.1", "port": null, "token": "" },
    "editor_style": { "dark_mode": true },
    "plugin_paths": ["~/nyx_plugins"]
}
```

### Top level

| Option | Default | Description |
| --- | --- | --- |
| `logging_level` | `20` | Logging level of the application, the numbers of Python's `logging` (`10` debug, `20` info, `30` warning, `40` error). |
| `plugin_paths` | `[]` | Extra directories to search for `nyx_plugin.py` files. `~` is expanded. Directories that do not exist are reported in the log and skipped. |

### `bridge`

The server external processes (Maya, Blender, ...) connect to. See
[Remote nodes](remote-nodes.md).

| Option | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Start the server when the application launches. It can be started later from the Bridge dock. |
| `host` | `"127.0.0.1"` | Interface to listen on. Anyone holding the token can run code in a client, so only change it on a network you trust. |
| `port` | `null` | Port to listen on. `null` tries the default port and the ones after it. |
| `token` | `""` | Secret clients have to present. Random on every launch if empty. Set it to keep a fixed token across launches. |

### `editor_behaviour`

| Option | Default | Description |
| --- | --- | --- |
| `new_stage_on_launch` | `true` | Create an empty stage at startup. |
| `show_splash_screen` | `true` | Show a splash screen with the startup progress. |
| `show_address_names` | `false` | Show the address names of nodes and components (the names paths are made of) instead of their display names. |
| `undo_limit` | `100` | Undoable steps each stage remembers, `0` for no limit. Applies to stages opened after the change. Deleting and pasting nodes keep a copy of them, so a high limit costs memory on big stages. |

### `editor_session`

State the editor maintains itself.

| Option | Default | Description |
| --- | --- | --- |
| `recent_files` | `[]` | Recently used stage files, most recent first. Files that no longer exist are dropped when the config is loaded and saved. |
| `max_recent_files` | `10` | Number of recent files that are kept. |

### `main_window`

Saved when the window closes.

| Option | Default | Description |
| --- | --- | --- |
| `size` | `null` | Window size in pixels, `[width, height]`. |
| `position` | `null` | Window position on the screen, `[x, y]`. |
| `is_always_on_top` | `false` | Keep the window above other windows. |
| `layout.version` | `0` | Layout version the state was saved with. |
| `layout.state` | `null` | Base64 encoded Qt window state (the arrangement of the docks). Set it to `null` to reset the layout. |

### `editor_style`

| Option | Default | Description |
| --- | --- | --- |
| `dark_mode` | `true` | Use the dark palette. |
| `animations.link_pulse.color` | `"#4BE3FF"` | Color of the dot and its tail, a color name or `#RRGGBB`. |
| `animations.link_pulse.speed` | `160.0` | Scene units the dot travels per second. |
| `animations.link_pulse.radius` | `5` | Radius of the dot in scene units. |
| `animations.link_pulse.tail_samples` | `6` | Number of dots the tail is made of. |
| `animations.link_pulse.tail_step` | `6.0` | Scene units between the dots of the tail. |
| `animations.link_glow.color` | `"#4BE3FF"` | Color of the halo. |
| `animations.link_glow.period` | `1.6` | Seconds for the glow to swell and fade once. |
| `animations.link_glow.layers` | `[[12.0, 0.15], [8.0, 0.25], [4.0, 0.4]]` | Strokes the halo is made of, as `[width, opacity]` pairs. The width is in scene units, the opacity is the one at full intensity. |

### `editor_widgets`

| Option | Default | Description |
| --- | --- | --- |
| `log_widget.auto_scroll` | `true` | Scroll the log to new records. |
| `log_widget.is_expanded` | `false` | The log dock is expanded. |
| `log_widget.expanded_height` | `220` | Height of the expanded log dock in pixels. |
| `log_widget.minimum_level` | `10` | Minimum logging level shown in the log. |
| `graphics_stage.link_style` | `"bezier"` | Shape links are drawn with: `bezier`, `direct` or `square`. |
| `graphics_stage.highlight_flow_chain` | `true` | Animate the flow links that are part of the execution chain of the drawn scope. |
| `graphics_stage.highlight_flow_chain_style` | `"pulse"` | Animation that highlights the chain: `pulse` or `glow`. |
| `graphics_stage.background_style` | `"grid"` | Pattern of the stage background: `grid` or `dots`. |
| `graphics_stage.background_color` | `"#393939"` | Fill color of the stage background. |
| `graphics_stage.default_note_color` | `"#e8c95a"` | Color new notes get. |
| `graphics_stage.default_group_color` | `"#5b8def"` | Color new groups get. |
| `graphics_stage.viewport_debug_overlay` | `false` | Show performance numbers over the graph views. |
| `graphics_stage.nodes.hover_diagnostics` | `false` | Show the model roles as a tooltip when hovering nodes and plugs. |

## Layers

`NyxConfig` is a *layered* config from the `json-config` package. The user file is its
root layer, and Nyx registers no other. Plugin authors reach the resolved config of the
running application with `nyx.core.layered_config.get_app_config()`, whose `values`
attribute has the sections above as typed objects (`config.values.bridge.port`).
