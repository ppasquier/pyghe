"""The project: one attribute per node of the Analysis Tree of GHE Analysis."""

import copy
import json
from pathlib import Path

from . import _case, _cli
from ._base import Node, instance_of, integer, node, param, private, real
from .borehole_resistance import BOREHOLE_TYPES, StandingColumn, _OuterPipe, _ULoop
from .building_loads import (BUILDING_LOAD_TYPES, HourlyBuildingLoadsCombined, HourlyBuildingLoadsSeparate,
                             HourlyGroundLoadsCombined, MonthlyBuildingLoadsSeparate)
from .errors import InvalidInputError
from .ground_heat_exchanger import GroundHeatExchanger
from .gshp_system import GSHPSystem
from .heat_carrier_fluid import HeatCarrierFluid
from .heat_pump_performance import HeatPumpPerformance, PerformanceConstant, _Table
from .results import make

DURATIONS = (1, 3, 5, 10, 15, 20, 25, 50)


def _text(value, where):
    if not isinstance(value, str):
        raise InvalidInputError(f"{where} must be a string")
    return value


@node
class ProjectDescription(Node):
    """Project information. Carried with the project and its case files, never computed."""

    project_name: str = param("", _text)
    project_no: str = param("", _text)
    client_name: str = param("", _text)
    address: str = param("", _text)
    city: str = param("", _text)
    prov_state: str = param("", _text)
    postal_code: str = param("", _text)
    country: str = param("", _text)
    longitude: float = param("deg.", real)
    latitude: float = param("deg.", real)
    general_notes: str = param("", _text)


@node
class SizingTool(Node):
    """Durations of the yearly pulse qy and of the hourly peak pulse qh of the three-pulse
    sizing method."""

    duration_of_yearly_pulse: int = param("y", integer(choices=DURATIONS), symbol="ty")
    duration_of_hourly_peak_pulse: int = param("h", integer(choices=(1, 6)), symbol="th")


@node
class Project(Node):
    """A GHE Analysis project, with one attribute per node of the Analysis Tree.

    Units are those the interface shows in SI mode. Assignment shares objects, as everywhere in
    Python: ``q = p`` does not copy ``p``; use :meth:`copy`.

    Attributes
    ----------
    project_description : ProjectDescription
        Project description; never used in a computation.
    simulation_duration : int
        Simulation duration of the toolbar: 1, 3, 5, 10, 15, 20, 25 or 50 years.
    building_loads : HourlyBuildingLoadsCombined, HourlyBuildingLoadsSeparate, ...
        Building loads, one class per type of thermal load: also HourlyGroundLoadsCombined and
        MonthlyBuildingLoadsSeparate.
    gshp_system : GSHPSystem
        GSHP system: heat pumps, pumps and auxiliary heating.
    heat_pump_performance : HeatPumpPerformance
        Temperature limits and performance of one heat pump.
    heat_carrier_fluid : HeatCarrierFluid
        Heat carrier fluid.
    borehole_resistance : SingleULoop, DoubleULoopA, DoubleULoopD, Coaxial or StandingColumn
        Borehole, one class per type.
    ground_heat_exchanger : GroundHeatExchanger
        Ground properties, borehole length and field layout.
    sizing_tool : SizingTool
        Durations of the pulses of the Sizing tool.

    Examples
    --------
    >>> p = ga.Project.load("my_project.ghe")
    >>> p.ground_heat_exchanger.active_length = 180
    >>> p.simulate().eft.min()
    """

    project_description: ProjectDescription = param("", instance_of(ProjectDescription),
                                                    factory=ProjectDescription)
    simulation_duration: int = param("years", integer(choices=DURATIONS))
    building_loads: object = param("", instance_of(*BUILDING_LOAD_TYPES))
    gshp_system: GSHPSystem = param("", instance_of(GSHPSystem), factory=GSHPSystem)
    heat_pump_performance: HeatPumpPerformance = param("", instance_of(HeatPumpPerformance),
                                                       factory=HeatPumpPerformance)
    heat_carrier_fluid: HeatCarrierFluid = param("", instance_of(HeatCarrierFluid))
    borehole_resistance: object = param("", instance_of(*BOREHOLE_TYPES))
    ground_heat_exchanger: GroundHeatExchanger = param("", instance_of(GroundHeatExchanger),
                                                       factory=GroundHeatExchanger)
    sizing_tool: SizingTool = param("", instance_of(SizingTool), factory=SizingTool)
    _source: str = private()

    @property
    def source_file(self):
        """The project file this project was loaded from or last saved to, or None."""
        return self._source

    def copy(self):
        """Independent deep copy of the project, to build a variant without changing the original."""
        return copy.deepcopy(self)

    # Case files

    def to_case(self):
        """Case of AnalysisSuite-cli describing this project.

        Returns
        -------
        dict
            The JSON case, with the names of the executable (``docs/interface-spec.md``).
        """
        return _case.to_case(self)

    @classmethod
    def from_case(cls, case):
        """Project described by a case of AnalysisSuite-cli.

        Parameters
        ----------
        case : dict, str or pathlib.Path
            The case, or the path of a JSON file holding it.

        Returns
        -------
        Project
        """
        if isinstance(case, (str, Path)):
            case = json.loads(Path(case).read_text(encoding="utf-8"))
        return _case.from_case(case)

    @classmethod
    def load(cls, path, **run):
        """Project read from a project file of GHE Analysis or Analysis Suite.

        The file is read by the application's own reader, so the kernel receives what the
        application sends once the project is open. The base map, the energy and project costs
        and the report content are not read.

        Parameters
        ----------
        path : str or pathlib.Path
            A ``.ghe`` file, of any version the application opens.

        Returns
        -------
        Project
            The project; :attr:`source_file` is set to ``path``.

        Raises
        ------
        InvalidInputError
            The heat pumps come from the Keymark database, or an old project with a hot water
            load stores no hot water COP.
        """
        unknown = set(run) - {"threads", "timeout", "keep_files"}
        if unknown:
            raise TypeError(f"unexpected keyword argument(s): {', '.join(sorted(unknown))}")
        path = str(Path(path).resolve())
        doc = _cli.run("ghe project", {"project": path}, **run)
        p = _case.from_case(doc["result"]["case"])
        p._source = path
        return p

    def save(self, path=None, *, overwrite=False, **run):
        """Writes the project as a ``.ghe`` file that the application opens.

        No results are written: the application computes them when it opens the file. A project
        loaded from a file is written over that file's content, so what the package does not
        read (base map, costs, report texts, the TRT and GLN parts) is kept as it was. A project
        built in Python gets, for what it does not describe, the values of a new project.

        Parameters
        ----------
        path : str or pathlib.Path, optional
            File to write. Omitted, the file the project was loaded from or last saved to, which
            is then overwritten.
        overwrite : bool, default False
            Replace an existing file.

        Returns
        -------
        pathlib.Path
            The path written.

        Raises
        ------
        InvalidInputError
            A value that the application would repair or bound when opening the file.
        """
        unknown = set(run) - {"threads", "timeout", "keep_files"}
        if unknown:
            raise TypeError(f"unexpected keyword argument(s): {', '.join(sorted(unknown))}")
        if path is None:
            if self._source is None:
                raise ValueError("this project comes from no file: give the path to write")
            path, overwrite = self._source, True
        self._require("simulate")
        from . import __version__
        payload = dict(_case.to_case(self))
        payload.update(project=str(Path(path).resolve()), overwrite=bool(overwrite),
                       writer=f"pyghe {__version__}")
        if self._source is not None:
            payload["base"] = self._source
        doc = _cli.run("ghe save-project", payload, **run)
        self._source = doc["result"]["project"]
        return Path(self._source)

    def save_case(self, path):
        """Writes the case of the project (:meth:`to_case`) as a JSON file."""
        Path(path).write_text(json.dumps(self.to_case(), indent=2), encoding="utf-8")

    # Validation

    def validate(self, command="simulate"):
        """Lists what the project still lacks for a computation, without raising.

        Parameters
        ----------
        command : {'borehole_resistance', 'gfunction', 'simulate', 'size'}
            The computation about to be run; only what it needs is checked.

        Returns
        -------
        list of str
            One sentence per problem; empty when the project is complete.
        """
        return _missing(self, command)

    def _require(self, command):
        problems = _missing(self, command)
        if problems:
            raise InvalidInputError("the project is incomplete:\n  " + "\n  ".join(problems))

    # Computations

    def compute_borehole_resistance(self, include_grid=False, **run):
        """Borehole thermal resistances at the two temperature limits (Borehole designer).

        Parameters
        ----------
        include_grid : bool, default False
            Also return the tables of resistances over temperature and flow rate from which the
            kernel interpolates.
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        BoreholeResistanceResult

        Notes
        -----
        Single U-loop: first-order multipole formulas (Bennet et al., 1987) in the explicit form of
        Javed & Spitler (2017, eq. 26). Double U-loop: explicit multipole formulas of Claesson &
        Javed (2019). Coaxial and standing column well: thermal network of Lamarche (2023, eq. 5.96
        to 5.98). Convective resistance from the correlations given by Lamarche (2023, chapter 2).
        The effective resistance Rb* is the mean of its values under a uniform heat flux and a
        uniform wall temperature (Claesson & Javed, 2019).

        References
        ----------
        - Bennet, J., Claesson, J., Hellström, G., 1987. Multipole method to compute the
          conductive heat flows to and between pipes in a composite cylinder. Notes on Heat
          Transfer 3, University of Lund.
        - Javed, S., Spitler, J.D., 2017. Accuracy of borehole thermal resistance
          calculation methods for grouted single U-tube ground heat exchangers. Applied Energy
          187, 790–806.
        - Claesson, J., Javed, S., 2019. Explicit multipole formulas and thermal network
          models for calculating thermal resistances of double U-pipe borehole heat exchangers.
          Science and Technology for the Built Environment 25(8), 980–992.
        - Lamarche, L., 2023. Fundamentals of geothermal heat pump systems: design and
          application. Springer, Cham.
        """
        self._require("borehole_resistance")
        case = self.to_case()
        if include_grid:
            case["options"] = {"includeGrid": True}
        return _compute("ghe resistance", case, run)

    def compute_gfunction(self, **run):
        """g-function: thermal response of the field to a constant heat rate.

        Parameters
        ----------
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        GFunctionResult

        Notes
        -----
        The response between boreholes is the moving finite line source with buried depth (Guo et
        al., 2020), or its inclined counterpart when a borehole is inclined (Marcotte & Pasquier,
        2009). The field's g-function is built under a uniform borehole wall temperature by
        successive flux estimation (Pasquier & Marcotte, 2013; Nguyen & Pasquier, 2021). A standing
        column well uses the analytical model of Nguyen et al. (2025), improved by
        Jacques et al. (2025).

        References
        ----------
        - Guo, Y., Hu, X., Banks, J., Liu, W.V., 2020. Considering buried depth in the
          moving finite line source model for vertical borehole heat exchangers. Energy and
          Buildings 214, 109859.
        - Marcotte, D., Pasquier, P., 2009. The effect of borehole inclination on fluid and
          ground temperature for GLHE systems. Geothermics 38(4), 392–398.
        - Pasquier, P., Marcotte, D., 2013. Efficient computation of heat flux signals to
          ensure the reproduction of prescribed temperatures at several interacting heat
          sources. Applied Thermal Engineering 59, 515–526.
        - Nguyen, A., Pasquier, P., 2021. A successive flux estimation method for rapid
          g-function construction of small to large-scale ground heat exchangers. Renewable
          Energy 165, 359–368.
        - Nguyen, A., Jacques, L., Pasquier, P., 2025. An easy-to-use analytical model for
          standing column wells operating with bleed. Applied Thermal Engineering 258, 124543.
        - Jacques, L., Pasquier, P., Nguyen, A., Beaudry, G., 2025. Improvement and
          experimental validation of an analytical model for standing column wells operated
          with bleed. Applied Thermal Engineering 279, 127620.
        """
        self._require("gfunction")
        case = self.to_case()
        return _compute("ghe gfunction", case, run)

    def simulate(self, series=None, include_gfunction=False, **run):
        """Hourly simulation of the field coupled to the heat pumps, over the simulation duration.

        Parameters
        ----------
        series : None, 'all' or list of str, optional
            Hourly series to return. None: the entering fluid temperature and the effective COP
            (``ga.DEFAULT_SERIES``); ``'all'``: the twenty series; a list: the series it names
            (``ga.SERIES``).
        include_gfunction : bool, default False
            Also return the g-function used.
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        SimulationResult

        Notes
        -----
        The borehole wall temperature is the convolution of the ground load with the g-function,
        evaluated in the spectral domain for the whole simulation at once (Marcotte & Pasquier,
        2008; Pasquier et al., 2013), with the quasi-3D response of the borehole (Pasquier &
        Marcotte, 2014). A fixed-point iteration couples the heat pumps and the ground; it stops when the entering fluid temperature changes by less than
        1e-3 K and the ground load by less than 0.1 kW.

        References
        ----------
        - Marcotte, D., Pasquier, P., 2008. Fast fluid and ground temperature computation
          for geothermal ground-loop heat exchanger systems. Geothermics 37(6), 651–665.
        - Pasquier, P., Marcotte, D., Bernier, M., Kummert, M., 2013. Simulation of
          ground-coupled heat pump systems using a spectral approach. Proceedings of the 13th
          Conference of IBPSA, Chambéry, 2691–2698.
        - Pasquier, P., Marcotte, D., 2014. Joint use of quasi-3D response model and
          spectral method to simulate borehole heat exchanger. Geothermics 51, 281–299.
        """
        self._require("simulate")
        case = self.to_case()
        options = {}
        names = _case.series_option(series)
        if names is not None:
            options["series"] = names
        if include_gfunction:
            options["includeGFunction"] = True
        if options:
            case["options"] = options
        return _compute("ghe simulation", case, run)

    def size(self, **run):
        """Sizing tool: total borehole length required in each mode.

        Parameters
        ----------
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        SizingResult

        Notes
        -----
        Three-pulse method of the ASHRAE handbook (Kavanaugh & Rafferty, 1997), in the form revised
        by Ahmadfard & Bernier (2018):
        L = (qy·Rgy + qm·Rgm + qh·Rgh + qh·Rb*) / (Tg − Tm), the response factors being read from
        the g-function of the field. The method has no convergence flag; the package checks that
        the lengths are finite.

        References
        ----------
        - Kavanaugh, S.P., Rafferty, K., 1997. Ground-source heat pumps: design of
          geothermal systems for commercial and institutional buildings. ASHRAE, Atlanta.
        - Ahmadfard, M., Bernier, M., 2018. Modifications to ASHRAE's sizing method for
          vertical ground heat exchangers. Science and Technology for the Built Environment 24,
          803–817.
        """
        self._require("size")
        case = self.to_case()
        return _compute("ghe sizing", case, run)

    def compute_thermal_plume_2d(self, time, reading="Temp. perturbation", **run):
        """Thermal plume of the 2D view of the Ground heat exchanger panel.

        The simulation is run first, and its hourly ground load is superposed on the response
        of each borehole: moving infinite line sources, at mid-length, over a 300 m window around
        each borehole.

        Parameters
        ----------
        time : int
            Hours since commissioning, at least 1.
        reading : {'Temp. perturbation', 'Ground Temp.'}
            ΔT in K, or the undisturbed ground temperature plus ΔT in °C.
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        ThermalPlume2DResult
            The field on the interface's grid, ``values[iy, ix]``.

        Notes
        -----
        The response of each borehole is the moving infinite line source (Pasquier & Lamarche,
        2022).

        References
        ----------
        - Pasquier, P., Lamarche, L., 2022. Analytic expressions for the moving infinite line
          source model. Geothermics 103, 102413.
        """
        self._require("simulate")
        case = self.to_case()
        case["plume"] = {"hours": _plume_time(time), "reading": _plume_reading(reading)}
        return _compute("ghe plume2d", case, run)

    def compute_thermal_plume_3d(self, time, reading="Temp. perturbation", contour_min=None,
                                 contour_max=None, num_of_contours=10, **run):
        """Thermal plume of the 3D view of the Ground heat exchanger panel.

        The simulation is run first, and its hourly ground load is superposed on moving finite
        line sources with buried depth (Guo et al., 2020), for vertical boreholes.

        Parameters
        ----------
        time : int
            Hours since commissioning, at least 1.
        reading : {'Temp. perturbation', 'Ground Temp.'}
            ΔT in K, or Tu(z) + ΔT in °C, Tu being the undisturbed profile (equal to Tg at
            mid-length).
        contour_min, contour_max : float, optional
            Lowest and highest contour levels, in the terms of the reading. Give both or neither;
            unset, ten levels of ΔT from 0.1 to 1.0 K.
        num_of_contours : int, default 10
            Number of levels. The grid is fitted to the region the smallest level reaches.
        threads, timeout, keep_files, strict
            Common to every computation; see :doc:`../many-cases` and :doc:`../errors`.

        Returns
        -------
        ThermalPlume3DResult
            The field on that grid, ``values[iz, iy, ix]``, z being the depth.

        References
        ----------
        - Guo, Y., Hu, X., Banks, J., Liu, W.V., 2020. Considering buried depth in the
          moving finite line source model for vertical borehole heat exchangers. Energy and
          Buildings 214, 109859.
        """
        self._require("simulate")
        case = self.to_case()
        plume = {"hours": _plume_time(time), "reading": _plume_reading(reading)}
        if contour_min is not None or contour_max is not None:
            if contour_min is None or contour_max is None:
                raise InvalidInputError("give both contour_min and contour_max, or neither")
            n = int(num_of_contours)
            if n < 1:
                raise InvalidInputError("num_of_contours must be >= 1")
            lo, hi = float(contour_min), float(contour_max)
            plume["levels"] = [lo] if n == 1 else [lo + (hi - lo) * i / (n - 1) for i in range(n)]
        case["plume"] = plume
        return _compute("ghe plume3d", case, run)


PLUME_READINGS = {"Temp. perturbation": "deltaT", "Ground Temp.": "temperature"}


def _plume_reading(reading):
    if reading not in PLUME_READINGS:
        raise InvalidInputError(f"reading must be one of {', '.join(map(repr, PLUME_READINGS))}, got {reading!r}")
    return PLUME_READINGS[reading]


def _plume_time(time):
    if isinstance(time, bool) or not float(time).is_integer() or int(time) < 1:
        raise InvalidInputError(f"time must be a whole number of hours >= 1, got {time!r}")
    return int(time)


def fluid_properties(fluid, temperatures, **run):
    """Properties of a heat carrier fluid at the given temperatures.

    Parameters
    ----------
    fluid : HeatCarrierFluid
        The fluid and its antifreeze concentration.
    temperatures : array_like
        Temperatures, °C.
    threads, timeout, keep_files
        Common to every computation; see :doc:`../many-cases`.

    Returns
    -------
    FluidProperties

    Notes
    -----
    Polynomial correlations of Melinder (2010), in temperature and mass concentration.

    References
    ----------
    - Melinder, Å., 2010. Properties of secondary working fluids (secondary refrigerants or
      coolants, heat transfer fluids) for indirect systems. International Institute of
      Refrigeration, Paris.

    Examples
    --------
    >>> water = ga.HeatCarrierFluid("Water", antifreeze_mass_concentration=0)
    >>> ga.fluid_properties(water, [10]).density
    array([998.78766858])
    """
    if not isinstance(fluid, HeatCarrierFluid) or fluid.fluid is None:
        raise InvalidInputError("fluid_properties: give a HeatCarrierFluid with its fluid set")
    case = _case.fluid_case(fluid, temperatures)
    return _compute("fluid properties", case, run)


def _compute(command, case, run):
    """Runs one command. run: threads, timeout, keep_files, and strict (raise
    NotConvergedError instead of warning when the computation did not converge)."""
    unknown = set(run) - {"threads", "timeout", "keep_files", "strict"}
    if unknown:
        raise TypeError(f"unexpected keyword argument(s): {', '.join(sorted(unknown))}")
    run = dict(run)
    strict = run.pop("strict", False)
    return make(_cli.run(command, case, **run), case, strict)


def _unset(node, names, where):
    return [f"{where}.{n} is not set" for n in names if getattr(node, n) is None]


def _missing(p, command):
    if command not in ("borehole_resistance", "gfunction", "simulate", "size"):
        raise ValueError(f"unknown command {command!r}")
    out = []

    def shape(check):
        try:
            check()
        except InvalidInputError as e:
            out.append(str(e))

    ghe = p.ground_heat_exchanger
    b = p.borehole_resistance
    is_well = isinstance(b, StandingColumn)
    if b is None:
        out.append("p.borehole_resistance is not set")
    else:
        names = ["borehole_diameter", "grout_thermal_conductivity", "pipe_inner_diameter",
                 "pipe_outer_diameter", "pipe_thermal_conductivity"]
        if isinstance(b, _ULoop):
            names.append("shank_spacing")
        if isinstance(b, _OuterPipe):
            names += ["outer_pipe_inner_diameter", "outer_pipe_outer_diameter", "outer_pipe_thermal_conductivity"]
        if is_well:
            names.append("bleed_flow_rate")
        out += _unset(b, names, "p.borehole_resistance")

    out += _unset(ghe, ["active_length", "burial_depth", "coordinates"], "p.ground_heat_exchanger")
    if ghe.coordinates is not None:
        shape(lambda: ghe.coordinates.check_shape("p.ground_heat_exchanger.coordinates"))
    ground = ["ground_thermal_conductivity"]
    if command != "borehole_resistance":
        ground += ["ground_volumetric_capacity", "mean_surface_temperature", "geothermal_heat_flux"]
        if p.simulation_duration is None:
            out.append("p.simulation_duration is not set")
    out += _unset(ghe, ground, "p.ground_heat_exchanger")

    s = p.gshp_system
    if command != "gfunction" or is_well:
        if s.flow_rate_of_pump_a is None:
            out.append("p.gshp_system.flow_rate_of_pump_a is not set")
        else:
            out += _unset(s.flow_rate_of_pump_a, ["heating", "cooling"], "p.gshp_system.flow_rate_of_pump_a")
        if is_well:
            out += _unset(s, ["flow_rate_of_pump_c"], "p.gshp_system")

    hp = p.heat_pump_performance
    if command in ("borehole_resistance", "simulate", "size"):
        if p.heat_carrier_fluid is None:
            out.append("p.heat_carrier_fluid is not set")
        if hp.temperature_limit is None:
            out.append("p.heat_pump_performance.temperature_limit is not set")
        else:
            out += _unset(hp.temperature_limit, ["heating", "cooling"], "p.heat_pump_performance.temperature_limit")

    if command in ("simulate", "size"):
        out += _unset(s, ["system_type", "number_of_heat_pumps"], "p.gshp_system")
        out += _unset(hp, ["performance_data"], "p.heat_pump_performance")
        data = hp.performance_data
        if isinstance(data, _Table):
            shape(lambda: data.check_shape("p.heat_pump_performance.performance_data"))
        elif isinstance(data, PerformanceConstant):
            out += _unset(data, ["cooling_cap", "cooling_cop", "heating_cap", "heating_cop"],
                          "p.heat_pump_performance.performance_data")
        loads = p.building_loads
        where = "p.building_loads"
        if loads is None:
            out.append(f"{where} is not set")
        elif isinstance(loads, (HourlyBuildingLoadsCombined, HourlyGroundLoadsCombined)):
            out += _unset(loads, ["combined_demand"], where)
        elif isinstance(loads, HourlyBuildingLoadsSeparate):
            out += _unset(loads, ["cooling_demand", "heating_demand"], where)
        elif isinstance(loads, MonthlyBuildingLoadsSeparate):
            out += _unset(loads, ["cooling_demand", "cooling_peak", "heating_demand", "heating_peak"], where)

    if command == "size":
        out += _unset(p.sizing_tool, ["duration_of_yearly_pulse", "duration_of_hourly_peak_pulse"], "p.sizing_tool")
    return out
