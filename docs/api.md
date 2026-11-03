# API reference

The classes and functions of `pyghe`, taken from their docstrings. [Nodes](nodes.md) lists the
fields of each node with their symbols and units.

## Project

```{eval-rst}
.. currentmodule:: pyghe

.. autoclass:: Project()
   :members: load, save, copy, validate, simulate, size, compute_borehole_resistance,
             compute_gfunction, compute_thermal_plume_2d, compute_thermal_plume_3d,
             to_case, from_case, save_case, source_file

.. autofunction:: fluid_properties
```

## Nodes and values

```{eval-rst}
.. currentmodule:: pyghe

.. autoclass:: ByMode

.. autoclass:: Coordinates
   :members: rectangle, from_points
```

## Many cases

```{eval-rst}
.. currentmodule:: pyghe

.. autofunction:: run_many

.. autofunction:: sweep
```

## Results

```{eval-rst}
.. currentmodule:: pyghe

.. autoclass:: Result
   :members: save

.. autoclass:: SimulationResult
   :members: to_dataframe

.. autoclass:: SizingResult

.. autoclass:: BoreholeResistanceResult

.. autoclass:: GFunctionResult

.. autoclass:: FluidProperties

.. autoclass:: ThermalPlume2DResult

.. autoclass:: ThermalPlume3DResult

.. autofunction:: load_result
```

## Executable and servers

```{eval-rst}
.. currentmodule:: pyghe

.. autofunction:: configure

.. autofunction:: find_cli

.. autofunction:: close_servers
```

## Errors and warnings

```{eval-rst}
.. currentmodule:: pyghe

.. autoexception:: PygheError
.. autoexception:: InvalidInputError
.. autoexception:: LicenseError
.. autoexception:: KernelError
.. autoexception:: CliError
.. autoexception:: CliNotFoundError
.. autoexception:: NotConvergedError
.. autoexception:: SeriesNotRequested
.. autoexception:: KernelWarning
.. autoexception:: OutsideInterfaceWarning
.. autoexception:: ConvergenceWarning
```
