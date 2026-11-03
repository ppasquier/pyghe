# Project files

The package reads and writes `.ghe` files, the project format of GHE Analysis, the application the
kernel comes from. A project can therefore move between a script and the application in either
direction. The script does the repetitive part: the variants, the sweeps, the batches. The
application is where you open the result to look at it, with its charts, thermal plumes, results
summaries and report. A demonstration version can be
[downloaded](https://www.gheanalysis.com/pages/download), and the
[manual](https://www.gheanalysis.com/pages/ghe-analysis-documentation) describes the application.
The package also writes case files, a plainer format meant for sharing a case outside the
application.

## Reading a `.ghe`

```python skip
p = ga.Project.load("site_a.ghe")
```

Any version the application opens will do, whether an Analysis Suite project or a GHE Analysis
2.x file. The file goes through the application's own reader, the code that runs when you press
*Open*, with its defaults for whatever an old file lacks and its repairs of impossible values. The
kernel receives from a script what it would receive from the application once the project is open.

Part of the project is not read: the base map, the energy and project costs, the report texts, the
plume settings, and the TRT and hydraulic-network parts. They are kept when the project is saved
back to the same file (below).

Two kinds of project are refused, and the `InvalidInputError` says which:

- A project whose heat pumps come from the Keymark database. It stores coefficients rather than a
  table, which the package cannot read yet.
- A project saved before the domestic hot water COPs existed, if it has a hot water load. The old
  file stores no value for them. Without a hot water load, the project loads with the COPs of a
  new project (2.75, and free recovery in cooling) and a `KernelWarning`, since with no hot water
  to produce they change nothing.

Files from 2.4 and before store no borehole orientation, so their boreholes are read as vertical.

## Writing a `.ghe`

```python
import tempfile, pathlib
folder = pathlib.Path(tempfile.mkdtemp())

path = p.save(folder / "study_1.ghe")            # returns the path written
print(p.source_file)                              # where this project was last saved
```

The file opens in GHE Analysis. It holds no results, because the application computes its own
when it opens it, which is how you see the study in its charts and report. Besides the inputs, what
it contains depends on where the project came from.

- A project loaded from a file is written over that file's content. Whatever the package does not
  read (the TRT and network parts, the base map, costs, report texts, the application's display
  settings, blocks written by a newer version of the application) stays as it was.
- A project built in Python gets, for everything it does not describe, the values of a new project
  in GHE Analysis.

An existing file is replaced only with `overwrite=True`, except by `save()` without a path, which
writes back to the file the project was loaded from or last saved to:

```python
p.save(folder / "study_1.ghe", overwrite=True)
p.ground_heat_exchanger.active_length = 160
p.save()                                          # study_1.ghe again
```

The package refuses to write a project that the application would open as a different one. The
application repairs some values when it reads a file (a pipe wall thinner than its fields allow,
for example), and a repaired project is no longer the one computed in Python. The package then
raises `InvalidInputError` and names the value. The same applies to a value outside the range of
its field, such as an active length of 800 m when the field stops at 500: the application would
show one value and compute another ([Beyond the interface](errors.md#beyond-the-interface)). Such
a value is written only when the project was loaded from a file that already held it. The heat
pump table is a related case. The application keeps it to two decimals, so if the values have more,
the package warns that it will compute with the rounded ones.

A project read back is equivalent to the one written, though not always identical. The usual
difference is a coordinate table that had no `az` and `dip`: it comes back with an azimuth of 0 and
a dip of 90, which describes the same vertical field.

The file also records who wrote it. For a file written from Python, it holds `pyghe` and its
version, next to the application's versions.

## Case files

A case is the project as the executable reads it, in JSON. It is a JSON file that
can be read without GHE Analysis. A case file
is therefore a good thing to publish with a paper.

```python
p.save_case(folder / "case.json")
same = ga.Project.from_case(folder / "case.json")        # a path, or a dict
case = p.to_case()                                        # the case as a dict
```

Unlike a `.ghe`, a case file keeps `longitude` and `latitude` of the project description. It does
not open in any application.

## A result keeps its case

A result keeps the case that produced it, and saving the result writes both:

```python
result = p.simulate()
result.save(folder / "result.json")                       # case and output together
again = ga.load_result(folder / "result.json")
print(again.case == result.case)
```
