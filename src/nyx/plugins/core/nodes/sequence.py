from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class SequenceNode(Node):
    TYPE_ID = CoreNodes.SEQUENCE
    DEFAULT_NAME = "sequence"
    REQUIRED_PLUGINS = {"NyxCore"}
    TAGS = {"logic"}
    DEFAULT_OUTPUTS_COUNT = 4

    def setup(self):
        for output_index in range(4):
            flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
            flow_cpnt.name = f"flow_{output_index}"
            flow_cpnt.is_writable = output_index == 0
            flow_cpnt.is_readable = True
            self.components_model.add_component(flow_cpnt)
