"""The scripts of examples/ run and save their figure. The figures shown in the documentation
(docs/_static/examples) are made the same way. Needs the executable and matplotlib."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SCRIPTS = ["conductivity_uncertainty", "building_growth", "borehole_spacing", "field_ageing"]


def test_every_script_is_listed():
    helpers = {"demo_project", "ghestyle", "ghecharts"}
    on_disk = sorted(p.stem for p in EXAMPLES.glob("*.py") if p.stem not in helpers)
    assert on_disk == sorted(SCRIPTS)


@pytest.mark.parametrize("name", SCRIPTS)
def test_the_script_runs(name, cli, tmp_path):
    figure = tmp_path / f"{name}.png"
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONIOENCODING="utf-8", PYGHE_CLI=str(cli))
    done = subprocess.run([sys.executable, f"{name}.py", str(figure)], cwd=EXAMPLES, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr
    assert figure.stat().st_size > 10_000
