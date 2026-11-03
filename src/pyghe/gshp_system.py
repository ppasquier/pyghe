"""GSHP system node: system type, heat pumps, auxiliary and pumps, as in the interface's
'Ground source heat pump system' panel.

Pump A circulates the fluid through the borehole field (its flow rate is the field's), pump B
serves the building side, pump C recirculates a standing column well. Pump powers change no
computed temperature or load; the flow rate of pump B enters no computation at all and is kept
for the project file.
"""

from ._base import ByMode, Node, by_mode, integer, node, non_negative, one_of, param, positive

SYSTEM_TYPES = ("Water-air (zone)", "Water-water (zone)", "Water-water (loop)",
                "Water-water (zone) - Geocooling", "Water-water (loop) - Geocooling")


def _zero():
    return ByMode(heating=0.0, cooling=0.0)


@node
class GSHPSystem(Node):
    """In a zone system each heat pump has its own auxiliary unit (power_of_auxiliary is per
    heat pump); in a loop system one unit serves them all. The geocooling variants serve
    cooling hours through a heat exchanger, without compressor."""

    system_type: str = param("", one_of(*SYSTEM_TYPES))
    number_of_heat_pumps: int = param("HP", integer(minimum=1), symbol="nHP")
    power_of_auxiliary: ByMode = param("kW", by_mode(non_negative, "kW"), factory=_zero, symbol="QAux")
    flow_rate_of_pump_a: ByMode = param("L/min", by_mode(positive, "L/min"), symbol="VA")
    power_of_pump_a: ByMode = param("kW", by_mode(non_negative, "kW"), factory=_zero, symbol="QA")
    flow_rate_of_pump_b: ByMode = param("L/min", by_mode(non_negative, "L/min"), factory=_zero, symbol="VB")
    power_of_pump_b: ByMode = param("kW", by_mode(non_negative, "kW"), factory=_zero, symbol="QB")
    flow_rate_of_pump_c: float = param("L/min", positive, symbol="VC")
    power_of_pump_c: float = param("kW", non_negative, default=0.0, symbol="QC")
