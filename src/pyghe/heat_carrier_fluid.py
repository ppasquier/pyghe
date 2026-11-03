"""Heat carrier fluid node. Properties from the Melinder (2010) correlations."""

from ._base import Node, between, node, one_of, param

FLUIDS = ("Water", "Ethylene glycol", "Methyl alcohol", "Ethyl alcohol", "Propylene glycol")


@node(kw_only=False)
class HeatCarrierFluid(Node):
    """Fluid and antifreeze mass concentration (25 for 25 %w), as in the interface."""

    fluid: str = param("", one_of(*FLUIDS))
    antifreeze_mass_concentration: float = param("%w", between(0.0, 60.0), default=0.0)
