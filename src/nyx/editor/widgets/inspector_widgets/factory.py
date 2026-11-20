from nyx.core.plugin_subsystem.registry import NYX_REGISTRY


def register_builtin_inspector_widgets() -> None:
    """Register the inspector widget showing nodes.

    The ones showing the util objects of the standard library come with its plugin.
    """
    from .node_inspector import NodeInspectorWidget

    NYX_REGISTRY.register_builtin_inspector_widget(
        NodeInspectorWidget.get_type_id(), NodeInspectorWidget
    )
