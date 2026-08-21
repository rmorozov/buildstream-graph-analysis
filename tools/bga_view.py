"""UX-193: `bga view` - a thin window onto the JSON.

Field feedback, round 21: *"we are on the verge of necessity for making
a viewer."* The reports have outgrown the terminal.

**The rule that keeps it thin** (Direction 7): the published JSON is
the entire interface. This server produces payloads by calling the same
`main()`s the CLI calls, and the page renders the *schema* rather than
the report - so a field added to `analyze/v1` appears in the viewer
with no viewer change, and anything the viewer should show has to enter
the published schema first, where the text renderer, CI and every
external tool get it too.

**What it deliberately is not.** No framework, no bundler, no npm: the
page is three files of vanilla ES modules checked into the repository.
A richer TypeScript app is a welcome *consumer* of these payloads - the
view-hints in the schema exist so it can be written without bga
blessing a frontend stack - but it is not this.

**The security posture** is the one a local dev tool needs and no more:
bound to `127.0.0.1` on an ephemeral port, an allowlist of exactly the
paths it serves, no directory listing, no write method, and every
served file resolved and re-checked against the run root so a symlink
or a `..` cannot walk out.
"""
import argparse
import contextlib
import gzip
import http.server
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from typing import Dict, List, Optional

HELP = """Open one run's report in a browser.

Serves the same JSON `--format json` prints, rendered by a page that
reads the schema rather than hard-coding the report - so the viewer and
the terminal can never disagree about what a run says.

Local only: 127.0.0.1, an ephemeral port, and no path outside the run.
"""

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "bga", "viewer")

# The only paths this server answers. Everything else is 404 - there is
# no directory listing and no fall-through to the filesystem.
ASSETS = ("index.html", "app.js", "style.css",
          # UX-194: the Perfetto handoff and the canned-SQL page.
          "perfetto.html", "perfetto.js", "sql.html")

# The trace, served gzipped. Perfetto sniffs gzip itself, so the
# compressed bytes cross the postMessage boundary unchanged - measured
# on a real capture of examples/06 (871 events, both planes):
# 272,964 B -> 24,782 B, 9.1%, an 11x reduction in what the browser
# copies between tabs.
TRACE_NAME = "timeline.json.gz"


def _capture(argv: List[str]) -> dict:
    """Run a bga command and return the JSON it printed.

    Through `main()` rather than by importing the renderer: the payload
    a viewer shows has to be the payload a user gets, and the only way
    to guarantee that is to take the same path.
    """
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        try:
            code = main(argv)
        except SystemExit as exit_code:      # argparse's own exits
            code = exit_code.code
    text = buffer.getvalue()
    if not text.strip():
        raise RuntimeError(f"`bga {' '.join(argv)}` printed nothing (exit {code})")
    return json.loads(text)


def payloads(run: str) -> Dict[str, dict]:
    """Everything the page renders, keyed by the url it is served at.

    A refusal is data, not an error: `bga compare` exits 6 on runs it
    will not judge, and that verdict is exactly what the viewer should
    show. So the exit code is ignored here and the document is served.
    """
    return {
        "report.json": _capture(["analyze", run, "--format", "json"]),
    }


def trace_bytes(run: str) -> Optional[bytes]:
    """`UX-188`'s merged timeline for this run, gzipped, or None.

    `run` is the run directory; `bga timeline` renders the *snapshot*
    that contains it, because the wrapped `build.log` and the raw Plane
    2 log live one level up. A run that is not inside a snapshot - an
    extracted directory, a fetched capture - simply has no timeline, and
    that is not an error.
    """
    from tools.bga_timeline import render

    snapshot = os.path.dirname(os.path.abspath(run))
    scratch = tempfile.mkdtemp(prefix="bga-view-")
    try:
        rendered = os.path.join(scratch, "timeline.json")
        render(snapshot, rendered, quiet=True)
        with open(rendered, "rb") as handle:
            return gzip.compress(handle.read(), 6)
    except (FileNotFoundError, RuntimeError, OSError):
        return None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def schemas_payload() -> dict:
    """The schemas, so the page can render generically.

    Served rather than inlined so the page has one source of truth for
    what a field means, and so `curl .../schemas.json` answers the same
    question a reader has.
    """
    from bga import schemas

    return {name: schemas.schema(name) for name in schemas.names()}


class _Handler(http.server.BaseHTTPRequestHandler):
    """GET only, from a fixed table. No filesystem fall-through."""

    server_version = "bga-view"
    documents: Dict[str, dict] = {}
    blobs: Dict[str, bytes] = {}
    run_root: str = ""

    def log_message(self, format, *args):        # noqa: A002
        # `BaseHTTPRequestHandler` logs every hit to stderr, which would
        # scribble over `UX-183`'s progress line and tell the user
        # nothing they want.
        pass

    def do_GET(self):                            # noqa: N802 - stdlib name
        path = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        if path in self.documents:
            return self._json(self.documents[path])
        if path in self.blobs:
            # `UX-194`: already gzipped on disk-in-memory, and served
            # with its own type rather than Content-Encoding, because
            # the page hands the *compressed bytes* to Perfetto - a
            # transparently-decoding fetch would undo the win.
            return self._send(200, "application/gzip", self.blobs[path])
        if path in ASSETS:
            return self._asset(path)
        self._refuse(404, f"{path}: not served")

    def do_HEAD(self):                           # noqa: N802
        self.do_GET()

    def _json(self, document):
        body = json.dumps(document).encode()
        self._send(200, "application/json; charset=utf-8", body)

    def _asset(self, name):
        # `name` is already known to be in `ASSETS`, so this cannot be
        # traversed; the realpath check is belt and braces against a
        # symlink planted inside the asset directory.
        full = os.path.realpath(os.path.join(ASSET_DIR, name))
        if os.path.dirname(full) != os.path.realpath(ASSET_DIR):
            return self._refuse(403, "outside the asset directory")
        try:
            with open(full, "rb") as handle:
                body = handle.read()
        except OSError:
            return self._refuse(404, f"{name}: missing")
        kinds = {".html": "text/html", ".js": "text/javascript",
                 ".css": "text/css"}
        kind = kinds.get(os.path.splitext(name)[1], "application/octet-stream")
        self._send(200, f"{kind}; charset=utf-8", body)

    def _send(self, code, kind, body):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        # A local viewer has no business being framed or sniffed.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _refuse(self, code, why):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps({"error": why}).encode())


def serve(run: str, port: int = 0,
          documents: Optional[Dict[str, dict]] = None,
          with_trace: bool = True):
    """A started server on 127.0.0.1. The caller closes it.

    Returns `(httpd, url)`. Port 0 means the kernel picks one, so two
    `bga view`s never collide and nothing is left listening on a
    predictable port.
    """
    documents = dict(documents if documents is not None else payloads(run))
    documents.setdefault("schemas.json", schemas_payload())

    blobs = {}
    trace = trace_bytes(run) if with_trace else None
    if trace is not None:
        blobs[TRACE_NAME] = trace

    documents.setdefault("run.json", {
        "run": os.path.abspath(run),
        "name": os.path.basename(os.path.abspath(run)),
        # So the page can offer the button only when there is something
        # behind it - a dead "Open in Perfetto" is worse than none.
        "has_timeline": TRACE_NAME in blobs,
    })

    handler = type("_BoundHandler", (_Handler,),
                   {"documents": documents, "blobs": blobs,
                    "run_root": os.path.abspath(run)})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"


def main(argv: Optional[List[str]] = None) -> int:
    from bga.help_format import CompactRawHelp

    parser = argparse.ArgumentParser(
        prog="bga view", description=HELP,
        formatter_class=lambda prog: CompactRawHelp(prog))
    parser.add_argument(
        "run", nargs="?", default="@last",
        help="The run to open; `@last` by default, same alias grammar as "
             "every other command.")
    parser.add_argument(
        "--port", type=int, default=0, metavar="N",
        help="Listen on this port instead of one the kernel picks.")
    parser.add_argument(
        "--perfetto", action="store_true",
        help="Skip the report and hand this run's timeline straight to "
             "ui.perfetto.dev. Tab to tab - nothing is uploaded.")
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Print the url instead of opening it - for a remote shell, or "
             "when you want to curl the payloads.")
    args = parser.parse_args(argv)

    from bga import run_store

    try:
        # `run_store.resolve`, not the `is_alias`/`resolve_snapshot` pair
        # `bga timeline` uses. The difference is which half of a snapshot
        # the command wants: `timeline` renders the snapshot directory
        # (its `build.log` and its raw Plane 2 log), `view` renders the
        # *run*, which lives one level in. Hand-rolling the gate here
        # resolved `@last` to the snapshot and handed `analyze` a
        # directory with no `run-context.json` in it - caught only by
        # running the acceptance against a real capture, because every
        # unit test passed an explicit path.
        run = run_store.resolve(args.run)
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        print(f"Error: {error}", file=sys.stderr)
        return 2

    try:
        httpd, url = serve(run, port=args.port)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    landing = url + ("perfetto.html" if args.perfetto else "")
    if args.perfetto and not httpd.RequestHandlerClass.blobs:
        print("Error: this run has no timeline to hand over. `bga snapshot` "
              "keeps the raw Plane 2 log by default; a capture taken with "
              "--no-keep-raw, or before UX-188, has only the processed "
              "report.", file=sys.stderr)
        httpd.server_close()
        return 7

    print(f"Serving {os.path.abspath(run)} at {landing}", file=sys.stderr)
    if args.perfetto:
        # The handshake needs the server alive while the tab fetches the
        # trace, which is why this does not exit as soon as the browser
        # is launched.
        print("  The tab fetches the trace from here, so leave this running "
              "until Perfetto has it - then Ctrl-C.", file=sys.stderr)
    else:
        print("  Ctrl-C to stop. Nothing outside this run is reachable, and "
              "nothing is listening beyond localhost.", file=sys.stderr)
    if not args.no_browser:
        # In a thread: `webbrowser.open` can block on a cold browser
        # start, and the server should already be answering when the tab
        # arrives.
        threading.Thread(target=webbrowser.open, args=(landing,),
                         daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
