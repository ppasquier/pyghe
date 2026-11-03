"""Ground heat exchanger node: the ground, the boreholes' active length and burial depth, and the
coordinate table of the field, as in the interface's GHE Designer."""

import numpy as np

from ._base import Node, instance_of, node, non_negative, param, positive, real, series
from .errors import InvalidInputError

MAX_BOREHOLES = 625


@node
class Coordinates(Node):
    """The coordinate table: borehole heads (x easting, y northing), the direction of
    inclination (az, clockwise from north) and the angle from the horizontal (dip, 90 =
    vertical), and an optional label. From 1 to 625 boreholes; two may not share a head."""

    x: object = param("m", series(minimum_length=1))
    y: object = param("m", series(minimum_length=1))
    az: object = param("deg.", series(minimum_length=0), symbol="Az.")
    dip: object = param("deg.", series(minimum_length=0), symbol="Dip.")
    label: object = param("")

    def __len__(self):
        return 0 if self.x is None else self.x.size

    @classmethod
    def from_points(cls, xy, az=None, dip=None, label=None):
        """Borehole heads from a list of points.

        Parameters
        ----------
        xy : array_like, shape (n, 2)
            Easting and northing of each head, m.
        az : array_like, optional
            Direction of inclination, clockwise from north, degrees.
        dip : array_like, optional
            Angle from the horizontal, degrees; 90 is vertical. Unset, the boreholes are vertical.
        label : sequence of str, optional

        Returns
        -------
        Coordinates
        """
        a = np.asarray(xy, dtype=np.float64)
        if a.ndim != 2 or a.shape[1] != 2:
            raise InvalidInputError(f"Coordinates.from_points: expected (x, y) pairs, got shape {a.shape}")
        return cls(x=a[:, 0], y=a[:, 1], az=az, dip=dip, label=label)

    @classmethod
    def rectangle(cls, nx, ny, spacing, origin=(0.0, 0.0)):
        """Vertical boreholes on a rectangular grid.

        Parameters
        ----------
        nx, ny : int
            Number of boreholes along x and along y.
        spacing : float
            Distance between neighbouring boreholes, m.
        origin : tuple of float, default (0, 0)
            Position of the first borehole, m.

        Returns
        -------
        Coordinates
            ``nx * ny`` boreholes.
        """
        if int(nx) < 1 or int(ny) < 1:
            raise InvalidInputError("Coordinates.rectangle: nx and ny must be >= 1")
        positive(spacing, "Coordinates.rectangle spacing")
        i, j = np.meshgrid(np.arange(int(nx)), np.arange(int(ny)), indexing="xy")
        return cls(x=origin[0] + spacing * i.ravel(), y=origin[1] + spacing * j.ravel())

    def check_shape(self, where):
        n = len(self)
        if self.x is None or self.y is None:
            raise InvalidInputError(f"{where}.x and {where}.y must be set")
        if self.y.size != n:
            raise InvalidInputError(f"{where}.y holds {self.y.size} values, x {n}")
        if not 1 <= n <= MAX_BOREHOLES:
            raise InvalidInputError(f"{where} holds {n} boreholes; 1 to {MAX_BOREHOLES} are allowed")
        for name in ("az", "dip"):
            v = getattr(self, name)
            if v is not None and v.size not in (0, n):
                raise InvalidInputError(f"{where}.{name} holds {v.size} values for {n} boreholes")
        if self.label is not None and len(self.label) != n:
            raise InvalidInputError(f"{where}.label holds {len(self.label)} values for {n} boreholes")
        unique, counts = np.unique(np.stack([self.x, self.y], axis=1), axis=0, return_counts=True)
        if (counts > 1).any():
            x, y = unique[np.argmax(counts > 1)]
            raise InvalidInputError(f"{where}: two boreholes share the head ({x:g}, {y:g})")


@node
class GroundHeatExchanger(Node):
    """The undisturbed ground temperature Tg is computed by the kernel, never given:
    Tg = T0 + (D + H/2) qg / λs, the mean of the undisturbed profile over the active length.

    groundwater_flow is the Darcy velocity in m/s (the interface shows its logarithm); leave it
    unset for no groundwater flow.
    """

    ground_thermal_conductivity: float = param("W/m·K", positive, symbol="λs")
    ground_volumetric_capacity: float = param("MJ/m³·K", positive, symbol="Cs")
    mean_surface_temperature: float = param("°C", real, symbol="T0")
    geothermal_heat_flux: float = param("mW/m²", non_negative, symbol="qg")
    groundwater_flow: float = param("m/s", positive, symbol="vD")
    groundwater_flow_direction: float = param("deg.", real, default=0.0, symbol="θ")
    active_length: float = param("m", positive, symbol="H")
    burial_depth: float = param("m", non_negative, symbol="D")
    coordinates: Coordinates = param("", instance_of(Coordinates))
