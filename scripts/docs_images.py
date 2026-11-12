"""Render the images of the built-in nodes, components and util objects for the docs.

Nodes and util objects are cropped from the graph scene of the editor. Components are
cropped from their item in the Inspector, fully expanded. The images are written to
`docs/_static/images/stdlib/{nodes,components,util-objects}/<name>.png`, the name being
the type id without its namespace, with `_` replaced by `-`.

The link images (a link without pins and with pins) are cropped from the graph scene
too and written to `docs/_static/images/link-pins/`.

The kinds need different Qt settings, so each runs in its own process:

    uv run python scripts/docs_images.py              # everything
    uv run python scripts/docs_images.py graph        # nodes and util objects
    uv run python scripts/docs_images.py components   # components
    uv run python scripts/docs_images.py links        # links and their pins
    uv run python scripts/docs_images.py --out DIR    # write somewhere else

The look follows the editor config of the user running it (background style and color).
Nothing is saved to the config.
"""

import argparse
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "_static" / "images" / "stdlib"
LINKS_OUT = ROOT / "docs" / "_static" / "images" / "link-pins"

GRAPH_SCALE = 2
GRAPH_MARGIN = 20
GRAPH_ROW_SPACING = 600
"""Distance between the things rendered, so that none shows in the image of another."""
INSPECTOR_SCALE_FACTOR = "2"


def page_name(type_id) -> str:
    """Get the name of the page and image of a type.

    Args:
        type_id (str | enum.Enum): type id, like `core:for_loop`.

    Returns:
        str: the id without the namespace and with dashes, like `for-loop`.
    """
    text = str(getattr(type_id, "value", type_id))
    return text.split(":", 1)[1].replace("_", "-")


def create_editor():
    """Start the editor with a new stage.

    Returns:
        tuple: the application and the editor of the new stage.
    """
    from nyx.application import NyxEditorApplication

    app = NyxEditorApplication()
    # Nothing of this run is written to the config of the user.
    app.config.save = lambda *args, **kwargs: None
    app.config.values.editor_behaviour.show_address_names = False
    window = app.main_window()
    window.resize(1400, 900)
    window.show()
    window.on_stage_new()
    pump(app)
    return app, window


def pump(app, times: int = 30) -> None:
    """Let the application handle its pending events.

    Args:
        app (QtWidgets.QApplication): application.
        times (int): how many rounds of events to process.
    """
    for _ in range(times):
        app.processEvents()


def render_graph(out: pathlib.Path) -> None:
    """Render nodes and util objects from the graph scene.

    Args:
        out (pathlib.Path): images folder, the kinds go in subfolders.
    """
    from PySide6 import QtCore, QtGui

    from nyx.api.v1 import NYX_REGISTRY, commands

    app, window = create_editor()
    stage = window.current_stage_graph.stage
    gr_stage = window.current_stage_graph.gr_stage
    row = 0

    def next_position() -> tuple[float, float]:
        nonlocal row
        row += 1
        return (0.0, row * GRAPH_ROW_SPACING)

    def create_node(type_id, position):
        command = commands.CreateNodeCommand(
            stage=stage, type_id=type_id, position=position
        )
        stage.push_command(command)
        app.processEvents()
        return command.result_node

    def save(rect: QtCore.QRectF, kind: str, name: str) -> None:
        gr_stage.clearSelection()
        rect = rect.adjusted(-GRAPH_MARGIN, -GRAPH_MARGIN, GRAPH_MARGIN, GRAPH_MARGIN)
        image = QtGui.QImage(
            int(rect.width() * GRAPH_SCALE),
            int(rect.height() * GRAPH_SCALE),
            QtGui.QImage.Format.Format_ARGB32,
        )
        image.fill(QtGui.QColor("transparent"))
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        gr_stage.render(painter, QtCore.QRectF(image.rect()), rect)
        painter.end()
        path = out / kind / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        assert image.save(str(path)), path

    for type_id in NYX_REGISTRY.nodes:
        if not str(getattr(type_id, "value", type_id)).startswith("core:"):
            continue
        node = create_node(type_id, next_position())
        save(gr_stage.get_gr_node(node).sceneBoundingRect(), "nodes", page_name(type_id))

    note = commands.CreateUtilObjectCommand(
        stage,
        "core:note",
        position=next_position(),
        size=(240, 120),
        properties={"text": "Notes explain what\na part of the graph does."},
    )
    stage.push_command(note)
    app.processEvents()
    save(
        gr_stage.get_gr_util_object(note.result_object).sceneBoundingRect(),
        "util-objects",
        "note",
    )

    x, y = next_position()
    group = commands.CreateUtilObjectCommand(
        stage, "core:group", position=(x, y), size=(440, 220)
    )
    stage.push_command(group)
    create_node("core:action", (x + 30, y + 60))
    create_node("core:action", (x + 240, y + 60))
    save(
        gr_stage.get_gr_util_object(group.result_object).sceneBoundingRect(),
        "util-objects",
        "group",
    )


def render_links(out: pathlib.Path) -> None:
    """Render a link between two nodes without pins and with them.

    Args:
        out (pathlib.Path): folder to write the images to.
    """
    from PySide6 import QtCore, QtGui

    from nyx.api.v1 import commands

    app, window = create_editor()
    stage = window.current_stage_graph.stage
    gr_stage = window.current_stage_graph.gr_stage

    def create_node(position):
        command = commands.CreateNodeCommand(
            stage=stage, type_id="core:action", position=position
        )
        stage.push_command(command)
        app.processEvents()
        return command.result_node

    source = create_node((0.0, 0.0))
    target = create_node((420.0, 40.0))
    link_command = commands.LinkNodeComponentsCommand(
        stage=stage, source=source["flow"], target=target["flow"]
    )
    stage.push_command(link_command)
    pump(app)
    link = link_command.result_link

    def save(name: str) -> None:
        gr_stage.clearSelection()
        gr_link = gr_stage.get_gr_link(link)
        rect = gr_stage.get_gr_node(source).sceneBoundingRect()
        rect = rect.united(gr_stage.get_gr_node(target).sceneBoundingRect())
        rect = rect.united(gr_link.sceneBoundingRect())
        rect = rect.adjusted(-GRAPH_MARGIN, -GRAPH_MARGIN, GRAPH_MARGIN, GRAPH_MARGIN)
        image = QtGui.QImage(
            int(rect.width() * GRAPH_SCALE),
            int(rect.height() * GRAPH_SCALE),
            QtGui.QImage.Format.Format_ARGB32,
        )
        image.fill(QtGui.QColor("transparent"))
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        gr_stage.render(painter, QtCore.QRectF(image.rect()), rect)
        painter.end()
        path = out / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        assert image.save(str(path)), path

    def set_pins(pins: list[QtCore.QPointF]) -> None:
        stage.push_command(commands.SetLinkPinsCommand(stage, link, pins))
        pump(app)

    save("link")
    middle = gr_stage.get_gr_link(link).path().pointAtPercent(0.5)
    set_pins([middle + QtCore.QPointF(0.0, -110.0)])
    save("link-pin")
    set_pins(
        [
            middle + QtCore.QPointF(-110.0, -110.0),
            middle + QtCore.QPointF(110.0, 130.0),
        ]
    )
    save("link-pins")


def apply_dark_palette(app, view) -> None:
    """Give the Inspector the dark palette.

    The offscreen platform hands Qt Quick a light palette whatever the application one
    is, which leaves the text dark on dark. The roles are written to the palette of the
    root item instead, the items inside inherit it.

    Args:
        app (QtWidgets.QApplication): application.
        view (QtQuickWidgets.QQuickWidget): components view of the Inspector.
    """
    from PySide6 import QtGui, QtQml

    from nyx.utils import pyside_fn

    pyside_fn.set_dark_fusion_palette(app)
    palette = pyside_fn.dark_fusion_palette()
    role = QtGui.QPalette.ColorRole
    roles = {
        "windowText": role.WindowText,
        "text": role.Text,
        "buttonText": role.ButtonText,
        "window": role.Window,
        "base": role.Base,
        "alternateBase": role.AlternateBase,
        "button": role.Button,
        "highlight": role.Highlight,
        "highlightedText": role.HighlightedText,
        "link": role.Link,
        "light": role.Light,
        "midlight": role.Midlight,
        "mid": role.Mid,
        "dark": role.Dark,
        "shadow": role.Shadow,
    }
    colors = {name: palette.color(color_role) for name, color_role in roles.items()}
    # Not set by the dark palette: Qt derives it from the text color at half opacity.
    placeholder = QtGui.QColor(palette.color(role.Text))
    placeholder.setAlpha(128)
    colors["placeholderText"] = placeholder

    script = "".join(
        f"palette.{name} = '{color.name(QtGui.QColor.NameFormat.HexArgb)}';"
        for name, color in colors.items()
    )
    root = view.rootObject()
    expression = QtQml.QQmlExpression(
        QtQml.QQmlEngine.contextForObject(root), root, script
    )
    expression.evaluate()
    assert not expression.hasError(), expression.error().toString()


def render_components(out: pathlib.Path) -> None:
    """Render components as their item in the Inspector, expanded with their links.

    Each is on an Action node of its own. Components added to a node have no sockets,
    and so no Links section, until one is enabled, which is done here.

    Args:
        out (pathlib.Path): images folder, the images go in `components`.
    """
    from PySide6 import QtCore

    from nyx.api.v1 import NYX_REGISTRY, NodeComponent, commands

    app, window = create_editor()
    editor = window.current_stage_graph
    stage = editor.stage
    view = window.inspector._node_components_view
    apply_dark_palette(app, view)
    pump(app, 10)

    def find_item(name: str):
        list_view = view.rootObject().findChild(QtCore.QObject, "componentsListView")
        for item in list_view.property("contentItem").childItems():
            if item.property("name") == name:
                return item
        raise LookupError(name)

    for type_id in NYX_REGISTRY.node_components:
        command = commands.CreateNodeCommand(stage=stage, type_id="core:action")
        stage.push_command(command)
        node = command.result_node
        if page_name(type_id) == "flow":  # Action already has a flow component
            component = node.components_model.get_component("flow")
        else:
            add = commands.AddNodeComponentCommand(node, type_id)
            stage.push_command(add)
            component = add.result_component
            component.writable = True
        component.is_expanded = True
        component.setData(True, role=NodeComponent.Roles.LINKS_EXPANDED)
        pump(app, 10)

        editor.gr_stage.clearSelection()
        editor.gr_stage.get_gr_node(node).setSelected(True)
        pump(app, 40)

        item = find_item(component.name)
        pixmap = view.grab()
        ratio = pixmap.devicePixelRatio()
        top_left = item.mapToScene(QtCore.QPointF(0, 0))
        rect = QtCore.QRect(
            int(top_left.x() * ratio),
            int(top_left.y() * ratio),
            int(item.width() * ratio),
            int(item.height() * ratio),
        )
        path = out / "components" / f"{page_name(type_id)}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        assert pixmap.copy(rect).save(str(path)), path


def main() -> None:
    """Render the requested images, each kind in a process of its own."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("kind", nargs="?", choices=("graph", "components", "links"))
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()

    if args.kind is None:
        for kind in ("graph", "components", "links"):
            command = [sys.executable, __file__, kind]
            if args.out is not None:
                command += ["--out", str(args.out)]
            subprocess.run(command, check=True)
        return

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    if args.kind == "components":
        out = args.out or DEFAULT_OUT
        os.environ["QT_SCALE_FACTOR"] = INSPECTOR_SCALE_FACTOR
        render_components(out)
    elif args.kind == "links":
        out = args.out or LINKS_OUT
        render_links(out)
    else:
        out = args.out or DEFAULT_OUT
        render_graph(out)
    print(f"Rendered {args.kind} images to {out}")


if __name__ == "__main__":
    main()
