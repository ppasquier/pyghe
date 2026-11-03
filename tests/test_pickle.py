"""Projects, results and errors go through pickle: multiprocessing, joblib and
ProcessPoolExecutor send them so, and keep their checks on the way."""

import math
import pickle

import numpy as np
import pytest

import pyghe as ga


def twin(obj):
    return pickle.loads(pickle.dumps(obj))


def test_a_project_survives_pickle(project):
    q = twin(project)
    assert q == project and q is not project
    assert q.heat_pump_performance.dhw_performance.cooling == math.inf


def test_checks_survive_pickle(project):
    q = twin(project)
    with pytest.raises(ga.InvalidInputError, match="flow_rate_of_pump_a.heating"):
        q.gshp_system.flow_rate_of_pump_a.heating = -1
    with pytest.raises(ga.InvalidInputError, match="temperature_limit.cooling"):
        q.heat_pump_performance.temperature_limit.cooling = 80
    with pytest.raises(ga.InvalidInputError):
        q.sizing_tool.duration_of_yearly_pulse = 7
    with pytest.raises(ga.InvalidInputError):
        q.heat_carrier_fluid.fluid = "Brine"
    with pytest.raises(ValueError):
        q.building_loads.combined_demand[0] = 1.0


def test_every_node_type_survives_pickle():
    nodes = [ga.SingleULoop(borehole_diameter=0.15), ga.DoubleULoopA(), ga.DoubleULoopD(), ga.Coaxial(),
             ga.StandingColumn(bleed_flow_rate=5), ga.HourlyBuildingLoadsSeparate(),
             ga.MonthlyBuildingLoadsSeparate(cooling_demand=np.ones(12)), ga.HourlyGroundLoadsCombined(),
             ga.ManufacturerData(eft=[0, 10], tc=[1, 2], hr=[2, 3], hc=[3, 4], he=[1, 2]),
             ga.PerformanceConstant(cooling_cop=4), ga.ProjectDescription(project_name="x"),
             ga.Coordinates.rectangle(2, 3, 5.0), ga.ByMode(1, 2)]
    for n in nodes:
        assert twin(n) == n


def test_errors_survive_pickle():
    e = twin(ga.InvalidInputError("p.x must be > 0"))
    assert isinstance(e, ga.InvalidInputError) and str(e) == "p.x must be > 0"
    e = twin(ga.NotConvergedError("did not converge", None))
    assert isinstance(e, ga.NotConvergedError) and str(e) == "did not converge" and e.result is None


def test_results_survive_pickle(cli, project):
    for result in (project.simulate(series="all"), project.size(), project.compute_gfunction(),
                   project.compute_borehole_resistance(include_grid=True),
                   ga.fluid_properties(project.heat_carrier_fluid, [0, 10])):
        r = twin(result)
        assert type(r) is type(result) and r.status == result.status and r.case == result.case
    r = twin(project.simulate(series="all"))
    assert np.array_equal(r.eft, project.simulate().eft)
    assert r.summary.minimum_eft == project.simulate().summary.minimum_eft
    with pytest.raises(ga.SeriesNotRequested):
        twin(project.simulate()).hourly.ground_load
    s = twin(project.size())
    assert s.total_borehole_length == project.size().total_borehole_length


def test_a_not_converged_error_carries_its_result(cli, project):
    e = twin(ga.NotConvergedError("ghe sizing: the computation did not converge", project.size()))
    assert isinstance(e.result, ga.SizingResult) and math.isfinite(e.result.governing_total_borehole_length)
