"""Locating and running AnalysisSuite-cli; statuses become exceptions and warnings.

Computations go to a server, `AnalysisSuite-cli serve`, which keeps the kernel's objects from
one command to the next: building them (FFT plans, arrays sized for 625 boreholes) takes about
0.45 s, more than most computations. A server answers exactly as a fresh process would (the
executable resets each object's state before each command; checked byte for byte). One server
serves the ordinary calls, replaced when the thread count changes, and lives until the end of
the session or close_servers(); a batch (run_many, sweep) has its own servers, closed with it.
"""

import atexit
import itertools
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import warnings
from pathlib import Path

import numpy as np

from .errors import (CliError, CliNotFoundError, InvalidInputError, KernelError, KernelWarning, LicenseError,
                     OutsideInterfaceWarning)

EXECUTABLE = "AnalysisSuite-cli"
ENV_VARIABLE = "PYGHE_CLI"
# 1.9: licence check (1.1), cases in the interface units (1.2), series in a binary file (1.3),
# server mode (1.4), thermal plumes (1.5), reading project files (1.6), writing them (1.7), pump B
# flow rate (1.8), the interface's ranges and impossible geometries (1.9).
MINIMUM_INTERFACE = (1, 9)
ANSWER_PREFIX = "@AS "
OUTSIDE_INTERFACE = ", outside what the interface accepts"
_PACKAGE = os.path.dirname(os.path.abspath(__file__))


def warn(message, category):
    """Warns at the first frame outside the package: the user's line, whatever the path the
    call took inside it."""
    frame, level = sys._getframe(1), 2
    while frame is not None and os.path.dirname(os.path.abspath(frame.f_code.co_filename)) == _PACKAGE:
        frame, level = frame.f_back, level + 1
    warnings.warn(message, category, stacklevel=level)

_configured = None
_use_server = True
_checked = {}

# Hours without building load have no COP by definition (interface-spec §5.4): expected NaN,
# not a condition worth a warning.
_EXPECTED = re.compile(r"^hourly\.(cop|effectiveCop|effectiveCapacity): \d+ non-finite")


def configure(cli=None, server=None):
    """Sets the path of AnalysisSuite-cli, overriding the environment variable PYGHE_CLI
    and the PATH; configure(None) returns to the automatic search. server=False runs every
    computation in a new process instead of a server (slower by about 0.45 s per call)."""
    global _configured, _use_server
    _configured = None if cli is None else str(cli)
    if server is not None:
        _use_server = bool(server)
        if not _use_server:
            close_servers()


def _default_locations():
    """Folders where the executable is likely to be, most likely first: the folder the separate
    download of the executable is meant to be unpacked into, the folder the Windows installer
    proposes in the user's home, the macOS application bundle."""
    name = EXECUTABLE + (".exe" if sys.platform == "win32" else "")
    found = [Path.home() / "AnalysisSuite-cli" / name]
    if sys.platform == "win32":
        found.append(Path.home() / "AnalysisSuite" / name)
        for variable in ("ProgramFiles", "ProgramW6432", "LOCALAPPDATA"):
            if os.environ.get(variable):
                found.append(Path(os.environ[variable]) / "Analysis Suite" / name)
    elif sys.platform == "darwin":
        for root in (Path("/Applications"), Path.home() / "Applications"):
            if root.is_dir():
                for bundle in sorted(root.glob("*Analysis*Suite*.app")):
                    found.append(bundle / "Contents" / "MacOS" / name)
    return found


def find_cli():
    """Path of the executable: configure(), then PYGHE_CLI, then the PATH, then the folders
    where the Analysis Suite installer puts it."""
    candidates = []
    if _configured:
        candidates.append(("configure()", _configured))
    if os.environ.get(ENV_VARIABLE):
        candidates.append((ENV_VARIABLE, os.environ[ENV_VARIABLE]))
    for origin, path in candidates:
        if Path(path).is_file():
            return str(path)
        raise CliNotFoundError(f"{origin} names {path}, which does not exist")
    found = shutil.which(EXECUTABLE)
    if found:
        return found
    for path in _default_locations():
        if path.is_file():
            return str(path)
    raise CliNotFoundError(
        f"{EXECUTABLE} was not found. It comes with the Analysis Suite desktop application, which "
        f"you can download at https://www.gheanalysis.com/pages/download; pyghe looks for it in the "
        f"folder where the installer puts it. If you installed it elsewhere, give its path with "
        f"pyghe.configure(cli=...) or the environment variable {ENV_VARIABLE}.")


def _interface_of(cli):
    if cli not in _checked:
        try:
            out = subprocess.run([cli, "version", "--compact"], capture_output=True, timeout=60)
            meta = json.loads(out.stdout)["meta"]
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
            raise CliNotFoundError(f"{cli} does not answer as {EXECUTABLE}: {e}") from None
        major, minor = (int(v) for v in meta["interfaceVersion"].split(".")[:2])
        if major != MINIMUM_INTERFACE[0] or minor < MINIMUM_INTERFACE[1]:
            raise CliNotFoundError(
                f"{cli} has interface {meta['interfaceVersion']}; this package needs "
                f"{MINIMUM_INTERFACE[0]}.{MINIMUM_INTERFACE[1]} or a later 1.x. Update Analysis Suite.")
        _checked[cli] = meta
    return _checked[cli]


def _environment(threads):
    env = dict(os.environ)
    if threads is not None:
        env["OMP_NUM_THREADS"] = str(int(threads))
    return env


class _ServerStopped(Exception):
    pass


class _Server:
    """One `AnalysisSuite-cli serve` process. Not thread-safe: one caller at a time.

    The answers are read by a thread of their own, so that the caller waits in short steps: a
    blocking read of the pipe would hold off Ctrl+C until the kernel finishes, minutes for some
    computations. A call left without its answer (interrupted) kills the server, which cannot be
    stopped otherwise; an answer that is not the one awaited is dropped."""

    _ids = itertools.count()

    def __init__(self, cli, threads):
        self.cli, self.threads = cli, threads
        self.process = subprocess.Popen([cli, "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, env=_environment(threads),
                                        text=True, encoding="utf-8", bufsize=1)
        self.answers = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            for line in self.process.stdout:
                if line.startswith(ANSWER_PREFIX):
                    try:
                        self.answers.put(json.loads(line[len(ANSWER_PREFIX):]))
                    except ValueError:
                        pass
        except (OSError, ValueError):
            pass
        self.answers.put(None)

    def alive(self):
        return self.process.poll() is None

    def call(self, command, inp, out, binary):
        request_id = next(self._ids)
        request = {"id": request_id, "command": command, "in": str(inp), "out": str(out),
                   "binary": str(binary)}
        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            while True:
                try:
                    answer = self.answers.get(timeout=0.1)
                except queue.Empty:
                    continue
                if answer is None:
                    raise _ServerStopped()
                if answer.get("id") == request_id:
                    return answer
        except (OSError, ValueError):
            self.kill()
            raise _ServerStopped() from None
        except BaseException:
            self.kill()
            raise

    def close(self):
        if self.alive():
            try:
                self.process.stdin.close()
                self.process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                self.kill()

    def kill(self):
        if self.alive():
            self.process.kill()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass


_servers = {}                       # cli -> _Server, for ordinary calls
_servers_lock = threading.Lock()
_current_batch = threading.local()  # .context: the batch_servers of a batch worker thread


def close_servers():
    """Stops the servers kept for ordinary calls, freeing their memory (about 1.5 GB each once
    they have run a simulation, a g-function and a sizing)."""
    with _servers_lock:
        for server in _servers.values():
            server.close()
        _servers.clear()


atexit.register(close_servers)


class batch_servers:
    """The servers of a batch: one per worker thread, all closed when the batch ends. A worker
    thread joins the batch with `with batch.joined():`."""

    def __init__(self):
        self._by_thread = {}
        self._lock = threading.Lock()
        self._stopped = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        with self._lock:
            for server in self._by_thread.values():
                server.close()
            self._by_thread.clear()

    def stop(self):
        """Kills the batch's servers, ending the computations under way, and refuses new ones."""
        with self._lock:
            self._stopped = True
            servers = list(self._by_thread.values())
        for server in servers:
            server.kill()

    def joined(self):
        batch = self

        class _Joined:
            def __enter__(self):
                _current_batch.context = batch

            def __exit__(self, *exc):
                _current_batch.context = None

        return _Joined()

    def server(self, cli, threads):
        key = threading.get_ident()
        with self._lock:
            if self._stopped:
                raise _ServerStopped()
            server = self._by_thread.get(key)
        if server is None or not server.alive() or (server.cli, server.threads) != (cli, threads):
            if server is not None:
                server.close()
            server = _Server(cli, threads)
            with self._lock:
                self._by_thread[key] = server
        return server

    def drop(self):
        with self._lock:
            server = self._by_thread.pop(threading.get_ident(), None)
        if server is not None:
            server.close()


def _run_on_server(cli, threads, command, inp, out, binary):
    batch = getattr(_current_batch, "context", None)
    if batch is not None:
        try:
            return batch.server(cli, threads).call(command, inp, out, binary)["status"]
        except _ServerStopped:
            batch.drop()
            raise
    with _servers_lock:
        # One server only: each holds about 1.5 GB, and the thread count is fixed at its start.
        server = _servers.get(cli)
        if server is not None and server.threads != threads:
            server.close()
        if server is None or not server.alive() or server.threads != threads:
            server = _servers[cli] = _Server(cli, threads)
        try:
            return server.call(command, inp, out, binary)["status"]
        except BaseException:
            if _servers.get(cli) is server and not server.alive():
                del _servers[cli]
            raise


def run(command, case, threads=None, timeout=None, keep_files=False):
    """Runs one command on one case and returns the executable's output document (status 0
    or 1). Raises for statuses 2 to 5. With a timeout the command runs in its own process,
    which can be stopped."""
    from ._case import translate_error

    cli = find_cli()
    _interface_of(cli)
    folder = Path(tempfile.mkdtemp(prefix="pyghe-"))
    inp, out, binary = folder / "case.json", folder / "result.json", folder / "series.f64"
    inp.write_text(json.dumps(case), encoding="utf-8")

    stderr = ""
    try:
        if _use_server and timeout is None:
            try:
                _run_on_server(cli, threads, command, inp, out, binary)
            except _ServerStopped:
                raise KernelError(f"{command}: the executable stopped during the computation") from None
        else:
            try:
                proc = subprocess.run([cli, *command.split(), "--in", str(inp), "--out", str(out),
                                       "--binary", str(binary), "--compact"],
                                      capture_output=True, env=_environment(threads), timeout=timeout)
            except subprocess.TimeoutExpired:
                raise KernelError(f"{command}: no result after {timeout} s") from None
            stderr = f" (exit code {proc.returncode}) {proc.stderr.decode(errors='replace').strip()}"

        try:
            doc = json.loads(out.read_text(encoding="utf-8"))
            if "binary" in doc and "result" in doc:
                values = np.fromfile(binary, dtype="<f8")
                values.setflags(write=False)
                doc["result"] = _attach(doc["result"], values)
        except (OSError, ValueError):
            raise KernelError(f"{command}: the executable stopped without a result{stderr}") from None
    finally:
        if not keep_files:
            shutil.rmtree(folder, ignore_errors=True)

    status, error = doc.get("status"), doc.get("error", "")
    if status == 2:
        raise InvalidInputError(translate_error(error))
    if status == 3:
        raise KernelError(error)
    if status == 4:
        raise CliError(error)
    if status == 5:
        raise LicenseError(error)
    if status not in (0, 1):
        raise CliError(f"unexpected status {status}: {error}")

    for w in doc.get("warnings", []):
        if not _EXPECTED.match(w):
            category = OutsideInterfaceWarning if w.endswith(OUTSIDE_INTERFACE) else KernelWarning
            warn(translate_error(w), category)
    doc["threads"] = threads
    if keep_files:
        doc["files"] = {"case": str(inp), "result": str(out), "series": str(binary)}
    return doc


def _attach(node, values):
    """Replaces each {"binary": {"offset", "count"}} of the output by its slice of values."""
    if isinstance(node, dict):
        at = node.get("binary")
        if len(node) == 1 and isinstance(at, dict) and set(at) == {"offset", "count"}:
            start = int(at["offset"])
            return values[start:start + int(at["count"])]
        return {k: _attach(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_attach(v, values) for v in node]
    return node


def plain(node):
    """The output as the executable writes it in JSON: arrays as lists, non-finite as None."""
    if isinstance(node, np.ndarray):
        return [float(v) if np.isfinite(v) else None for v in node]
    if isinstance(node, dict):
        return {k: plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [plain(v) for v in node]
    return node
