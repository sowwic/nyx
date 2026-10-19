# Based on https://github.com/mCodingLLC/VideosSampleCode/blob/master/videos/124_abc_collections/main.py. #noqa: E501
from __future__ import annotations

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections.abc import MutableMapping
from typing import TypeVar

KT = TypeVar("KT")
VT = TypeVar("VT")


class InvertibleDict(MutableMapping):
    """Invertible 1-to-1 mapping"""

    __slots__ = ("_forward", "_backward")
    _forward: dict[KT, VT]
    _backward: dict[VT, KT]

    def __init__(
        self,
        forward: dict[KT, VT] | None = None,
        _backward: dict[VT, KT] | None = None,
    ) -> None:
        """Initialize InvertibleDict.

        Args:
            forward (dict[KT, VT] | None): initial items.
            _backward (dict[VT, KT] | None): prebuilt inverse mapping, used to
                create the inverse view.

        Raises:
            ValueError: if two keys map to the same value.
        """
        if forward is None:
            self._forward = {}
            self._backward = {}
        elif _backward is not None:
            self._forward = forward
            self._backward = _backward
        else:
            self._forward = forward
            self._backward = {value: key for key, value in self._forward.items()}
            self._check_non_invertible()

    def _check_non_invertible(self):
        """Check that no two keys map to the same value.

        Raises:
            ValueError: if the mapping can't be inverted.
        """
        if len(self._backward) != len(self._forward):
            for key, value in self._forward.items():
                other_key = self._backward[value]
                if other_key != key:
                    self._raise_non_invertible(key, other_key, value)

    def _raise_non_invertible(self, key1: KT, key2: KT, value: VT):
        """Raise the error for two keys sharing a value.

        Args:
            key1 (KT): first key.
            key2 (KT): second key.
            value (VT): shared value.

        Raises:
            ValueError: always.
        """
        raise ValueError(f"non-invertible: {key1}, {key2} both map to: {value}")

    @property
    def inv(self) -> InvertibleDict[KT, VT]:
        """InvertibleDict[KT, VT]: view mapping values back to keys."""
        return self.__class__(self._backward, _backward=self._forward)

    def __getitem__(self, key: KT) -> VT:
        """Get the value of a key.

        Args:
            key (KT): key.

        Returns:
            VT: value.
        """
        return self._forward[key]

    def __setitem__(self, key: KT, value: VT) -> None:
        """Set a key, keeping the inverse mapping in sync.

        Args:
            key (KT): key.
            value (VT): value.

        Raises:
            ValueError: if another key already maps to the value.
        """
        missing = object()
        old_key = self._backward.get(value, missing)
        if old_key is not missing and old_key != key:
            self._raise_non_invertible(old_key, key, value)

        old_value = self._forward.get(key, missing)
        if old_value is not missing:
            del self._backward[old_value]

        self._forward[key] = value
        self._backward[value] = key

    def __delitem__(self, key: KT) -> None:
        """Remove a key and its inverse entry.

        Args:
            key (KT): key.
        """
        value = self._forward[key]
        del self._forward[key]
        del self._backward[value]

    def __iter__(self):
        """Iterate keys."""
        return iter(self._forward)

    def __len__(self) -> int:
        """int: number of items."""
        return len(self._forward)

    def __repr__(self) -> str:
        """str: class name and items."""
        return f"{self.__class__.__name__}({self._forward})"

    def clear(self) -> None:
        """Remove all items."""
        self._forward.clear()
        self._backward.clear()
