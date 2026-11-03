# pyghe

pyghe runs the simulation kernel of [GHE Analysis](https://www.gheanalysis.com) from Python:
borehole thermal resistance, g-functions, hourly entering fluid temperatures over several decades,
and the length a borehole field needs. The kernel is incredibly fast, and it is the same code as the
application, so a script and the desktop 
application give the same answer.

I wrote it for advanced studies that are tedious to do by hand: parametric sweeps, uncertainty
analyses, etc. Each variant is one more turn of a loop.

```python skip
import pyghe as ga

p = ga.Project.load("my_project.ghe")      # a .ghe file, or a Project built in Python

for length in range(120, 241, 20):          # active length of each borehole, m
    p.ground_heat_exchanger.active_length = length
    result = p.simulate()
    print(length, result.eft.min())         # minimum entering fluid temperature, °C
```

[Getting started](getting-started.md) builds a project from nothing instead of loading one.

## Where the kernel comes from

The simulation kernel of GHE Analysis is the product of research done at Polytechnique Montréal
since 2008, with my colleague Denis Marcotte and several of my students: spectral convolution of
the loads (Marcotte & Pasquier, 2008; Pasquier et al., 2013), the quasi-3D borehole response
(Pasquier & Marcotte, 2014), successive flux estimation for the g-function (Pasquier & Marcotte,
2013; Nguyen & Pasquier, 2021) and the standing column well (Nguyen et al., 2025). The section
[Methods](methods.md) shows which paper each computation uses.

## How it works

pyghe has no physics in it. It writes your project as a JSON case, passes it to
`AnalysisSuite-cli` (the application's kernel without the interface) and gives the result back as
Python objects and numpy arrays. I chose this over a Python port so there is only one
implementation to check: the application's verification scenarios test the code your scripts run.

Run from Python, a case gives the same numbers as the executable, bit for bit. Note, however, that
the application can differ slightly, within the convergence criterion, because it starts each
simulation from its previous solution ([Reproducibility](reproducibility.md)).

The names follow those of GHE Analysis and the units are SI. For example, the burial depth of the
ground heat exchanger is `p.ground_heat_exchanger.burial_depth`, in metres. Every quantity is
defined in [Nodes](nodes.md) and [Nomenclature](nomenclature.md), and in more detail in the
[manual](https://www.gheanalysis.com/pages/ghe-analysis-documentation). Whoever opens the same
project in the application later finds the same names there.

## The application

GHE Analysis is the desktop application built on the same kernel. It draws the borehole field and
its thermal plume, plots the results and writes reports, and it also covers thermal response tests
(TRT) and hydraulic networks. A project saved from a script opens in it, so a calculation prepared
in Python can be inspected, plotted and presented there ([Project files](project-files.md)). A
demonstration version can be
[downloaded](https://www.gheanalysis.com/pages/download).

## Scope and requirements

pyghe covers the GHE module only. TRT, hydraulic networks and costs stay in the application, but
a `.ghe` file you load and save from Python keeps them intact. There is no plotting: results are
numpy arrays, and the [examples](examples/index.md) show how to plot them.

You need Python 3.10 or later, numpy, and either a free Academic licence or a Large/Enterprise
commercial licence of Analysis Suite, activated on the computer. pandas is optional. The licence
options are on the [pricing page](https://www.gheanalysis.com/pages/pricing).

## Contact

Bug reports and suggestions are welcome through [www.gheanalysis.com](https://www.gheanalysis.com).
Many improvements to the application came from the engineers and students who use it, and I would
like the same for this package.

```{toctree}
:maxdepth: 1
:hidden:

install
getting-started
project
nodes
computations
many-cases
recipes
examples/index
project-files
errors
reproducibility
methods
nomenclature
api
citing
changelog
```
