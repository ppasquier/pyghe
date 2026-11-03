"""Common machinery of the project's nodes: slots, validation on assignment, units, repr."""

import dataclasses
import math

import numpy as np

from .errors import InvalidInputError

HOURS_PER_YEAR = 8760


def param(unit="", check=None, default=None, factory=None, symbol=""):
    """A node field: its unit and symbol as the interface shows them (both printed by repr)
    and the check run on every assignment. None always means 'not set' and is never checked."""
    meta = {"unit": unit, "check": check, "symbol": symbol}
    if factory is not None:
        return dataclasses.field(default_factory=factory, metadata=meta)
    return dataclasses.field(default=default, metadata=meta)


def private():
    """A field the user does not set: not a constructor argument, not compared, not printed."""
    return dataclasses.field(default=None, init=False, metadata={"private": True})


def _public(obj):
    return [f for f in dataclasses.fields(obj) if not f.metadata.get("private")]


_checks_cache = {}


def _checks_of(cls):
    checks = _checks_cache.get(cls)
    if checks is None:
        checks = {f.name: f.metadata.get("check") for f in dataclasses.fields(cls)}
        _checks_cache[cls] = checks
    return checks


class Node:
    """Base of every node. Subclasses are dataclasses with slots, so that assigning a
    misspelt attribute raises AttributeError instead of creating a new field."""

    __slots__ = ()

    def __setattr__(self, name, value):
        check = _checks_of(type(self)).get(name)
        if check is not None and value is not None:
            value = check(value, f"{type(self).__name__}.{name}")
        object.__setattr__(self, name, value)

    def __eq__(self, other):
        if type(other) is not type(self):
            return NotImplemented
        for f in _public(self):
            a, b = getattr(self, f.name), getattr(other, f.name)
            if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
                if a is None or b is None or not np.array_equal(a, b, equal_nan=True):
                    return False
            elif a != b:
                return False
        return True

    __hash__ = None

    def __repr__(self):
        return "\n".join(self._describe())

    def _describe(self, indent=""):
        lines = [f"{indent}{type(self).__name__}"]
        for f in _public(self):
            value = getattr(self, f.name)
            symbol = f.metadata.get("symbol", "")
            name = f"{f.name} ({symbol})" if symbol else f.name
            if isinstance(value, Node):
                sub = value._describe(indent + "    ")
                lines.append(f"{indent}  {name}: {sub[0].strip()}")
                lines.extend(sub[1:])
            elif isinstance(value, ByMode):
                lines.append(f"{indent}  {name} = {value!r}")
            else:
                lines.append(f"{indent}  {name} = {_show(value, f.metadata.get('unit', ''))}")
        return lines


def _show(value, unit):
    if value is None:
        return "(not set)"
    if isinstance(value, np.ndarray):
        if value.size == 0:
            text = "[] (0 values)"
        else:
            text = f"[{value.min():.6g} … {value.max():.6g}] ({value.size} values)"
    else:
        text = repr(value)
    return f"{text} {unit}".rstrip()


# Checks. Each returns the value to store, converted, or raises InvalidInputError naming the
# attribute. Those taking settings are classes, not closures: a ByMode keeps its check, and
# pickle (multiprocessing, joblib) refuses local functions.

def real(value, where):
    if isinstance(value, bool):
        raise InvalidInputError(f"{where} must be a number, got {value!r}")
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise InvalidInputError(f"{where} must be a number, got {value!r}") from None
    if not math.isfinite(x):
        raise InvalidInputError(f"{where} must be finite, got {x}")
    return x


def positive(value, where):
    x = real(value, where)
    if x <= 0:
        raise InvalidInputError(f"{where} must be > 0, got {x}")
    return x


def non_negative(value, where):
    x = real(value, where)
    if x < 0:
        raise InvalidInputError(f"{where} must be >= 0, got {x}")
    return x


class between:
    def __init__(self, low, high, low_open=False, high_open=False):
        self.low, self.high, self.low_open, self.high_open = low, high, low_open, high_open

    def __call__(self, value, where):
        x = real(value, where)
        low, high = self.low, self.high
        if (x < low or (self.low_open and x == low)) or (x > high or (self.high_open and x == high)):
            lo = "(" if self.low_open else "["
            hi = ")" if self.high_open else "]"
            raise InvalidInputError(f"{where} must lie in {lo}{low}, {high}{hi}, got {x}")
        return x


class integer:
    def __init__(self, minimum=None, choices=None):
        self.minimum, self.choices = minimum, choices

    def __call__(self, value, where):
        if isinstance(value, bool) or not float(real(value, where)).is_integer():
            raise InvalidInputError(f"{where} must be an integer, got {value!r}")
        n = int(value)
        if self.minimum is not None and n < self.minimum:
            raise InvalidInputError(f"{where} must be >= {self.minimum}, got {n}")
        if self.choices is not None and n not in self.choices:
            raise InvalidInputError(f"{where} must be one of {', '.join(map(str, self.choices))}, got {n}")
        return n


class one_of:
    def __init__(self, *choices):
        self.choices = choices

    def __call__(self, value, where):
        if value not in self.choices:
            raise InvalidInputError(f"{where} must be one of {', '.join(map(repr, self.choices))}, got {value!r}")
        return value


class instance_of:
    def __init__(self, *classes):
        self.classes = classes

    def __call__(self, value, where):
        if not isinstance(value, self.classes):
            names = " or ".join(c.__name__ for c in self.classes)
            raise InvalidInputError(f"{where} must be a {names}, got {type(value).__name__}")
        return value


class series:
    """A read-only float64 array. Reassign the attribute to change it: an array edited in place
    would bypass the checks."""

    def __init__(self, length=None, minimum_length=1, allow_nan=False):
        self.length, self.minimum_length, self.allow_nan = length, minimum_length, allow_nan

    def __call__(self, value, where):
        try:
            a = np.array(value, dtype=np.float64, copy=True)
        except (TypeError, ValueError):
            raise InvalidInputError(f"{where} must be an array of numbers") from None
        if a.ndim != 1:
            raise InvalidInputError(f"{where} must be one-dimensional, got shape {a.shape}")
        if self.length is not None and a.size != self.length:
            raise InvalidInputError(f"{where} must hold {self.length} values, got {a.size}")
        if a.size < self.minimum_length:
            raise InvalidInputError(f"{where} must hold at least {self.minimum_length} value(s)")
        bad = ~np.isfinite(a) if not self.allow_nan else np.isinf(a)
        if bad.any():
            raise InvalidInputError(f"{where}[{int(np.argmax(bad))}] is not finite")
        a.setflags(write=False)
        return a


def node(dc=None, kw_only=True):
    """Decorator: a slotted keyword-only dataclass deriving from Node."""
    def wrap(cls):
        return dataclasses.dataclass(slots=True, kw_only=kw_only, repr=False, eq=False)(cls)
    return wrap(dc) if dc is not None else wrap


class ByMode:
    """A pair of values, one for heating and one for cooling. Assigned to a node, it takes the
    unit and the check of that attribute, which then apply to each of its two values."""

    __slots__ = ("heating", "cooling", "_check", "_unit", "_where")

    def __init__(self, heating=None, cooling=None):
        object.__setattr__(self, "_check", None)
        object.__setattr__(self, "_unit", "")
        object.__setattr__(self, "_where", "ByMode")
        self.heating = heating
        self.cooling = cooling

    def __setattr__(self, name, value):
        if name in ("heating", "cooling") and value is not None and self._check is not None:
            value = self._check(value, f"{self._where}.{name}")
        object.__setattr__(self, name, value)

    def __eq__(self, other):
        return (isinstance(other, ByMode) and self.heating == other.heating
                and self.cooling == other.cooling)

    def __deepcopy__(self, memo):
        twin = ByMode()
        for name in self.__slots__:
            object.__setattr__(twin, name, getattr(self, name))
        return twin

    def __reduce__(self):
        return _restore_by_mode, tuple(getattr(self, name) for name in self.__slots__)

    def __repr__(self):
        return (f"ByMode(heating={_show(self.heating, self._unit)}, "
                f"cooling={_show(self.cooling, self._unit)})")


def _restore_by_mode(*values):
    pair = ByMode()
    for name, value in zip(ByMode.__slots__, values):
        object.__setattr__(pair, name, value)
    return pair


class by_mode:
    """Check of an attribute holding a ByMode. Accepts a ByMode, a (heating, cooling) pair or
    a dict with those keys; returns a new ByMode bound to check and unit."""

    def __init__(self, check, unit=""):
        self.check, self.unit = check, unit

    def __call__(self, value, where):
        if isinstance(value, ByMode):
            h, c = value.heating, value.cooling
        elif isinstance(value, dict) and set(value) <= {"heating", "cooling"}:
            h, c = value.get("heating"), value.get("cooling")
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            h, c = value
        else:
            raise InvalidInputError(f"{where} must be a ByMode(heating=..., cooling=...)")
        pair = ByMode()
        object.__setattr__(pair, "_check", self.check)
        object.__setattr__(pair, "_unit", self.unit)
        object.__setattr__(pair, "_where", where)
        pair.heating = h
        pair.cooling = c
        return pair
