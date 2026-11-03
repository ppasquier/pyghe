"""Every status of the executable becomes the right exception. The executable is replaced by a
fake, so these tests run anywhere."""

import json
import subprocess

import pytest

import pyghe as ga
from pyghe import _cli


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    """Installs a fake executable; returns a dict to set what it answers."""
    exe = tmp_path / "AnalysisSuite-cli.exe"
    exe.write_bytes(b"")
    answer = {"interface": "1.9", "status": 0, "statusText": "ok", "error": None, "result": {},
              "warnings": [], "write": True}
    calls = []

    def run(args, capture_output=True, env=None, timeout=None, **kw):
        calls.append({"args": args, "env": env})
        if args[1] == "version":
            meta = {"interfaceVersion": answer["interface"], "command": "version"}
            return subprocess.CompletedProcess(args, 0, json.dumps({"meta": meta}).encode(), b"")
        if answer["write"]:
            out = args[args.index("--out") + 1]
            doc = {"meta": {"program": "AnalysisSuite-cli", "version": "x",
                            "interfaceVersion": answer["interface"], "command": " ".join(args[1:3])},
                   "status": answer["status"], "statusText": answer["statusText"],
                   "warnings": answer["warnings"]}
            if answer["error"] is not None:
                doc["error"] = answer["error"]
            if answer["status"] <= 1:
                doc["result"] = answer["result"]
            with open(out, "w", encoding="utf-8") as f:
                json.dump(doc, f)
        return subprocess.CompletedProcess(args, answer["status"], b"", b"boom")

    monkeypatch.setattr(_cli.subprocess, "run", run)
    monkeypatch.setattr(_cli, "_checked", {})
    monkeypatch.setattr(_cli, "_use_server", False)
    ga.configure(cli=exe)
    answer["calls"] = calls
    yield answer
    ga.configure(None)


@pytest.mark.parametrize("status, error, exception", [
    (3, "internal error: bad_alloc", ga.KernelError),
    (4, "cannot read the input", ga.CliError),
    (5, "scripted access requires an active licence", ga.LicenseError),
    (9, "?", ga.CliError),
])
def test_statuses_become_exceptions(fake_cli, project, status, error, exception):
    fake_cli.update(status=status, statusText="x", error=error)
    with pytest.raises(exception, match=error[:10].replace("?", r"\?")):
        project.compute_gfunction()


def test_input_error_is_translated(fake_cli, project):
    fake_cli.update(status=2, statusText="invalidInput", error="ground.conductivity: must be > 0")
    with pytest.raises(ga.InvalidInputError, match=r"^p\.ground_heat_exchanger\.ground_thermal_conductivity: must be > 0$"):
        project.compute_gfunction()


def test_missing_output_is_a_kernel_error(fake_cli, project):
    fake_cli.update(write=False, status=3)
    with pytest.raises(ga.KernelError, match="without a result.*boom"):
        project.compute_gfunction()


def test_old_executable_is_refused(fake_cli, project):
    fake_cli.update(interface="1.7")
    with pytest.raises(ga.CliNotFoundError, match="1.7"):
        project.compute_gfunction()


def test_kernel_warnings_are_raised(fake_cli, project):
    fake_cli.update(result={"converged": True, "timeStep": 3600, "values": [0.1]},
                    warnings=["borehole: the flow rate per borehole is clamped to the table"])
    with pytest.warns(ga.KernelWarning, match="clamped"):
        project.compute_gfunction()


def test_threads_reach_the_environment(fake_cli, project):
    fake_cli.update(result={"converged": True, "timeStep": 3600, "values": [0.1]})
    project.compute_gfunction(threads=3)
    assert fake_cli["calls"][-1]["env"]["OMP_NUM_THREADS"] == "3"


def test_keep_files(fake_cli, project):
    fake_cli.update(result={"converged": True, "timeStep": 3600, "values": [0.1]})
    r = project.compute_gfunction(keep_files=True)
    case = json.loads(open(r.files["case"], encoding="utf-8").read())
    assert case == r.case and case["units"] == "interface"


def test_configured_path_must_exist(tmp_path):
    ga.configure(cli=tmp_path / "nowhere.exe")
    try:
        with pytest.raises(ga.CliNotFoundError, match="does not exist"):
            ga.find_cli()
    finally:
        ga.configure(None)


def test_environment_path_must_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("PYGHE_CLI", str(tmp_path / "nowhere.exe"))
    with pytest.raises(ga.CliNotFoundError, match="PYGHE_CLI"):
        ga.find_cli()


def test_not_found_says_how_to_configure(monkeypatch):
    monkeypatch.delenv("PYGHE_CLI", raising=False)
    monkeypatch.setattr(_cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(_cli, "_default_locations", lambda: [])
    with pytest.raises(ga.CliNotFoundError, match="configure"):
        ga.find_cli()


def test_not_found_points_to_the_download(monkeypatch):
    monkeypatch.delenv("PYGHE_CLI", raising=False)
    monkeypatch.setattr(_cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(_cli, "_default_locations", lambda: [])
    with pytest.raises(ga.CliNotFoundError, match="gheanalysis.com/pages/download"):
        ga.find_cli()


def test_the_installation_folder_is_searched_last(tmp_path, monkeypatch):
    installed = tmp_path / "AnalysisSuite-cli.exe"
    installed.write_bytes(b"")
    monkeypatch.delenv("PYGHE_CLI", raising=False)
    monkeypatch.setattr(_cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(_cli, "_default_locations", lambda: [tmp_path / "missing.exe", installed])
    assert ga.find_cli() == str(installed)
    on_path = tmp_path / "on-path.exe"
    on_path.write_bytes(b"")
    monkeypatch.setattr(_cli.shutil, "which", lambda name: str(on_path))
    assert ga.find_cli() == str(on_path)


def test_default_locations_follow_the_installer(tmp_path, monkeypatch):
    monkeypatch.setattr(_cli.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(_cli.sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "pf"))
    places = _cli._default_locations()
    assert places[0] == tmp_path / "AnalysisSuite-cli" / "AnalysisSuite-cli.exe"
    assert tmp_path / "AnalysisSuite" / "AnalysisSuite-cli.exe" in places
    assert tmp_path / "pf" / "Analysis Suite" / "AnalysisSuite-cli.exe" in places
    monkeypatch.setattr(_cli.sys, "platform", "linux")
    assert _cli._default_locations() == [tmp_path / "AnalysisSuite-cli" / "AnalysisSuite-cli"]
