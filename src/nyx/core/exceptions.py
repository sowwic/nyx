class NyxCommandValidationError(RuntimeError):
    """Raised when an undo command is created with invalid arguments."""


class StageObjectRegistrationError(RuntimeError, KeyError):
    """Raised when a stage object can't be registered with the stage."""


class StageObjectUnregistrationError(RuntimeError, KeyError):
    """Raised when a stage object can't be unregistered from the stage."""


class StageObjectQueryError(RuntimeError):
    """Raised when a stage object can't be found by path or id."""


class NodeComponentLinkError(RuntimeError):
    """Raised when node components can't be linked or unlinked."""


class ActionRegistrationError(RuntimeError):
    """Raised when an editor action can't be registered."""


class ActionLookupError(RuntimeError):
    """Raised when an editor action id isn't registered."""
