from nyx.api.v1 import CoreNodes, Node, NodeRenderOptions
from nyx.editor.graphics.graphics_node import GraphicsNode


def test_node_returns_new_default_options_every_time():
    first = Node.get_render_options()
    second = Node.get_render_options()

    assert first == NodeRenderOptions()
    assert first is not second
    first.status_icons.clear()
    assert second.status_icons


def test_overridden_options_are_used_by_the_graphics_node(
    stage_editor, create_node, monkeypatch
):
    node = create_node(stage_editor.stage, "tweaked", type_id=CoreNodes.ACTION)

    def tweaked(cls):
        options = super(type(node), cls).get_render_options()
        options.min_width = 300.0
        options.lower_padding = 20.0
        return options

    monkeypatch.setattr(type(node), "get_render_options", classmethod(tweaked))

    gr_node = GraphicsNode(node)

    assert gr_node.options.min_width == 300.0
    assert gr_node.width >= 300.0
    assert gr_node.options.lower_padding == 20.0
    assert gr_node.options.title_offset_x == NodeRenderOptions().title_offset_x
