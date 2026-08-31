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

from bga import plane2 as _plane2_shape

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
          # `UX-337`: the primitives the viewer chapters share, in a
          # module below all of them. Served as well as inlined - the
          # served page loads real ES modules and would 404 on it.
          "primitives.js",
          # `UX-337`: the two chapters `views.js` grew too long to hold,
          # and the two `app.js` did - the schema hints and formatters,
          # and the machinery that turns a value into an interrogable
          # table.
          "element.js", "decision.js", "format.js", "structured.js",
          # UX-194: the Perfetto handoff and the canned-SQL page.
          # `UX-266`: each page's script is a *file*. They were inline
          # `<script type="module">` blocks, which the server's own
          # `default-src 'self'` refuses - `sql.html` rendered nothing
          # and `perfetto.html`'s button had no listener.
          "perfetto.html", "perfetto.js", "perfetto_page.js",
          # `UX-373`: `sql.html` is a redirect to `perfetto.html`, whose
          # second half it used to be. Still served, because the URL is
          # published and older exports point at it.
          "sql.html",
          # UX-199: navigation, and the questions as data so the export
          # can inline what it used to strip.
          "nav.js", "questions.js",
          # UX-204: the link-builder the investigate buttons read, and
          # `perfetto.html` renders its list from `questions.js` rather
          # than carrying a copy - so the page needs it served too.
          # `UX-373` moved that list off `sql.html`.
          "trace_context.js",
          # `UX-450`: the section walk, split out of `app.js` when that
          # file sat exactly on `UX-337`'s 1,500-line ceiling. Served
          # as well as inlined, because `bga view` fetches the modules
          # one by one and an unserved import is a page that never
          # boots - which is what `test_everything_inlined_is_also_
          # served` caught when this list was missed.
          "sections.js",
          # UX-205: the filters, thresholds and copy helpers.
          "tables.js",
          # UX-211: the view state that travels in the fragment.
          "viewstate.js",
          # UX-286: the chapters the document is grouped into. Left out
          # of this tuple the page 404s on the import and renders
          # nothing at all - measured, in Chromium, on a served run -
          # which is why the guard over this list now follows every
          # import from each entry module rather than naming three.
          "chapters.js",
          # UX-302: the style guide's §1 dispatch table, and the "view
          # as JSON" toggle that is one of its two deliberate raw-JSON
          # sites. Served as well as inlined: a served page imports
          # these by URL, and a module missing from this tuple 404s and
          # takes the whole boot with it.
          "shapes.js", "rawjson.js",
          # UX-303: §2's two drawings, which import nothing and take
          # their formatter - so they are a module of their own rather
          # than more of `views.js`.
          "drawings.js",
          # UX-318: opening one nested or capped table full width. Its
          # own module because it imports nothing and both `app.js` and
          # `viewstate.js` need it - which would be a cycle anywhere
          # else.
          "tablefocus.js",
          # UX-334: `name`/`id` for every form control the page builds,
          # and `for` on the labels beside them. Imports nothing, and
          # `views.js` uses it - which `app.js` could not have provided
          # without the cycle its own note forbids.
          "controls.js")

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


# UX-296: how large a Plane 2 report this command will parse when the
# capture published no analysis of its own.
#
# The measurement that sets it: one `json.load` of the monolith costs a
# measured **2.9x its bytes** in resident memory. 64 MB of report is
# therefore ~186 MB of transient RSS - the most an interactive command
# should take without being asked, and two orders of magnitude below the
# field capture that started this (1.5 GB of report, ~4.3 GB of RAM,
# ~30 s, twice, before the socket existed). Above it the page renders
# without Plane 2 and says which command publishes the payload; it does
# not quietly spend the memory, and it does not quietly drop the plane.
# UX-329: moved to `bga.plane2.VIEW_MAX_BYTES`, which is where the
# policy that reads it lives now. Kept as an alias because
# `bga/viewer/perfetto.js` and two guards quote this name.
PLANE2_VIEW_MAX_BYTES = _plane2_shape.VIEW_MAX_BYTES


def published_analysis(run: str) -> Optional[dict]:
    """The analysis this run's capture published, or None.

    `UX-296`, Direction 15's first rule: **capture computes, view
    serves.** `bga snapshot` writes `analyze.json` beside the run from
    the analysis it already ran, so a page load reads a small document
    rather than re-deriving one - which meant re-parsing the Plane 2
    report on every view.
    """
    from bga import run_store

    path = os.path.join(os.path.dirname(os.path.abspath(run)),
                        run_store.ANALYSIS_NAME)
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return None
    return document if isinstance(document, dict) else None


def _analyze_now(run: str) -> dict:
    """Analyze a run whose capture published nothing - the older case.

    Plane 2 joins that analysis only when its report is small enough to
    parse here (`PLANE2_VIEW_MAX_BYTES`). Above the bound the page is
    rendered from Plane 1 and told what to run, which is the choice
    `UX-194` made for a dead button: an affordance whose precondition is
    absent is named, not silently exercised.
    """
    from bga import plane2 as plane2_shape

    # UX-329: the same discovery and the same bound `bga analyze` uses,
    # from `bga.plane2` - this function and the CLI held two copies of
    # the policy, and the copies disagreed: the page attached the
    # sibling and the terminal did not.
    argv = ["analyze", run, "--format", "json"]
    path, refusal = plane2_shape.attachable(run)
    if path:
        argv += ["--plane2", path]
    elif refusal:
        print(refusal, file=sys.stderr)
    return _capture(argv)


def _offered(documents: Dict[str, dict]) -> List[str]:
    """The payload names the page may load, from the table it will be given.

    `UX-334`: keyed by *name* - "compare" - because that is what
    `load()` takes, while the served table is keyed by url and the
    export's by name. Deriving it from the table rather than listing it
    means a payload added later joins the manifest with no edit here,
    and a payload that failed to build is absent from both at once.
    """
    return sorted(name[:-len(".json")] if name.endswith(".json") else name
                  for name in documents)


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

    documents = {"report.json": published_analysis(run) or _analyze_now(run)}
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


def has_timeline(run: str) -> bool:
    """Could this run produce a timeline, without producing one?

    `UX-296`. The page needs the answer to decide whether to offer the
    Perfetto button (`UX-194`: a dead affordance is worse than none),
    and *building* the timeline to find out is what made startup O(the
    trace) - the merge read a 4.7 GB decompressed log as one string, at
    a measured 6.3x amplification, immediately before the server bound
    its socket.

    The precondition is a file test: `bga timeline` renders a snapshot,
    and a snapshot with no `build.log` has no timeline. Everything
    beyond that - a raw log that turns out to have no anchor element -
    is discovered when the bytes are actually asked for, and the handler
    answers 404 rather than the page lying about it up front.
    """
    from .bga_timeline import WRAPPED_LOG_NAME

    snapshot = os.path.dirname(os.path.abspath(run))
    return os.path.isfile(os.path.join(snapshot, WRAPPED_LOG_NAME))


def timeline_flow_accounting(run: str):
    """`UX-431`'s edge accounting for a served run, or `None`.

    `UX-443`. Takes the same `run` directory `has_timeline` does and
    resolves the snapshot the same way, so the two cannot disagree
    about which capture they are answering for.

    The work is in `bga_timeline.flow_accounting`, which reads the build
    log and the dependency graph and nothing else - in particular not
    the raw Plane 2 log, which is what `UX-296` moved off this path.
    """
    from .bga_timeline import flow_accounting

    return flow_accounting(os.path.dirname(os.path.abspath(run)))


def trace_file(run: str, destination: str) -> Optional[str]:
    """Render this run's timeline to `destination`, gzipped. Path or None.

    `UX-296`: to a **file**, never to a `bytes` in the server's memory,
    and compressed in fixed-size chunks rather than in one call - the
    whole point is that the largest artifact this tool handles never has
    to fit in RAM twice.

    `UX-298`: and in Perfetto's own format, which the writer gzips as it
    goes - so the render *is* the served file and there is no second
    pass over it at all. The blob is still `application/gzip` and
    Perfetto still decompresses it on arrival; what changed is that what
    comes out is the format it reads natively rather than the JSON it
    tolerates.
    """
    return (trace_render(run, destination) or {}).get("path")


def trace_render(run: str, destination: str) -> Optional[dict]:
    """`render`'s own result for this run, plus `path`. `None` on refusal.

    `UX-364`: the renderer already reports **which planes it put in the
    trace** - `["1"]` or `["1", "2"]` - and every caller threw that away.
    The page then told a reader of a Plane 1 capture that "Plane 2's
    process lanes" were in the trace they were about to open.

    It is not derivable from anything else the page holds.
    `has_timeline` is true for both. `plane2_absence` is wrong in the
    other direction: `DECLINED` means the analysis was told to ignore
    Plane 2, while `bga timeline` reads the raw log regardless and the
    lanes *are* there. Only the render knows, so the render is asked.
    """
    from .bga_timeline import render

    snapshot = os.path.dirname(os.path.abspath(run))
    try:
        result = render(snapshot, destination, quiet=True)
    except (FileNotFoundError, RuntimeError, OSError):
        return None
    return dict(result or {}, path=destination)


def trace_bytes(run: str) -> Optional[bytes]:
    """The timeline as bytes - for `--export`, which inlines it.

    Still whole-file, because an export *is* one file by definition
    (`UX-195`); `UX-299` is where a capture too large to inline stops
    being inlined. The **serving** path no longer uses this
    (`trace_file` above), which is where the memory ceiling lives.
    """
    return trace_with_planes(run)[0]


def trace_with_planes(run: str):
    """`(bytes, planes, flow_losses, tracks)` - and what it will draw.

    `UX-364`. `trace_bytes` is the same call with the rest dropped; the
    export wants all of it, because the section that pitches the handoff
    has to name what the reader will actually see.

    `UX-431` adds the third: the graph's edges, how many became arrows,
    and the named reason for each one that did not. The page draws no
    arrows on a mostly-cached build and used to say nothing about it,
    which reads as "your graph has no edges" rather than "nothing in
    this run was built".

    `UX-430` adds the fourth: the **track** count, which is what Perfetto
    spends and what `TRACE_BUDGET_B` cannot see. See `TRACE_TRACK_BUDGET`
    for the measurement.
    """
    scratch = tempfile.mkdtemp(prefix="bga-view-")
    try:
        rendered = trace_render(run, os.path.join(scratch, "timeline.json.gz"))
        if rendered is None:
            return None, None, None, None
        with open(rendered["path"], "rb") as handle:
            return (handle.read(), list(rendered.get("planes") or []),
                    rendered.get("flow_losses"), rendered.get("tracks"))
    except OSError:
        return None, None, None, None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def schemas_payload(documents: Optional[Dict[str, dict]] = None) -> dict:
    """The schemas, so the page can render generically.

    Served rather than inlined so the page has one source of truth for
    what a field means, and so `curl .../schemas.json` answers the same
    question a reader has.

    `UX-342`: with `documents`, only the ones those documents *declare*.
    An export embeds its payloads and cannot fetch anything, so it used
    to carry all eight schemas - 83,669 B, byte-identical between two
    runs, against a golden report of 17,891 B. The page resolves a
    schema in exactly two places, `schemas[payload.schema]` and
    `schemas[store?.schema]`, and the other six were 35,185 B nothing
    could reach. Derived from what is being embedded rather than
    subtracted from a list, so a page that later embeds a
    `correlate/v1` document gets that schema with no edit here.

    The **served** side passes nothing and still answers with all of
    them: `schemas.json` is a published API, and a byte there costs the
    page nothing.
    """
    from bga import schemas

    names = schemas.names() if documents is None else _declared_schemas(
        documents, set(schemas.names()))
    return {name: schemas.schema(name) for name in sorted(names)}


def _declared_schemas(documents: Dict[str, dict], known) -> set:
    """Every schema id the documents name, at any depth.

    At any depth because a document can carry another's id inside it -
    `UX-253`'s aggregate says which contract sets it mixes - and a page
    that draws the inner one needs its schema as much as the outer.
    Unknown ids are dropped rather than raising: an id this build does
    not publish is a payload written by a newer one, and refusing to
    export it would be worse than rendering it generically.
    """
    found = set()

    def walk(value):
        if isinstance(value, dict):
            declared = value.get("schema")
            if isinstance(declared, str) and declared in known:
                found.add(declared)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(documents)
    return found


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
#
# `UX-299` made this **one** threshold with one explanation, because the
# two questions it answers are the same question. Above it, a trace
# stops being something to *carry*:
#
#   - the export stops inlining it, because a `data:` URL of gigabytes
#     is not an attachment anyone can open; and
#   - the served page stops posting it tab to tab, because that
#     transport copies the bytes at least twice inside the report tab -
#     `arrayBuffer()` materialises the whole response, `postMessage`
#     structured-clones it - before Perfetto decompresses a third copy
#     in its own. The `?url=` deep link has none of those copies:
#     Perfetto fetches from this server itself.
#
# 4 MiB compressed is where that lands. Measured compression on real
# traces runs 4.2x (`UX-298`'s 40,000-process fixture) to 11x
# (`UX-198`'s capture of `examples/06`), so 4 MiB is ~17-45 MiB
# decompressed and ~25-55 MiB across the two tabs at the conservative
# end - comfortable. It is also the number a mail client will still
# take, which is the export half of the same constant.
TRACE_BUDGET_B = 4 * 1024 * 1024

#: `UX-430`: the bound in the unit the **consumer** spends.
#:
#: `TRACE_BUDGET_B` above bounds transfer, and it bounds it correctly.
#: Perfetto does not draw bytes; it draws a **row per track**, and
#: `_write_trackevent` opens one process track per element and one
#: thread track per traced pid - so the track count rises with the
#: process population, which is what a build worth tracing has a lot of.
#:
#: Measured on the seeded scale run, `bga gen-synthetic --seed 1` at
#: 1,202 elements with twelve processes an element
#: (`tests/pages.py::scale_two_plane_snapshot`):
#:
#: ```text
#:                       tracks   slices     bytes   share of TRACE_BUDGET_B
#:   both planes         16,832   15,628   486,167   11.6%
#:   --planes 1           1,205    1,204    72,080    1.7%
#:   --only-element       1,219    1,216    73,017    1.7%
#: ```
#:
#: **More tracks than slices, at an eighth of the byte bound.** Scaled
#: from that measurement, the byte bound first bites at roughly 145,000
#: tracks - nine times the population a field report already described
#: as freezing the UI. The one number `bga` had could not see the
#: quantity that decides whether the handoff opens at all, which is the
#: fixing guide's §5 on the design side: a real number, honestly
#: reported, measuring a different thing.
#:
#: **This bound is one sample, and says so.** It is sized under the
#: 16,832 that fixture draws, because that is the population the field
#: report came from and the only evidence anybody has; it is not a
#: prediction of what Perfetto can draw. Its job is to make the reader
#: choose - `--planes 1` is a fourteenfold reduction on the same run -
#: rather than to be right about a viewer this repository does not
#: measure. `UX-445` is the item that would replace it with a
#: measurement of the drawing cost itself.
TRACE_TRACK_BUDGET = 8_000


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
    """The module's lines, minus every comment and every blank line.

    `UX-205` is where the export crossed Direction 7's page ceiling, and
    the honest place to find the bytes was here: this project's comments
    are written for someone reading the repository, and an attached
    report carries none of those readers. Measured: 79,180 B of modules
    become 52,870 B.

    `UX-307` made the pass **literal-aware**. What it replaced dropped
    lines whose first non-space characters opened a comment - safe, but
    it can only ever reach a comment that starts a line, so four
    trailing `//` comments rode into every export and the rule could not
    be extended to reach them without understanding literals first. Four
    lines in the same bundle are why:

        const PERFETTO_ORIGIN = "https://ui.perfetto.dev";
        const SVG_NS = "http://www.w3.org/2000/svg";

    A stripper that cuts at the first `//` truncates those into
    unterminated strings, and the page does not parse, let alone boot.
    `views.js` carries the same hazard in the block form: the regex
    literal `/\\s*\\n\\s*/g` contains `*/`, so a `/\\*.*?\\*/` run over
    the whole text can pair it with a `/*` anywhere above and delete
    everything in between.

    It is still **not a minifier** and must not become one: code is left
    exactly as written, so a stack trace from an exported page still
    quotes the source. The only bytes it takes are comments, and the
    whitespace that led into them.
    """
    return _uncomment_js(text).splitlines()


# A `/` opens a regex literal only where a value may not appear - after
# an operator, a keyword or an opening bracket. After an identifier, a
# number or a closing bracket it is division instead.
_VALUE_MAY_FOLLOW = frozenset("=(,:[!&|?{};+-*%~^<>\n")
_KEYWORDS_BEFORE_REGEX = frozenset((
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "case", "do", "else", "yield", "await"))


def _comment_spans(text: str):
    """Yield `(start, end)` of every comment, literals excluded.

    One pass. The states that matter are the ones in which a `//` or a
    `/*` is *not* a comment: the two quoted string forms, a template
    literal - whose `${ }` is code again, and may hold more of either -
    and a regex literal.
    """
    i, n = 0, len(text)
    prev = ""          # last significant character of code
    word = ""          # last identifier, for `return /re/`
    while i < n:
        char = text[i]
        if char in "\"'":
            i, prev, word = _close_string(text, i, char), char, ""
        elif char == "`":
            i, prev, word = _close_template(text, i), "`", ""
        elif char == "/" and i + 1 < n and text[i + 1] == "/":
            end = text.find("\n", i)
            end = n if end < 0 else end
            yield i, end
            i = end
        elif char == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            yield i, end
            i = end
        elif char == "/" and (not prev or prev in _VALUE_MAY_FOLLOW
                              or word in _KEYWORDS_BEFORE_REGEX):
            i, prev, word = _close_regex(text, i), "/", ""
        else:
            if not char.isspace():
                prev = char
                word = word + char if (char.isalpha() or char == "_") else ""
            i += 1


def _close_string(text: str, i: int, quote: str) -> int:
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote or text[i] == "\n":
            return i + 1
        i += 1
    return i


def _close_regex(text: str, i: int) -> int:
    i, in_class = i + 1, False
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "/" and not in_class:
            return i + 1
        elif char == "\n":
            return i          # unterminated: it was division after all
        i += 1
    return i


def _close_template(text: str, i: int) -> int:
    i += 1
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "`":
            return i + 1
        if char == "$" and i + 1 < len(text) and text[i + 1] == "{":
            i = _close_interpolation(text, i + 2)
            continue
        i += 1
    return i


def _close_interpolation(text: str, i: int) -> int:
    """Code inside `${ }`: nested braces, strings and templates count."""
    depth = 1
    while i < len(text):
        char = text[i]
        if char in "\"'":
            i = _close_string(text, i, char)
            continue
        if char == "`":
            i = _close_template(text, i)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _uncomment_js(text: str) -> str:
    """`text` with every comment gone and every blank line dropped.

    Newlines inside a removed block comment are kept, so two statements
    a comment sat between never end up on one line - which would change
    what automatic semicolon insertion does to them.
    """
    out, at = [], 0
    for start, end in _comment_spans(text):
        # The run of spaces that led into the comment goes with it. That
        # whitespace is provably outside every literal, because a comment
        # is only recognised in code context - so this can never take the
        # trailing spaces of a line inside a template literal, which are
        # part of the string.
        while start > at and text[start - 1] in " \t":
            start -= 1
        out.append(text[at:start])
        out.append("\n" * text.count("\n", start, end))
        at = end
    out.append(text[at:])
    return "\n".join(
        line for line in "".join(out).splitlines() if line.strip())


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
    # `UX-342`: after the payloads and before the manifest - it has to
    # see what is being embedded, and `_offered` has to see it.
    documents["schemas"] = schemas_payload(documents)
    documents["run"] = {"run": os.path.abspath(run),
                        "name": os.path.basename(os.path.abspath(run)),
                        # UX-334: the same manifest the server
                        # publishes. An export inlines every payload it
                        # has, so `load` never reaches the network here
                        # - but the page reads one key either way, and
                        # a key that exists on one side only is a key
                        # that gets tested on one side only.
                        "payloads": _offered(documents)}

    trace, trace_planes, flow_losses, trace_tracks = (
        trace_with_planes(run) if with_trace else (None, None, None, None))
    omitted = None
    if trace is None:
        # UX-329: which absence, from `bga.plane2` - the same sentence
        # the terminal prints and the JSON publishes. The one this
        # replaced said "no raw Plane 2 log" for a run that never
        # captured the plane at all, which reads as "Plane 2 is
        # missing" when the report is right there beside the run.
        from bga import plane2 as plane2_shape

        omitted = plane2_shape.absence(run) or (
            "this run kept no raw Plane 2 log, so there is no timeline "
            "to carry")
    else:
        # Two bounds, each named in its own unit. `UX-299` set the byte
        # one; `UX-430` added the track one, because Perfetto draws a row
        # per track and a capture can sit at an eighth of the byte bound
        # with sixteen thousand rows in it. A refusal reading "4 MiB"
        # when the problem is the rows sends the reader to compress
        # something that is not the cost.
        if len(trace) * 4 / 3 > TRACE_BUDGET_B:
            omitted = (f"the timeline is {len(trace) / 1048576:.1f} MiB "
                       f"compressed, over this export's "
                       f"{TRACE_BUDGET_B / 1048576:.0f} MiB ceiling for it")
        elif (trace_tracks or 0) > TRACE_TRACK_BUDGET:
            omitted = (f"the timeline draws {trace_tracks:,} tracks, over "
                       f"this export's {TRACE_TRACK_BUDGET:,}-track "
                       f"ceiling - Perfetto draws a row per track, and the "
                       f"byte size ({len(trace) / 1048576:.1f} MiB) is well "
                       f"inside its own ceiling")
    if omitted and trace is not None:
        # UX-299: and what to do instead, because "the timeline is not
        # in this file" is a dead end without it. The blast box's
        # honesty pattern: name the command that produces what the page
        # cannot carry - and, since `UX-430`, the two flags that make it
        # smaller in the unit that was actually exceeded.
        documents["run"]["timeline_recipe"] = {
            "command": f"bga view {os.path.dirname(os.path.abspath(run))} "
                       f"--perfetto",
            "note": "That serves this run and hands the timeline to "
                    "Perfetto over a deep link, which streams it from the "
                    "server instead of copying it through the page. "
                    "`bga timeline` writes the same trace to a file if "
                    "you would rather open it yourself, and "
                    "`--planes 1` or `--only-element ELEMENT` write a "
                    "smaller one: the process lanes are where the track "
                    "count grows.",
        }
        trace = None
    documents["run"]["has_timeline"] = trace is not None
    # UX-364: and *which* planes are in it, when there is one. The
    # handoff's lead sentence names them; before this it named both
    # unconditionally, on a capture that had one.
    if trace is not None:
        documents["run"]["trace_planes"] = trace_planes
        # `UX-431`: and what the graph's edges became. The handoff page
        # is where the reader goes to look for the arrows, so it is
        # where their absence has to be accounted for.
        if flow_losses:
            documents["run"]["trace_flow_losses"] = flow_losses
    # UX-299: the threshold travels with the payload rather than being
    # written down twice. The page applies the same number to the same
    # decision on the served side, where the size is only knowable once
    # the trace has been rendered.
    documents["run"]["trace_inline_max_bytes"] = TRACE_BUDGET_B
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
    page = page.replace(
        '<a href="perfetto.html">Questions to ask it</a>', "")

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
    # `UX-394`: the other runs of this run's own store, by the stamp
    # the store lists them under, and what has been built for each.
    # Empty where there is no store, which is what makes the selector
    # absent rather than empty (`UX-388`'s rule).
    sibling_runs: Dict[str, str] = {}
    sibling_documents: Dict[str, Dict[str, dict]] = {}
    sibling_lock: Optional[threading.Lock] = None

    def _for_run(self, raw: str) -> Dict[str, dict]:
        """The documents for the run `?run=` names, or this one's.

        **Built on request, cached per stamp.** `payloads` runs the
        analysis, and a server that built every run in the store at
        startup would pay for runs nobody opens - which is `UX-296`'s
        rule for the timeline, applied to the second run.

        An unknown stamp falls back to the run this server was started
        on rather than refusing: the selector only ever offers stamps
        from this store, so an unknown one is a hand-edited URL, and
        the page it lands on is a real report of a real run.
        """
        query = raw.split("?", 1)[1] if "?" in raw else ""
        wanted = urllib.parse.parse_qs(query).get("run", [None])[0]
        target = self.sibling_runs.get(wanted or "")
        if not wanted or not target or os.path.abspath(target) == self.run_root:
            return self.documents
        with (self.sibling_lock or contextlib.nullcontext()):
            built = self.sibling_documents.get(wanted)
            if built is None:
                built = dict(payloads(target))
                built.setdefault("schemas.json", schemas_payload())
                # The store and its aggregate are properties of the
                # *project*, not of the run, so the two are shared
                # rather than recomputed - which also keeps the
                # selector's own list identical on every run's page.
                for shared in ("store.json", "store-aggregate.json"):
                    if shared in self.documents:
                        built.setdefault(shared, self.documents[shared])
                built.setdefault("run.json", dict(
                    self.documents.get("run.json") or {},
                    run=os.path.abspath(target),
                    name=os.path.basename(os.path.abspath(target)),
                    payloads=_offered(built),
                    # A trace belongs to the snapshot this server was
                    # started on; offering one for a run it is not
                    # serving would be the dead affordance `UX-194`
                    # ruled out.
                    has_timeline=False))
                self.sibling_documents[wanted] = built
            return built

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
        if path == "favicon.ico":
            # UX-334: a browser asks for this on every navigation
            # whether the document links one or not, and a 404 is an
            # *error* in the console - one per boot, forever, for a
            # file this report has no use for. 204 is the answer that
            # says "nothing here, and that is fine".
            #
            # The alternative - `<link rel="icon" href="data:,">` in
            # the page - was tried and measured: this server's own
            # `default-src 'self'` refuses a `data:` image, so it
            # traded a 404 for a CSP violation, which is worse.
            return self._send(204, "image/x-icon", b"")
        # `UX-394`: `?run=<stamp>` selects another run of this store.
        # A full load rather than a re-render: the page reads its
        # payload once at boot (`UX-296`), so the URL *is* the state,
        # and a link to it reloads to the same view.
        serving = self._for_run(raw)
        if path in serving:
            return self._json(serving[path])
        if path in self.blobs:
            # `UX-194`: already gzipped on disk-in-memory, and served
            # with its own type rather than Content-Encoding, because
            # the page hands the *compressed bytes* to Perfetto - a
            # transparently-decoding fetch would undo the win.
            return self._send(200, "application/gzip", self.blobs[path],
                              cors=True)
        if path == TRACE_NAME and getattr(self, "trace_run", None):
            return self._trace()
        if path in ASSETS:
            return self._asset(path)
        self._refuse(404, f"{path}: not served")

    def do_HEAD(self):                           # noqa: N802
        self.do_GET()

    def do_OPTIONS(self):                        # noqa: N802 - stdlib name
        """The CORS pre-flight for the trace blob, and nothing else.

        `UX-265`: the `?url=` hand-off used to be a *simple* request -
        a bare cross-origin `GET`, which no browser pre-flights - so
        answering `GET` with an allow header was enough, and
        `BaseHTTPRequestHandler` replying `501 Unsupported method` to
        `OPTIONS` never came up. Chrome's Private Network Access
        changed that without anything here changing: a request from a
        **public** origin to a **local** address is pre-flighted now,
        and the pre-flight carries `Access-Control-Request-Private-
        Network: true`. A 501 with no allow header on it is reported to
        the reader as *"No 'Access-Control-Allow-Origin' header is
        present on the requested resource"*, which is the pre-flight
        being refused rather than the read.

        Scoped exactly as narrowly as the `GET` grant it precedes: the
        trace blob only, Perfetto's origin only, `GET`/`HEAD` only.
        Everything else answers as it did, so a pre-flight against the
        report, the schemas or the blast endpoint is still refused.
        """
        path = self.path.split("?", 1)[0].lstrip("/")
        # UX-296: the trace is no longer a blob held in memory - it is
        # rendered when it is first asked for - so "is this the trace"
        # is asked of what the server *offers*, not of what it has
        # already built. Pre-flighting it must not build it: a
        # pre-flight is a question about policy, and answering it by
        # rendering gigabytes would put the whole cost back on the path
        # this item took it off.
        offered = self.path is not None and (
            path in self.blobs
            or (path == TRACE_NAME and getattr(self, "trace_run", None)))
        if not offered:
            return self._refuse(404, f"{path}: not served")
        if self.headers.get("Origin") != PERFETTO_ORIGIN:
            return self._refuse(403, "pre-flight is granted to Perfetto only")
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", PERFETTO_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD")
        # Whatever headers the reader asked to send, echoed back. This
        # does not widen *who* may read - the origin and the path are
        # still the only ones granted - it only avoids guessing which
        # headers a fetch we do not control attaches (`range`,
        # `cache-control`, a client's own). Naming a fixed list here
        # would make the hand-off break again the next time the other
        # side adds one, which is exactly how this broke.
        asked = self.headers.get("Access-Control-Request-Headers")
        if asked:
            self.send_header("Access-Control-Allow-Headers", asked)
        # The header Private Network Access asks for by name. Without
        # it the pre-flight is refused even when the origin matches.
        self.send_header("Access-Control-Allow-Private-Network", "true")
        # A pre-flight per read of a possibly large trace is a round
        # trip nobody needs; ten minutes outlives any hand-off.
        self.send_header("Access-Control-Max-Age", "600")
        # The answer depends on the request's `Origin`, so a cache that
        # ignored it could serve the grant to a page that has none.
        self.send_header("Vary", "Origin, Access-Control-Request-Headers, "
                         "Access-Control-Request-Private-Network")
        self.end_headers()

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

    def _trace(self):
        """The merged timeline, rendered on first request and streamed.

        `UX-296`. Two rules, and the second is the one that matters at
        scale: it is built **here** rather than at startup, so a page
        that nobody asks a timeline of never pays for one; and it is
        sent from a **file in fixed-size chunks**, so the largest
        artifact this tool produces is never a `bytes` in the server's
        address space.

        Rendered once per server - the lock is what stops two tabs
        rendering the same gigabytes twice - and a render that fails
        answers 404 with what would have produced it, rather than
        pretending the button was never offered.
        """
        cls = type(self)
        with cls.trace_lock:
            if cls.trace_path is None:
                if cls.trace_scratch is None:
                    cls.trace_scratch = tempfile.mkdtemp(prefix="bga-serve-")
                cls.trace_path = trace_file(
                    cls.trace_run,
                    os.path.join(cls.trace_scratch, TRACE_NAME)) or ""
        if not cls.trace_path:
            return self._refuse(
                404, f"{TRACE_NAME}: this snapshot has a build log but no "
                     f"timeline could be rendered from it - `bga timeline "
                     f"{os.path.dirname(cls.trace_run)}` says why")
        try:
            size = os.path.getsize(cls.trace_path)
            handle = open(cls.trace_path, "rb")
        except OSError as error:
            return self._refuse(404, f"{TRACE_NAME}: {error}")
        with handle:
            self._begin(200, "application/gzip", size, cors=True)
            if self.command != "HEAD":
                shutil.copyfileobj(handle, self.wfile, length=256 * 1024)

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
        self._begin(code, kind, len(body), cors=cors)
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _begin(self, code, kind, length, cors=False):
        """The headers, without a body in hand.

        `UX-296`: the trace is streamed from a file, so its response has
        a length before it has bytes. Every header `_send` sets is set
        here, once, so the two cannot drift about the policy.
        """
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(length))
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
        if cors:
            # `Vary` whether or not the grant is issued: the response
            # differs by `Origin`, and a cache told otherwise could hand
            # Perfetto's grant to a page that was refused one.
            self.send_header("Vary", "Origin")
            if self.headers.get("Origin") == PERFETTO_ORIGIN:
                self.send_header("Access-Control-Allow-Origin", PERFETTO_ORIGIN)
        self.end_headers()

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

    # UX-296: the timeline is *not* built here. Startup asks whether one
    # could exist - a file test - and the first request for the bytes is
    # what renders them, into a file the handler streams. Building it
    # here is what put a 30 GB projected read between the user and the
    # socket on the field capture.
    offered = bool(with_trace) and has_timeline(run)

    documents.setdefault("run.json", {
        "run": os.path.abspath(run),
        "name": os.path.basename(os.path.abspath(run)),
        # UX-334: which optional payloads exist, so the page stops
        # asking the network. `compare`, `store` and `store-aggregate`
        # are each absent on a perfectly ordinary run, and the page
        # learned that by fetching them and catching the 404 - three
        # red lines in every console on every boot, which is three
        # lines of noise a real error has to be spotted among. The
        # server already knows the answer here; it just never said it.
        "payloads": _offered(documents),
        # So the page can offer the button only when there is something
        # behind it - a dead "Open in Perfetto" is worse than none.
        "has_timeline": offered,
        # UX-299: the threshold above which the trace is fetched by
        # Perfetto rather than copied through this page. The *size* is
        # not here, and cannot be: knowing it means rendering the
        # trace, which `UX-296` moved off the startup path. The page
        # asks for the headers when the user asks for the timeline.
        "trace_inline_max_bytes": TRACE_BUDGET_B,
    })

    # `UX-443`: and what the graph's edges became - the third reader of
    # `UX-431`'s accounting, after the terminal and the export.
    #
    # The *size* above cannot be known without rendering, and this can:
    # the accounting is a function of the build log and the dependency
    # graph, and `flow_accounting` reads only those two. It never opens
    # the raw Plane 2 log, which is the file `UX-296`'s 30 GB
    # measurement was about, so the startup path is unchanged in the
    # only way that measurement cared about.
    if offered:
        accounting = timeline_flow_accounting(run)
        if accounting:
            documents["run.json"]["trace_flow_losses"] = accounting

    # `UX-394`: the store's other runs, so `?run=<stamp>` can reach
    # them. Read from the listing the page is already given, so the
    # selector and the server cannot disagree about what is on disk -
    # and empty where there is no store, which is what makes the
    # selector absent rather than empty.
    from bga.run_store import RUN_SUBDIR

    siblings = {row["stamp"]: os.path.join(row["path"], RUN_SUBDIR)
                for row in ((store or {}).get("snapshots") or [])
                if row.get("has_run") and row.get("path")}
    handler = type("_BoundHandler", (_Handler,),
                   {"documents": documents, "blobs": {},
                    "sibling_runs": siblings, "sibling_documents": {},
                    "sibling_lock": threading.Lock(),
                    "trace_run": os.path.abspath(run) if offered else None,
                    "trace_scratch": None, "trace_path": None,
                    "trace_lock": threading.Lock(),
                    "run_root": os.path.abspath(run)})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    return httpd, landing_url(httpd.server_address[1])


# `UX-314`: the two plain-http origins ui.perfetto.dev's own
# `connect-src` will let it fetch a trace from. Read from Perfetto's
# source, quoted in `bga/viewer/perfetto.js`, which is where the rule
# and its provenance live; this is the serving half of the same fact.
#
# `9001` is fetchable and deliberately not recommended: it is
# `trace_processor_shell --httpd`'s port, and Perfetto probes it at
# startup expecting an RPC endpoint. `8080` is the llama-server port,
# which nothing probes.
PERFETTO_FETCHABLE_PORTS = {8080: "localhost", 9001: "127.0.0.1"}


def landing_url(port: int) -> str:
    """The URL to hand the browser, spelled so Perfetto can follow it.

    The server binds `127.0.0.1` and every port but one is named that
    way. CSP matches the host **name**, not the address it resolves to,
    so `http://127.0.0.1:8080` is refused where `http://localhost:8080`
    is allowed - the same interface, and the spelling is the whole
    difference between a working `?url=` handoff and a console error.
    """
    return f"http://{PERFETTO_FETCHABLE_PORTS.get(port, '127.0.0.1')}:{port}/"


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
    # UX-296: what the server *offers*, not what it has already built -
    # the timeline is rendered when Perfetto fetches it, and asking for
    # `--perfetto` is exactly the case where that happens a moment later.
    if args.perfetto and not (httpd.RequestHandlerClass.blobs
                              or httpd.RequestHandlerClass.trace_run):
        print("Error: this run has no timeline to hand over. `bga snapshot` "
              "keeps the raw Plane 2 log by default; a capture taken with "
              "--no-keep-raw, or before UX-188, has only the processed "
              "report.", file=sys.stderr)
        httpd.server_close()
        return 7

    print(f"Serving {os.path.abspath(run)} at {landing}", file=sys.stderr)
    # `UX-314`: say it here, once, where the port is known. A trace over
    # the tab-to-tab threshold can only reach Perfetto through the
    # `?url=` deep link, and Perfetto's CSP refuses every origin but
    # two - so on the default ephemeral port a big trace has no
    # one-click route at all, and the page can only say so after the
    # reader has clicked.
    if args.port not in PERFETTO_FETCHABLE_PORTS:
        print(f"  ui.perfetto.dev may not fetch from this port, so a trace "
              f"over {TRACE_BUDGET_B // 1048576} MiB has no one-click "
              f"handoff. Re-run with --port 8080 for that, or save the "
              f"trace and drag it in.", file=sys.stderr)
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
