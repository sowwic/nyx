# Based on https://github.com/mCodingLLC/VideosSampleCode/blob/master/videos/124_abc_collections/main.py
from __future__ import annotations
try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping
from typing import TypeVar


KT = TypeVar("KT")
VT = TypeVar("VT")


class InvertibleDict(MutableMapping):
    """Invertible 1-to-1 mapping"""
    __slots__ = ("_forward", "_backward")
    _forward: "dict[KT, VT]"
    _backward: "dict[VT, KT]"

    def __init__(
        self,
        forward: "dict[KT, VT] | None" = None,
        _backward: "dict[VT, KT] | None" = None
    ) -> None:
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
        if len(self._backward) != len(self._forward):
            for key, value in self._forward.items():
                other_key = self._backward[value]
                if other_key != key:
                    self._raise_non_invertible(key, other_key, value)

    def _raise_non_invertible(self, key1: KT, key2: KT, value: VT):
        raise ValueError(f"non-invertible: {key1}, {key2} both map to: {value}")

    @property
    def inv(self) -> "InvertibleDict[KT, VT]":
        return self.__class__(self._backward, _backward=self._forward)

    def __getitem__(self, key: KT) -> VT:
        return self._forward[key]

    def __setitem__(self, key: KT, value: VT) -> None:
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
        value = self._forward[key]
        del self._forward[key]
        del self._backward[value]

    def __iter__(self):
        return iter(self._forward)

    def __len__(self) -> int:
        return len(self._forward)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__(self._forward)}"

    def clear(self) -> None:
        self._forward.clear()
        self._backward.clear()
