"""Translation between the project and the JSON case of AnalysisSuite-cli
(docs/interface-spec.md §5.1). The only module that knows the JSON names and the units of the
kernel; the project holds the units the interface shows in SI."""

import math
import re

from ._base import ByMode
from .borehole_resistance import BOREHOLE_TYPES, StandingColumn, _OuterPipe, _ULoop
from .building_loads import (HourlyBuildingLoadsCombined, HourlyBuildingLoadsSeparate, HourlyGroundLoadsCombined,
                             MonthlyBuildingLoadsSeparate)
from .errors import InvalidInputError
from .ground_heat_exchanger import Coordinates, GroundHeatExchanger
from .gshp_system import SYSTEM_TYPES, GSHPSystem
from .heat_carrier_fluid import FLUIDS, HeatCarrierFluid
from .heat_pump_performance import HeatPumpPerformance, ManufacturerData, PerformanceConstant, PerformanceTemperature

# Cases are written with "units": "interface" (interface-spec 1.2): flow rates in L/min, mass
# fractions in %, Cs in MJ/(m³·K), qg in mW/m², the units the application stores, so that a
# value reaches the kernel exactly as typed. A case in the kernel's units (the default of the
# executable) is still read, with these factors.
LITRES_PER_MINUTE = 60000.0      # L/min per m³/s
MEGA = 1e6                       # J per MJ
MILLI = 1e3                      # mW per W
PERCENT = 100.0                  # %w per mass fraction

_FLUID_CODES = dict(zip(FLUIDS, ("water", "ethyleneGlycol", "methylAlcohol", "ethylAlcohol", "propyleneGlycol")))
_SYSTEM_CODES = dict(zip(SYSTEM_TYPES, ("waterToAirZone", "waterToWaterZone", "waterToWaterLoop",
                                        "waterToWaterZoneGeocooling", "waterToWaterLoopGeocooling")))

# Python name -> JSON name of the hourly series of ghe simulation (interface-spec §5.4).
SERIES = {
    "entering_fluid_temperature": "enteringFluidTemperature",
    "leaving_fluid_temperature": "leavingFluidTemperature",
    "fluid_temperature_difference": "fluidTemperatureDifference",
    "ground_load": "groundLoad",
    "building_load": "buildingLoad",
    "dhw_load": "dhwLoad",
    "heat_pump_load": "heatPumpLoad",
    "auxiliary_load": "auxiliaryLoad",
    "dhw_covered": "dhwCovered",
    "cop": "cop",
    "effective_cop": "effectiveCop",
    "effective_capacity": "effectiveCapacity",
    "heat_pumps_full_load": "heatPumpsFullLoad",
    "heat_pumps_part_load": "heatPumpsPartLoad",
    "heat_pumps_off": "heatPumpsOff",
    "equivalent_heat_pumps": "equivalentHeatPumps",
    "part_load_ratio": "partLoadRatio",
    "part_load_factor": "partLoadFactor",
    "effective_borehole_resistance": "effectiveBoreholeResistance",
    "fluid_resistance": "fluidResistance",
}
DEFAULT_SERIES = ("entering_fluid_temperature", "effective_cop")


def series_option(series):
    """Value of options.series for the requested series; None asks for all of them."""
    if series is None:
        series = DEFAULT_SERIES
    elif series == "all":
        return None
    elif isinstance(series, str):
        series = (series,)
    unknown = [s for s in series if s not in SERIES]
    if unknown:
        raise InvalidInputError(f"unknown series {', '.join(map(repr, unknown))}; "
                                f"available: {', '.join(SERIES)}")
    return [SERIES[s] for s in series]


def _put(d, key, value):
    if value is not None:
        d[key] = float(value)


def _mass_fraction(fluid):
    return float(fluid.antifreeze_mass_concentration or 0.0)


def _pair(mode):
    d = {}
    if mode is not None:
        _put(d, "heating", mode.heating)
        _put(d, "cooling", mode.cooling)
    return d


def _array(a, sign=1.0):
    return [sign * float(v) for v in a]


def fluid_case(fluid, temperatures):
    return {"units": "interface", "type": _FLUID_CODES[fluid.fluid],
            "massFraction": _mass_fraction(fluid),
            "temperatures": [float(t) for t in temperatures]}


def _borehole(b, ghe):
    d = {"type": BOREHOLE_TYPES[type(b)]}
    _put(d, "activeLength", ghe.active_length)
    _put(d, "burialDepth", ghe.burial_depth)
    _put(d, "diameter", b.borehole_diameter)
    _put(d, "groutConductivity", b.grout_thermal_conductivity)
    if isinstance(b, _ULoop):
        _put(d, "shankSpacing", b.shank_spacing)
    pipe = {}
    _put(pipe, "innerDiameter", b.pipe_inner_diameter)
    _put(pipe, "outerDiameter", b.pipe_outer_diameter)
    _put(pipe, "conductivity", b.pipe_thermal_conductivity)
    d["pipe"] = pipe
    if isinstance(b, _OuterPipe):
        outer = {}
        _put(outer, "innerDiameter", b.outer_pipe_inner_diameter)
        _put(outer, "outerDiameter", b.outer_pipe_outer_diameter)
        _put(outer, "conductivity", b.outer_pipe_thermal_conductivity)
        d["outerPipe"] = outer
    return d


def _field(c):
    rows = []
    for i in range(len(c)):
        row = {"x": float(c.x[i]), "y": float(c.y[i])}
        if c.az is not None and c.az.size:
            row["azimuth"] = float(c.az[i])
        if c.dip is not None and c.dip.size:
            row["dip"] = float(c.dip[i])
        rows.append(row)
    return rows


def _ground(ghe):
    d = {}
    _put(d, "conductivity", ghe.ground_thermal_conductivity)
    if ghe.ground_volumetric_capacity is not None:
        d["volumetricHeatCapacity"] = float(ghe.ground_volumetric_capacity)
    _put(d, "surfaceTemperature", ghe.mean_surface_temperature)
    _put(d, "geothermalHeatFlux", ghe.geothermal_heat_flux)
    if ghe.groundwater_flow is not None:
        w = {"darcyVelocity": float(ghe.groundwater_flow)}
        _put(w, "direction", ghe.groundwater_flow_direction)
        d["groundwater"] = w
    return d


_TEMPERATURE_COLUMNS = {"cooling_cap": "coolingCapacity", "cooling_cop": "coolingCop",
                        "heating_cap": "heatingCapacity", "heating_cop": "heatingCop"}
_MANUFACTURER_COLUMNS = {"tc": "totalCooling", "hr": "heatRejection", "hc": "heatingCapacity",
                         "he": "heatExtraction"}


def _performance(data):
    if isinstance(data, PerformanceConstant):
        d = {"model": "constant", "cooling": {}, "heating": {}}
        _put(d["cooling"], "capacity", data.cooling_cap)
        _put(d["cooling"], "cop", data.cooling_cop)
        _put(d["heating"], "capacity", data.heating_cap)
        _put(d["heating"], "cop", data.heating_cop)
        return d
    if isinstance(data, PerformanceTemperature):
        model, keys = "table", _TEMPERATURE_COLUMNS
    else:
        model, keys = "manufacturer", _MANUFACTURER_COLUMNS
    points = []
    for i, t in enumerate(data.eft):
        point = {"enteringFluidTemperature": float(t)}
        for attr, key in keys.items():
            v = float(getattr(data, attr)[i])
            if not math.isnan(v):
                point[key] = v
        points.append(point)
    return {"model": model, "points": points}


def _heat_pumps(hp, system):
    d = {}
    if hp.temperature_limit is not None:
        _put(d, "minimumHeatingEFT", hp.temperature_limit.heating)
        _put(d, "maximumCoolingEFT", hp.temperature_limit.cooling)
    if system.number_of_heat_pumps is not None:
        d["count"] = int(system.number_of_heat_pumps)
    if hp.degradation_coefficient is not None:
        d["degradationCoefficient"] = _pair(hp.degradation_coefficient)
    if hp.dhw_performance is not None:
        cop = {}
        _put(cop, "heating", hp.dhw_performance.heating)
        c = hp.dhw_performance.cooling
        cop["cooling"] = None if c is None or math.isinf(c) else float(c)
        d["dhwCop"] = cop
    if hp.performance_data is not None:
        d["performance"] = _performance(hp.performance_data)
    return d


def _system(s, borehole):
    d = {}
    if s.system_type is not None:
        d["type"] = _SYSTEM_CODES[s.system_type]
    if s.flow_rate_of_pump_a is not None:
        d["flowRate"] = _pair(s.flow_rate_of_pump_a)
    if s.flow_rate_of_pump_b is not None:
        d["loadFlowRate"] = _pair(s.flow_rate_of_pump_b)
    for attr, key in (("power_of_pump_a", "sourcePumpPower"), ("power_of_pump_b", "loadPumpPower"),
                      ("power_of_auxiliary", "auxiliaryCapacity")):
        if getattr(s, attr) is not None:
            d[key] = _pair(getattr(s, attr))
    if isinstance(borehole, StandingColumn):
        w = {}
        _put(w, "recirculationFlowRate", s.flow_rate_of_pump_c)
        _put(w, "bleedFlowRate", borehole.bleed_flow_rate)
        _put(w, "pumpPower", s.power_of_pump_c)
        d["standingColumnWell"] = w
    return d


def _loads(loads):
    if isinstance(loads, HourlyBuildingLoadsCombined):
        return {"type": "hourlyBuildingCombined", "combined": _array(loads.combined_demand)}
    if isinstance(loads, HourlyGroundLoadsCombined):
        return {"type": "hourlyGroundCombined", "combined": _array(loads.combined_demand)}
    if isinstance(loads, HourlyBuildingLoadsSeparate):
        d = {"type": "hourlyBuildingSeparate"}
        if loads.cooling_demand is not None:
            d["cooling"] = _array(loads.cooling_demand)
        if loads.heating_demand is not None:
            d["heating"] = _array(loads.heating_demand)
        if loads.dhw_demand is not None:
            d["dhw"] = _array(loads.dhw_demand)
        return d
    d = {"type": "monthlyBuildingSeparate"}
    for attr, key in (("cooling_demand", "coolingEnergy"), ("cooling_peak", "coolingPeak"),
                      ("heating_demand", "heatingEnergy"), ("heating_peak", "heatingPeak"),
                      ("dhw_demand", "dhwEnergy")):
        if getattr(loads, attr) is not None:
            d[key] = _array(getattr(loads, attr))
    return d


_DESCRIPTION = ("project_name", "project_no", "client_name", "address", "city", "prov_state",
                "postal_code", "country", "longitude", "latitude", "general_notes")


def to_case(p):
    case = {"units": "interface"}
    desc = {k: getattr(p.project_description, k) for k in _DESCRIPTION
            if getattr(p.project_description, k) is not None}
    if desc:
        case["description"] = desc
    if p.simulation_duration is not None:
        case["simulation"] = {"years": int(p.simulation_duration)}
    ghe = p.ground_heat_exchanger
    if p.borehole_resistance is not None:
        case["borehole"] = _borehole(p.borehole_resistance, ghe)
    if ghe.coordinates is not None and len(ghe.coordinates):
        case["field"] = _field(ghe.coordinates)
    case["ground"] = _ground(ghe)
    if p.heat_carrier_fluid is not None:
        f = p.heat_carrier_fluid
        case["fluid"] = {"type": _FLUID_CODES[f.fluid],
                         "massFraction": _mass_fraction(f)}
    case["heatPumps"] = _heat_pumps(p.heat_pump_performance, p.gshp_system)
    case["system"] = _system(p.gshp_system, p.borehole_resistance)
    if p.building_loads is not None:
        case["loads"] = _loads(p.building_loads)
    st = p.sizing_tool
    if st.duration_of_yearly_pulse is not None or st.duration_of_hourly_peak_pulse is not None:
        s = {}
        if st.duration_of_yearly_pulse is not None:
            s["yearlyPulse"] = int(st.duration_of_yearly_pulse)
        if st.duration_of_hourly_peak_pulse is not None:
            s["hourlyPulse"] = int(st.duration_of_hourly_peak_pulse)
        case["sizing"] = s
    return case


# From a case back to a project

def _scaled(d, key, scale=1.0):
    v = d.get(key)
    return None if v is None else v * scale


def _get_pair(d, scale=1.0, default=None):
    def one(key):
        v = d.get(key, default)
        return None if v is None else v * scale
    return ByMode(heating=one("heating"), cooling=one("cooling"))


def _get_performance(d):
    model = d.get("model")
    if model == "constant":
        c, h = d.get("cooling", {}), d.get("heating", {})
        return PerformanceConstant(cooling_cap=c.get("capacity"), cooling_cop=c.get("cop"),
                                   heating_cap=h.get("capacity"), heating_cop=h.get("cop"))
    if model == "table":
        cls, keys = PerformanceTemperature, _TEMPERATURE_COLUMNS
    elif model == "manufacturer":
        cls, keys = ManufacturerData, _MANUFACTURER_COLUMNS
    else:
        raise InvalidInputError(f"heatPumps.performance.model {model!r} is unknown")
    points = d.get("points", [])
    kw = {"eft": [p["enteringFluidTemperature"] for p in points]}
    for attr, key in keys.items():
        kw[attr] = [p.get(key, math.nan) for p in points]
    return cls(**kw)


def from_case(case):
    from .project import Project, ProjectDescription, SizingTool

    p = Project()
    interface = case.get("units") == "interface"
    lpm = 1.0 if interface else LITRES_PER_MINUTE
    mega = 1.0 if interface else MEGA
    milli = 1.0 if interface else MILLI
    pct = 1.0 if interface else PERCENT
    if "description" in case:
        p.project_description = ProjectDescription(**case["description"])
    if "simulation" in case:
        p.simulation_duration = case["simulation"].get("years")

    b, g = case.get("borehole", {}), case.get("ground", {})
    ghe = GroundHeatExchanger(
        ground_thermal_conductivity=g.get("conductivity"),
        ground_volumetric_capacity=None if g.get("volumetricHeatCapacity") is None
        else g["volumetricHeatCapacity"] / mega,
        mean_surface_temperature=g.get("surfaceTemperature"),
        geothermal_heat_flux=_scaled(g, "geothermalHeatFlux", milli),
        active_length=b.get("activeLength"), burial_depth=b.get("burialDepth"))
    if "groundwater" in g:
        ghe.groundwater_flow = g["groundwater"].get("darcyVelocity")
        ghe.groundwater_flow_direction = g["groundwater"].get("direction", 0.0)
    rows = case.get("field")
    if rows:
        ghe.coordinates = Coordinates(
            x=[r["x"] for r in rows], y=[r["y"] for r in rows],
            az=[r.get("azimuth", 0.0) for r in rows] if any("azimuth" in r for r in rows) else None,
            dip=[r.get("dip", 90.0) for r in rows] if any("dip" in r for r in rows) else None)
    p.ground_heat_exchanger = ghe

    s = case.get("system", {})
    well = s.get("standingColumnWell", {})
    if b:
        cls = {v: k for k, v in BOREHOLE_TYPES.items()}.get(b.get("type"))
        if cls is None:
            raise InvalidInputError(f"borehole.type {b.get('type')!r} is unknown")
        pipe, outer = b.get("pipe", {}), b.get("outerPipe", {})
        kw = dict(borehole_diameter=b.get("diameter"), grout_thermal_conductivity=b.get("groutConductivity"),
                  pipe_inner_diameter=pipe.get("innerDiameter"), pipe_outer_diameter=pipe.get("outerDiameter"),
                  pipe_thermal_conductivity=pipe.get("conductivity"))
        if issubclass(cls, _ULoop):
            kw["shank_spacing"] = b.get("shankSpacing")
        if issubclass(cls, _OuterPipe):
            kw.update(outer_pipe_inner_diameter=outer.get("innerDiameter"),
                      outer_pipe_outer_diameter=outer.get("outerDiameter"),
                      outer_pipe_thermal_conductivity=outer.get("conductivity"))
        if cls is StandingColumn:
            kw["bleed_flow_rate"] = _scaled(well, "bleedFlowRate", lpm)
        p.borehole_resistance = cls(**kw)

    if "fluid" in case:
        f = case["fluid"]
        name = {v: k for k, v in _FLUID_CODES.items()}.get(f.get("type"))
        p.heat_carrier_fluid = HeatCarrierFluid(name, antifreeze_mass_concentration=f.get("massFraction", 0.0) * pct)

    h = case.get("heatPumps", {})
    hp = HeatPumpPerformance()
    if "minimumHeatingEFT" in h or "maximumCoolingEFT" in h:
        hp.temperature_limit = ByMode(heating=h.get("minimumHeatingEFT"), cooling=h.get("maximumCoolingEFT"))
    if "degradationCoefficient" in h:
        hp.degradation_coefficient = _get_pair(h["degradationCoefficient"], default=0.0)
    if "dhwCop" in h:
        cooling = h["dhwCop"].get("cooling")
        hp.dhw_performance = ByMode(heating=h["dhwCop"].get("heating", 2.75),
                                    cooling=math.inf if cooling is None else cooling)
    if "performance" in h:
        hp.performance_data = _get_performance(h["performance"])
    p.heat_pump_performance = hp

    system = GSHPSystem(number_of_heat_pumps=h.get("count"))
    if "type" in s:
        system.system_type = {v: k for k, v in _SYSTEM_CODES.items()}.get(s["type"])
    if "flowRate" in s:
        system.flow_rate_of_pump_a = _get_pair(s["flowRate"], lpm)
    if "loadFlowRate" in s:
        system.flow_rate_of_pump_b = _get_pair(s["loadFlowRate"], lpm, default=0.0)
    for attr, key in (("power_of_pump_a", "sourcePumpPower"), ("power_of_pump_b", "loadPumpPower"),
                      ("power_of_auxiliary", "auxiliaryCapacity")):
        if key in s:
            setattr(system, attr, _get_pair(s[key], default=0.0))
    if well:
        system.flow_rate_of_pump_c = _scaled(well, "recirculationFlowRate", lpm)
        system.power_of_pump_c = well.get("pumpPower", 0.0)
    p.gshp_system = system

    if "loads" in case:
        d = case["loads"]
        kind = d.get("type")
        if kind == "hourlyBuildingCombined":
            p.building_loads = HourlyBuildingLoadsCombined(combined_demand=d.get("combined"))
        elif kind == "hourlyGroundCombined":
            p.building_loads = HourlyGroundLoadsCombined(combined_demand=d.get("combined"))
        elif kind == "hourlyBuildingSeparate":
            p.building_loads = HourlyBuildingLoadsSeparate(cooling_demand=d.get("cooling"),
                                                           heating_demand=d.get("heating"), dhw_demand=d.get("dhw"))
        elif kind == "monthlyBuildingSeparate":
            p.building_loads = MonthlyBuildingLoadsSeparate(
                cooling_demand=d.get("coolingEnergy"), cooling_peak=d.get("coolingPeak"),
                heating_demand=d.get("heatingEnergy"), heating_peak=d.get("heatingPeak"),
                dhw_demand=d.get("dhwEnergy"))
        else:
            raise InvalidInputError(f"loads.type {kind!r} is unknown")
    if "sizing" in case:
        p.sizing_tool = SizingTool(duration_of_yearly_pulse=case["sizing"].get("yearlyPulse"),
                                   duration_of_hourly_peak_pulse=case["sizing"].get("hourlyPulse"))
    return p


# Error paths of the executable -> Python attributes. Indices are written [i] here.

_PATHS = {
    "simulation.years": "simulation_duration",
    "borehole": "borehole_resistance",
    "borehole.type": "borehole_resistance",
    "borehole.activeLength": "ground_heat_exchanger.active_length",
    "borehole.burialDepth": "ground_heat_exchanger.burial_depth",
    "borehole.diameter": "borehole_resistance.borehole_diameter",
    "borehole.groutConductivity": "borehole_resistance.grout_thermal_conductivity",
    "borehole.shankSpacing": "borehole_resistance.shank_spacing",
    "borehole.pipe": "borehole_resistance",
    "borehole.pipe.innerDiameter": "borehole_resistance.pipe_inner_diameter",
    "borehole.pipe.outerDiameter": "borehole_resistance.pipe_outer_diameter",
    "borehole.pipe.conductivity": "borehole_resistance.pipe_thermal_conductivity",
    "borehole.outerPipe": "borehole_resistance",
    "borehole.outerPipe.innerDiameter": "borehole_resistance.outer_pipe_inner_diameter",
    "borehole.outerPipe.outerDiameter": "borehole_resistance.outer_pipe_outer_diameter",
    "borehole.outerPipe.conductivity": "borehole_resistance.outer_pipe_thermal_conductivity",
    "field": "ground_heat_exchanger.coordinates",
    "field[i]": "ground_heat_exchanger.coordinates (row i)",
    "field[i].x": "ground_heat_exchanger.coordinates.x[i]",
    "field[i].y": "ground_heat_exchanger.coordinates.y[i]",
    "field[i].azimuth": "ground_heat_exchanger.coordinates.az[i]",
    "field[i].dip": "ground_heat_exchanger.coordinates.dip[i]",
    "ground": "ground_heat_exchanger",
    "ground.conductivity": "ground_heat_exchanger.ground_thermal_conductivity",
    "ground.volumetricHeatCapacity": "ground_heat_exchanger.ground_volumetric_capacity",
    "ground.surfaceTemperature": "ground_heat_exchanger.mean_surface_temperature",
    "ground.geothermalHeatFlux": "ground_heat_exchanger.geothermal_heat_flux",
    "ground.groundwater": "ground_heat_exchanger",
    "ground.groundwater.darcyVelocity": "ground_heat_exchanger.groundwater_flow",
    "ground.groundwater.direction": "ground_heat_exchanger.groundwater_flow_direction",
    "fluid": "heat_carrier_fluid",
    "fluid.type": "heat_carrier_fluid.fluid",
    "fluid.massFraction": "heat_carrier_fluid.antifreeze_mass_concentration",
    "heatPumps": "heat_pump_performance",
    "heatPumps.minimumHeatingEFT": "heat_pump_performance.temperature_limit.heating",
    "heatPumps.maximumCoolingEFT": "heat_pump_performance.temperature_limit.cooling",
    "heatPumps.count": "gshp_system.number_of_heat_pumps",
    "heatPumps.degradationCoefficient": "heat_pump_performance.degradation_coefficient",
    "heatPumps.degradationCoefficient.heating": "heat_pump_performance.degradation_coefficient.heating",
    "heatPumps.degradationCoefficient.cooling": "heat_pump_performance.degradation_coefficient.cooling",
    "heatPumps.dhwCop": "heat_pump_performance.dhw_performance",
    "heatPumps.dhwCop.heating": "heat_pump_performance.dhw_performance.heating",
    "heatPumps.dhwCop.cooling": "heat_pump_performance.dhw_performance.cooling",
    "heatPumps.performance": "heat_pump_performance.performance_data",
    "heatPumps.performance.points": "heat_pump_performance.performance_data",
    "heatPumps.performance.points[i]": "heat_pump_performance.performance_data (row i)",
    # heatingCapacity names a column of both tables (heating_cap, hc): left as it is.
    "heatPumps.performance.points[i].coolingCapacity": "heat_pump_performance.performance_data.cooling_cap",
    "heatPumps.performance.points[i].coolingCop": "heat_pump_performance.performance_data.cooling_cop",
    "heatPumps.performance.points[i].heatingCop": "heat_pump_performance.performance_data.heating_cop",
    "heatPumps.performance.points[i].totalCooling": "heat_pump_performance.performance_data.tc",
    "heatPumps.performance.points[i].heatRejection": "heat_pump_performance.performance_data.hr",
    "heatPumps.performance.points[i].heatExtraction": "heat_pump_performance.performance_data.he",
    "system": "gshp_system",
    "system.type": "gshp_system.system_type",
    "system.flowRate": "gshp_system.flow_rate_of_pump_a",
    "system.flowRate.heating": "gshp_system.flow_rate_of_pump_a.heating",
    "system.flowRate.cooling": "gshp_system.flow_rate_of_pump_a.cooling",
    "system.sourcePumpPower": "gshp_system.power_of_pump_a",
    "system.loadPumpPower": "gshp_system.power_of_pump_b",
    "system.loadFlowRate": "gshp_system.flow_rate_of_pump_b",
    "system.auxiliaryCapacity": "gshp_system.power_of_auxiliary",
    **{f"system.{key}.{mode}": f"gshp_system.{attr}.{mode}"
       for key, attr in (("sourcePumpPower", "power_of_pump_a"), ("loadPumpPower", "power_of_pump_b"),
                         ("loadFlowRate", "flow_rate_of_pump_b"), ("auxiliaryCapacity", "power_of_auxiliary"))
       for mode in ("heating", "cooling")},
    "system.standingColumnWell": "gshp_system",
    "system.standingColumnWell.recirculationFlowRate": "gshp_system.flow_rate_of_pump_c",
    "system.standingColumnWell.bleedFlowRate": "borehole_resistance.bleed_flow_rate",
    "system.standingColumnWell.pumpPower": "gshp_system.power_of_pump_c",
    "loads": "building_loads",
    "loads.combined": "building_loads.combined_demand",
    "loads.cooling": "building_loads.cooling_demand",
    "loads.heating": "building_loads.heating_demand",
    "loads.dhw": "building_loads.dhw_demand",
    "loads.coolingEnergy": "building_loads.cooling_demand",
    "loads.heatingEnergy": "building_loads.heating_demand",
    "loads.coolingPeak": "building_loads.cooling_peak",
    "loads.heatingPeak": "building_loads.heating_peak",
    "loads.dhwEnergy": "building_loads.dhw_demand",
    "sizing": "sizing_tool",
    "sizing.yearlyPulse": "sizing_tool.duration_of_yearly_pulse",
    "sizing.hourlyPulse": "sizing_tool.duration_of_hourly_peak_pulse",
    "plume": "compute_thermal_plume (arguments)",
    "plume.hours": "compute_thermal_plume (time)",
    "plume.reading": "compute_thermal_plume (reading)",
    "plume.levels": "compute_thermal_plume (contour_min, contour_max)",
}


def python_path(json_path):
    """'heatPumps.minimumHeatingEFT' -> 'p.heat_pump_performance.temperature_limit.heating'.
    A path not in the table comes back unchanged, prefixed with 'case.'."""
    indices = iter(re.findall(r"\[(\d+)\]", json_path))
    target = _PATHS.get(re.sub(r"\[\d+\]", "[i]", json_path))
    if target is None:
        return f"case.{json_path}"
    return "p." + re.sub(r"\[i\]|row i", lambda m: m.group(0).replace("i", next(indices)), target)


def translate_error(message):
    """Rewrites an executable's input error in Python terms: the leading JSON path, and the
    JSON names it mentions relative to that path."""
    head, sep, rest = message.partition(": ")
    if not (sep and re.fullmatch(r"[A-Za-z][\w.\[\]]*", head)):
        return message

    def word(m):
        target = _PATHS.get(re.sub(r"\[\d+\]", "[i]", f"{head}.{m.group(0)}"))
        return target.rsplit(".", 1)[-1] if target else m.group(0)

    rest = re.sub(r"\b[a-z]+(?:[A-Z][a-z0-9]*)+\b", word, rest)
    return f"{python_path(head)}: {rest}"
