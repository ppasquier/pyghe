import math

import numpy as np
import pytest

import pyghe as ga


def test_nodes_are_named_after_the_analysis_tree():
    p = ga.Project()
    assert [f for f in p.__dataclass_fields__ if not f.startswith("_")] == [
        "project_description", "simulation_duration", "building_loads", "gshp_system",
        "heat_pump_performance", "heat_carrier_fluid", "borehole_resistance", "ground_heat_exchanger",
        "sizing_tool"]


def test_misspelt_attribute_is_refused(project):
    with pytest.raises(AttributeError):
        project.ground_heat_exchanger.ground_thermal_conductivty = 3.0
    with pytest.raises(AttributeError):
        project.heat_pumps = None


@pytest.mark.parametrize("value", [-1.0, float("nan"), "2.5 W/mK"])
def test_out_of_range_values_are_refused(project, value):
    with pytest.raises(ga.InvalidInputError, match="ground_thermal_conductivity"):
        project.ground_heat_exchanger.ground_thermal_conductivity = value


def test_choices_use_the_interface_wording(project):
    with pytest.raises(ga.InvalidInputError, match="Water-water"):
        project.gshp_system.system_type = "waterToWaterZone"
    with pytest.raises(ga.InvalidInputError, match="Propylene glycol"):
        ga.HeatCarrierFluid("propyleneGlycol")
    assert "Water-water (loop) - Geocooling" in ga.SYSTEM_TYPES


def test_concentration_in_percent():
    ga.HeatCarrierFluid("Ethylene glycol", antifreeze_mass_concentration=30)
    with pytest.raises(ga.InvalidInputError, match="60"):
        ga.HeatCarrierFluid("Ethylene glycol", antifreeze_mass_concentration=70)


def test_simulation_duration_choices(project):
    project.simulation_duration = 10.0
    assert project.simulation_duration == 10 and isinstance(project.simulation_duration, int)
    with pytest.raises(ga.InvalidInputError, match="one of"):
        project.simulation_duration = 7
    with pytest.raises(ga.InvalidInputError):
        project.simulation_duration = True


def test_hourly_series_length_and_read_only():
    with pytest.raises(ga.InvalidInputError, match="8760"):
        ga.HourlyBuildingLoadsCombined(combined_demand=np.zeros(8759))
    loads = ga.HourlyBuildingLoadsCombined(combined_demand=np.zeros(8760))
    with pytest.raises(ValueError):
        loads.combined_demand[0] = 1.0


def test_input_array_is_copied():
    q = np.zeros(8760)
    loads = ga.HourlyBuildingLoadsCombined(combined_demand=q)
    q[0] = 99.0
    assert loads.combined_demand[0] == 0.0


def test_by_mode_values_stay_checked(project):
    with pytest.raises(ga.InvalidInputError, match="flow_rate_of_pump_a.heating"):
        project.gshp_system.flow_rate_of_pump_a.heating = 0.0
    project.gshp_system.flow_rate_of_pump_a = (90, 100)
    assert project.gshp_system.flow_rate_of_pump_a.cooling == 100
    with pytest.raises(ga.InvalidInputError, match="temperature_limit.cooling"):
        project.heat_pump_performance.temperature_limit = ga.ByMode(heating=0, cooling=50)


def test_copy_is_independent(project):
    q = project.copy()
    q.ground_heat_exchanger.ground_thermal_conductivity = 3.0
    q.gshp_system.flow_rate_of_pump_a.heating = 120
    assert project.ground_heat_exchanger.ground_thermal_conductivity == 2.5
    assert project.gshp_system.flow_rate_of_pump_a.heating == 96
    assert q == q.copy() and q != project


def test_free_heat_recovery_is_the_default():
    assert ga.HeatPumpPerformance().dhw_performance.cooling == math.inf


def test_coordinates_helpers():
    c = ga.Coordinates.rectangle(nx=4, ny=5, spacing=6.0)
    assert len(c) == 20 and c.x.max() == 18.0 and c.y.max() == 24.0
    assert len(ga.Coordinates.from_points([(0, 0), (5, 0)], dip=[80, 90])) == 2


def test_validate_reports_shape_problems(project):
    ghe = project.ground_heat_exchanger
    ghe.coordinates = ga.Coordinates.from_points([(0, 0), (0, 0)])
    assert any("share the head" in m for m in project.validate())
    ghe.coordinates = ga.Coordinates.rectangle(nx=26, ny=25, spacing=5)
    assert any("625" in m for m in project.validate())


def test_validate_depends_on_the_command():
    p = ga.Project()
    p.borehole_resistance = ga.SingleULoop(borehole_diameter=0.15, grout_thermal_conductivity=1.5,
                                           shank_spacing=0.08, pipe_inner_diameter=0.026,
                                           pipe_outer_diameter=0.033, pipe_thermal_conductivity=0.4)
    p.ground_heat_exchanger = ga.GroundHeatExchanger(
        ground_thermal_conductivity=2, ground_volumetric_capacity=2, mean_surface_temperature=8,
        geothermal_heat_flux=50, active_length=150, burial_depth=2,
        coordinates=ga.Coordinates.rectangle(nx=1, ny=1, spacing=1))
    p.simulation_duration = 10
    assert p.validate("gfunction") == []
    missing = p.validate("simulate")
    assert "p.heat_carrier_fluid is not set" in missing and "p.building_loads is not set" in missing
    assert "p.gshp_system.number_of_heat_pumps is not set" in missing


def test_standing_column_needs_pump_c_and_bleed(project):
    project.borehole_resistance = ga.StandingColumn(
        borehole_diameter=0.15, grout_thermal_conductivity=1.5, pipe_inner_diameter=0.1,
        pipe_outer_diameter=0.11, pipe_thermal_conductivity=0.4, outer_pipe_inner_diameter=0.14,
        outer_pipe_outer_diameter=0.145, outer_pipe_thermal_conductivity=40)
    missing = project.validate("gfunction")
    assert "p.gshp_system.flow_rate_of_pump_c is not set" in missing
    assert "p.borehole_resistance.bleed_flow_rate is not set" in missing


def test_incomplete_project_raises_before_running(project):
    project.heat_carrier_fluid = None
    with pytest.raises(ga.InvalidInputError, match="p.heat_carrier_fluid is not set"):
        project.compute_borehole_resistance()


def test_repr_shows_symbols_and_units(project):
    text = repr(project)
    assert "ground_thermal_conductivity (λs) = 2.5 W/m·K" in text
    assert "ground_volumetric_capacity (Cs) = 2.2 MJ/m³·K" in text
    assert "flow_rate_of_pump_a (VA) = ByMode(heating=96.0 L/min" in text
