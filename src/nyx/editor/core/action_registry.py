"""Central registry of editor actions.

The registry owns action *definitions* (id, text, icon, default shortcut, ...),
exactly one shared `QAction` per definition, and shortcut configuration. It does
not decide what an action does: see `nyx.editor.core.action_router` for routing
triggered actions to widget handlers.
"""

import dataclasses
import logging
import typing
import weakref
from collections.abc import Iterator

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.core.exceptions import ActionLookupError, ActionRegistrationError

LOGGER = logging.getLogger("ActionRegistry")


@dataclasses.dataclass(frozen=True)
class ActionDefinition:
    """Static description of an editor action.

    Attributes:
        action_id: unique id, e.g. "edit.copy"
        text: menu / button text
        category: grouping used by shortcut editors, e.g. "Edit"
        icon_path: Qt resource path or file path of the icon
        default_shortcut: key sequence text, empty for no shortcut
        shortcut_context: where the shortcut is active by default
        status_tip: text shown in status bar / tooltip
        checkable: the action is a toggle, its handler receives the checked state
    """

    action_id: str
    text: str
    category: str = ""
    icon_path: str | None = None
    default_shortcut: str = ""
    shortcut_context: QtCore.Qt.ShortcutContext = (
        QtCore.Qt.ShortcutContext.WindowShortcut
    )
    status_tip: str = ""
    checkable: bool = False


class ActionRegistry(QtCore.QObject):
    """Registry of editor action definitions and the shared QActions created from them.

    Attributes:
        action_created: emitted when a shared action is lazily created
        cleared: emitted after the registry was cleared
    """

    action_created = QtCore.Signal(str, QtGui.QAction)
    """Emitted when a shared action is lazily created: (action_id, action)."""
    cleared = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        """Initialize ActionRegistry.

        Args:
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._definitions: dict[str, ActionDefinition] = {}
        self._shortcut_overrides: dict[str, str] = {}
        self._actions: dict[str, QtGui.QAction] = {}
        self._adopted: dict[str, weakref.WeakSet[QtGui.QAction]] = {}

    # ---- Definitions ----
    def register_definition(self, definition: ActionDefinition) -> None:
        """Register an action definition.

        Args:
            definition (ActionDefinition): definition to register.

        Raises:
            ActionRegistrationError: if the action id is already registered.
        """
        if definition.action_id in self._definitions:
            raise ActionRegistrationError(
                f"Action already registered: {definition.action_id}"
            )
        self._definitions[definition.action_id] = definition
        LOGGER.debug("Registered action: %s", definition.action_id)

    def register_definitions(self, definitions: typing.Iterable[ActionDefinition]):
        """Register several action definitions.

        Args:
            definitions (typing.Iterable[ActionDefinition]): definitions to register.
        """
        for definition in definitions:
            self.register_definition(definition)

    def has_definition(self, action_id: str) -> bool:
        """Check whether an action id is registered.

        Args:
            action_id (str): action id.

        Returns:
            bool: action is registered.
        """
        return action_id in self._definitions

    def get_definition(self, action_id: str) -> ActionDefinition:
        """Get an action definition.

        Args:
            action_id (str): action id.

        Returns:
            ActionDefinition: registered definition.

        Raises:
            ActionLookupError: if the action id isn't registered.
        """
        try:
            return self._definitions[action_id]
        except KeyError:
            raise ActionLookupError(
                f"Unknown action: {action_id}. Registered: {sorted(self._definitions)}"
            ) from None

    def iter_definitions(
        self, category: str | None = None
    ) -> Iterator[ActionDefinition]:
        """Iterate registered definitions.

        Args:
            category (str | None): only yield definitions of this category.

        Yields:
            ActionDefinition: matching definitions.
        """
        for definition in self._definitions.values():
            if category is None or definition.category == category:
                yield definition

    def clear(self) -> None:
        """Remove all definitions, shortcut overrides and shared actions."""
        for action in self._actions.values():
            action.deleteLater()
        self._definitions.clear()
        self._shortcut_overrides.clear()
        self._actions.clear()
        self._adopted.clear()
        self.cleared.emit()

    # ---- Shared actions ----
    def action(self, action_id: str) -> QtGui.QAction:
        """Return the single shared `QAction` for `action_id`, creating it lazily.

        Add it to menus / toolbars / context menus freely. To make its shortcut
        work, the action must also be added to a widget (see `attach_shortcuts`).
        """
        existing = self._actions.get(action_id)
        if existing is not None:
            return existing

        definition = self.get_definition(action_id)
        action = QtGui.QAction(definition.text, self)
        action.setObjectName(action_id)
        action.setCheckable(definition.checkable)
        action.setStatusTip(definition.status_tip)
        if definition.status_tip:
            action.setToolTip(definition.status_tip)
        if definition.icon_path:
            action.setIcon(QtGui.QIcon(definition.icon_path))
        action.setShortcutContext(definition.shortcut_context)
        action.setShortcut(QtGui.QKeySequence(self.get_shortcut_text(action_id)))
        self._actions[action_id] = action
        self.action_created.emit(action_id, action)
        return action

    def existing_action(self, action_id: str) -> QtGui.QAction | None:
        """Return the shared action if it was already created, else None."""
        return self._actions.get(action_id)

    def iter_actions(self) -> Iterator[tuple[str, QtGui.QAction]]:
        """Iterate over the shared actions created so far."""
        yield from list(self._actions.items())

    def attach_shortcuts(self, widget: QtWidgets.QWidget) -> None:
        """Add every defined action to `widget` so their shortcuts are live."""
        for definition in self.iter_definitions():
            widget.addAction(self.action(definition.action_id))

    def adopt_action(self, action_id: str, action: QtGui.QAction) -> QtGui.QAction:
        """Apply a definition to an externally owned action (e.g. undo/redo).

        The action keeps its own text (Qt updates it dynamically) but gets the
        registry shortcut and receives future shortcut overrides.
        """
        definition = self.get_definition(action_id)
        shared = self._actions.pop(action_id, None)
        if shared is not None:
            # The external action replaces it; avoid duplicate shortcuts.
            shared.setShortcut(QtGui.QKeySequence())
            shared.deleteLater()
        action.setObjectName(action_id)
        action.setShortcutContext(definition.shortcut_context)
        action.setShortcut(QtGui.QKeySequence(self.get_shortcut_text(action_id)))
        self._adopted.setdefault(action_id, weakref.WeakSet()).add(action)
        return action

    # ---- Shortcuts ----
    def get_shortcut_text(self, action_id: str) -> str:
        """Get the effective shortcut of an action, the user override if there is one.

        Args:
            action_id (str): action id.

        Returns:
            str: shortcut key sequence text.
        """
        definition = self.get_definition(action_id)
        return self._shortcut_overrides.get(action_id, definition.default_shortcut)

    def set_shortcut_override(self, action_id: str, shortcut_text: str) -> None:
        """Override the shortcut. An empty string clears it."""
        self.get_definition(action_id)
        self._shortcut_overrides[action_id] = shortcut_text
        self._apply_shortcut(action_id)

    def reset_shortcut(self, action_id: str) -> None:
        """Drop the shortcut override of an action and apply the default.

        Args:
            action_id (str): action id.
        """
        self._shortcut_overrides.pop(action_id, None)
        self._apply_shortcut(action_id)

    def iter_live_actions(self, action_id: str) -> Iterator[QtGui.QAction]:
        """Iterate the shared action and all adopted actions of an action id.

        Args:
            action_id (str): action id.

        Yields:
            QtGui.QAction: live actions.
        """
        shared = self._actions.get(action_id)
        if shared is not None:
            yield shared
        yield from list(self._adopted.get(action_id, ()))

    def _apply_shortcut(self, action_id: str) -> None:
        """Apply the effective shortcut to all live actions of an action id.

        Args:
            action_id (str): action id.
        """
        key_sequence = QtGui.QKeySequence(self.get_shortcut_text(action_id))
        for action in self.iter_live_actions(action_id):
            action.setShortcut(key_sequence)

    # ---- Persistence (hook into NyxConfig later) ----
    def export_shortcut_overrides(self) -> dict[str, str]:
        """Get the user shortcut overrides.

        Returns:
            dict[str, str]: shortcut text by action id.
        """
        return dict(self._shortcut_overrides)

    def import_shortcut_overrides(self, overrides: dict[str, str]) -> None:
        """Apply shortcut overrides, ignoring unknown actions.

        Args:
            overrides (dict[str, str]): shortcut text by action id.
        """
        for action_id, shortcut_text in overrides.items():
            if action_id not in self._definitions:
                LOGGER.warning("Ignoring shortcut for unknown action: %s", action_id)
                continue
            self.set_shortcut_override(action_id, shortcut_text)


ACTION_REGISTRY = ActionRegistry()
