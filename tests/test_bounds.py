"""Inputs no borehole field can have are refused; values the interface's fields cannot hold are
computed with a warning, and refused when written as a project file. Needs the executable."""

import warnings

import numpy as np
import pytest

import pyghe as ga


def caught(call):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = call()
    return result, w


def table(**columns):
    data = dict(eft=[-5, 30], cooling_cap=[25, 20], cooling_cop=[6, 3.5], heating_cap=[15, 24], heating_cop=[3, 5])
    data.update(columns)
    return ga.PerformanceTemperature(**data)


@pytest.mark.parametrize("change, where", [
    (lambda p: setattr(p.heat_pump_performance, "temperature_limit", ga.ByMode(25, 5)),
     "p.heat_pump_performance.temperature_limit.heating"),
    (lambda p: setattr(p.heat_pump_performance, "temperature_limit", ga.ByMode(20, 20)),
     "p.heat_pump_performance.temperature_limit.heating"),
    (lambda p: setattr(p.heat_pump_performance, "performance_data", table(cooling_cop=[-6, 3.5])),
     "p.heat_pump_performance.performance_data (row 0)"),
    (lambda p: setattr(p.borehole_resistance, "shank_spacing", 0.12), "p.borehole_resistance.shank_spacing"),
    (lambda p: setattr(p.borehole_resistance, "shank_spacing", 0.04), "p.borehole_resistance.shank_spacing"),
    (lambda p: setattr(p.ground_heat_exchanger, "coordinates", ga.Coordinates(x=[0, 0.1], y=[0, 0])),
     "p.ground_heat_exchanger.coordinates"),
])
def test_an_impossible_input_is_refused(cli, project, change, where):
    change(project)
    for command in ("simulate", "size"):
        with pytest.raises(ga.InvalidInputError, match=where.replace("(", r"\(").replace(")", r"\)")):
            getattr(project, command)()


def test_the_legs_of_a_double_u_need_more_room(cli, project):
    b = project.borehole_resistance
    project.borehole_resistance = ga.DoubleULoopA(
        borehole_diameter=b.borehole_diameter, grout_thermal_conductivity=b.grout_thermal_conductivity,
        shank_spacing=0.05, pipe_inner_diameter=0.027, pipe_outer_diameter=0.04,
        pipe_thermal_conductivity=b.pipe_thermal_conductivity)
    with pytest.raises(ga.InvalidInputError, match="√2"):
        project.compute_borehole_resistance()
    project.borehole_resistance.shank_spacing = 0.06
    assert project.compute_borehole_resistance().converged


def test_a_complete_project_draws_no_warning(cli, project):
    for command in ("simulate", "size", "compute_borehole_resistance", "compute_gfunction"):
        _, w = caught(getattr(project, command))
        assert not w, [str(x.message) for x in w]


@pytest.mark.parametrize("change, where, shown", [
    (lambda p: setattr(p.ground_heat_exchanger, "active_length", 5000.0),
     "p.ground_heat_exchanger.active_length", "5000 m lies outside [50, 500] m"),
    (lambda p: setattr(p.ground_heat_exchanger, "ground_thermal_conductivity", 8.0),
     "p.ground_heat_exchanger.ground_thermal_conductivity", "8 W/m·K lies outside [0.5, 6] W/m·K"),
    (lambda p: setattr(p.gshp_system, "flow_rate_of_pump_a", ga.ByMode(5, 96)),
     "p.gshp_system.flow_rate_of_pump_a.heating", "5 L/min lies outside [10, 9999] L/min"),
    (lambda p: setattr(p.heat_pump_performance, "temperature_limit", ga.ByMode(-12, 30)),
     "p.heat_pump_performance.temperature_limit.heating", "-12 °C lies outside [-10, 45] °C"),
    (lambda p: setattr(p.ground_heat_exchanger, "groundwater_flow", 1e-2),
     "p.ground_heat_exchanger.groundwater_flow", "0.01 m/s lies outside [1e-12, 1e-06] m/s"),
    (lambda p: setattr(p.ground_heat_exchanger, "coordinates", ga.Coordinates(
        x=[0, 6], y=[0, 0], az=[0, 0], dip=[30, 90])),
     "p.ground_heat_exchanger.coordinates.dip[0]", "30° lies outside [45, 90]°"),
    (lambda p: setattr(p, "heat_carrier_fluid", ga.HeatCarrierFluid("Propylene glycol", 50)),
     "p.heat_carrier_fluid.antifreeze_mass_concentration", "50 %w lies outside [10, 40] %w"),
])
def test_a_value_beyond_the_interface_is_computed_with_a_warning(cli, project, change, where, shown):
    change(project)
    result, w = caught(project.simulate)
    assert result.status in ("ok", "notConverged")
    found = [x for x in w if issubclass(x.category, ga.OutsideInterfaceWarning)]
    assert len(found) == 1, [str(x.message) for x in w]
    assert str(found[0].message) == f"{where}: {shown}, outside what the interface accepts"
    assert found[0].filename == __file__
    with pytest.raises(ga.InvalidInputError, match="which the interface cannot show"):
        project.save(project_path(), overwrite=True)


def project_path():
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp()) / "p.ghe"


def test_the_warning_can_be_silenced(cli, project):
    project.ground_heat_exchanger.active_length = 1000.0
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        warnings.simplefilter("ignore", ga.OutsideInterfaceWarning)
        assert project.simulate().converged


def test_water_ignores_its_antifreeze(cli, project):
    project.heat_carrier_fluid = ga.HeatCarrierFluid("Water", 30)
    _, w = caught(project.compute_borehole_resistance)
    assert any("water takes no antifreeze" in str(x.message) for x in w)


def test_pump_b_at_zero_is_a_new_project(cli, project, tmp_path):
    assert project.gshp_system.flow_rate_of_pump_b == ga.ByMode(0, 0)
    _, w = caught(lambda: project.save(tmp_path / "p.ghe"))
    assert not w, [str(x.message) for x in w]


def test_disabled_fields_are_not_checked(cli, project):
    # Pump B's fields are disabled under a water-to-air system.
    project.gshp_system.system_type = "Water-air (zone)"
    project.gshp_system.flow_rate_of_pump_b = ga.ByMode(5, 5)
    _, w = caught(project.size)
    assert not w, [str(x.message) for x in w]
    project.gshp_system.system_type = "Water-water (zone)"
    _, w = caught(project.size)
    assert len(w) == 2 and all(issubclass(x.category, ga.OutsideInterfaceWarning) for x in w)


def test_a_project_of_the_application_opens_without_warning(cli, tmp_path, project):
    path = project.save(tmp_path / "p.ghe")
    q, w = caught(lambda: ga.Project.load(path))
    assert q.to_case()["borehole"] == project.to_case()["borehole"] and not w
    _, w = caught(q.simulate)
    assert not w
