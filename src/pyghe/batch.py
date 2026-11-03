"""Many cases at once: run_many() and sweep().

One executable process per case, several at a time. The kernel parallelises a single case
poorly (a 25-year simulation of 100 boreholes takes 1.20 s on 1 thread and 1.02 s on 20), so
several processes at once do better. They do not scale with the logical cores, though: each
process holds about 760 MB of arrays sized for 625 boreholes, and memory bandwidth saturates
first. Measured on 10 physical / 20 logical cores, 20 such simulations: 20.2 s one after the
other, 6.2 s with 10 processes of 2 threads, 8.3 s with 20 processes of 1 thread. Hence the
default: one process per physical core (taken as half the logical ones), the threads shared,
and no more processes than the free memory holds.
"""

import ctypes
import itertools
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from ._base import ByMode
from ._cli import batch_servers
from .errors import PygheError, InvalidInputError

# Peak working set of one process running one kind of computation, whatever the field (the
# arrays are sized for 625 boreholes); measured with AnalysisSuite-cli 1.8.
MEMORY_PER_PROCESS = {
    "borehole_resistance": 0.1e9,
    "gfunction": 0.9e9,
    "simulate": 0.9e9,
    "size": 0.9e9,
}
# Share of the free memory a batch may take by default.
MEMORY_SHARE = 0.8

_METHODS = {
    "borehole_resistance": "compute_borehole_resistance",
    "gfunction": "compute_gfunction",
    "simulate": "simulate",
    "size": "size",
}


def _method(command):
    name = _METHODS.get(command, command)
    if name not in _METHODS.values():
        raise ValueError(f"unknown command {command!r}; one of {', '.join(_METHODS)}")
    return name


def available_memory():
    """Physical memory free for new processes, in bytes, or None when it cannot be read."""
    try:
        if sys.platform == "win32":
            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                            ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong),
                            ("pageTotal", ctypes.c_ulonglong), ("pageAvailable", ctypes.c_ulonglong),
                            ("virtualTotal", ctypes.c_ulonglong), ("virtualAvailable", ctypes.c_ulonglong),
                            ("extended", ctypes.c_ulonglong)]
            status = Status()
            status.length = ctypes.sizeof(Status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return float(status.available)
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return float(line.split()[1]) * 1024.0
        # macOS reports no free memory through sysconf: half the installed memory, a guess.
        return 0.5 * os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, AttributeError):
        return None


def _plan(workers, threads, command="simulate"):
    cores = os.cpu_count() or 1
    if workers is None:
        workers = max(1, cores // 2)
        memory = available_memory()
        if memory is not None:
            per_process = MEMORY_PER_PROCESS.get(command, max(MEMORY_PER_PROCESS.values()))
            workers = max(1, min(workers, int(MEMORY_SHARE * memory // per_process)))
    else:
        workers = max(1, int(workers))
    if threads is None:
        threads = max(1, cores // workers)
    return workers, threads


def run_many(projects, command="simulate", workers=None, threads=None, **options):
    """Runs the same computation on each project, in parallel.

    Each worker has its own server, kept for the whole batch and closed with it. Ctrl+C stops
    the whole batch: the computations under way are killed, the others never start.

    Parameters
    ----------
    projects : iterable of Project
        The projects, usually variants of one made with :meth:`Project.copy`.
    command : {'simulate', 'size', 'gfunction', 'borehole_resistance'}
        The computation to run on each project.
    workers : int, optional
        Servers running at once. Default: half the logical cores, fewer when the free memory
        would not hold them at about 0.9 GB each.
    threads : int, optional
        Threads per server. Default: logical cores // workers.
    **options
        Passed to the computation (``series=``, ``strict=``, ``timeout=``...).

    Returns
    -------
    list
        One result per project, in the order of the projects. A case that failed holds its
        exception (a :class:`PygheError`) instead, and does not stop the others.
    """
    projects = list(projects)
    name = _method(command)
    command = next(k for k, v in _METHODS.items() if v == name)
    workers, threads = _plan(workers, threads, command)

    with batch_servers() as servers:
        def one(p):
            with servers.joined():
                try:
                    return getattr(p, name)(threads=threads, **options)
                except PygheError as e:
                    return e

        pool = ThreadPoolExecutor(max_workers=min(workers, max(1, len(projects))))
        try:
            futures = [pool.submit(one, p) for p in projects]
            results = []
            for f in futures:
                # Short waits keep the main thread able to take Ctrl+C.
                while True:
                    try:
                        results.append(f.result(timeout=0.1))
                        break
                    except FutureTimeout:
                        pass
            return results
        except BaseException:
            pool.shutdown(wait=False, cancel_futures=True)
            servers.stop()
            raise
        finally:
            pool.shutdown(wait=True)


def _assign(project, path, value):
    """Sets 'node.field' (or 'node.field.heating' for one mode of a ByMode) on project."""
    *parents, leaf = path.split(".")
    target = project
    for part in parents:
        if not hasattr(target, part):
            raise InvalidInputError(f"{path}: {type(target).__name__} has no attribute {part!r}")
        target = getattr(target, part)
        if target is None:
            raise InvalidInputError(f"{path}: {part} is not set")
    if not hasattr(target, leaf):
        raise InvalidInputError(f"{path}: {type(target).__name__} has no attribute {leaf!r}")
    setattr(target, leaf, value)


def _flatten(prefix, value, row):
    if isinstance(value, ByMode):
        row[f"{prefix}_heating"] = value.heating
        row[f"{prefix}_cooling"] = value.cooling
    else:
        row[prefix] = value


def _outputs(result):
    """The columns a sweep reports for each computation."""
    from .results import BoreholeResistanceResult, GFunctionResult, SimulationResult, SizingResult

    row = {}
    if isinstance(result, SizingResult):
        row["governing_mode"] = result.governing_mode
        row["governing_total_borehole_length"] = result.governing_total_borehole_length
        for name in ("total_borehole_length", "active_length", "mean_fluid_temperature",
                     "effective_borehole_resistance"):
            _flatten(name, getattr(result, name), row)
    elif isinstance(result, SimulationResult):
        s = result.summary
        for name in ("minimum_eft", "maximum_eft", "hours_below_temperature_limit",
                     "hours_above_temperature_limit"):
            row[name] = getattr(s, name)
        row["iterations"] = result.iterations
    elif isinstance(result, BoreholeResistanceResult):
        for name in ("equivalent_borehole_resistance", "effective_borehole_resistance",
                     "borehole_efficiency"):
            _flatten(name, getattr(result, name), row)
    elif isinstance(result, GFunctionResult):
        row["final_dimensionless_gfunction"] = (float(result.dimensionless[-1])
                                                if result.dimensionless.size else math.nan)
    return row


def sweep(project, parameters, command="size", workers=None, threads=None, outputs=None, **options):
    """Parametric study: every combination of the values given, each run on a copy of a project.

    Parameters
    ----------
    project : Project
        The project the variants are made from; it is not changed.
    parameters : dict
        ``{path: values}``, a path being the attribute as written after ``p.``, for example
        ``{"ground_heat_exchanger.ground_thermal_conductivity": [1.5, 2.0, 2.5],
        "gshp_system.flow_rate_of_pump_a.heating": [200, 300]}``.
    command : {'size', 'simulate', 'gfunction', 'borehole_resistance'}
        The computation to run on each combination.
    workers, threads : int, optional
        As in :func:`run_many`.
    outputs : callable, optional
        A function ``result -> dict`` of columns, replacing the default columns of the
        computation.
    **options
        Passed to the computation.

    Returns
    -------
    pandas.DataFrame
        One row per combination, in the order of the product: the parameters, the output
        columns, ``status`` (``'ok'``, ``'notConverged'`` or ``'failed'``), ``error`` and
        ``result`` (the result object). A list of dicts when pandas is not installed.

    Examples
    --------
    >>> table = ga.sweep(p, {"ground_heat_exchanger.ground_thermal_conductivity": [2.0, 2.5, 3.0]})
    >>> table["governing_total_borehole_length"]
    """
    if not isinstance(parameters, dict) or not parameters:
        raise InvalidInputError("sweep: parameters must be a non-empty dict {path: values}")
    paths = list(parameters)
    combinations = list(itertools.product(*(list(parameters[p]) for p in paths)))

    cases, rows = [], []
    for combo in combinations:
        row = dict(zip(paths, combo))
        case = project.copy()
        try:
            for path, value in row.items():
                _assign(case, path, value)
        except PygheError as e:
            case = e
        cases.append(case)
        rows.append(row)

    runnable = [c for c in cases if not isinstance(c, Exception)]
    results = iter(run_many(runnable, command, workers=workers, threads=threads, **options))
    extract = outputs or _outputs
    for row, case in zip(rows, cases):
        result = case if isinstance(case, Exception) else next(results)
        if isinstance(result, Exception):
            row.update(status="failed", error=str(result), result=None)
        else:
            row.update(extract(result))
            row.update(status=result.status, error=None, result=result)

    try:
        import pandas as pd
    except ImportError:
        return rows
    return pd.DataFrame(rows)
