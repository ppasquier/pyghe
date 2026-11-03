import numpy as np
import pytest

import pyghe as ga


def make_project():
    """A complete project: 2 × 2 single U-loop field, hourly combined loads, 25 years."""
    k = np.arange(8760)
    p = ga.Project()
    p.simulation_duration = 25
    p.building_loads = ga.HourlyBuildingLoadsCombined(
        combined_demand=40 * np.cos(2 * np.pi * k / 8760) + 8 * np.sin(2 * np.pi * k / 24))

    s = p.gshp_system
    s.system_type = "Water-water (zone)"
    s.number_of_heat_pumps = 4
    s.power_of_auxiliary = ga.ByMode(heating=15, cooling=20)
    s.flow_rate_of_pump_a = ga.ByMode(heating=96, cooling=96)

    hp = p.heat_pump_performance
    hp.temperature_limit = ga.ByMode(heating=0, cooling=30)
    hp.performance_data = ga.PerformanceTemperature(
        eft=[-5, 30], cooling_cap=[25, 20], cooling_cop=[6, 3.5], heating_cap=[15, 24], heating_cop=[3, 5])

    p.heat_carrier_fluid = ga.HeatCarrierFluid("Propylene glycol", antifreeze_mass_concentration=25)
    p.borehole_resistance = ga.SingleULoop(
        borehole_diameter=0.152, grout_thermal_conductivity=1.25, shank_spacing=0.1,
        pipe_inner_diameter=0.033, pipe_outer_diameter=0.044, pipe_thermal_conductivity=0.39)

    ghe = p.ground_heat_exchanger
    ghe.ground_thermal_conductivity = 2.5
    ghe.ground_volumetric_capacity = 2.2
    ghe.mean_surface_temperature = 10.0
    ghe.geothermal_heat_flux = 60.0
    ghe.active_length = 150.0
    ghe.burial_depth = 2.0
    ghe.coordinates = ga.Coordinates.rectangle(nx=2, ny=2, spacing=6.0)

    p.sizing_tool.duration_of_yearly_pulse = 10
    p.sizing_tool.duration_of_hourly_peak_pulse = 6
    return p


@pytest.fixture
def project():
    return make_project()


@pytest.fixture(scope="session")
def cli():
    """Path of AnalysisSuite-cli (PYGHE_CLI or PATH); the test is skipped without it."""
    try:
        return ga.find_cli()
    except ga.CliNotFoundError as e:
        pytest.skip(str(e))
