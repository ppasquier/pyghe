"""Every kind of input through the four computations: the package's result is identical to the bit
to a direct run of the executable on the same case. Needs the executable."""

import json
import math
import os
import subprocess
import warnings

import numpy as np
import pytest

import pyghe as ga
from pyghe._cli import plain

K = np.arange(8760)
SEASON = np.cos(2 * np.pi * K / 8760)
DAY = np.sin(2 * np.pi * K / 24)


def direct(cli, command, case):
    """One thread on both sides: with several, the order of some sums varies from run to run
    (about 1e-13 relative on an inclined field)."""
    env = dict(os.environ, OMP_NUM_THREADS="1")
    out = subprocess.run([cli, *command.split(), "--compact"], input=json.dumps(case).encode(),
                         capture_output=True, env=env)
    return json.loads(out.stdout)


def double_u_separate(p):
    p.borehole_resistance = ga.DoubleULoopA(
        borehole_diameter=0.15, grout_thermal_conductivity=1.7, shank_spacing=0.09,
        pipe_inner_diameter=0.026, pipe_outer_diameter=0.0334, pipe_thermal_conductivity=0.4)
    p.building_loads = ga.HourlyBuildingLoadsSeparate(
        heating_demand=np.maximum(0, 40 * SEASON) + 5, cooling_demand=np.maximum(0, -30 * SEASON) + 3,
        dhw_demand=np.full(8760, 2.0))
    p.heat_pump_performance.degradation_coefficient = ga.ByMode(heating=0.1, cooling=0.15)
    p.heat_pump_performance.dhw_performance = ga.ByMode(heating=3.0, cooling=4.0)


def double_u_monthly_loop(p):
    p.borehole_resistance = ga.DoubleULoopD(
        borehole_diameter=0.15, grout_thermal_conductivity=1.7, shank_spacing=0.09,
        pipe_inner_diameter=0.026, pipe_outer_diameter=0.0334, pipe_thermal_conductivity=0.4)
    months = np.cos(2 * np.pi * (np.arange(12) + 0.5) / 12)
    p.building_loads = ga.MonthlyBuildingLoadsSeparate(
        heating_demand=np.maximum(0, 20000 * months) + 1000, cooling_demand=np.maximum(0, -15000 * months) + 500,
        heating_peak=np.full(12, 45.0), cooling_peak=np.full(12, 35.0), dhw_demand=np.full(12, 800.0))
    p.heat_pump_performance.performance_data = ga.PerformanceConstant(
        cooling_cap=20, cooling_cop=5, heating_cap=15, heating_cop=3.5)
    p.gshp_system.system_type = "Water-water (loop)"


def coaxial_groundwater_geocooling(p):
    p.borehole_resistance = ga.Coaxial(
        borehole_diameter=0.14, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.04,
        pipe_outer_diameter=0.05, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.1,
        outer_pipe_outer_diameter=0.11, outer_pipe_thermal_conductivity=0.4)
    ghe = p.ground_heat_exchanger
    ghe.groundwater_flow = 1e-7
    ghe.groundwater_flow_direction = 30
    # Inclined away from the field's centre: boreholes leaning towards each other would cross
    # (150 m at 80° drift 26 m sideways), and the g-function of crossing boreholes diverges.
    ghe.coordinates = ga.Coordinates.from_points([(0, 0), (8, 0), (0, 8), (8, 8)],
                                                 az=[225, 135, 315, 45], dip=[80, 80, 80, 80])
    p.heat_pump_performance.performance_data = ga.ManufacturerData(
        eft=[-5, 10, 30], tc=[25, 23, 20], hr=[29, 27, 25], hc=[15, 19, 24], he=[10, 14, 19])
    p.gshp_system.system_type = "Water-water (zone) - Geocooling"


def standing_column(p):
    p.borehole_resistance = ga.StandingColumn(
        borehole_diameter=0.15, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.1,
        pipe_outer_diameter=0.11, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.14,
        outer_pipe_outer_diameter=0.145, outer_pipe_thermal_conductivity=40, bleed_flow_rate=30)
    p.heat_carrier_fluid = ga.HeatCarrierFluid("Water")
    p.ground_heat_exchanger.active_length = 300
    p.ground_heat_exchanger.burial_depth = 0
    p.ground_heat_exchanger.coordinates = ga.Coordinates.rectangle(nx=1, ny=1, spacing=1)
    p.gshp_system.system_type = "Water-air (zone)"
    p.gshp_system.flow_rate_of_pump_c = 300
    p.gshp_system.power_of_pump_c = 2.5
    p.heat_pump_performance.temperature_limit = ga.ByMode(heating=4, cooling=25)


def ground_loads_loop_geocooling(p):
    p.building_loads = ga.HourlyGroundLoadsCombined(combined_demand=20 * SEASON + 3 * DAY)
    p.gshp_system.system_type = "Water-water (loop) - Geocooling"
    p.heat_carrier_fluid = ga.HeatCarrierFluid("Ethylene glycol", antifreeze_mass_concentration=30)


VARIANTS = {
    "reference": lambda p: None,
    "double_u_separate": double_u_separate,
    "double_u_monthly_loop": double_u_monthly_loop,
    "coaxial_groundwater_geocooling": coaxial_groundwater_geocooling,
    "standing_column": standing_column,
    "ground_loads_loop_geocooling": ground_loads_loop_geocooling,
}

# The sizing recomputes the g-function at each length; inclined boreholes with groundwater make
# that 38 s on one thread, twice per test. Covered by test_slow_sizing_runs instead.
SLOW_SIZING = {"coaxial_groundwater_geocooling"}

COMPUTATIONS = [
    ("compute_borehole_resistance", "ghe resistance", {}),
    ("compute_gfunction", "ghe gfunction", {}),
    ("simulate", "ghe simulation", {"series": "all"}),
    ("size", "ghe sizing", {}),
]


@pytest.mark.parametrize("variant", VARIANTS)
def test_variant_identical_to_a_direct_run(cli, project, variant):
    project.simulation_duration = 1
    VARIANTS[variant](project)
    for method, command, options in COMPUTATIONS:
        if method == "size" and variant in SLOW_SIZING:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = getattr(project, method)(threads=1, **options)
        d = direct(cli, command, r.case)
        assert (r.status, plain(r.raw)) == (d["statusText"], d["result"]), f"{variant}: {command}"
        if method != "size":
            assert r.converged, f"{variant}: {command}"
        if method == "simulate":
            assert np.isfinite(r.eft).all(), variant
        if method == "size" and variant != "standing_column":
            assert math.isfinite(r.governing_total_borehole_length), variant


def test_interface_spec_example(cli):
    """Appendix B of the interface-spec, in the kernel units, read by the package and run in the
    interface units: the same result as the executable on the original case."""
    case = {
        "simulation": {"years": 5},
        "ground": {"conductivity": 2.5, "volumetricHeatCapacity": 2.2e6,
                   "surfaceTemperature": 10, "geothermalHeatFlux": 0.06},
        "borehole": {"type": "singleU", "activeLength": 150, "burialDepth": 2, "diameter": 0.152,
                     "groutConductivity": 1.25, "shankSpacing": 0.1,
                     "pipe": {"innerDiameter": 0.033, "outerDiameter": 0.044, "conductivity": 0.39}},
        "field": [{"x": 0, "y": 0}, {"x": 6, "y": 0}, {"x": 0, "y": 6}, {"x": 6, "y": 6}],
        "fluid": {"type": "propyleneGlycol", "massFraction": 0.25},
        "heatPumps": {"count": 2, "minimumHeatingEFT": 0, "maximumCoolingEFT": 30,
                      "performance": {"model": "table", "points": [
                          {"enteringFluidTemperature": -5, "coolingCapacity": 25, "coolingCop": 6,
                           "heatingCapacity": 15, "heatingCop": 3},
                          {"enteringFluidTemperature": 30, "coolingCapacity": 20, "coolingCop": 3.5,
                           "heatingCapacity": 24, "heatingCop": 5}]}},
        "system": {"type": "waterToWaterZone", "flowRate": {"heating": 0.003, "cooling": 0.003},
                   "auxiliaryCapacity": {"heating": 15, "cooling": 20}},
        "loads": {"type": "hourlyBuildingCombined", "combined": list(50.0 * SEASON)},
    }
    p = ga.Project.from_case(case)
    assert p.gshp_system.flow_rate_of_pump_a.heating == 0.003 * 60000
    assert p.heat_carrier_fluid.antifreeze_mass_concentration == 0.25 * 100
    r = p.simulate(series="all", threads=1)
    assert r.converged
    assert plain(r.raw) == direct(cli, "ghe simulation", case)["result"]


def test_slow_sizing_runs(cli, project):
    project.simulation_duration = 1
    coaxial_groundwater_geocooling(project)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = project.size()
    assert r.converged and math.isfinite(r.governing_total_borehole_length)
