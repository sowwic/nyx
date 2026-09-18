import logging
from nyx.api.v1 import Node, CoreNodes, CoreNodeComponents


class LogNode(Node):
    DEFAULT_NAME = "log"
    REQUIRED_PLUGINS = {"NyxCore"}

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodes.LOG

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Log"

    @classmethod
    def get_tags(cls) -> set[str]:
        return {"utils"}

    def setup(self) -> None:
        """Create log node components"""
        self._logger: logging.Logger | None = None
        self.flow_cpnt = self.components_model.create_component(
            type_id=CoreNodeComponents.FLOW
        )
        self.flow_cpnt.is_readable = True
        self.flow_cpnt.is_writable = True

        self.message = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.message.name = "message"
        self.message.is_writable = True
        self.message.value = ""

        self.level = self.components_model.create_component(
            type_id=CoreNodeComponents.VALUE
        )
        self.level.name = "level"
        self.level.value = 10
        self.level.is_writable = True

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

    def execute_components(self) -> None:
        """Log message"""
        if not self.message:
            return
        self.logger.log(level=int(self.level.value), msg=self.message)
