import math

import pytest

import pyghe as ga
from pyghe._cli import plain


def test_unknown_command_is_refused(project):
    with pytest.raises(ValueError, match="unknown command"):
        ga.run_many([project], "sizing")


def test_sweep_needs_parameters(project):
    with pytest.raises(ga.InvalidInputError):
        ga.sweep(project, {})


def test_default_workers_fit_in_memory(monkeypatch):
    from pyghe import batch
    monkeypatch.setattr(batch.os, "cpu_count", lambda: 32)
    monkeypatch.setattr(batch, "available_memory", lambda: 3.5 * batch.MEMORY_PER_PROCESS["simulate"] / batch.MEMORY_SHARE)
    workers, threads = batch._plan(None, None, "simulate")
    assert workers == 3 and threads == 10
    monkeypatch.setattr(batch, "available_memory", lambda: 0.0)
    assert batch._plan(None, None, "simulate")[0] == 1
    assert batch._plan(8, None, "simulate") == (8, 4)
    monkeypatch.setattr(batch, "available_memory", lambda: None)
    assert batch._plan(None, None, "simulate")[0] == 16


def test_available_memory_is_plausible():
    from pyghe.batch import available_memory
    m = available_memory()
    assert m is None or 1e8 < m < 1e14


def test_run_many_keeps_the_order_and_matches_single_runs(cli, project):
    projects = []
    for k in (1.5, 2.5, 3.5):
        q = project.copy()
        q.ground_heat_exchanger.ground_thermal_conductivity = k
        projects.append(q)
    results = ga.run_many(projects, "size", workers=3, threads=1)
    singles = [q.size(threads=1) for q in projects]
    assert [plain(r.raw) for r in results] == [plain(s.raw) for s in singles]
    lengths = [r.governing_total_borehole_length for r in results]
    assert lengths[0] > lengths[1] > lengths[2]
    assert all(r.meta["threads"] == 1 for r in results)


def test_a_failed_case_does_not_stop_the_others(cli, project):
    broken = project.copy()
    broken.heat_carrier_fluid = None
    results = ga.run_many([project, broken, project], "borehole_resistance", workers=2)
    assert isinstance(results[1], ga.InvalidInputError)
    assert "heat_carrier_fluid" in str(results[1])
    assert results[0].converged and results[2].converged


def test_sweep_product_and_columns(cli, project):
    pd = pytest.importorskip("pandas")
    table = ga.sweep(project, {
        "ground_heat_exchanger.ground_thermal_conductivity": [2.0, 3.0],
        "gshp_system.flow_rate_of_pump_a.heating": [80, 120],
    }, "size", workers=4)
    assert isinstance(table, pd.DataFrame) and len(table) == 4
    assert list(table["ground_heat_exchanger.ground_thermal_conductivity"]) == [2.0, 2.0, 3.0, 3.0]
    assert list(table["gshp_system.flow_rate_of_pump_a.heating"]) == [80, 120, 80, 120]
    assert set(table["status"]) == {"ok"}
    for column in ("governing_total_borehole_length", "total_borehole_length_heating",
                   "total_borehole_length_cooling", "governing_mode", "result"):
        assert column in table
    shorter = table.groupby("ground_heat_exchanger.ground_thermal_conductivity")["governing_total_borehole_length"].mean()
    assert shorter[3.0] < shorter[2.0]
    assert table["result"][0].case["system"]["flowRate"]["heating"] == 80


def test_sweep_reports_a_refused_value(cli, project):
    pytest.importorskip("pandas")
    table = ga.sweep(project, {"ground_heat_exchanger.ground_thermal_conductivity": [2.0, -1.0]},
                     "borehole_resistance")
    assert list(table["status"]) == ["ok", "failed"]
    assert "ground_thermal_conductivity" in table["error"][1]
    assert math.isnan(table["equivalent_borehole_resistance_heating"][1])


def test_sweep_unknown_path(cli, project):
    pytest.importorskip("pandas")
    table = ga.sweep(project, {"ground_heat_exchanger.conductivity": [2.0]}, "gfunction")
    assert table["status"][0] == "failed" and "no attribute" in table["error"][0]


def test_sweep_custom_outputs(cli, project):
    pytest.importorskip("pandas")
    table = ga.sweep(project, {"simulation_duration": [1, 5]}, "simulate",
                     outputs=lambda r: {"eft_hours": r.eft.size})
    assert list(table["eft_hours"]) == [8760, 5 * 8760]
