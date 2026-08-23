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
import base64
import contextlib
import gzip
import http.server
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.parse
import webbrowser
from typing import Dict, List, Optional

HELP = """Open one run's report in a browser.

Serves the same JSON `--format json` prints, rendered by a page that
reads the schema rather than hard-coding the report - so the viewer and
the terminal can never disagree about what a run says.

Local only: 127.0.0.1, an ephemeral port, and no path outside the run.
"""

def _asset_dir() -> str:
    """Where the page's files are, from a checkout *and* from a wheel.

    `UX-193` computed this as "two directories up, then `bga/viewer`",
    which is right from a checkout and wrong once installed: `UX-94`
    packages this directory as `bga._tools`, so two up is
    `site-packages`, and the answer became `site-packages/bga/bga/
    viewer`. Asking the `bga` package where it lives is correct in both
    shapes and needs no branch.
    """
    import bga

    return os.path.join(os.path.dirname(os.path.abspath(bga.__file__)), "viewer")


ASSET_DIR = _asset_dir()

# The only paths this server answers. Everything else is 404 - there is
# no directory listing and no fall-through to the filesystem.
ASSETS = ("index.html", "app.js", "style.css", "views.js", "focus.js",
          # UX-194: the Perfetto handoff and the canned-SQL page.
          "perfetto.html", "perfetto.js", "sql.html",
          # UX-199: navigation, and the questions as data so the export
          # can inline what it used to strip.
          "nav.js", "questions.js",
          # UX-204: the link-builder the investigate buttons read, and
          # `sql.html` now renders its list from `questions.js` rather
          # than carrying a copy - so the page needs it served too.
          "trace_context.js",
          # UX-205: the filters, thresholds and copy helpers.
          "tables.js",
          # UX-211: the view state that travels in the fragment.
          "viewstate.js")

# The trace, served gzipped. Perfetto sniffs gzip itself, so the
# compressed bytes cross the postMessage boundary unchanged - measured
# on a real capture of examples/06 (871 events, both planes):
# 272,964 B -> 24,782 B, 9.1%, an 11x reduction in what the browser
# copies between tabs.
TRACE_NAME = "timeline.json.gz"

# `UX-198`: the only origin this server will hand a trace to
# cross-origin, and the target of the `?url=` deep link. Kept in step
# with `bga/viewer/perfetto.js`'s own constant by a guard.
PERFETTO_ORIGIN = "https://ui.perfetto.dev"


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


def history(run: str) -> List[str]:
    """Every run in `run`'s own store that precedes it, oldest first.

    `UX-203`: the band needs a *set*, not a pair.
    `compare.MIN_BASELINE_RUNS` is 3, and a pairwise comparison has no
    `baseline_band` at all - so serving one comparison would have left
    `renderBand` returning null exactly as before, for a subtler
    reason. The store is where the set comes from: it is the history
    the user already captured.
    """
    from bga import run_store

    snapshot = os.path.dirname(os.path.abspath(run.rstrip("/")))
    project = run_store.project_root(snapshot)
    if project is None:
        return []
    try:
        runs = [os.path.abspath(r) for r in run_store.list_runs(project)]
    except OSError:
        return []
    try:
        index = runs.index(snapshot)
    except ValueError:
        return []
    return [os.path.join(r, run_store.RUN_SUBDIR) for r in runs[:index]]


def predecessor(run: str) -> Optional[str]:
    """The run one snapshot before `run` in its own store, or None.

    `UX-203`: this is what makes the band view reachable. `bga view`
    served exactly one payload - the analyze document - while
    `renderBand` needs a *compare* document (`baseline_band` plus
    `candidate.total_duration_us`). Measured before the fix:
    `renderBand(analyze)` returns `null` for every real report, so
    `UX-196`'s headline view had never rendered outside its own test
    harness.

    Nothing else in the tool answers "the run before this one": `@prev`
    is relative to the store's newest, and the run being viewed is not
    always that.
    """
    earlier = history(run)
    return earlier[-1] if earlier else None


def payloads(run: str, baseline: Optional[str] = None) -> Dict[str, dict]:
    """Everything the page renders, keyed by the url it is served at.

    A refusal is data, not an error: `bga compare` exits 6 on runs it
    will not judge, and that verdict is exactly what the viewer should
    show. So the exit code is ignored here and the document is served.
    """
    # `UX-202`: the evidence header states what this capture can
    # support, and Plane 2's coverage is half that answer - but
    # `analyze` only reads Plane 2 when told to. `bga snapshot` already
    # writes the report beside the run, so the page gets it for free
    # wherever the store put one, and silently goes without elsewhere.
    from bga import run_store

    argv = ["analyze", run, "--format", "json"]
    plane2 = run_store.sibling_plane2(os.path.abspath(run))
    if plane2:
        argv += ["--plane2", plane2]
    documents = {
        "report.json": _capture(argv),
    }
    # `UX-203`: the comparison the user already has. `bga snapshot`
    # compares against the previous run automatically, so by the time
    # anyone runs `bga view` the answer usually exists - it was just
    # never put in front of the page.
    earlier = history(run)
    against = baseline if baseline is not None else (earlier[-1] if earlier else None)
    if against:
        argv = ["compare", against, run, "--format", "json"]
        # Every earlier run in this store becomes a band sample, so the
        # band is derived from the history the user actually has.
        #
        # Including the one used as the positional baseline: `compare`
        # builds the band from `--baseline-run` *only* (compare.py:819),
        # so leaving it out both narrowed the band and, in a two-run
        # store, produced neither a band nor the `baseline_band_shortfall`
        # that explains its absence - a blank where an answer belongs.
        for path in earlier:
            argv += ["--baseline-run", path]
        try:
            documents["compare.json"] = _capture(argv)
        except (RuntimeError, json.JSONDecodeError, OSError):
            # A predecessor that cannot be compared is not an error
            # here - the report still renders, minus one view. An
            # explicit `--compare` that fails is reported by `main`.
            if baseline is not None:
                raise
    return documents


def store_payload(run: str) -> Optional[dict]:
    """`store/v1` for the project this run belongs to, or None.

    `UX-196`'s store trend. Through `bga_snapshot.store_listing`, which
    is also what `--list` renders from, so the drawing and the terminal
    cannot disagree about what is on disk.
    """
    from bga import run_store
    # Relative: packaged, this module is `bga._tools.bga_view`,
    # and `tools` does not exist. `UX-94` made these siblings
    # import each other relatively for exactly this reason.
    from .bga_snapshot import store_listing

    project = run_store.project_root(os.path.abspath(run))
    if project is None:
        return None
    try:
        return store_listing(project)
    except OSError:
        return None


def store_aggregate_payload(store: Optional[dict]) -> Optional[dict]:
    """`store-aggregate/v1` for a listing, or None.

    Built from the listing the page is already given rather than from
    the directory, so the trend's points and the band behind them
    cannot describe different sets of snapshots. `blend=False`: the
    page never asks for a mixed claim, and a chart is the last place to
    make one silently.
    """
    if store is None:
        return None
    from bga.store_aggregate import aggregate

    try:
        return aggregate(store)
    except OSError:
        return None


def whatif_answer(run: str, elements) -> dict:
    """`UX-230`: what the build drops to for a chosen subset.

    The blast transport, again, and for the same reason: an arbitrary
    subset is not in the payload and a page must never compute one. The
    projection is `bga.whatif.project` - the same function `bga whatif`
    calls, over the same analysis - so the served answer and the
    command-line answer are the same bytes.
    """
    import pathlib

    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.whatif import project

    directory = pathlib.Path(run)
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(directory)
    return project(analyzer.analyze(directory), analyzer.graph, list(elements))


def blast_answer(run: str, target: str) -> dict:
    """`bga blast`'s answer for `target`, from the same function.

    `UX-196` item 3, and the rule it is bound by: no viewer-side
    semantics. Resolution order, keying, kinds and cost are all decided
    by `bga.blast.blast` - this only carries the string in and the
    document out, so the served answer and `bga blast --format json`
    cannot diverge.
    """
    from bga import run_store, schemas
    from bga.blast import blast

    project = run_store.project_root(os.path.abspath(run))
    # `measure=False`: this is answered while a user waits on a page,
    # and the measured half is the whole UX-168/169 pipeline. The
    # payload says `measured: false`, which is the honest answer, and
    # `bga blast` on the command line still measures by default.
    return schemas.stamp(
        blast(run, target, project_dir=project, measure=False), schemas.BLAST)


def trace_bytes(run: str) -> Optional[bytes]:
    """`UX-188`'s merged timeline for this run, gzipped, or None.

    `run` is the run directory; `bga timeline` renders the *snapshot*
    that contains it, because the wrapped `build.log` and the raw Plane
    2 log live one level up. A run that is not inside a snapshot - an
    extracted directory, a fetched capture - simply has no timeline, and
    that is not an error.
    """
    from .bga_timeline import render

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


# ---------------------------------------------------------------- export
#
# `UX-195`: the same page, as one file. Measured on the runs the item
# names:
#
#     1,202-element synthetic   report.json   816,573 B
#     golden run                report.json    14,797 B
#     the page itself (7 files)               39,119 B
#     the schemas                              4,535 B
#
# (Re-measured after `UX-196` added `views.js`; at `UX-195` the page was
# 6 files and 26,387 B.)
#
# At 1,202 elements the payload is 21x the page, which is Direction 7's
# own test of whether the viewer stayed thin. The budget below is a
# ceiling on the *file*, not an aspiration: past it a mail client
# starts refusing the attachment, which is the whole use.
EXPORT_BUDGET_B = 8 * 1024 * 1024
# The trace is the one part that can be dropped without losing the
# report, so it is the one part with its own ceiling.
TRACE_BUDGET_B = 4 * 1024 * 1024


# One relative `import` statement, however its specifier list is
# wrapped. `.*?` under `re.S` so a `{ a, b }` list broken across lines is
# still one match - `UX-202` wrapped one and reintroduced UX-199's
# export defect, which is why this is shared rather than written twice.
_IMPORT_RE = re.compile(r"""^[ \t]*import\s.*?from\s+["']\./([\w.-]+)["'];?""",
                        re.M | re.S)


def _module_order(entry: str = "app.js") -> List[str]:
    """Every module the export must inline, dependencies first.

    **Derived, not listed.** `UX-199` found the export defining none of
    `renderBand`, `renderTrend` or `renderBlastSearch` while calling all
    three: `UX-196` added `views.js` and the hand-written pair
    `perfetto.js + app.js` was never updated, so every exported report
    since then threw a `ReferenceError` in `boot()` and rendered
    **empty**. Reproduced under a DOM shim before this was written.

    A hardcoded list is a thing to forget; walking `entry`'s own
    `import` lines is not.
    """
    seen, order = set(), []

    def walk(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        text = open(os.path.join(ASSET_DIR, name), encoding="utf-8").read()
        for match in re.finditer(_IMPORT_RE, text):
            walk(match.group(1))
        order.append(name)

    walk(entry)
    return order


def _inline_module(name: str) -> str:
    """One ES module's source, with its module syntax removed.

    An export opens over `file://`, where a browser refuses a relative
    `import` - so the modules are concatenated into a single inline
    module instead. Stripping `export ` leaves plain top-level
    declarations in one scope, and dropping the `import` statement is
    safe because what it imported is now declared above it.
    """
    text = open(os.path.join(ASSET_DIR, name), encoding="utf-8").read()
    # Removed with the same expression `_module_order` walks, over the
    # whole text rather than line by line: an `import { a, b }` list
    # wrapped across two lines matched neither half of the old
    # line-based test, so the statement survived into the concatenated
    # blob and the browser died on `ERR_INVALID_URL` - `UX-199`'s defect
    # exactly, reintroduced by reformatting one import. Blanked rather
    # than deleted, so a line number in a stack trace still points at
    # the right line of the original module.
    text = _IMPORT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return "\n".join(
        re.sub(r"^export\s+(?=(function|const|let|class|async)\b)", "", line)
        for line in _uncommented(text))


def _uncommented(text: str):
    """The module's lines, minus whole-line comments and blank lines.

    `UX-205` is where the export crossed Direction 7's page ceiling, and
    the honest place to find the bytes was here: this project's comments
    are written for someone reading the repository, and an attached
    report carries none of those readers. Measured: 79,180 B of modules
    become 52,870 B.

    Deliberately conservative - only lines whose first non-space
    characters open a comment, and block comments delimited on their own
    lines. A `//` inside a string or a regex literal is never at the
    start of a line, so nothing here can truncate an expression. It is
    not a minifier and must not become one: code is left exactly as
    written, so a stack trace from an exported page still quotes the
    source.
    """
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if in_block:
            in_block = "*/" not in stripped
            continue
        if stripped.startswith("/*"):
            in_block = "*/" not in stripped
            continue
        if not stripped or stripped.startswith("//"):
            continue
        yield line


def _uncommented_css(text: str) -> str:
    """The stylesheet, minus its comments and blank lines.

    The same rule `_uncommented` applies to the modules, applied to the
    one other checked-in file an export inlines. `style.css` is
    commented for a reader of this repository, and an attached report
    carries none of those readers. CSS has no line comments and no
    string escaping problem worth worrying about here - `/* */` is the
    only form, and a `/*` inside a `content:` string would be the only
    hazard, which this file does not have and a guard would catch.

    Measured on round 23's stylesheet: 12,004 B become 10,765 B.
    """
    return "\n".join(
        line.rstrip() for line in re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        .splitlines() if line.strip())


def export(run: str, path: str, with_trace: bool = True) -> dict:
    """Write one self-contained file. Returns what went into it."""
    # `payloads()` keys documents by the *url* they are served at, so
    # they arrive as "report.json". The inline blocks are keyed by name
    # - `id="bga-report"` - which is what `load()` looks for. Getting
    # this wrong is silent: the block is written as `bga-report.json`,
    # the loader does not find it, and it falls through to `fetch`,
    # which works when served and fails on `file://` - so the export
    # looks fine everywhere except where it is used.
    documents = {name[:-len(".json")] if name.endswith(".json") else name: body
                 for name, body in payloads(run).items()}
    documents["schemas"] = schemas_payload()
    documents["run"] = {"run": os.path.abspath(run),
                        "name": os.path.basename(os.path.abspath(run))}

    trace = trace_bytes(run) if with_trace else None
    omitted = None
    if trace is None:
        omitted = ("this run kept no raw Plane 2 log, so there is no "
                   "timeline to carry")
    elif len(trace) * 4 / 3 > TRACE_BUDGET_B:
        omitted = (f"the timeline is {len(trace) / 1048576:.1f} MiB "
                   f"compressed, over this export's "
                   f"{TRACE_BUDGET_B / 1048576:.0f} MiB ceiling for it")
        trace = None
    documents["run"]["has_timeline"] = trace is not None
    if omitted:
        documents["run"]["timeline_omitted"] = omitted

    page = open(os.path.join(ASSET_DIR, "index.html"), encoding="utf-8").read()
    style = _uncommented_css(
        open(os.path.join(ASSET_DIR, "style.css"), encoding="utf-8").read())
    script = "\n".join(_inline_module(name) for name in _module_order())

    blocks = []
    for name, document in documents.items():
        # `</script>` inside a payload would end the block early. A
        # string can carry one (an element named after an html file is
        # not hypothetical), so it is escaped rather than trusted.
        body = json.dumps(document).replace("</", "<\\/")
        blocks.append(
            f'<script type="application/json" id="bga-{name}">{body}</script>')
    if trace is not None:
        encoded = base64.b64encode(trace).decode()
        blocks.append(
            '<script type="application/json" id="bga-trace">'
            f'"data:application/gzip;base64,{encoded}"</script>')

    page = page.replace('<link rel="stylesheet" href="style.css">',
                        f"<style>\n{style}\n</style>")
    page = page.replace('<script type="module" src="app.js"></script>',
                        "\n".join(blocks) +
                        f'\n<script type="module">\n{script}\n</script>')
    # Nothing may remain that would reach the network from a file:// page.
    page = page.replace('<a href="report.json">report.json</a> ·\n     '
                        '<a href="schemas.json">schemas.json</a>',
                        "Everything it needs is in this file.")
    page = page.replace('<a href="sql.html">Questions to ask it</a>', "")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)

    size = os.path.getsize(path)
    return {"path": os.path.abspath(path), "bytes": size,
            "has_timeline": trace is not None, "omitted": omitted,
            "over_budget": size > EXPORT_BUDGET_B}


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
        raw = self.path
        path = raw.split("?", 1)[0].lstrip("/") or "index.html"
        if path == "blast.json":
            return self._blast(raw)
        if path == "whatif.json":
            return self._whatif(raw)
        if path in self.documents:
            return self._json(self.documents[path])
        if path in self.blobs:
            # `UX-194`: already gzipped on disk-in-memory, and served
            # with its own type rather than Content-Encoding, because
            # the page hands the *compressed bytes* to Perfetto - a
            # transparently-decoding fetch would undo the win.
            return self._send(200, "application/gzip", self.blobs[path],
                              cors=True)
        if path in ASSETS:
            return self._asset(path)
        self._refuse(404, f"{path}: not served")

    def do_HEAD(self):                           # noqa: N802
        self.do_GET()

    def _blast(self, raw):
        """The one endpoint that takes a parameter. Read-only, and it
        calls the same function the CLI does."""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        target = (query.get("target") or [""])[0].strip()
        if not target:
            return self._refuse(400, "blast.json needs ?target=")
        if len(target) > 512:
            # A bound, because this reaches a resolver that touches the
            # filesystem. Nothing here is a secret, but an unbounded
            # string from a url is not something to hand a path walker.
            return self._refuse(400, "target is too long")
        try:
            return self._json(blast_answer(self.run_root, target))
        except Exception as error:  # noqa: BLE001 - reported as data
            return self._refuse(422, f"{target}: {error}")

    def _whatif(self, raw):
        """UX-230's transport. Same shape as `_blast`: read-only, bounded,
        and it calls the function the CLI calls."""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        raw_elements = (query.get("elements") or [""])[0]
        if len(raw_elements) > 4096:
            return self._refuse(400, "too many elements")
        elements = [uid for uid in raw_elements.split(",") if uid.strip()]
        try:
            return self._json(whatif_answer(self.run_root, elements))
        except Exception as error:  # noqa: BLE001 - reported as data
            return self._refuse(422, str(error))

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

    def _send(self, code, kind, body, cors=False):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        # A local viewer has no business being framed or sniffed.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; frame-ancestors 'none'")
        # `UX-198`: the `?url=` deep link has Perfetto fetch the trace
        # from this server, which is a cross-origin read and needs an
        # allow header. Granted on the trace blob **only**, and only to
        # Perfetto's own origin - never `*`, and never on the report,
        # the schemas or the blast endpoint, which is where a run's
        # element names and paths live. An echo of whatever `Origin`
        # asked would be the same as `*`, so the value is a constant
        # and the request's own origin only decides whether to send it.
        if cors and self.headers.get("Origin") == PERFETTO_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", PERFETTO_ORIGIN)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _refuse(self, code, why):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps({"error": why}).encode())


def serve(run: str, port: int = 0,
          documents: Optional[Dict[str, dict]] = None,
          with_trace: bool = True,
          baseline: Optional[str] = None):
    """A started server on 127.0.0.1. The caller closes it.

    Returns `(httpd, url)`. Port 0 means the kernel picks one, so two
    `bga view`s never collide and nothing is left listening on a
    predictable port.
    """
    documents = dict(documents if documents is not None
                     else payloads(run, baseline))
    documents.setdefault("schemas.json", schemas_payload())

    store = store_payload(run)
    if store is not None:
        documents.setdefault("store.json", store)
        # UX-234: and what that store says about itself as a
        # distribution. A second document rather than a key of the
        # listing - one row per snapshot and one row per host class are
        # different shapes - and absent rather than empty when it
        # cannot be built, which is the page's cue to draw no band.
        aggregate = store_aggregate_payload(store)
        if aggregate is not None:
            documents.setdefault("store-aggregate.json", aggregate)

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
        "--export", default=None, metavar="PATH",
        help="Write one self-contained HTML file instead of serving: the "
             "same page with this run's payloads inlined. No port, no "
             "network - for a CI artifact, or for \"send me your report\".")
    parser.add_argument(
        "--perfetto", action="store_true",
        help="Skip the report and hand this run's timeline straight to "
             "ui.perfetto.dev. Tab to tab - nothing is uploaded.")
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Print the url instead of opening it - for a remote shell, or "
             "when you want to curl the payloads.")
    parser.add_argument(
        "--compare", default=None, metavar="BASELINE",
        help="Draw the band against this run instead of the one before "
             "RUN in the same store. Same alias grammar.")
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
        baseline = run_store.resolve(args.compare) if args.compare else None
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if args.export:
        try:
            written = export(run, args.export)
        except (OSError, RuntimeError, ValueError,
                json.JSONDecodeError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 2
        size = written["bytes"]
        print(f"Wrote {written['path']} ({size / 1024:.0f} KiB). Open it with "
              f"a browser - it needs no server and no network.",
              file=sys.stderr)
        if written["omitted"]:
            print(f"  No Perfetto timeline in it: {written['omitted']}. "
                  f"`bga timeline` renders one beside the snapshot.",
                  file=sys.stderr)
        if written["over_budget"]:
            # Said, not enforced: a report that large is still the
            # user's report, and refusing to write it would help nobody.
            print(f"  Note: {size / 1048576:.1f} MiB is over the "
                  f"{EXPORT_BUDGET_B / 1048576:.0f} MiB an attachment "
                  f"usually survives.", file=sys.stderr)
        print(json.dumps(written))
        return 0

    try:
        httpd, url = serve(run, port=args.port, baseline=baseline)
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
