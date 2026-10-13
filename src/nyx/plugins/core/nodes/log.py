import logging
from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class LogNode(Node):
    DEFAULT_NAME = "log"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.LOG

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Log"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/log_node"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"utils"}

    def setup(self) -> None:
        """Create log node components"""
        self._logger: logging.Logger | None = None
        self.flow_cpnt = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.flow_cpnt.produces_output = True
        self.flow_cpnt.accepts_input = True

        self.message = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.message.name = "message"
        self.message.is_editable = True
        self.message.accepts_input = True
        self.message.value = ""

        self.level = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.level.name = "level"
        self.level.value = 10
        self.level.is_editable = True
        self.level.accepts_input = True

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.message)
        self.components_model.add_component(self.level)

    def _compose_logger_name(self) -> str:
        """Get logger name in a form of LogNode(<node name>)

        Returns:
            Logger name
        """
        return f"{__class__}({self.name})"

    @property
    def logger(self) -> logging.Logger:
        """Get logger with node name.

        Returns:
            Logger instance
        """
        expected_logger_name = self._compose_logger_name()
        if self._logger and not self._logger.name == expected_logger_name:
            self._logger = None

        if self._logger is None:
            self._logger = logging.getLogger(expected_logger_name)
        return self._logger

    def execute(self) -> None:
        """Log message"""
        if not self.message.value:
            return

        message = f"({self.name}): {self.message.pull_value()}"
        self.logger.log(level=int(self.level.pull_value()), msg=message)
