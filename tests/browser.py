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

    def __enter__(self):
        self.process = subprocess.Popen(
            [self.binary, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", f"--remote-debugging-port={self.port}",
             f"--user-data-dir={self.profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                import urllib.request
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{self.port}/json/version",
                        timeout=1):
                    return self
            except Exception:                            # noqa: BLE001
                time.sleep(0.2)
        self.__exit__(None, None, None)
        raise RuntimeError(f"{self.binary} did not open a debugging port")

    def __exit__(self, *_):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:            # pragma: no cover
                self.process.kill()
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
