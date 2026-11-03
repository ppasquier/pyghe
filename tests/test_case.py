import json

import numpy as np
import pytest

import pyghe as ga
from pyghe._case import python_path, series_option, translate_error


def roundtrip(p):
    return ga.Project.from_case(json.loads(json.dumps(p.to_case())))


def test_case_carries_the_interface_units(project):
    case = project.to_case()
    assert case["units"] == "interface"
    assert case["system"]["flowRate"] == {"heating": 96.0, "cooling": 96.0}
    assert case["ground"]["volumetricHeatCapacity"] == 2.2
    assert case["ground"]["geothermalHeatFlux"] == 60.0
    assert case["fluid"] == {"type": "propyleneGlycol", "massFraction": 25.0}
    assert case["system"]["type"] == "waterToWaterZone"
    assert case["heatPumps"]["count"] == 4
    assert case["borehole"]["activeLength"] == 150.0 and case["borehole"]["burialDepth"] == 2.0


def test_a_case_in_kernel_units_is_converted(project):
    case = project.to_case()
    del case["units"]
    case["system"]["flowRate"] = {"heating": 0.002, "cooling": 0.001}
    case["ground"]["volumetricHeatCapacity"] = 2.2e6
    case["ground"]["geothermalHeatFlux"] = 0.06
    case["fluid"]["massFraction"] = 0.25
    p = ga.Project.from_case(case)
    assert p.gshp_system.flow_rate_of_pump_a.heating == 0.002 * 60000
    assert p.ground_heat_exchanger.ground_volumetric_capacity == 2.2e6 / 1e6
    assert p.ground_heat_exchanger.geothermal_heat_flux == 0.06 * 1000
    assert p.heat_carrier_fluid.antifreeze_mass_concentration == 0.25 * 100


def test_complete_project_round_trip(project):
    assert roundtrip(project) == project


def test_round_trip_of_every_variant(project):
    k = np.arange(8760)
    variants = []

    p = project.copy()
    p.building_loads = ga.HourlyBuildingLoadsSeparate(
        heating_demand=np.maximum(0, 30 * np.cos(2 * np.pi * k / 8760)),
        cooling_demand=np.maximum(0, -30 * np.cos(2 * np.pi * k / 8760)), dhw_demand=np.full(8760, 2.0))
    p.heat_pump_performance.dhw_performance = ga.ByMode(heating=3.0, cooling=4.0)
    p.heat_pump_performance.degradation_coefficient = ga.ByMode(heating=0.1, cooling=0.15)
    p.gshp_system.power_of_pump_a = ga.ByMode(heating=1.5, cooling=1.5)
    p.gshp_system.power_of_pump_b = ga.ByMode(heating=0.5, cooling=0.7)
    variants.append(p)

    p = project.copy()
    p.building_loads = ga.MonthlyBuildingLoadsSeparate(
        heating_demand=np.arange(12) * 1e3, cooling_demand=np.arange(12)[::-1] * 1e3,
        heating_peak=np.full(12, 40.0), cooling_peak=np.full(12, 30.0))
    p.heat_pump_performance.performance_data = ga.PerformanceConstant(
        heating_cap=15, heating_cop=3.5, cooling_cap=20, cooling_cop=5)
    variants.append(p)

    p = project.copy()
    p.building_loads = ga.HourlyGroundLoadsCombined(combined_demand=10 * np.sin(2 * np.pi * k / 8760))
    p.heat_pump_performance.performance_data = ga.ManufacturerData(
        eft=[-5, 10, 30], tc=[25, 23, np.nan], hr=[29, 27, np.nan], hc=[15, 19, 24], he=[10, 14, 19])
    variants.append(p)

    p = project.copy()
    p.borehole_resistance = ga.Coaxial(
        borehole_diameter=0.14, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.04,
        pipe_outer_diameter=0.05, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.1,
        outer_pipe_outer_diameter=0.11, outer_pipe_thermal_conductivity=0.4)
    p.ground_heat_exchanger.groundwater_flow = 1e-7
    p.ground_heat_exchanger.groundwater_flow_direction = 45
    p.ground_heat_exchanger.coordinates = ga.Coordinates.from_points(
        [(0, 0), (8, 0), (0, 8)], az=[0, 90, 180], dip=[90, 80, 75])
    variants.append(p)

    p = project.copy()
    p.borehole_resistance = ga.StandingColumn(
        borehole_diameter=0.15, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.1,
        pipe_outer_diameter=0.11, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.15,
        outer_pipe_outer_diameter=0.16, outer_pipe_thermal_conductivity=40, bleed_flow_rate=60)
    p.gshp_system.flow_rate_of_pump_c = 600
    p.gshp_system.power_of_pump_c = 2.5
    p.project_description = ga.ProjectDescription(project_name="Test", latitude=45.5, general_notes="free text")
    variants.append(p)

    for v in variants:
        assert roundtrip(v) == v


def test_ground_loads_keep_the_sign_of_the_interface():
    k = np.arange(8760)
    q = 10 * np.sin(2 * np.pi * k / 8760)
    p = ga.Project()
    p.building_loads = ga.HourlyGroundLoadsCombined(combined_demand=q)
    loads = p.to_case()["loads"]
    assert loads["type"] == "hourlyGroundCombined" and loads["combined"][2000] == q[2000]


def test_free_heat_recovery_is_written_null(project):
    assert project.to_case()["heatPumps"]["dhwCop"]["cooling"] is None
    project.heat_pump_performance.dhw_performance.cooling = 4.0
    assert project.to_case()["heatPumps"]["dhwCop"]["cooling"] == 4.0


def test_table_mode_skipped_with_nan(project):
    project.heat_pump_performance.performance_data = ga.PerformanceTemperature(
        eft=[-5, 30], cooling_cap=[np.nan, 20], cooling_cop=[np.nan, 3.5], heating_cap=[15, 24], heating_cop=[3, 5])
    first = project.to_case()["heatPumps"]["performance"]["points"][0]
    assert "coolingCapacity" not in first and first["heatingCapacity"] == 15


@pytest.mark.parametrize("json_path, expected", [
    ("simulation.years", "p.simulation_duration"),
    ("heatPumps.minimumHeatingEFT", "p.heat_pump_performance.temperature_limit.heating"),
    ("heatPumps.count", "p.gshp_system.number_of_heat_pumps"),
    ("heatPumps.performance.points[2]", "p.heat_pump_performance.performance_data (row 2)"),
    ("field[3].azimuth", "p.ground_heat_exchanger.coordinates.az[3]"),
    ("ground.groundwater.darcyVelocity", "p.ground_heat_exchanger.groundwater_flow"),
    ("borehole.activeLength", "p.ground_heat_exchanger.active_length"),
    ("borehole.outerPipe.innerDiameter", "p.borehole_resistance.outer_pipe_inner_diameter"),
    ("system.flowRate", "p.gshp_system.flow_rate_of_pump_a"),
    ("system.standingColumnWell.bleedFlowRate", "p.borehole_resistance.bleed_flow_rate"),
    ("loads.coolingEnergy", "p.building_loads.cooling_demand"),
    ("something.unknown", "case.something.unknown"),
])
def test_error_paths_in_python_terms(json_path, expected):
    assert python_path(json_path) == expected


def test_error_message_translated():
    assert translate_error("borehole.pipe: outerDiameter must exceed innerDiameter") == \
        "p.borehole_resistance: pipe_outer_diameter must exceed pipe_inner_diameter"
    assert translate_error("the input is not a JSON object") == "the input is not a JSON object"


def test_series_option():
    assert series_option(None) == ["enteringFluidTemperature", "effectiveCop"]
    assert series_option("all") is None
    assert series_option(["ground_load"]) == ["groundLoad"]
    with pytest.raises(ga.InvalidInputError, match="unknown series"):
        series_option(["eft"])


def test_case_equals_a_hand_written_one(project):
    """The whole case of the reference project, written by hand from the interface-spec (§5.1),
    with the interface units of §3."""
    case = project.to_case()
    loads = case.pop("loads")
    assert loads["type"] == "hourlyBuildingCombined" and len(loads["combined"]) == 8760
    assert loads["combined"] == list(project.building_loads.combined_demand)
    assert case == {
        "units": "interface",
        "simulation": {"years": 25},
        "borehole": {"type": "singleU", "activeLength": 150.0, "burialDepth": 2.0, "diameter": 0.152,
                     "groutConductivity": 1.25, "shankSpacing": 0.1,
                     "pipe": {"innerDiameter": 0.033, "outerDiameter": 0.044, "conductivity": 0.39}},
        "field": [{"x": 0.0, "y": 0.0}, {"x": 6.0, "y": 0.0}, {"x": 0.0, "y": 6.0}, {"x": 6.0, "y": 6.0}],
        "ground": {"conductivity": 2.5, "volumetricHeatCapacity": 2.2, "surfaceTemperature": 10.0,
                   "geothermalHeatFlux": 60.0},
        "fluid": {"type": "propyleneGlycol", "massFraction": 25.0},
        "heatPumps": {"minimumHeatingEFT": 0.0, "maximumCoolingEFT": 30.0, "count": 4,
                      "degradationCoefficient": {"heating": 0.0, "cooling": 0.0},
                      "dhwCop": {"heating": 2.75, "cooling": None},
                      "performance": {"model": "table", "points": [
                          {"enteringFluidTemperature": -5.0, "coolingCapacity": 25.0, "coolingCop": 6.0,
                           "heatingCapacity": 15.0, "heatingCop": 3.0},
                          {"enteringFluidTemperature": 30.0, "coolingCapacity": 20.0, "coolingCop": 3.5,
                           "heatingCapacity": 24.0, "heatingCop": 5.0}]}},
        "system": {"type": "waterToWaterZone", "flowRate": {"heating": 96.0, "cooling": 96.0},
                   "loadFlowRate": {"heating": 0.0, "cooling": 0.0},
                   "sourcePumpPower": {"heating": 0.0, "cooling": 0.0},
                   "loadPumpPower": {"heating": 0.0, "cooling": 0.0},
                   "auxiliaryCapacity": {"heating": 15.0, "cooling": 20.0}},
        "sizing": {"yearlyPulse": 10, "hourlyPulse": 6},
    }
