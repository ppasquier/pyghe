"""Writing .ghe project files, read back by the executable as the application reads them.
Uses the project files of test_project.py when they are present. Needs the executable."""

import warnings

import pytest

import pyghe as ga
from conftest import make_project
from test_project import PROJECTS, project_file


def written(project):
    """The case of a project as a file holds it: every borehole with its orientation."""
    case = project.to_case()
    case["field"] = [{"azimuth": 0.0, "dip": 90.0, **b} for b in case["field"]]
    return case


def load_quietly(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ga.Project.load(path)


def test_a_new_project_reads_back_as_written(cli, tmp_path, project):
    path = project.save(tmp_path / "new.ghe")
    assert project.source_file == str(path)
    back = ga.Project.load(path)
    assert back.to_case() == written(project)
    assert back.source_file == str(path)


def test_saving_again_writes_where_it_was_saved(cli, tmp_path, project):
    path = project.save(tmp_path / "new.ghe")
    project.ground_heat_exchanger.active_length = 120.0
    assert project.save() == path
    assert ga.Project.load(path).ground_heat_exchanger.active_length == 120.0


@pytest.mark.parametrize("path", PROJECTS or [pytest.param(None, marks=pytest.mark.skip("no project files"))],
                         ids=lambda p: p.split("\\")[-1].split("/")[-1] if p else "none")
def test_every_project_reads_back_as_written(cli, tmp_path, path):
    p = load_quietly(path)
    copy = p.save(tmp_path / "copy.ghe")
    assert load_quietly(copy).to_case() == p.to_case()


def test_a_loaded_project_keeps_what_the_package_does_not_read(cli, tmp_path):
    cbor2 = pytest.importorskip("cbor2")
    source = project_file("Test1_Version3p1.ghe")
    p = load_quietly(source)
    p.ground_heat_exchanger.active_length = 111.0
    copy = p.save(tmp_path / "copy.ghe")

    with open(source, "rb") as f:
        before = cbor2.load(f)
    with open(copy, "rb") as f:
        after = cbor2.load(f)
    assert set(after["modules"]) == set(before["modules"])
    for code in before["modules"]:
        if code != "GHE":
            assert after["modules"][code] == before["modules"][code]
    ghe_before, ghe_after = before["modules"]["GHE"]["data"], after["modules"]["GHE"]["data"]
    for key in ("saveContour", "EnergyCost", "ProjectCost", "BaseMapImage", "ReportContent", "fluidEvalT"):
        assert ghe_after.get(key) == ghe_before.get(key), key
    assert ghe_after["paraGui"][10] == 111.0
    assert after["createdBy"] == before["createdBy"]
    assert after["writtenBy"]["writer"].startswith("pyghe ")
    assert after["writtenBy"]["ghe"]


def test_the_flow_rate_of_pump_b_goes_through(cli, tmp_path):
    p = load_quietly(project_file("Test1_Version3p1.ghe"))
    assert p.gshp_system.flow_rate_of_pump_b == ga.ByMode(heating=200.0, cooling=200.0)
    q = ga.Project.from_case(p.to_case())
    q.gshp_system.flow_rate_of_pump_b = ga.ByMode(heating=150.0, cooling=120.0)
    back = ga.Project.load(q.save(tmp_path / "pump_b.ghe"))
    assert back.gshp_system.flow_rate_of_pump_b == ga.ByMode(heating=150.0, cooling=120.0)


def test_an_existing_file_is_kept_without_overwrite(cli, tmp_path, project):
    path = tmp_path / "taken.ghe"
    path.write_bytes(b"not mine")
    with pytest.raises(ga.CliError, match="overwrite"):
        project.save(path)
    assert path.read_bytes() == b"not mine"
    project.save(path, overwrite=True)
    assert ga.Project.load(path).to_case() == written(project)


def test_a_project_from_no_file_needs_a_path(project):
    with pytest.raises(ValueError, match="give the path"):
        project.save()


def test_an_incomplete_project_is_not_written(tmp_path):
    with pytest.raises(ga.InvalidInputError):
        ga.Project().save(tmp_path / "empty.ghe")
    assert not (tmp_path / "empty.ghe").exists()


def test_a_value_the_application_would_repair_is_refused(cli, tmp_path, project):
    project.borehole_resistance.pipe_outer_diameter = 0.035  # wall of 1 mm; the interface wants 2
    with pytest.raises(ga.InvalidInputError, match="pipe_outer_diameter|outerDiameter"):
        project.save(tmp_path / "thin.ghe")
    assert not (tmp_path / "thin.ghe").exists()


def test_table_values_beyond_two_decimals_are_reported(cli, tmp_path, project):
    project.heat_pump_performance.performance_data.cooling_cop = [6.125, 3.5]
    with pytest.warns(ga.KernelWarning, match="two decimals"):
        project.save(tmp_path / "rounded.ghe")


def test_make_project_is_complete():
    assert make_project().validate("simulate") == []
