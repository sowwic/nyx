"""Routes triggered editor actions to widget handlers.

Widgets register *handlers* for an action id, optionally scoped to themselves.
When the shared `QAction` from the `ActionRegistry` is triggered, the router runs
the handler whose scope contains the focused widget, falling back to a global
handler. It also keeps each action's enabled state in sync with handler
availability.
"""

import dataclasses
import itertools
import logging
import typing
import weakref
from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY, ActionRegistry

LOGGER = logging.getLogger("ActionRouter")


@dataclasses.dataclass(eq=False)
class _Binding:
    handle: int
    action_id: str
    handler: Callable[[], Callable[..., typing.Any] | None]
    scope: weakref.ref[QtWidgets.QWidget] | None
    enabled_fn: Callable[[], bool] | None

    def is_alive(self) -> bool:
        if self.handler() is None:
            return False
        return self.scope is None or self.scope() is not None


def _weak_callable(fn: Callable[..., typing.Any]) -> Callable[[], typing.Any]:
    if hasattr(fn, "__self__") and hasattr(fn, "__func__"):
        return weakref.WeakMethod(fn)
    return lambda: fn


class ActionRouter(QtCore.QObject):
    def __init__(
        self, registry: ActionRegistry, parent: QtCore.QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._bindings: dict[str, list[_Binding]] = {}
        self._handle_counter = itertools.count(1)
        self._focus_connected = False

        registry.action_created.connect(self._on_action_created)
        registry.cleared.connect(self.clear)
        for action_id, action in registry.iter_actions():
            self._on_action_created(action_id, action)

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    def clear(self) -> None:
        self._bindings.clear()

    # ---- Handlers ----
    def register_handler(
        self,
        action_id: str,
        handler: Callable[..., typing.Any],
        scope: QtWidgets.QWidget | None = None,
        enabled_fn: Callable[[], bool] | None = None,
    ) -> int:
        """Register `handler` for an action.

        Args:
            action_id: registered action id
            handler: callable invoked when the action triggers; bound methods
                are held weakly
            scope: handler is used while the focus is inside this widget (or its
                descendants). None registers a global fallback handler.
            enabled_fn: extra condition for the action to be enabled while this
                handler is the active one; call `refresh_enabled` when it changes

        Returns:
            handle usable with `unregister_handler`
        """
        self._registry.get_definition(action_id)
        binding = _Binding(
            handle=next(self._handle_counter),
            action_id=action_id,
            handler=_weak_callable(handler),
            scope=weakref.ref(scope) if scope is not None else None,
            enabled_fn=enabled_fn,
        )
        self._bindings.setdefault(action_id, []).insert(0, binding)
        if scope is not None:
            scope.destroyed.connect(lambda *_: self._prune(action_id))
        self.refresh_enabled(action_id)
        return binding.handle

    def unregister_handler(self, handle: int) -> None:
        for action_id, bindings in self._bindings.items():
            kept = [b for b in bindings if b.handle != handle]
            if len(kept) != len(bindings):
                self._bindings[action_id] = kept
                self.refresh_enabled(action_id)
                return

    # ---- Resolution ----
    def resolve_binding(
        self, action_id: str, focus_widget: QtWidgets.QWidget | None = None
    ) -> _Binding | None:
        """Find the active binding: scoped to the focus chain, else global."""
        self._prune(action_id, refresh=False)
        bindings = self._bindings.get(action_id, ())
        if focus_widget is None:
            focus_widget = self._current_focus_widget()

        widget = focus_widget
        while widget is not None:
            for binding in bindings:
                if binding.scope is not None and binding.scope() is widget:
                    return binding
            widget = widget.parentWidget()

        for binding in bindings:
            if binding.scope is None:
                return binding
        return None

    def resolve_handler(
        self, action_id: str, focus_widget: QtWidgets.QWidget | None = None
    ) -> Callable[..., typing.Any] | None:
        binding = self.resolve_binding(action_id, focus_widget)
        return binding.handler() if binding else None

    def dispatch(self, action_id: str) -> bool:
        """Run the active handler for `action_id`. Returns False if none."""
        handler = self.resolve_handler(action_id)
        if handler is None:
            LOGGER.warning("No handler for action: %s", action_id)
            return False
        handler()
        return True

    # ---- Enabled state ----
    def refresh_enabled(self, action_id: str | None = None) -> None:
        """Enable shared actions that currently have an active handler."""
        if action_id:
            targets = [(action_id, self._registry.existing_action(action_id))]
        else:
            targets = list(self._registry.iter_actions())
        for current_id, action in targets:
            if action is None:
                continue
            binding = self.resolve_binding(current_id)
            enabled = binding is not None and (
                binding.enabled_fn is None or bool(binding.enabled_fn())
            )
            action.setEnabled(enabled)

    # ---- Internals ----
    def _on_action_created(self, action_id: str, action: QtGui.QAction) -> None:
        action.triggered.connect(lambda _checked=False, i=action_id: self.dispatch(i))
        self.refresh_enabled(action_id)
        self._connect_focus_tracking()

    def _prune(self, action_id: str, refresh: bool = True) -> None:
        bindings = self._bindings.get(action_id)
        if not bindings:
            return
        alive = [b for b in bindings if b.is_alive()]
        if len(alive) != len(bindings):
            self._bindings[action_id] = alive
            if refresh:
                self.refresh_enabled(action_id)

    @staticmethod
    def _current_focus_widget() -> QtWidgets.QWidget | None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return None
        popup = app.activePopupWidget()
        return popup or app.focusWidget()

    def _connect_focus_tracking(self) -> None:
        if self._focus_connected:
            return
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        app.focusChanged.connect(lambda *_: self.refresh_enabled())
        self._focus_connected = True


ACTION_ROUTER = ActionRouter(ACTION_REGISTRY)
