"""The project used by the three notebooks: a small office building heated and cooled by four
heat pumps on a field of twelve boreholes.

Everything in it is invented, but built to look like a real case: the heating load follows the
outdoor temperature and the occupancy of the week, there is a cooling season, domestic hot water
on weekdays, and a field a little longer than the Sizing tool asks for, so that the entering fluid
temperature comes close to its limit without crossing it. `make_project()` returns a fresh
`Project` each time, so a notebook can change its copy freely.
"""

import numpy as np

import pyghe as ga


def hourly_loads(seed=7):
    """Heating, cooling and domestic hot water demands in kW, 8760 values each."""
    rng = np.random.default_rng(seed)
    hour = np.arange(8760)
    day = hour // 24
    hour_of_day = hour % 24
    weekday = (day % 7) < 5

    # Outdoor temperature: a seasonal wave, a daily wave, and weather that lingers for days.
    seasonal = -10 * np.cos(2 * np.pi * (day - 15) / 365)                 # coldest in mid-January
    daily = -3.5 * np.cos(2 * np.pi * (hour_of_day - 4) / 24)             # coldest at 4 am
    weather = np.repeat(rng.normal(0, 3.0, 366), 24)[:8760]
    outdoor = 6 + seasonal + daily + weather

    # Occupancy: full on weekdays between 7 and 18, a reduced night and weekend setback.
    occupied = weekday & (hour_of_day >= 7) & (hour_of_day < 18)
    occupancy = np.where(occupied, 1.0, 0.45)

    heating = 1.7 * np.clip(14 - outdoor, 0, None) * occupancy
    cooling = 2.6 * np.clip(outdoor - 10, 0, None) * np.where(occupied, 1.0, 0.3)
    dhw = np.where(weekday & (hour_of_day >= 8) & (hour_of_day < 17), 1.5, 0.3)
    return heating, cooling, dhw


def make_project():
    heating, cooling, dhw = hourly_loads()

    p = ga.Project()
    p.project_description.project_name = "Office building (notebooks)"
    p.simulation_duration = 25

    p.building_loads = ga.HourlyBuildingLoadsSeparate(
        cooling_demand=cooling, heating_demand=heating, dhw_demand=dhw)

    s = p.gshp_system
    s.system_type = "Water-water (zone)"
    s.number_of_heat_pumps = 4
    s.flow_rate_of_pump_a = ga.ByMode(heating=300, cooling=300)           # L/min, whole field
    s.power_of_auxiliary = ga.ByMode(heating=8, cooling=0)                # kW per heat pump

    hp = p.heat_pump_performance
    hp.temperature_limit = ga.ByMode(heating=0.0, cooling=30.0)           # °C
    hp.performance_data = ga.PerformanceTemperature(
        eft=[-5, 0, 10, 20, 30],
        cooling_cap=[0, 0, 11.5, 10.5, 9.5], cooling_cop=[0, 0, 6.8, 5.2, 4.0],
        heating_cap=[8.0, 8.8, 10.5, 12.0, 13.0], heating_cop=[2.9, 3.2, 3.9, 4.6, 5.3])   # per heat pump

    p.heat_carrier_fluid = ga.HeatCarrierFluid("Propylene glycol", antifreeze_mass_concentration=25)
    p.borehole_resistance = ga.SingleULoop(
        borehole_diameter=0.152, grout_thermal_conductivity=1.25, shank_spacing=0.1,
        pipe_inner_diameter=0.033, pipe_outer_diameter=0.044, pipe_thermal_conductivity=0.39)

    g = p.ground_heat_exchanger
    g.ground_thermal_conductivity = 2.5
    g.ground_volumetric_capacity = 2.2
    g.mean_surface_temperature = 8.0
    g.geothermal_heat_flux = 60
    g.active_length = 100
    g.burial_depth = 2
    g.coordinates = ga.Coordinates.rectangle(nx=4, ny=3, spacing=6.0)

    p.sizing_tool.duration_of_yearly_pulse = 10
    p.sizing_tool.duration_of_hourly_peak_pulse = 6
    return p
