# Errors and warnings

A scripted study can run for an hour with nobody watching. So whatever makes a result doubtful
comes out as a Python exception or a warning, and not only as a field of the result.

## Exceptions

The exceptions of the package all derive from `ga.PygheError`, so a single `except` clause
catches them. Each situation also has its own class.

| Exception | When |
|---|---|
| `InvalidInputError` | a value is missing, of the wrong type or out of range. Nothing was computed. The message names the attribute |
| `LicenseError` | no Large or Academic licence is active on this computer |
| `KernelError` | the computation itself failed |
| `CliError` | the executable could not run the command (file not found, cannot write…) |
| `CliNotFoundError` | the executable was not found, or is older than this package needs |
| `NotConvergedError` | an iterative computation did not converge, and you asked for `strict=True` |
| `SeriesNotRequested` | you read an hourly series from a simulation that was run without it |

You will meet `InvalidInputError` most often. Its message uses the names of the project:

```python
try:
    ga.Project().simulate()
except ga.InvalidInputError as error:
    print(error)
```

```text
the project is incomplete:
  p.borehole_resistance is not set
  p.ground_heat_exchanger.active_length is not set
  ...
```

The message lists everything that is missing, so one run is enough to see what remains to fill.

## Warnings

A condition that does not stop the computation is reported as an ordinary Python warning.

| Warning | When |
|---|---|
| `KernelWarning` | the kernel reports something that did not stop it: a value clamped, a table row ignored, antifreeze given to water |
| `OutsideInterfaceWarning` | a value the interface's field cannot hold: an active length beyond 500 m, a dip below 45°, a pipe wall thinner than 2 mm… It is computed as given (a subclass of `KernelWarning`) |
| `ConvergenceWarning` | an iterative computation did not meet its criterion |

A warning points at the line of your script that made the call and names the attribute as you
wrote it:

```text
study.py:12: OutsideInterfaceWarning: p.ground_heat_exchanger.active_length: 800 m lies outside [50, 500] m, outside what the interface accepts
```

## Beyond the interface

The package takes its limits from the application, which bounds its input fields: an active length from 50
to 500 m, a ground conductivity from 0.5 to 6 W/(m·K), temperature limits from −10 to 45 °C, flow
rates from 10 to 9999 L/min, a dip from 45 to 90°, and so on. A research study may need to go
beyond these, so the package computes such a value and issues an `OutsideInterfaceWarning`.

Saving is another matter. A project file holding 800 m would open in the application with the
field showing 500 m while the kernel computes 800 m. `Project.save()` therefore refuses it
(`InvalidInputError`), unless the project was loaded from a file that already held that value.

If a study goes beyond these bounds on purpose, the warning can be silenced:

```python
import warnings
warnings.simplefilter("ignore", ga.OutsideInterfaceWarning)
```

```python
warnings.simplefilter("default")
```

Some inputs describe no borehole field at all. These are refused whatever the command
(`InvalidInputError`): a heating temperature limit not below the cooling one, a negative value in
a heat pump table, pipes standing outside the borehole or overlapping, two boreholes closer than
their diameter.

The warnings are standard ones and obey `warnings.filterwarnings`. If a study has to run clean,
some of them can be turned into errors:

```python
import warnings
warnings.simplefilter("error", ga.ConvergenceWarning)
```

```python
warnings.simplefilter("default")
```

## When a simulation does not converge

The simulation iterates between the heat pumps and the ground until the entering fluid
temperature changes by less than 10⁻³ K and the ground load by less than 0.1 kW from one
iteration to the next. When it does not converge, the result is returned anyway, because a partial
answer helps to find out why:

```python skip
result = p.simulate()
result.converged        # False
result.status           # 'notConverged'
```

A `ConvergenceWarning` is issued too. For a long unattended study, `strict=True` is the better
choice: the call then raises `NotConvergedError`, with the partial result attached to it:

```python skip
try:
    p.simulate(strict=True)
except ga.NotConvergedError as error:
    partial = error.result
```

The Sizing tool has no convergence flag. All the package can do is check that the lengths it
returns are finite.

## The licence

`LicenseError` carries the executable's own message ([Installation](install.md#the-licence)).
