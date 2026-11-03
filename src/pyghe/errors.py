"""Exceptions and warnings raised by pyghe."""


class PygheError(Exception):
    """Base class of every error raised by the package."""


class InvalidInputError(PygheError, ValueError):
    """A value is missing, of the wrong type or out of range. Nothing was computed."""


class KernelError(PygheError):
    """The computation kernel failed (status 3 of the executable)."""


class CliError(PygheError):
    """The executable could not run the command (status 4)."""


class CliNotFoundError(PygheError):
    """AnalysisSuite-cli was not found, or is too old for this package."""


class LicenseError(PygheError):
    """No licence of the 625-borehole level (Large or Academic) is active on this computer."""


class NotConvergedError(PygheError):
    """Raised instead of ConvergenceWarning when strict=True. The result is in .result."""

    def __init__(self, message, result):
        super().__init__(message)
        self.result = result

    def __reduce__(self):
        return type(self), (str(self), self.result)


class SeriesNotRequested(PygheError, AttributeError):
    """An hourly series read from a simulation that was run without it."""


class KernelWarning(UserWarning):
    """A condition reported by the kernel that did not stop the computation (a value clamped
    to a table, a non-finite output value...)."""


class OutsideInterfaceWarning(KernelWarning):
    """A value the interface's field cannot hold (an active length beyond 500 m, a dip below
    45°...). It is computed as given, but a project holding it is not saved: the application
    would open it showing another value. Silence it for a study that goes beyond the interface
    on purpose: warnings.simplefilter("ignore", pyghe.OutsideInterfaceWarning)."""


class ConvergenceWarning(UserWarning):
    """An iterative computation did not meet its convergence criterion."""
