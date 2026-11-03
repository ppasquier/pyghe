"""Sphinx configuration of the pyghe documentation."""

import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / "src"))

import pyghe  # noqa: E402

project = "pyghe"
author = "Philippe Pasquier"
copyright = "2026, Philippe Pasquier"
release = pyghe.__version__
version = release

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "numpydoc",
]

# The pages stay in Markdown so that tests/test_docs.py can run their code blocks.
source_suffix = {".md": "myst-nb", ".ipynb": "myst-nb", ".rst": "restructuredtext"}
root_doc = "index"
exclude_patterns = ["_build"]
myst_enable_extensions = ["dollarmath", "deflist"]
myst_heading_anchors = 3

# The notebooks are shown with the outputs saved in them: building the documentation needs
# neither the executable nor a licence.
nb_execution_mode = "off"

numpydoc_show_class_members = False

html_theme = "sphinx_rtd_theme"
html_title = f"pyghe {release}"
html_static_path = ["_static"]
html_show_sourcelink = False


def _copy_notebooks():
    """Sphinx reads only what lies under docs/, so the notebooks of examples/ are copied into
    docs/notebooks/, with their links to docs/ made relative to the copy."""
    target = DOCS / "notebooks"
    target.mkdir(exist_ok=True)
    for source in sorted((DOCS.parent / "examples").glob("*.ipynb")):
        notebook = json.loads(source.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "markdown":
                cell["source"] = [line.replace("](../docs/", "](../") for line in cell["source"]]
        (target / source.name).write_text(json.dumps(notebook, ensure_ascii=False), encoding="utf-8")


_copy_notebooks()
