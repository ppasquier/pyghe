"""Result classes: names, units and signs of the interface, read against the executable's raw
output. The first tests need no executable."""

import json
import math
import warnings

import numpy as np
import pytest

import pyghe as ga
from pyghe.results import make


def fake(command, result, status=0):
    return {"meta": {"program": "AnalysisSuite-cli", "version": "x", "interfaceVersion": "1.2",
                     "command": command},
            "status": status, "statusText": "ok" if status == 0 else "notConverged",
            "warnings": [], "result": result}


def test_not_converged_warns_or_raises():
    doc = fake("ghe gfunction", {"converged": False, "timeStep": 3600, "values": [1e-3, 2e-3]}, status=1)
    with pytest.warns(ga.ConvergenceWarning):
        r = make(doc, {"ground": {"conductivity": 2.0}})
    assert not r.converged and not r.gfunction_converged
    with pytest.raises(ga.NotConvergedError) as e:
        make(doc, {"ground": {"conductivity": 2.0}}, strict=True)
    assert e.value.result.values[1] == 2e-3


def test_gfunction_dimensionless_and_time():
    r = make(fake("ghe gfunction", {"converged": True, "timeStep": 3600, "values": [0.01, 0.02]}),
             {"ground": {"conductivity": 2.0}})
    assert list(r.time) == [3600.0, 7200.0]
    assert r.dimensionless[1] == 2 * math.pi * 2.0 * 0.02


def test_sizing_without_finite_length_warns():
    side = {"totalLength": None, "lengthPerBorehole": None, "groundLoadPulses": {}, "groundResistances": {}}
    doc = fake("ghe sizing", {"heating": side, "cooling": side, "heatPumps": {}})
    with pytest.warns(ga.KernelWarning, match="no finite"):
        r = make(doc, {})
    assert r.governing_mode is None and math.isnan(r.governing_total_borehole_length)


def test_resistance_in_interface_units(cli, project):
    r = project.compute_borehole_resistance()
    raw = r.raw
    assert r.flow_rate_per_borehole.heating == raw["heating"]["flowRatePerBorehole"] * 60000
    assert r.flow_rate_per_borehole.heating == pytest.approx(96 / 4)
    assert r.borehole_efficiency.cooling == raw["cooling"]["efficiency"] * 100
    assert r.effective_borehole_resistance.heating == raw["heating"]["effectiveBoreholeResistance"]
    assert r.equivalent_borehole_resistance.cooling == raw["cooling"]["boreholeResistance"]
    assert r.temperature_limit.heating == 0.0 and r.temperature_limit.cooling == 30.0
    assert r.grid is None
    assert "effective_borehole_resistance (Rb*)" in repr(r)


def test_resistance_grid(cli, project):
    g = project.compute_borehole_resistance(include_grid=True).grid
    assert g.effective_borehole_resistance.shape == (160, 280)
    assert g.flow_rate_per_borehole[0] == pytest.approx(10.0) and g.flow_rate_per_borehole[-1] == pytest.approx(120.0)


def test_simulation_result(cli, project):
    r = project.simulate()
    assert r.converged and r.gfunction_converged and r.iterations > 0
    assert r.eft.shape == (25 * 8760,) and r.eft is r.hourly.entering_fluid_temperature
    assert sorted(r.hourly.names) == ["effective_cop", "entering_fluid_temperature"]
    assert r.daily_eft.size == 25 * 365 and r.monthly_eft.size == 25 * 12
    assert r.summary.minimum_eft == pytest.approx(np.nanmin(r.eft))
    assert r.summary.maximum_eft == pytest.approx(np.nanmax(r.eft))
    assert r.residuals.eft <= 1e-3
    assert r.heat_pumps.total_installed_capacity_at_tlim.heating > 0
    assert r.undisturbed_ground_temperature == pytest.approx(10 + (2 + 75) * 0.06 / 2.5)
    with pytest.raises(ga.SeriesNotRequested, match="ground_load"):
        r.hourly.ground_load
    with pytest.raises(AttributeError):
        r.hourly.eft_typo
    with pytest.raises(AttributeError):
        r.hourly.entering_fluid_temperature = None


def test_simulation_ground_load_sign(cli, project):
    """Heating months extract heat: the ground load is negative there, as in the interface's
    chart (positive when heat is injected)."""
    r = project.simulate(series=["ground_load", "building_load"])
    january = slice(0, 744)
    assert np.mean(r.hourly.building_load[january]) > 0
    assert np.mean(r.hourly.ground_load[january]) < 0


def test_sizing_result(cli, project):
    r = project.size()
    raw = r.raw
    assert r.total_borehole_length.heating == raw["heating"]["totalLength"]
    assert r.active_length.cooling == raw["cooling"]["lengthPerBorehole"]
    assert r.yearly_ground_load.heating == raw["heating"]["groundLoadPulses"]["yearly"]
    assert r.hourly_peak_response_factor.cooling == raw["cooling"]["groundResistances"]["peak"]
    assert r.governing_total_borehole_length == max(r.total_borehole_length.heating, r.total_borehole_length.cooling)
    assert r.governing_mode in ("heating", "cooling")
    # Three-pulse formula as the Sizing tool writes it, per mode.
    for m in ("heating", "cooling"):
        q = [getattr(r.yearly_ground_load, m), getattr(r.monthly_ground_load, m), getattr(r.hourly_ground_load, m)]
        rg = [getattr(r.yearly_response_factor, m), getattr(r.monthly_response_factor, m),
              getattr(r.hourly_peak_response_factor, m)]
        rb = getattr(r.effective_borehole_resistance, m)
        tg, tm = getattr(r.undisturbed_ground_temperature, m), getattr(r.mean_fluid_temperature, m)
        length = 1000 * (sum(a * b for a, b in zip(q, rg)) + q[2] * rb) / (tg - tm)
        assert length == pytest.approx(getattr(r.total_borehole_length, m), rel=1e-3)


def test_fluid_properties_in_interface_units(cli):
    r = ga.fluid_properties(ga.HeatCarrierFluid("Water"), [20.0])
    assert r.viscosity[0] == pytest.approx(r.raw["properties"][0]["dynamicViscosity"] * 1000)
    assert 0.9 < r.viscosity[0] < 1.1
    assert 990 < r.density[0] < 1000


def test_save_and_load(cli, project, tmp_path):
    r = project.size()
    r.save(tmp_path / "sizing.json")
    back = ga.load_result(tmp_path / "sizing.json")
    assert isinstance(back, ga.SizingResult)
    assert back.total_borehole_length == r.total_borehole_length and back.case == r.case


def test_to_dataframe(cli, project):
    pd = pytest.importorskip("pandas")
    frame = project.simulate(series=["ground_load"]).to_dataframe()
    assert isinstance(frame, pd.DataFrame) and len(frame) == 25 * 8760
    assert frame["year"].iloc[-1] == 25 and frame["day"].iloc[23] == 1 and frame["day"].iloc[24] == 2


def test_strict_passes_through(cli, project):
    with warnings.catch_warnings():
        warnings.simplefilter("error", ga.ConvergenceWarning)
        assert project.compute_gfunction(strict=True).converged


def test_simulation_saved_and_loaded(cli, project, tmp_path):
    r = project.simulate(series=["ground_load", "entering_fluid_temperature"])
    r.save(tmp_path / "simulation.json")
    back = ga.load_result(tmp_path / "simulation.json")
    assert np.array_equal(back.eft, r.eft) and np.array_equal(back.hourly.ground_load, r.hourly.ground_load)
    assert back.summary.maximum_eft == r.summary.maximum_eft


def test_series_arrive_from_the_binary_file(cli, project):
    r = project.simulate(keep_files=True)
    out = json.loads(open(r.files["result"], encoding="utf-8").read())
    assert out["result"]["hourly"]["enteringFluidTemperature"] == {"binary": {"offset": out["result"]["hourly"][
        "enteringFluidTemperature"]["binary"]["offset"], "count": 25 * 8760}}
    assert out["binary"]["format"] == "float64, little-endian"
    assert not r.eft.flags.writeable
