"""The documentation is tested like the code: every code block fenced as `python` in the README
and in docs/ is run against the executable. A block fenced `python skip` is shown but not run.
The pages of docs/ share one namespace, in reading order, like a tutorial: a later page uses the
project `p` that an earlier one built. Needs the executable."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["install", "getting-started", "project", "nodes", "computations", "many-cases", "recipes",
         "project-files", "errors", "reproducibility", "methods", "nomenclature", "api", "citing", "changelog", "index"]
FENCE = re.compile(r"^```(?P<info>[^\n]*)\n(?P<code>.*?)^```[ \t]*$", re.S | re.M)


def blocks(path):
    """The runnable blocks of a Markdown page, with the line each starts at."""
    text = path.read_text(encoding="utf-8")
    found = []
    for m in FENCE.finditer(text):
        if m.group("info").strip() == "python":
            found.append((text.count("\n", 0, m.start("code")) + 1, m.group("code")))
    return found


def run(path, namespace):
    for line, code in blocks(path):
        try:
            exec(compile("\n" * (line - 1) + code, str(path), "exec"), namespace)
        except Exception as error:
            raise AssertionError(f"{path.name}, block at line {line}: {type(error).__name__}: {error}") from error


def test_the_readme_runs(cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert blocks(ROOT / "README.md"), "the README holds no runnable example"
    run(ROOT / "README.md", {"__name__": "readme"})


def test_the_pages_run_in_reading_order(cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    namespace = {"__name__": "docs"}
    for name in PAGES:
        run(ROOT / "docs" / f"{name}.md", namespace)


def test_the_numbers_quoted_in_the_text_are_the_ones_computed(cli, tmp_path, monkeypatch):
    """The prose of the recipes and of Getting started quotes results: a change of the kernel
    that moves them must be noticed here, not by a reader."""
    monkeypatch.chdir(tmp_path)
    namespace = {"__name__": "docs"}
    for name in PAGES[:PAGES.index("recipes") + 1]:
        run(ROOT / "docs" / f"{name}.md", namespace)

    assert namespace["sizing"].governing_mode == "heating"
    assert 905 < namespace["sizing"].governing_total_borehole_length < 915       # "about 910 m"
    assert 3.6 < namespace["eft"].min() < 3.8                                    # "3.7 °C"
    assert namespace["result"].summary.hours_below_temperature_limit == 0

    assert namespace["lengths"] == [1117, 999, 911, 843]
    margins = namespace["margins"]
    assert [round(margins[g], 1) for g in (1.0, 1.2, 1.4)] == [3.7, 2.3, 0.8]
    assert [round(x, 2) for x in namespace["coldest"]] == [3.14, 3.74, 3.85]
    by_year = namespace["coldest_by_year"]
    assert [round(by_year[y - 1], 2) for y in (1, 5, 10, 25)] == [4.90, 4.32, 4.06, 3.74]


def test_every_page_is_in_the_list():
    on_disk = sorted(p.stem for p in (ROOT / "docs").glob("*.md"))
    assert on_disk == sorted(PAGES)


@pytest.mark.parametrize("page", ["README.md"] + [f"docs/{n}.md" for n in PAGES])
def test_relative_links_resolve(page):
    path = ROOT / page
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("mailto:"):
            continue
        assert (path.parent / target).exists(), f"{page}: broken link {target}"
