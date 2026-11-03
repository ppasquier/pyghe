"""Heat pump performance node. One class per 'Input type' of the interface.

Capacities and heats are in kW for ONE heat pump. Between the rows of a table, COP and
capacity are interpolated by the kernel (monotone cubic Hermite); beyond them they keep the
end values.
"""

import math

import numpy as np

from ._base import ByMode, Node, between, by_mode, instance_of, node, param, positive, series
from .errors import InvalidInputError

_column = series(allow_nan=True)


@node
class PerformanceConstant(Node):
    """Performance Constant: capacity and COP that do not depend on the entering fluid
    temperature."""

    cooling_cap: float = param("kW/HP", positive, symbol="CAP")
    cooling_cop: float = param("", positive, symbol="COP")
    heating_cap: float = param("kW/HP", positive, symbol="CAP")
    heating_cop: float = param("", positive, symbol="COP")


@node
class _Table(Node):
    eft: object = param("°C", series(minimum_length=1), symbol="EFT")

    def _columns(self):
        return {n: getattr(self, n) for n in type(self).__dataclass_fields__ if n != "eft"}

    def check_shape(self, where):
        if self.eft is None:
            raise InvalidInputError(f"{where}.eft is not set")
        if np.any(np.diff(self.eft) <= 0):
            raise InvalidInputError(f"{where}.eft must strictly increase")
        for name, col in self._columns().items():
            if col is None:
                raise InvalidInputError(f"{where}.{name} is not set")
            if col.size != self.eft.size:
                raise InvalidInputError(f"{where}.{name} holds {col.size} values, eft {self.eft.size}")


@node
class PerformanceTemperature(_Table):
    """Performance - Temperature: capacity (CAP) and COP of one heat pump at several entering
    fluid temperatures (EFT). A mode may be left out of a row by giving NaN or 0 for its two
    values."""

    cooling_cap: object = param("kW/HP", _column, symbol="CAP")
    cooling_cop: object = param("", _column, symbol="COP")
    heating_cap: object = param("kW/HP", _column, symbol="CAP")
    heating_cop: object = param("", _column, symbol="COP")


@node
class ManufacturerData(_Table):
    """Manufacturer data: total cooling (TC), heat of rejection (HR), heating capacity (HC) and
    heat of extraction (HE) at several entering fluid temperatures. The kernel derives
    COP = TC / (HR - TC) in cooling and HC / (HC - HE) in heating."""

    tc: object = param("kW", _column, symbol="TC")
    hr: object = param("kW", _column, symbol="HR")
    hc: object = param("kW", _column, symbol="HC")
    he: object = param("kW", _column, symbol="HE")


def _cop_dhw(value, where):
    """Infinity in cooling means free recovery of the condenser heat."""
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == math.inf:
        return math.inf
    return positive(value, where)


@node
class HeatPumpPerformance(Node):
    """temperature_limit: lowest entering fluid temperature allowed in heating and highest in
    cooling, in [-15, 50) °C; the borehole resistances are reported, and the fluid properties
    evaluated, at these temperatures.
    degradation_coefficient: part-load degradation coefficient, in [0, 1].
    dhw_performance: COP of domestic hot water production in heating and in cooling hours; a
    cooling value of math.inf (the default) means free recovery of the condenser heat.
    performance_data: PerformanceConstant, PerformanceTemperature or ManufacturerData.
    """

    temperature_limit: ByMode = param("°C", by_mode(between(-15.0, 50.0, high_open=True), "°C"),
                                      symbol="TLim")
    degradation_coefficient: ByMode = param("", by_mode(between(0.0, 1.0)),
                                            factory=lambda: ByMode(heating=0.0, cooling=0.0), symbol="Cd")
    dhw_performance: ByMode = param("", by_mode(_cop_dhw), factory=lambda: ByMode(heating=2.75, cooling=math.inf),
                                    symbol="COPDHW")
    performance_data: object = param("", instance_of(PerformanceConstant, PerformanceTemperature, ManufacturerData))
