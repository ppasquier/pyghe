"""Python interface to the GHE module of Analysis Suite.

    import pyghe as ga
    p = ga.Project()
    p.ground_heat_exchanger.ground_thermal_conductivity = 2.5
    ...
    result = p.simulate()

Names and units follow the interface of GHE Analysis (SI): each attribute of a Project is a
node of the Analysis Tree. Every number is computed by the application's kernel through
AnalysisSuite-cli.
"""

from ._base import ByMode
from ._case import DEFAULT_SERIES, SERIES
from ._cli import close_servers, configure, find_cli
from .batch import run_many, sweep
from .borehole_resistance import Coaxial, DoubleULoopA, DoubleULoopD, SingleULoop, StandingColumn
from .building_loads import (HourlyBuildingLoadsCombined, HourlyBuildingLoadsSeparate, HourlyGroundLoadsCombined,
                             MonthlyBuildingLoadsSeparate)
from .errors import (CliError, CliNotFoundError, ConvergenceWarning, PygheError, InvalidInputError,
                     KernelError, KernelWarning, LicenseError, NotConvergedError, OutsideInterfaceWarning,
                     SeriesNotRequested)
from .ground_heat_exchanger import Coordinates, GroundHeatExchanger
from .gshp_system import SYSTEM_TYPES, GSHPSystem
from .heat_carrier_fluid import FLUIDS, HeatCarrierFluid
from .heat_pump_performance import HeatPumpPerformance, ManufacturerData, PerformanceConstant, PerformanceTemperature
from .project import PLUME_READINGS, Project, ProjectDescription, SizingTool, fluid_properties
from .results import (BoreholeResistanceResult, FluidProperties, GFunctionResult, Result, SimulationResult,
                      SizingResult, ThermalPlume2DResult, ThermalPlume3DResult, load_result)

__version__ = "0.1.0"

__all__ = [
    "BoreholeResistanceResult", "ByMode", "CliError", "CliNotFoundError", "Coaxial",
    "ConvergenceWarning", "Coordinates", "DEFAULT_SERIES", "DoubleULoopA", "DoubleULoopD",
    "FLUIDS", "FluidProperties", "GFunctionResult", "GSHPSystem", "PygheError",
    "GroundHeatExchanger", "HeatCarrierFluid", "HeatPumpPerformance",
    "HourlyBuildingLoadsCombined", "HourlyBuildingLoadsSeparate", "HourlyGroundLoadsCombined",
    "InvalidInputError", "KernelError", "KernelWarning", "LicenseError", "ManufacturerData",
    "MonthlyBuildingLoadsSeparate", "NotConvergedError", "OutsideInterfaceWarning", "PLUME_READINGS",
    "PerformanceConstant", "PerformanceTemperature", "Project", "ProjectDescription", "Result", "SERIES", "SYSTEM_TYPES",
    "SeriesNotRequested", "SimulationResult", "SingleULoop", "SizingResult", "SizingTool",
    "StandingColumn", "ThermalPlume2DResult", "ThermalPlume3DResult", "close_servers", "configure",
    "find_cli", "fluid_properties", "load_result", "run_many", "sweep",
]
