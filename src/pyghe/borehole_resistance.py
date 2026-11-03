"""Borehole resistance node: one class per borehole type of the interface's Borehole designer.
Every borehole of the field is of the same type. The active length and the burial depth are
those of the Ground heat exchanger node."""

from ._base import Node, node, non_negative, param, positive


@node
class _Borehole(Node):
    borehole_diameter: float = param("m", positive, symbol="db")
    grout_thermal_conductivity: float = param("W/m·K", positive, symbol="λg")
    pipe_inner_diameter: float = param("m", positive, symbol="di")
    pipe_outer_diameter: float = param("m", positive, symbol="do")
    pipe_thermal_conductivity: float = param("W/m·K", positive, symbol="λp")


@node
class _ULoop(_Borehole):
    shank_spacing: float = param("m", positive, symbol="s")


@node
class SingleULoop(_ULoop):
    """Single U-Loop. shank_spacing is the centre-to-centre distance between the two legs."""


@node
class DoubleULoopA(_ULoop):
    """Double U-Loop (a): the two U side by side."""


@node
class DoubleULoopD(_ULoop):
    """Double U-Loop (d): the two U crossed."""


@node
class _OuterPipe(_Borehole):
    outer_pipe_inner_diameter: float = param("m", positive, symbol="doi")
    outer_pipe_outer_diameter: float = param("m", positive, symbol="doo")
    outer_pipe_thermal_conductivity: float = param("W/m·K", positive, symbol="λo")


@node
class Coaxial(_OuterPipe):
    """Coaxial. The pipe is the inner one; borehole_diameter must exceed the outer pipe's outer
    diameter."""


@node
class StandingColumn(_OuterPipe):
    """Standing column well. The pipe is the dip tube, the outer pipe the casing; the annulus
    lies between the dip tube and the borehole wall, and the casing and the grout enter only the
    pipe resistance. The recirculation is pump C of the GSHP system; the bleed is at most 30 %
    of it."""

    bleed_flow_rate: float = param("L/min", non_negative, symbol="Vβ")


BOREHOLE_TYPES = {
    SingleULoop: "singleU",
    DoubleULoopA: "doubleUAdjacent",
    DoubleULoopD: "doubleUDiagonal",
    Coaxial: "coaxial",
    StandingColumn: "standingColumnWell",
}
