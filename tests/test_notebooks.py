"""The notebooks of examples/. Their committed outputs are checked without the executable (no error,
the figures are there, the links resolve); set PYGHE_TEST_NOTEBOOKS=1 to also run them afresh
against it, which takes about a minute. The notebooks are saved with their outputs, which is what
GitHub shows."""

import os
import re
import shutil
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
FIGURES = {"01_simulation.ipynb": 18, "02_sizing.ipynb": 7, "03_parametric_studies.ipynb": 5,
           "04_conductivity_uncertainty.ipynb": 1, "05_building_growth.ipynb": 1,
           "06_borehole_spacing.ipynb": 1, "07_field_ageing.ipynb": 1}


def outputs(notebook):
    for cell in notebook.cells:
        if cell.cell_type == "code":
            yield from cell.get("outputs", [])


@pytest.mark.parametrize("name", FIGURES)
def test_committed_outputs_are_complete(name):
    notebook = nbformat.read(EXAMPLES / name, as_version=4)
    assert not [o for o in outputs(notebook) if o.get("output_type") == "error"]
    figures = sum("image/png" in o.get("data", {}) for o in outputs(notebook))
    assert figures == FIGURES[name]
    assert all(c.execution_count for c in notebook.cells if c.cell_type == "code")


@pytest.mark.parametrize("name", FIGURES)
def test_links_resolve(name):
    notebook = nbformat.read(EXAMPLES / name, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type != "markdown":
            continue
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", cell.source):
            if "://" not in target:
                assert (EXAMPLES / target).exists(), f"{name}: broken link {target}"


def test_the_style_reproduces_the_application_palette():
    import sys
    sys.path.insert(0, str(EXAMPLES))
    pytest.importorskip("matplotlib")
    import ghestyle

    assert (ghestyle.RED, ghestyle.RED2, ghestyle.ORANGE, ghestyle.GREEN, ghestyle.BLUE, ghestyle.BLUE2) == (
        "#EA3E08", "#F1815E", "#FFA300", "#9ACA54", "#40ABFF", "#83C8FF")
    blue, red = ghestyle.hue_colours(10)[0], ghestyle.hue_colours(10)[-1]
    assert blue[2] > blue[0] and red[0] > red[2]


@pytest.mark.skipif(os.environ.get("PYGHE_TEST_NOTEBOOKS") != "1",
                    reason="set PYGHE_TEST_NOTEBOOKS=1 to run the notebooks")
@pytest.mark.parametrize("name", FIGURES)
def test_notebooks_run(cli, tmp_path, monkeypatch, name):
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("matplotlib")
    shutil.copytree(EXAMPLES, tmp_path / "examples")
    monkeypatch.setenv("PYGHE_CLI", str(cli))
    notebook = nbformat.read(tmp_path / "examples" / name, as_version=4)
    client = nbclient.NotebookClient(notebook, timeout=900, kernel_name="python3",
                                     resources={"metadata": {"path": str(tmp_path / "examples")}})
    client.execute()
    figures = sum("image/png" in o.get("data", {}) for o in outputs(notebook))
    assert figures == FIGURES[name]
