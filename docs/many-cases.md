# Many cases

Two functions run several projects in parallel and return the answers in the order of the
projects: `run_many` for a list you built, `sweep` for a grid of parameters.

## `run_many`

`run_many` applies the same computation to a list of projects, usually variants of one:

```python
variants = []
for length in (100, 150, 200):
    q = p.copy()
    q.ground_heat_exchanger.active_length = length
    variants.append(q)

results = ga.run_many(variants, "size")             # a list, in the order of the projects
print([round(r.governing_total_borehole_length) for r in results])
```

The second argument says what to compute: `"simulate"` (the default), `"size"`, `"gfunction"` or
`"borehole_resistance"`. Anything else you pass, such as `series=` or `strict=`, goes to the
computation.

If one case fails, the others carry on. In the list, the failed case holds its exception (a
`PygheError`) where a result would be.

## `sweep`

When the variants are every combination of a few parameters, `sweep` builds them for you. You give
each parameter by its path in the project, with the values to try, and you get a pandas table with
one row per case:

```python
table = ga.sweep(
    p,
    {"ground_heat_exchanger.ground_thermal_conductivity": [2.0, 2.5, 3.0],
     "heat_carrier_fluid.antifreeze_mass_concentration": [15, 25]},
    "size")
print(table[["governing_total_borehole_length"]].round(0))
```

The columns depend on the computation. A sizing table has the governing mode and length and,
for each mode, the total and active lengths, the mean fluid temperature and the effective borehole
resistance. A simulation table has `minimum_eft`, `maximum_eft`, the hours beyond the limits and
the number of iterations. All tables end with `status`, `error` and `result`. A row that failed
says why in `error`, and `result` holds the whole result object.

## Threads and servers

The first computation starts a server, `AnalysisSuite-cli serve`, and the package keeps it for the
session. Building the kernel's objects (FFT plans, arrays sized for 625 boreholes) takes about
0.45 s, after which a 25-year g-function takes a few milliseconds. With the server kept alive, a
call drops from half a second to a few tens of milliseconds, and the answers are the same, byte
for byte, as those of a command run in a fresh process.

A server that has run every kind of computation holds about 1.5 GB of memory. These settings
control it:

| | |
|---|---|
| `threads=` | threads used by one call (default: all cores) |
| `workers=` | servers running at once in a batch (default: half the logical cores, about one per physical core, and no more than the free memory holds at about 0.9 GB each) |
| `ga.close_servers()` | stops the server and gives the memory back |
| `ga.configure(server=False)` | a new process for every call: slower, nothing kept |
| `timeout=` | runs that call in its own process, stopped after that many seconds |

Ordinary calls share one server. The thread count is fixed when a server starts, so a call with
another `threads=` replaces it, and changing it often costs a restart each time.

A batch splits the cores among its workers (`cpu_count // workers` threads each) so that a sweep
does not oversubscribe the machine, and it closes its servers at the end.

Ctrl+C (or *Interrupt* in Jupyter) stops a call or a whole batch within a fraction of a second.
The servers at work are killed, the cases not yet started do not start, and the next call starts
a fresh server.

Projects, results and errors go through `pickle`, so `multiprocessing`, `joblib` or a
`ProcessPoolExecutor` can carry them; `run_many` does the same with less memory.

Don't expect the speed-up of a batch to follow the number of workers: memory bandwidth limits it
to about 1.7, and a lone call already uses every core.

Typical times (25 years, 4 boreholes, 20 cores, whole call from Python):

| Call | Time |
|---|---|
| borehole resistance | 0.03 s |
| g-function | 0.04 s |
| simulation, default series | 0.10 s |
| simulation, all twenty series | 0.16 s |
| sizing | 0.15 s |

The thread count changes the last bits of a result, by about 2·10⁻¹² K on the entering fluid
temperature between 1 and 20 threads. It is recorded in `meta`, and with `threads=1` two runs are
identical.
