import logging
from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents, CoreDatatypes


class LogNode(Node):
    """Node writing a message to the log."""

    DEFAULT_NAME = "log"
    DEFAULT_LEVEL = 20

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.LOG

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Log"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/log_node"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Writes a message to the log with the chosen level."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"utils"}

    def setup(self) -> None:
        """Create log node components"""
        self._logger: logging.Logger | None = None
        self.flow_cpnt = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.message = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.message.name = "message"
        self.message.description = "Text to write to the log."
        self.message.is_editable = True
        self.message.writable = True
        self.message.set_datatype(CoreDatatypes.STRING)
        self.message.push_value("")

        self.level = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.level.name = "level"
        self.level.description = (
            "Importance of the message as a logging level: 10 debug, 20 info, "
            "30 warning, 40 error, 50 critical."
        )
        self.level.set_datatype(CoreDatatypes.INT)
        self.level.push_value(self.DEFAULT_LEVEL)
        self.level.default_value = self.DEFAULT_LEVEL
        self.level.is_editable = True
        self.level.writable = True

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
        value = self.message.pull_value()
        if value is None or value == "":
            return

        message = f"({self.name}): {value}"
        self.logger.log(level=int(self.level.pull_value()), msg=message)
