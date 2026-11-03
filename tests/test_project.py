"""Reading .ghe project files. The projects live beside the repository, in "5-GHE Files" (set
PYGHE_PROJECTS to another folder); the tests that need them are skipped without it.
Needs the executable."""

import glob
import os
import warnings
from pathlib import Path

import pytest

import pyghe as ga

FOLDER = Path(os.environ.get("PYGHE_PROJECTS",
                             Path(__file__).resolve().parents[3] / ".." / "5-GHE Files")).resolve()
PROJECTS = sorted(glob.glob(str(FOLDER / "**" / "*.ghe"), recursive=True))


def project_file(name):
    found = [p for p in PROJECTS if p.endswith(name)]
    if not found:
        pytest.skip(f"{name} not found under {FOLDER}")
    return found[0]


@pytest.mark.parametrize("path", PROJECTS or [pytest.param(None, marks=pytest.mark.skip("no project files"))],
                         ids=lambda p: Path(p).name if p else "none")
def test_every_project_loads_and_simulates(cli, path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = ga.Project.load(path)
        assert p.validate("simulate") == []
        p.simulation_duration = 1
        r = p.simulate(threads=1)
    assert r.eft.size == 8760


def test_a_recent_project(cli):
    p = ga.Project.load(project_file("Test1_Version3p1.ghe"))
    assert isinstance(p.borehole_resistance, ga.DoubleULoopA)
    assert len(p.ground_heat_exchanger.coordinates) == 28
    assert isinstance(p.heat_pump_performance.performance_data, ga.ManufacturerData)
    assert p.simulation_duration == 10
    assert p.gshp_system.system_type in ga.SYSTEM_TYPES
    assert p.to_case()["units"] == "interface"


def test_an_old_project_warns_about_hot_water_cops(cli):
    with pytest.warns(ga.KernelWarning, match="domestic hot water COPs"):
        p = ga.Project.load(project_file("Test1_Version2p3.ghe"))
    assert p.heat_pump_performance.dhw_performance.heating == 2.75


def test_a_project_without_orientation_is_vertical(cli):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p = ga.Project.load(project_file("Example_3.ghe"))
    assert set(p.ground_heat_exchanger.coordinates.dip) == {90.0}


def test_missing_file(cli, tmp_path):
    with pytest.raises(ga.CliError, match="cannot open"):
        ga.Project.load(tmp_path / "nowhere.ghe")


def test_not_a_project(cli, tmp_path):
    other = tmp_path / "other.ghe"
    other.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ga.InvalidInputError, match="not an Analysis Suite project"):
        ga.Project.load(other)
