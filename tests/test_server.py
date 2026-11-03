"""The server answers exactly as a fresh process, and is reused, replaced and closed as it
should. Needs the executable."""

import _thread
import json
import threading
import time

import numpy as np
import pytest

import pyghe as ga
from pyghe import _cli
from pyghe._cli import plain


@pytest.fixture
def fresh_servers():
    ga.close_servers()
    yield
    ga.close_servers()
    ga.configure(server=True)


def test_server_and_process_give_the_same_bits(cli, project, fresh_servers):
    q = project.copy()
    q.ground_heat_exchanger.ground_thermal_conductivity = 3.1
    q.simulation_duration = 5
    runs = [(project, "simulate", {"series": "all"}), (q, "size", {}), (project, "compute_gfunction", {}),
            (q, "simulate", {"series": "all"}), (project, "size", {}), (q, "compute_borehole_resistance", {})]
    served = [plain(getattr(p, m)(threads=1, **o).raw) for p, m, o in runs]
    ga.configure(server=False)
    alone = [plain(getattr(p, m)(threads=1, **o).raw) for p, m, o in runs]
    assert served == alone


def test_one_server_is_reused(cli, project, fresh_servers):
    project.compute_gfunction(threads=1)
    first = _cli._servers[cli]
    project.compute_borehole_resistance(threads=1)
    project.size(threads=1)
    assert _cli._servers[cli] is first and len(_cli._servers) == 1


def test_another_thread_count_replaces_the_server(cli, project, fresh_servers):
    # A server holds about 1.5 GB: one per thread count would pile them up.
    project.compute_gfunction(threads=1)
    first = _cli._servers[cli]
    project.compute_gfunction(threads=2)
    assert len(_cli._servers) == 1 and _cli._servers[cli].threads == 2
    assert first.process.poll() is not None


def test_a_dead_server_is_replaced(cli, project, fresh_servers):
    project.compute_gfunction(threads=1)
    server = _cli._servers[cli]
    server.process.kill()
    server.process.wait()
    assert project.compute_gfunction(threads=1).converged
    assert _cli._servers[cli] is not server


def test_close_servers_stops_them(cli, project, fresh_servers):
    project.compute_gfunction(threads=1)
    server = _cli._servers[cli]
    ga.close_servers()
    assert server.process.poll() is not None and not _cli._servers


def test_a_stale_answer_is_not_taken_for_the_next_one(cli, project, tmp_path, fresh_servers):
    # A request whose answer was never read (what an interrupt leaves on macOS and Linux).
    ref = project.compute_gfunction().values
    server = _cli._servers[cli]
    case = tmp_path / "case.json"
    case.write_text(json.dumps(project.to_case()), encoding="utf-8")
    server.process.stdin.write(json.dumps({"id": -1, "command": "ghe gfunction", "in": str(case),
                                           "out": str(tmp_path / "out.json"),
                                           "binary": str(tmp_path / "out.f64")}) + "\n")
    server.process.stdin.flush()
    for _ in range(3):
        assert np.array_equal(project.compute_gfunction().values, ref)


def _slow_project(project):
    # Sizing an inclined field in groundwater flow: about 100 s.
    c = ga.Coordinates.rectangle(3, 3, 6.0)
    project.ground_heat_exchanger.coordinates = ga.Coordinates(x=c.x, y=c.y, az=np.zeros(9), dip=np.full(9, 80.0))
    project.ground_heat_exchanger.groundwater_flow = 1e-7
    return project


def test_an_interrupt_stops_a_computation_on_a_server(cli, project, fresh_servers):
    small = project.copy()
    ref = small.compute_gfunction().values
    slow = _slow_project(project)
    threading.Timer(1.0, _thread.interrupt_main).start()
    start = time.perf_counter()
    with pytest.raises(KeyboardInterrupt):
        slow.size()
    assert time.perf_counter() - start < 10
    assert not _cli._servers
    assert np.array_equal(small.compute_gfunction().values, ref)


def test_an_interrupt_stops_a_batch(cli, project, fresh_servers):
    slow = _slow_project(project)
    threading.Timer(1.0, _thread.interrupt_main).start()
    start = time.perf_counter()
    with pytest.raises(KeyboardInterrupt):
        ga.run_many([slow.copy() for _ in range(6)], "size", workers=2, threads=1)
    assert time.perf_counter() - start < 15


def test_timeout_runs_in_its_own_process(cli, project, fresh_servers):
    r = project.compute_gfunction(timeout=120)
    assert r.converged and not _cli._servers


def test_batch_servers_are_closed_with_the_batch(cli, project, fresh_servers):
    made = []
    original = _cli._Server

    class Spy(original):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            made.append(self)

    _cli._Server = Spy
    try:
        projects = [project.copy() for _ in range(4)]
        results = ga.run_many(projects, "gfunction", workers=2, threads=1)
    finally:
        _cli._Server = original
    assert all(r.converged for r in results)
    assert 1 <= len(made) <= 2 and all(s.process.poll() is not None for s in made)
    assert not _cli._servers
