"""UX-443: the served hand-off can count its own edges.

`UX-431` gave the trace hand-off a sentence saying what the dependency
graph's edges became. It reached two readers of three:

| reader | had the accounting |
|---|---|
| `bga timeline` on a terminal | yes, from `describe()` |
| `bga view --export` | yes, `run.trace_flow_losses` in the payload |
| `bga view`, **served** | no |

The served page could not have it, and the reason was a decision worth
keeping: `UX-296` moved the trace render **off the startup path**,
because building it there put a 30 GB projected read between the user
and the socket on a field capture. `flow_losses` was a fact only the
render knew.

It does not have to be. The accounting is a function of the build log
and the dependency graph - both small, both parsed elsewhere already -
and `flow_accounting` computes it from those two alone. The expensive
thing is Plane 2, and it never opens it.

These clauses are on the **served** side on purpose. The export half is
held by `test_the_arrows_say_why_now.py::TestTheLostEdgesAreAccountedFor`,
and a guard that read the export would have passed before this item as
well as after it.
"""
import builtins
import gzip
import json
import os
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from tools.bga_timeline import dependency_edges, flow_accounting, render
from tools.bga_view import serve, timeline_flow_accounting


def served_run_json(run):
    """`run.json` as the **server** answers it, over a real socket.

    Not the document builder called directly: `run.json` is assembled
    inside `serve`, and a guard that reached past the server could pass
    while the served page still had nothing. `UX-443` is about what the
    served page receives, so this fetches it.
    """
    import threading
    import urllib.request

    httpd, url = serve(str(run), port=0)
    # The server answers on a thread, the way `bga view` runs it; a
    # bare `serve` returns a socket nobody is listening on and the
    # fetch below simply times out.
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/run.json",
                                    timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    finally:
        httpd.shutdown()
        httpd.server_close()

#: The one committed capture with a real raw Plane 2 log beside a build
#: log and a graph - which is what makes the "never opens it" clause
#: mean something. On a capture with no raw log there is nothing to
#: avoid opening and the clause would pass vacuously.
CAPTURE = REPO / "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z"

#: The named reasons an edge may fail to become an arrow (`UX-431`).
FLOW_LOSS_REASONS = ("no_task", "out_of_order")


needs_capture = pytest.mark.skipif(
    not (CAPTURE / "build.log").is_file(),
    reason="the example capture is not in this clone (UX-189)")


def _opened(fn, root):
    """Every path under `root` that `fn` opens, by wrapping `open`.

    Both `builtins.open` and `gzip.open`, because the raw Plane 2 log
    is gzipped and a census that watched only the first would report
    that the expensive file was never read while it was being read.
    """
    seen = []
    real_open, real_gzip = builtins.open, gzip.open

    def note(path):
        try:
            relative = os.path.relpath(str(path), str(root))
        except (TypeError, ValueError):
            return
        if not relative.startswith(".."):
            seen.append(relative)

    def spy(path, *args, **kwargs):
        note(path)
        return real_open(path, *args, **kwargs)

    def gzip_spy(path, *args, **kwargs):
        note(path)
        return real_gzip(path, *args, **kwargs)

    builtins.open, gzip.open = spy, gzip_spy
    try:
        fn()
    finally:
        builtins.open, gzip.open = real_open, real_gzip
    return sorted(set(seen))


@needs_capture
class TestTheServedRunCarriesTheAccounting:

    def test_the_served_payload_has_it(self):
        """The gap, closed. Before this item the key was simply absent
        from the served `run.json` and `questions.js` drew nothing -
        silent rather than wrong, which `UX-431`'s own §4e calls
        second-best."""
        run = served_run_json(CAPTURE / "run")
        assert run.get("has_timeline") is True, run.get("has_timeline")
        assert "trace_flow_losses" in run, (
            "the served run.json has no edge accounting, so the hand-off "
            f"section draws nothing: {sorted(run)}")

    def test_it_is_the_same_accounting_the_render_publishes(self, tmp_path):
        """Two ways of computing one fact, held equal.

        This is the clause that makes the cheap path trustworthy: it is
        not asserted to be equivalent, it is compared against the
        render's own numbers on the same capture.
        """
        served = served_run_json(CAPTURE / "run")["trace_flow_losses"]
        rendered = render(str(CAPTURE), str(tmp_path / "t.pftrace"),
                          quiet=True)["flow_losses"]
        assert served == rendered, (
            f"the served page and the render disagree about what the "
            f"graph's edges became: served {served}, rendered {rendered}")

    def test_the_identity_holds_on_the_served_numbers(self):
        """`UX-431`'s property, re-asserted where it now travels: drawn
        plus every named reason equals the edge count. A reason nobody
        counts breaks it."""
        losses = served_run_json(CAPTURE / "run")["trace_flow_losses"]
        edges = len(dependency_edges(str(CAPTURE)))
        named = sum(losses[reason] for reason in FLOW_LOSS_REASONS)
        assert losses["edges"] == edges, (losses, edges)
        assert losses["drawn"] + named == edges, losses


@needs_capture
class TestTheStartupPathStillDoesNotRenderTheTrace:
    """`UX-296` is not reopened, and this is what says so.

    A timing would not: on a 56 KB committed log every path is fast,
    and the measurement `UX-296` was made on is a 30 GB read that no
    fixture here can carry. What *can* be checked on any capture is
    **which files were opened** - and the raw Plane 2 log is the one
    that read was.
    """

    def test_the_accounting_never_opens_the_raw_plane_two_log(self):
        opened = _opened(lambda: flow_accounting(str(CAPTURE)), CAPTURE)
        assert not [p for p in opened if "plane2.log" in p], (
            f"the cheap accounting opened the raw Plane 2 log, which is "
            f"the read UX-296 moved off this path: {opened}")
        assert "build.log" in opened, opened
        assert any(p.endswith("graph.json") for p in opened), opened

    def test_the_full_render_does_open_it(self, tmp_path):
        """The other half of the same measurement, so the clause above
        is a distinction rather than a fact about this capture.

        If the render did not open the raw log either, "the cheap path
        avoids it" would be true and meaningless.
        """
        opened = _opened(
            lambda: render(str(CAPTURE), str(tmp_path / "t.pftrace"),
                           quiet=True), CAPTURE)
        assert [p for p in opened if "plane2.log" in p], (
            f"the full render did not open the raw Plane 2 log either, so "
            f"the clause above distinguishes nothing: {opened}")


@needs_capture
def test_the_wrapper_resolves_the_snapshot_the_way_has_timeline_does():
    """`timeline_flow_accounting` takes the *run* directory, like
    `has_timeline`, and both walk up to the snapshot. Passing the
    snapshot itself would find no `run/` and answer for the wrong
    capture - silently, since the failure mode is `None`."""
    assert timeline_flow_accounting(str(CAPTURE / "run")) == \
        flow_accounting(str(CAPTURE))


def test_a_capture_with_no_build_log_answers_none(tmp_path):
    """The absence path, so a snapshot that cannot be accounted for
    publishes no key rather than a zeroed one - a zero here would read
    as "this graph has no edges"."""
    assert flow_accounting(str(tmp_path)) is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
