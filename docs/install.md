# Installation

## Requirements

- Python 3.10 or later
- numpy 1.24 or later
- pandas 2 or later, optional: `to_dataframe()` and the tables returned by `sweep`
- matplotlib 3.8 or later, optional: the examples
- Analysis Suite, which provides the executable ([download](https://www.gheanalysis.com/pages/download)),
  with a Large or Academic licence activated on the computer

## Installing the package

pyghe is on the Python Package Index. In a terminal, preferably inside a virtual environment:

```console
pip install pyghe
```

numpy is installed with it. The optional tables (`to_dataframe()`, `sweep`) need pandas, and the
example notebooks need matplotlib and Jupyter; ask for them with an extra:

```console
pip install "pyghe[pandas]"
pip install "pyghe[notebooks]"
```

Installing the package is only half of the job: pyghe does not contain the computations, which are
done by an executable that comes from Analysis Suite (next section).

To work on the package itself, install it from a clone of the
[repository](https://github.com/ppasquier/pyghe):

```console
git clone https://github.com/ppasquier/pyghe
cd pyghe
pip install -e ".[test,docs]"
```

## Finding the executable

`AnalysisSuite-cli` does the computations. It is the kernel of the application without its
interface, and it is downloaded separately from Analysis Suite, from the
[download page](https://www.gheanalysis.com/pages/download), as a zip file. The order matters:

1. Install Analysis Suite and activate your licence in it. The executable reads that licence.
2. Unpack the zip into a folder named `AnalysisSuite-cli` in your home folder.

pyghe looks for the executable in `ga.configure(cli=...)`, then in the environment variable
`PYGHE_CLI`, then on the `PATH`, and finally in that folder of your home, then in the folder of
the application itself (`AnalysisSuite` in your home folder or `Analysis Suite` in `Program Files`
on Windows, the application bundle on macOS). If you unpacked the zip there, nothing needs to be
configured.

If none of these leads to it, you get a `CliNotFoundError`. When the executable is somewhere else,
give its path:

```console
set PYGHE_CLI=C:\path\to\AnalysisSuite-cli.exe
```

## Checking the installation

The properties of a fluid need no project and take a fraction of a second, which makes them a
convenient test:

```python
import pyghe as ga

water = ga.HeatCarrierFluid("Water", antifreeze_mass_concentration=0)
print(ga.fluid_properties(water, [10]).density)       # about 999 kg/m³
```

If a density is printed, the package, the executable and the licence are all in place. A
`LicenseError` means no suitable licence is activated on this computer.

## The licence

The executable checks the licence, not Python, so a script follows the same rule as the
application. The licence date is checked online at most once a day, and pyghe keeps working for
seven days without a connection.
