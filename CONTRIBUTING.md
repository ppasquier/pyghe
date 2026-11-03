# Contributing

Thank you for looking at pyghe. Bug reports, questions and pull requests are welcome.

## What belongs here

pyghe contains no physics. It writes a project as a JSON case, runs `AnalysisSuite-cli`, and turns
the answer into Python objects. So there are two kinds of problems:

- A wrong or surprising **number** comes from the kernel of GHE Analysis. Open an issue anyway,
  with the smallest script that shows it: I will tell you whether it is the package or the kernel.
- A wrong **name, unit, sign, default, error message or example** is the package's, and a pull
  request is the quickest fix.

Names and units follow GHE Analysis (SI): one attribute for each node of the project tree, one
field for each label of the application. A new parameter takes the application's name, in
`snake_case`, and the unit the application shows.

## Setting up

```console
git clone https://github.com/ppasquier/pyghe
cd pyghe
python -m venv .venv
.venv/bin/python -m pip install -e ".[test,docs]"     # .venv/Scripts/python on Windows
.venv/bin/python -m pytest -q
```

Most tests run the executable, `AnalysisSuite-cli`, which comes with GHE Analysis
([download](https://www.gheanalysis.com/pages/download)) and needs a licence activated on the
computer; the Academic licence is free. The executable exists for Windows and macOS only. Without
it, the tests that need it are skipped and the others run, which is also what the continuous
integration does. Say in the pull request whether you ran the whole suite.

To point pyghe at an executable it does not find by itself, set the environment variable
`PYGHE_CLI` to its path.

## Documentation

The documentation is in `docs/` and builds with Sphinx:

```console
.venv/bin/python -m sphinx -b html docs docs/_build/html
```

Every code block of the documentation is run by `tests/test_docs.py` against the executable, so an
example that stops working fails the tests. A block fenced `python skip` is shown without being
run. The notebooks in `examples/` are saved with their outputs; `tests/test_notebooks.py` checks
them, and `PYGHE_TEST_NOTEBOOKS=1` also runs them afresh.

I write in the first person and in plain sentences. Please do the same, and say what a quantity
is before saying where the application shows it.

## Pull requests

- One change at a time, with a test when it changes behaviour.
- Keep the code comments in English and about *why*, not *what*.
- Do not add a dependency without saying why in the pull request.

By contributing, you agree that your contribution is released under the MIT licence of the
project.
