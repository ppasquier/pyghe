"""Results of the computations, named and in the units the interface displays them: the
Borehole designer's resistances, the Sizing tool's outputs, the console's summary.

Signs are those the interface displays. A ground load in a simulation is positive when heat is
injected into the ground; the Sizing tool's ground loads qy, qm, qh are positive when heat is
extracted, as the kernel computes them (interface-spec §3).
"""

import json
import math
from pathlib import Path

import numpy as np

from ._base import ByMode, HOURS_PER_YEAR
from ._case import LITRES_PER_MINUTE, PERCENT, SERIES
from ._cli import plain, warn
from .errors import ConvergenceWarning, KernelWarning, NotConvergedError, SeriesNotRequested

_PYTHON_SERIES = {v: k for k, v in SERIES.items()}


def _num(x):
    return math.nan if x is None else float(x)


def _array(values, scale=1.0):
    if isinstance(values, np.ndarray):
        a = values if scale == 1.0 else values * scale
    else:
        a = np.array([math.nan if v is None else v for v in values], dtype=np.float64) * scale
    a.setflags(write=False)
    return a


def _pair(heating, cooling, unit="", scale=1.0):
    pair = ByMode(heating=_num(heating) * scale, cooling=_num(cooling) * scale)
    object.__setattr__(pair, "_unit", unit)
    return pair


def _modes(data, key, unit="", scale=1.0):
    return _pair(data["heating"].get(key), data["cooling"].get(key), unit, scale)


class _Record:
    """Read-only attributes with a unit each, printed by repr."""

    _units = {}
    _symbols = {}

    def __init__(self, **values):
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self).__name__} is read-only")

    def __repr__(self):
        lines = [type(self).__name__]
        for name, value in vars(self).items():
            if name.startswith("_"):
                continue
            symbol = self._symbols.get(name)
            label = f"{name} ({symbol})" if symbol else name
            unit = self._units.get(name, "")
            if isinstance(value, np.ndarray):
                text = f"[{np.nanmin(value):.6g} … {np.nanmax(value):.6g}] ({value.size} values)" if value.size else "[]"
            elif isinstance(value, (ByMode, _Record)):
                text = repr(value).replace("\n", "\n    ")
                unit = ""
            else:
                text = repr(value)
            lines.append(f"  {label} = {text} {unit}".rstrip())
        return "\n".join(lines)


class Result:
    """What one computation returned.

    status    "ok" or "notConverged"
    converged status == "ok"
    warnings  conditions reported by the kernel
    meta      versions of the executable and of its interface, command, thread count
    case      the exact case sent, as a dict
    raw       the result as the executable wrote it (interface-spec names and units)
    """

    def __init__(self, doc, case):
        self._doc = doc
        self.status = doc["statusText"]
        self.warnings = list(doc.get("warnings", []))
        self.meta = dict(doc["meta"], threads=doc.get("threads"))
        self.case = case
        self.raw = doc.get("result", {})
        self.files = doc.get("files")

    @property
    def converged(self):
        return self.status == "ok"

    def save(self, path):
        """Writes the case and the executable's output together, as JSON."""
        Path(path).write_text(json.dumps({"case": self.case, "output": plain(self._doc)}), encoding="utf-8")

    def __repr__(self):
        head = f"<{type(self).__name__} {self.meta['command']}: {self.status}"
        return head + (f", {len(self.warnings)} warning(s)>" if self.warnings else ">")


class FluidProperties(Result):
    """Fluid properties at the requested temperatures, as the Heat carrier fluid panel shows
    them."""

    def __init__(self, doc, case):
        super().__init__(doc, case)
        rows = self.raw.get("properties", [])
        self.freezing_temperature = _num(self.raw.get("freezingPoint"))      # °C
        self.temperature = _array([r["temperature"] for r in rows])           # °C
        self.density = _array([r.get("density") for r in rows])               # ρf, kg/m³
        self.specific_heat_capacity = _array([r.get("specificHeat") for r in rows])   # cp, J/kg·K
        self.thermal_conductivity = _array([r.get("thermalConductivity") for r in rows])   # kf, W/m·K
        self.viscosity = _array([r.get("dynamicViscosity") for r in rows], 1e3)  # μf, mPa·s


class _BoreholeResistances(_Record):
    """The Borehole designer's results, in heating (at TLim heating) and in cooling."""

    _symbols = {"temperature_limit": "TLim", "pipe_resistance": "Rp", "convective_resistance": "Rf",
                "internal_borehole_resistance": "Ra", "equivalent_borehole_resistance": "Rb",
                "effective_borehole_resistance": "Rb*", "borehole_efficiency": "χ"}
    _units = {"pipe_resistance": "mK/W"}


def _resistances(data):
    return _BoreholeResistances(
        temperature_limit=_modes(data, "temperature", "°C"),
        flow_rate_per_borehole=_modes(data, "flowRatePerBorehole", "L/min", LITRES_PER_MINUTE),
        pipe_resistance=_num(data.get("pipeResistance")),
        convective_resistance=_modes(data, "fluidResistance", "mK/W"),
        internal_borehole_resistance=_modes(data, "internalResistance", "mK/W"),
        equivalent_borehole_resistance=_modes(data, "boreholeResistance", "mK/W"),
        effective_borehole_resistance=_modes(data, "effectiveBoreholeResistance", "mK/W"),
        borehole_efficiency=_modes(data, "efficiency", "%", PERCENT))


class BoreholeResistanceResult(Result):
    """Borehole thermal resistance, as the Borehole designer shows it (mK/W, χ in %).

    Each value is a ByMode: heating at the heating temperature limit, cooling at the cooling
    one. With include_grid=True, `grid` holds the tables before interpolation.
    """

    def __init__(self, doc, case):
        super().__init__(doc, case)
        r = _resistances(self.raw)
        for name, value in vars(r).items():
            setattr(self, name, value)
        self.grid = None
        g = self.raw.get("grid")
        if g:
            nt, nv = len(g["temperatures"]), len(g["flowRatesPerBorehole"])

            def table(key, scale=1.0):
                return _array(g[key], scale).reshape(nt, nv)

            self.grid = _Record(
                temperature=_array(g["temperatures"]),
                flow_rate_per_borehole=_array(g["flowRatesPerBorehole"], LITRES_PER_MINUTE),
                convective_resistance=table("fluidResistance"),
                internal_borehole_resistance=table("internalResistance"),
                equivalent_borehole_resistance=table("boreholeResistance"),
                effective_borehole_resistance=table("effectiveBoreholeResistance"),
                borehole_efficiency=table("efficiency", PERCENT))

    def __repr__(self):
        return super().__repr__() + "\n" + "\n".join(repr(_resistances(self.raw)).splitlines()[1:])


class GFunctionResult(Result):
    """Temperature rise of the mean borehole wall per unit heat rate per metre of total borehole
    length, for a constant heat rate starting at t = 0, at the end of each hour.

    time: s; values: mK/W; dimensionless: 2π λs · values, the conventional g-function.
    """

    def __init__(self, doc, case):
        super().__init__(doc, case)
        self.gfunction_converged = bool(self.raw.get("converged"))
        self.values = _array(self.raw.get("values", []))
        step = float(self.raw.get("timeStep", 3600.0))
        self.time = _array(step * np.arange(1, self.values.size + 1))
        ks = case.get("ground", {}).get("conductivity", math.nan)
        self.dimensionless = _array(2.0 * math.pi * ks * self.values)


class _HeatPumpsAtLimit(_Record):
    _symbols = {"cop_at_tlim": "COP", "total_installed_capacity_at_tlim": "CAP × nHP"}


def _heat_pumps(raw):
    h = raw.get("heatPumps", {})
    return _HeatPumpsAtLimit(
        cop_at_tlim=_pair(h.get("heatingCopAtLimit"), h.get("coolingCopAtLimit")),
        total_installed_capacity_at_tlim=_pair(h.get("installedHeatingCapacity"),
                                               h.get("installedCoolingCapacity"), "kW"))


class Hourly:
    """Hourly series of a simulation, numpy arrays of years × 8760 values (index k = hour k;
    a temperature is the value at the end of the hour). Reading a series the simulation was not
    asked for raises SeriesNotRequested."""

    _units = {"entering_fluid_temperature": "°C", "leaving_fluid_temperature": "°C",
              "fluid_temperature_difference": "K", "ground_load": "kW", "building_load": "kW",
              "dhw_load": "kW", "heat_pump_load": "kW", "auxiliary_load": "kW", "dhw_covered": "kW",
              "effective_capacity": "kW", "effective_borehole_resistance": "mK/W",
              "fluid_resistance": "mK/W"}

    def __init__(self, raw_hourly):
        object.__setattr__(self, "_series", {_PYTHON_SERIES[k]: _array(v) for k, v in raw_hourly.items()
                                             if k in _PYTHON_SERIES})

    def __getattr__(self, name):
        series = object.__getattribute__(self, "_series")
        if name in series:
            return series[name]
        if name in SERIES:
            raise SeriesNotRequested(
                f"the series {name!r} was not computed; run p.simulate(series=[..., {name!r}]) "
                f"or p.simulate(series='all')")
        raise AttributeError(f"Hourly has no series {name!r}; available: {', '.join(SERIES)}")

    def __setattr__(self, name, value):
        raise AttributeError("Hourly is read-only")

    def __dir__(self):
        return list(self._series)

    @property
    def names(self):
        """Names of the series this simulation holds."""
        return list(self._series)

    def __repr__(self):
        lines = ["Hourly"]
        for name, a in self._series.items():
            lines.append(f"  {name} = [{np.nanmin(a):.6g} … {np.nanmax(a):.6g}] ({a.size} values) "
                         f"{self._units.get(name, '')}".rstrip())
        return "\n".join(lines)


class _Summary(_Record):
    _units = {"minimum_eft": "°C", "maximum_eft": "°C", "hours_below_temperature_limit": "h",
              "hours_above_temperature_limit": "h", "hours_below_r_cop_range": "h",
              "hours_above_r_cop_range": "h"}


class SimulationResult(Result):
    """Hourly simulation of the field coupled to the heat pumps.

    hourly: the requested series (shortcut eft); daily and monthly: mean EFT of each day and
    month; summary: extremes and hours outside the limits, as on the console; tg: undisturbed
    ground temperature; borehole_resistance: the Borehole designer's results;
    heat_pumps: COP and installed capacity at the temperature limits.
    """

    def __init__(self, doc, case):
        super().__init__(doc, case)
        raw = self.raw
        self.gfunction_converged = bool(raw.get("gFunctionConverged"))
        self.iterations = raw.get("iterations")
        res = raw.get("residuals", {})
        self.residuals = _Record(eft=_num(res.get("enteringFluidTemperature")),        # K
                                 ground_load=_num(res.get("groundLoad")))               # kW
        self.undisturbed_ground_temperature = _num(raw.get("undisturbedGroundTemperature"))   # Tg, °C
        self.borehole_resistance = _resistances(raw.get("boreholeResistance", {"heating": {}, "cooling": {}}))
        self.heat_pumps = _heat_pumps(raw)
        self.hourly = Hourly(raw.get("hourly", {}))
        self.daily_eft = _array(raw.get("daily", {}).get("enteringFluidTemperature", []))
        self.monthly_eft = _array(raw.get("monthly", {}).get("enteringFluidTemperature", []))
        s = raw.get("summary", {})
        self.summary = _Summary(
            minimum_eft=_num(s.get("minimumEnteringFluidTemperature")),
            maximum_eft=_num(s.get("maximumEnteringFluidTemperature")),
            hours_below_temperature_limit=s.get("hoursBelowMinimumHeatingEFT"),
            hours_above_temperature_limit=s.get("hoursAboveMaximumCoolingEFT"),
            hours_below_r_cop_range=s.get("hoursBelowResistanceTables"),
            hours_above_r_cop_range=s.get("hoursAboveResistanceTables"),
            peak_heat_pump_load=_pair(s.get("peakHeatPumpHeatingLoad"), s.get("peakHeatPumpCoolingLoad"), "kW"),
            peak_ground_load=_pair(s.get("peakLinearGroundLoadHeating"), s.get("peakLinearGroundLoadCooling"), "W/m"))
        self.gfunction = _array(raw["gFunction"]) if "gFunction" in raw else None

    @property
    def eft(self):
        """Entering fluid temperature, hourly (°C)."""
        return self.hourly.entering_fluid_temperature

    def __repr__(self):
        lines = [super().__repr__(),
                 f"  iterations = {self.iterations}, residuals: EFT {self.residuals.eft:.3g} K, "
                 f"ground load {self.residuals.ground_load:.3g} kW",
                 f"  undisturbed_ground_temperature (Tg) = {self.undisturbed_ground_temperature:.6g} °C",
                 "  hourly: " + ", ".join(self.hourly.names)]
        lines += repr(self.summary).splitlines()[1:]
        return "\n".join(lines)

    def to_dataframe(self):
        """The hourly series as a pandas DataFrame indexed by hour, with columns year and day
        (1-based; the kernel has no calendar and no leap day)."""
        import pandas as pd

        data = {name: getattr(self.hourly, name) for name in self.hourly.names}
        n = len(next(iter(data.values()))) if data else 0
        hour = np.arange(n)
        frame = pd.DataFrame(data, index=pd.Index(hour, name="hour"))
        frame.insert(0, "year", hour // HOURS_PER_YEAR + 1)
        frame.insert(1, "day", (hour % HOURS_PER_YEAR) // 24 + 1)
        return frame


class _SizingOutputs(_Record):
    _symbols = {"yearly_ground_load": "qy", "monthly_ground_load": "qm", "hourly_ground_load": "qh",
                "yearly_response_factor": "Rgy", "monthly_response_factor": "Rgm",
                "hourly_peak_response_factor": "Rgh", "effective_borehole_resistance": "Rb*",
                "dt": "dT", "total_borehole_length": "L", "active_length": "H",
                "mean_fluid_temperature": "Tm", "undisturbed_ground_temperature": "Tg"}


def _sizing_outputs(raw):
    def sub(key, inner):
        return _pair(raw["heating"].get(key, {}).get(inner), raw["cooling"].get(key, {}).get(inner))

    def pair(key, unit):
        return _modes(raw, key, unit)

    out = dict(
        yearly_ground_load=sub("groundLoadPulses", "yearly"),
        monthly_ground_load=sub("groundLoadPulses", "monthly"),
        hourly_ground_load=sub("groundLoadPulses", "peak"),
        yearly_response_factor=sub("groundResistances", "yearly"),
        monthly_response_factor=sub("groundResistances", "monthly"),
        hourly_peak_response_factor=sub("groundResistances", "peak"),
        effective_borehole_resistance=pair("effectiveBoreholeResistance", "mK/W"),
        dt=pair("fluidTemperatureDifference", "K"),
        total_borehole_length=pair("totalLength", "m"),
        active_length=pair("lengthPerBorehole", "m"),
        mean_fluid_temperature=pair("meanFluidTemperature", "°C"),
        undisturbed_ground_temperature=pair("undisturbedGroundTemperature", "°C"))
    for name in ("yearly_ground_load", "monthly_ground_load", "hourly_ground_load"):
        object.__setattr__(out[name], "_unit", "kW")
    for name in ("yearly_response_factor", "monthly_response_factor", "hourly_peak_response_factor"):
        object.__setattr__(out[name], "_unit", "mK/W")
    return out


class SizingResult(Result):
    """The Sizing tool's outputs, in heating and in cooling (each a ByMode), from the
    three-pulse method: L = (qy Rgy + qm Rgm + qh Rgh + qh Rb*) / (Tg - Tm).

    governing_mode is the mode needing the longer field, governing_total_borehole_length its L.
    The ground loads are positive when heat is extracted from the ground. The sizing has no
    convergence verdict (open in the application): `converged` only says that the executable
    returned, and the package checks that the lengths are finite.
    """

    def __init__(self, doc, case):
        super().__init__(doc, case)
        for name, value in _sizing_outputs(self.raw).items():
            setattr(self, name, value)
        self.heat_pumps = _heat_pumps(self.raw)
        L = self.total_borehole_length
        finite = [m for m in ("heating", "cooling") if math.isfinite(getattr(L, m))]
        self.governing_mode = max(finite, key=lambda m: getattr(L, m)) if finite else None
        self.governing_total_borehole_length = getattr(L, self.governing_mode) if finite else math.nan

    def __repr__(self):
        return (super().__repr__() + f"\n  governing_mode = {self.governing_mode!r}"
                f"\n  governing_total_borehole_length = {self.governing_total_borehole_length:.6g} m\n"
                + "\n".join(repr(_SizingOutputs(**_sizing_outputs(self.raw))).splitlines()[1:]))


_READINGS = {"deltaT": "Temp. perturbation", "temperature": "Ground Temp."}


class _ThermalPlume(Result):
    def __init__(self, doc, case):
        super().__init__(doc, case)
        raw = self.raw
        self.time = raw.get("hours")                                          # h
        self.reading = _READINGS.get(raw.get("reading"), raw.get("reading"))
        self.unit = "°C" if raw.get("reading") == "temperature" else "K"
        self.undisturbed_ground_temperature = _num(raw.get("undisturbedGroundTemperature"))  # Tg, °C
        self.simulation_converged = bool(raw.get("simulationConverged"))
        self.x = _array(raw.get("x", []))                                     # m, ascending
        self.y = _array(raw.get("y", []))                                     # m, ascending

    def _describe(self, shape):
        v = self.values
        return (f"{super().__repr__()}\n  time = {self.time} h, reading = {self.reading!r}\n"
                f"  grid {shape}, values [{np.nanmin(v):.6g} … {np.nanmax(v):.6g}] {self.unit}")


class ThermalPlume2DResult(_ThermalPlume):
    """The 2D plume on the interface's grid: x (m, ascending, nx values), y (m, ascending, ny
    values) and values[iy, ix] (ny × nx), in K for "Temp. perturbation" and °C for "Ground
    Temp." (Tg + ΔT; the 2D plume is the section at mid-length, where the undisturbed ground is
    at Tg). The grid gathers the base grid around each borehole (300 m window), so it is
    irregular, finer near the boreholes."""

    def __init__(self, doc, case):
        super().__init__(doc, case)
        values = _array(self.raw.get("values", []))
        self.values = values.reshape(self.y.size, self.x.size) if values.size else values

    def __repr__(self):
        return self._describe(f"{self.y.size} × {self.x.size} (y × x)")


class ThermalPlume3DResult(_ThermalPlume):
    """The 3D plume on the grid the interface fits to the plume: x, y (m, ascending), z (depth
    below the ground surface, m, ascending) and values[iz, iy, ix] (nz × ny × nx), in K for
    "Temp. perturbation" and °C for "Ground Temp." (Tu(z) + ΔT, Tu the undisturbed profile).
    The grid is graded: uniform over the field, coarser outward; layers refined at the head and
    the toe of the boreholes."""

    def __init__(self, doc, case):
        super().__init__(doc, case)
        self.z = _array(self.raw.get("z", []))
        values = _array(self.raw.get("values", []))
        self.values = values.reshape(self.z.size, self.y.size, self.x.size) if values.size else values

    def __repr__(self):
        return self._describe(f"{self.z.size} × {self.y.size} × {self.x.size} (z × y × x)")


_CLASSES = {
    "fluid properties": FluidProperties,
    "ghe resistance": BoreholeResistanceResult,
    "ghe gfunction": GFunctionResult,
    "ghe simulation": SimulationResult,
    "ghe sizing": SizingResult,
    "ghe plume2d": ThermalPlume2DResult,
    "ghe plume3d": ThermalPlume3DResult,
}


def make(doc, case, strict=False):
    """The result object of the executable's output; reports non-convergence."""
    result = _CLASSES[doc["meta"]["command"]](doc, case)
    if isinstance(result, SizingResult) and result.governing_mode is None:
        warn("ghe sizing: no finite borehole length was found", KernelWarning)
    if not result.converged:
        message = f"{result.meta['command']}: the computation did not converge"
        if strict:
            raise NotConvergedError(message, result)
        warn(message, ConvergenceWarning)
    return result


def load_result(path):
    """Reads back a result written by :meth:`Result.save`, with the case that produced it.

    Parameters
    ----------
    path : str or pathlib.Path

    Returns
    -------
    Result
        A result of the class of the computation that was saved.
    """
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    return _CLASSES[saved["output"]["meta"]["command"]](saved["output"], saved["case"])
