"""Runs the executable. Skipped when AnalysisSuite-cli is not found (PYGHE_CLI or PATH);
needs a licence of the 625-borehole level on the computer."""

import json
import subprocess
import warnings

import numpy as np
import pytest

import pyghe as ga
from pyghe._cli import plain


def direct(cli, command, case):
    """The same case run by the executable directly, without the package."""
    out = subprocess.run([cli, *command.split(), "--compact"], input=json.dumps(case).encode(),
                         capture_output=True)
    return json.loads(out.stdout)


@pytest.mark.parametrize("method, command", [
    ("compute_borehole_resistance", "ghe resistance"),
    ("compute_gfunction", "ghe gfunction"),
    ("simulate", "ghe simulation"),
    ("size", "ghe sizing"),
])
def test_result_identical_to_a_direct_run(cli, project, method, command):
    r = getattr(project, method)()
    assert r.status == "ok"
    assert plain(r.raw) == direct(cli, command, r.case)["result"]


def test_default_series(cli, project):
    r = project.simulate()
    assert sorted(r.raw["hourly"]) == ["effectiveCop", "enteringFluidTemperature"]
    assert len(r.raw["hourly"]["enteringFluidTemperature"]) == 25 * 8760
    assert len(project.simulate(series="all").raw["hourly"]) == len(ga.SERIES)


def test_description_is_ignored_by_the_kernel(cli, project):
    without = project.simulate()
    project.project_description = ga.ProjectDescription(project_name="École Saint-Laurent", latitude=45.5)
    assert plain(project.simulate().raw) == plain(without.raw)


def test_cross_field_error_comes_back_in_python_terms(cli, project):
    project.borehole_resistance.pipe_outer_diameter = 0.03
    with pytest.raises(ga.InvalidInputError, match=r"^p\.borehole_resistance: pipe_outer_diameter"):
        project.compute_borehole_resistance()


def test_threads_recorded(cli, project):
    assert project.compute_gfunction(threads=1).meta["threads"] == 1


def test_expected_nan_cop_does_not_warn(cli, project):
    q = project.building_loads.combined_demand.copy()
    q[:100] = 0.0
    project.building_loads = ga.HourlyBuildingLoadsCombined(combined_demand=q)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ga.KernelWarning)
        r = project.simulate()
    assert any(w.startswith("hourly.effectiveCop") for w in r.warnings)


def test_fluid_properties(cli):
    r = ga.fluid_properties(ga.HeatCarrierFluid("Water"), [5.0, 20.0])
    assert [row["temperature"] for row in r.raw["properties"]] == [5.0, 20.0]


def test_unknown_keyword_is_refused(cli, project):
    with pytest.raises(TypeError, match="thread"):
        project.compute_gfunction(thread=1)


def test_standing_column_runs(cli, project):
    project.borehole_resistance = ga.StandingColumn(
        borehole_diameter=0.152, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.08,
        pipe_outer_diameter=0.11, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.14,
        outer_pipe_outer_diameter=0.145, outer_pipe_thermal_conductivity=40, bleed_flow_rate=30)
    project.ground_heat_exchanger.active_length = 300
    project.ground_heat_exchanger.coordinates = ga.Coordinates.rectangle(nx=1, ny=1, spacing=1)
    project.gshp_system.flow_rate_of_pump_c = 300
    r = project.compute_borehole_resistance()
    assert np.isfinite(r.raw["heating"]["boreholeResistance"])


def test_interface_units_reach_the_kernel_like_kernel_units(cli, project):
    """The same project given in the interface units and in the kernel units computes the same
    thing, for values whose conversion is exact."""
    project.gshp_system.flow_rate_of_pump_a = (120.0, 90.0)
    project.ground_heat_exchanger.ground_volumetric_capacity = 2.5
    project.ground_heat_exchanger.geothermal_heat_flux = 50.0
    project.heat_carrier_fluid.antifreeze_mass_concentration = 25.0
    case = project.to_case()
    kernel = json.loads(json.dumps(case))
    del kernel["units"]
    kernel["system"]["flowRate"] = {"heating": 0.002, "cooling": 0.0015}
    kernel["ground"]["volumetricHeatCapacity"] = 2.5e6
    kernel["ground"]["geothermalHeatFlux"] = 0.05
    kernel["fluid"]["massFraction"] = 0.25
    assert 0.002 * 60000 == 120.0 and 0.0015 * 60000 == 90.0 and 2.5e6 / 1e6 == 2.5
    assert 0.05 * 1000 == 50.0 and 0.25 * 100 == 25.0
    for command in ("ghe resistance", "ghe gfunction", "ghe sizing"):
        assert direct(cli, command, case)["result"] == direct(cli, command, kernel)["result"], command


def test_flow_rate_without_exact_kernel_value(cli, project):
    """29.5 L/min has no value in m³/s that converts back to it exactly; in the interface units
    it reaches the kernel unchanged."""
    assert (29.5 / 60000) * 60000 != 29.5
    project.gshp_system.flow_rate_of_pump_a = (29.5 * 4, 29.5 * 4)
    r = project.compute_borehole_resistance()
    assert r.case["system"]["flowRate"]["heating"] == 118.0
