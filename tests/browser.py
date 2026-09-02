"""UX-257: a real browser, when there is one, and silence that says so.

Every geometric claim this repository makes about the viewer — "the
contents take 573px", "nothing overlaps", "the section is 2.5 screens"
— was measured by hand and then held by nothing. The shim the guards
run on has no layout engine (`tests/dom_shim.mjs` says so at the
bottom), so those claims could not be guarded there at any price.

**The decision.** A real browser, driven over the DevTools protocol,
with **no new dependency**: `node` is already required by every viewer
guard, and node 22's built-in `WebSocket` and `fetch` are the whole
client. Playwright was the obvious alternative and is declined — it
adds a package and a browser download to a repository whose test
dependencies are `pytest` and `jsonschema`, to drive a browser this
does in forty lines.

The cost is that a Chrome binary must exist. Where it does not, these
guards **skip**, and the skip is declared in `tests/conftest.py`'s
census — which is the mechanism that makes a skip loud rather than
comfortable (`UX-235`). A guard that runs nowhere and a guard that
runs somewhere and says where are different things.
"""
import atexit
import json
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import time

# In the order a machine is likely to have one. `BGA_CHROME` wins, so a
# runner with a browser in an unusual place can say where.
CANDIDATES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
)

NO_BROWSER = "no chrome/chromium for the geometry guards (set BGA_CHROME)"

#: `UX-523`: `{binary: Browser}` - the one this process launched, kept
#: alive across every `with Browser(...)` in the worker and closed at
#: exit. Per process, so xdist's workers do not share a debugging port.
_SHARED = {}


@atexit.register
def _close_shared():
    for opened in list(_SHARED.values()):
        opened._stop()
        shutil.rmtree(opened.profile, ignore_errors=True)
    _SHARED.clear()


def find_chrome():
    """A usable browser binary, or `None`."""
    named = os.environ.get("BGA_CHROME")
    if named and os.path.exists(named):
        return named
    for candidate in CANDIDATES:
        found = shutil.which(candidate) or (
            candidate if os.path.exists(candidate) else None)
        if found:
            return found
    return None


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Browser:
    """A headless Chrome and one page, spoken to over CDP.

    Deliberately tiny: open, navigate, evaluate, close. Anything that
    needs more than this is a sign the guard is trying to be a browser
    test suite rather than a geometry check.
    """

    def __init__(self, binary):
        self.binary = binary
        self.port = _free_port()
        self.profile = tempfile.mkdtemp(prefix="bga-geometry-")
        self.process = None
        #: `UX-523`: true once this instance is the worker's shared
        #: browser, which is what stops `__exit__` closing it.
        self._shared = False
        #: Held apart from `self.process` so it survives `_stop` and can
        #: be drained after the writer is gone (see `_why_it_failed`).
        self._stderr = None

    #: How long one launch may take to answer on its port, and how many
    #: launches are tried. `UX-456`: measured on CI, where the same
    #: suite passes in `test (3.x)` in 5m33s and takes ~10 minutes in
    #: `bst-tests` because that job runs the `bst` tier first - and
    #: where 18 setup errors, all this one, landed on one xdist worker
    #: in two of ten runs. Both figures are here rather than inline so
    #: the message below can name what it waited for.
    START_TIMEOUT_S = 30
    START_ATTEMPTS = 2

    def _launch(self):
        """One attempt, on a **freshly chosen** port. True if it answers.

        The port is re-rolled per attempt on purpose. `_free_port`
        binds a socket, reads the number and closes it, so between that
        close and Chrome's own bind the port is anyone's - and under
        `-n auto` the other things racing for it are this suite's own
        workers. A retry on the same port would re-run the collision;
        a retry on a new one does not.
        """
        self.port = _free_port()
        self.process = subprocess.Popen(
            [self.binary, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._stderr = self.process.stderr
        deadline = time.time() + self.START_TIMEOUT_S
        while time.time() < deadline:
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{self.port}/json/version",
                        timeout=1):
                    return True
            except Exception:                            # noqa: BLE001
                # A Chrome that has already exited will never answer, so
                # there is nothing to wait out - and *that it exited* is
                # the fact that distinguishes a taken port from a slow
                # runner. Both used to arrive as the same sentence.
                if self.process.poll() is not None:
                    return False
                time.sleep(0.2)
        return False

    def __enter__(self):
        # `UX-523`: one browser per worker per session. Thirty-eight
        # guard files each opened their own, and a page is loaded
        # through `Page.navigate` on a target this process owns alone -
        # pytest runs one test at a time inside a worker, so there is
        # never a second load in flight to isolate from. Measured at
        # 0.33s a launch; what it really buys is that the port race
        # `UX-456` retries for is run once instead of thirty-eight
        # times.
        shared = _SHARED.get(self.binary)
        if (shared is not None and shared.process is not None
                and shared.process.poll() is None):
            self.port = shared.port
            self._shared = True
            return self
        last = None
        for attempt in range(1, self.START_ATTEMPTS + 1):
            if self._launch():
                _SHARED[self.binary] = self
                self._shared = True
                return self
            # Order matters, and the falsification is why it is written
            # down: `_why_it_failed` reads the process's stderr, and a
            # read on a pipe whose writer is still alive blocks until
            # EOF. Asking before stopping hung the whole suite on the
            # one case this retry exists for - a browser that runs and
            # never listens. The code is taken first, the process is
            # stopped, and only then is the pipe drained.
            code = (self.process.poll() if self.process is not None
                    else None)
            self._stop()
            last = self._why_it_failed(attempt, code)
        raise RuntimeError(
            f"{self.binary} did not open a debugging port in "
            f"{self.START_ATTEMPTS} attempts of {self.START_TIMEOUT_S}s. "
            f"Last: {last}")

    def _why_it_failed(self, attempt, code):
        """One line saying which of the two it was, for the message.

        `UX-456`: the old error named the binary and nothing else, so
        eighteen identical copies of it said no more than one. A reader
        needs to know whether the process died - which is a port or a
        sandbox problem - or was still running, which is the runner.

        `code` is read by the caller **before** the process is stopped,
        because after `_stop` every exit code is the signal we sent.
        The stderr is drained here, after, when the pipe is at EOF.
        """
        said = b""
        if self._stderr is not None:
            try:
                said = self._stderr.read() or b""
            except Exception:                            # noqa: BLE001
                said = b""
            finally:
                self._stderr.close()
                self._stderr = None
        tail = said.decode("utf-8", "replace").strip().splitlines()[-1:]
        return (f"attempt {attempt} on port {self.port} "
                + (f"exited {code}" if code is not None
                   else f"was still running after {self.START_TIMEOUT_S}s")
                + (f": {tail[0]}" if tail else ""))

    def _stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:            # pragma: no cover
                self.process.kill()
            self.process = None

    def __exit__(self, *_):
        # A shared browser outlives its `with`; `_close_shared` at exit
        # is what ends it. A `Browser` that never became the shared one
        # (a guard that wants its own) still closes here.
        if not self._shared:
            self._stop()
            shutil.rmtree(self.profile, ignore_errors=True)

    def _drive(self, url, expression, width, height, extra=()):
        driver = pathlib.Path(__file__).resolve().parent / "cdp.mjs"
        node = shutil.which("node")
        if node is None:                                 # pragma: no cover
            raise RuntimeError("node is required to speak CDP")
        done = subprocess.run(
            [node, str(driver), str(self.port), url, str(width), str(height),
             *extra],
            input=expression, capture_output=True, text=True, timeout=120)
        if done.returncode != 0:                         # pragma: no cover
            raise RuntimeError(done.stderr)
        return json.loads(done.stdout)

    def measure(self, url, expression, width=1440, height=900):
        """Load `url` at `width`x`height` and return `expression`'s value.

        The evaluation happens in node rather than here because the CDP
        client is a WebSocket and Python's standard library has none.
        """
        return self._drive(url, expression, width, height)

    def observe(self, url, expression="null", width=1440, height=900):
        """The same load, plus everything the console and the CSP said.

        `UX-334`: `{"value", "console", "csp"}`. `console` is one entry
        per `console.*` call, uncaught exception and browser log line -
        which is where a 404 on a subresource appears, and nowhere the
        page itself can see. `csp` is one entry per
        `securitypolicyviolation` event, carrying the directive that
        refused it: a page can violate its own policy silently as far
        as `console.error` is concerned, so the two channels are
        collected separately and neither substitutes for the other.
        """
        return self._drive(url, expression, width, height, ("--observe",))
