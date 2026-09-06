"""`UX-740`: a task the epsilon grid published as zero is named.

`normalize_timestamps` quantizes start and finish independently, so a
span lying wholly inside one rounding bucket lands on the same grid
point at both ends and reports zero width, with no violation raised.
Under half the grid is necessary and not sufficient - the same span
straddling a bucket boundary survives - so the spans below start on a
grid multiple, where width alone decides.

The route taken is disclosure, not repair: rounding 24,999 us up to
50,000 overstates by as much as rounding it down understates, and only
one of the two is Part 3.2's documented rule.

What the guard has to discriminate is the erased zero from the honest
one. `stack` and `import` elements record a genuine zero duration - both
zero-width spans in every committed fixture are of that kind - so a
guard that reddened on "a zero reached a figure" would fire on correct
data and could never go green.
"""
import json
import pathlib
import subprocess
import sys

import pytest

from bga import analyze_run
from bga.normalize.timestamps import spans_below_resolution

EPSILON = 50_000
MACRO_MICRO = pathlib.Path("tests/fixtures/macro_micro/run")


def _run(tmp_path, durations, epsilon_us=EPSILON):
    """A run dir with one BUILD span per `{uid: raw dur_us}` entry."""
    run = tmp_path / "run"
    run.mkdir(parents=True, exist_ok=True)
    uids = list(durations)
    spans, at = [], epsilon_us
    for uid, dur in durations.items():
        spans.append({"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": at,
                      "dur_us": dur, "resources": ["PROCESS"],
                      "primary_resource": "PROCESS"})
        # The next grid multiple a second later: one builder, so the
        # spans never overlap, and each starts on the grid, so width
        # alone decides whether it is erased.
        at = -(-(at + dur + 1_000_000) // epsilon_us) * epsilon_us

    (run / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": epsilon_us, "wall_start_us": 0,
        "wall_end_us": 20_000_000, "max_jobs": 1,
        "resource_capacities": {"PROCESS": 1}}))
    (run / "graph.json").write_text(json.dumps({
        "elements": [{"uid": u, "requested_target": u == uids[-1]} for u in uids],
        "dependencies": []}))
    (run / "trace.json").write_text(json.dumps({"spans": spans, "phases": []}))
    return run


ERASED = {"sub.bst": 1, "half.bst": 24_999, "long.bst": 3_000_000}


class TestTheGridSaysWhatItCouldNotHold:

    def test_a_span_under_half_the_grid_is_named(self, tmp_path):
        published = analyze_run(_run(tmp_path, ERASED)).duration_resolution
        assert published.get("elements") == ["half.bst", "sub.bst"], published
        assert published["epsilon_us"] == EPSILON
        assert published["element_count"] == 2

    def test_the_boundary_is_half_the_grid(self, tmp_path):
        """Not the grid. 24,999 us of real work is erased and 25,001 us
        is not - the one number that decides whether an element's every
        figure is zero, so it is asserted rather than described."""
        result = analyze_run(_run(tmp_path, {
            "under.bst": EPSILON // 2 - 1, "over.bst": EPSILON // 2 + 1,
            "long.bst": 3_000_000}))
        assert result.duration_resolution.get("elements") == ["under.bst"], \
            result.duration_resolution

    def test_an_honest_zero_is_not_a_finding(self):
        """The discrimination clause. `macro_micro` has two zero-width
        spans - `toolchain.bst` (`import`) and `all.bst` (`stack`) - and
        both are zero in the raw trace. A guard that could not tell them
        from an erased span would red on the fixture the suite trusts
        most, so this clause is what keeps the other four honest."""
        raw = json.loads((MACRO_MICRO / "trace.json").read_text())["spans"]
        zeros = [s["task_key"] for s in raw if s["dur_us"] == 0]
        assert len(zeros) == 2, "the fixture stopped carrying its honest zeros"
        assert analyze_run(MACRO_MICRO).duration_resolution == {}

    def test_the_disclosure_reaches_the_published_document(self, tmp_path):
        run = _run(tmp_path, ERASED)
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run), "--format", "json"],
            capture_output=True, text=True, check=True)
        section = json.loads(done.stdout)["duration_resolution"]
        assert section["elements"] == ["half.bst", "sub.bst"]
        assert "unmeasurable at this epsilon" in section["note"]

    def test_the_disclosure_reaches_the_terminal(self, tmp_path):
        run = _run(tmp_path, ERASED)
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run)],
            capture_output=True, text=True, check=True)
        assert "Unmeasurable at this epsilon: half.bst, sub.bst" in done.stdout

    def test_a_run_with_nothing_erased_discloses_nothing(self, tmp_path):
        """Presence is the signal (`UX-676`'s rule for the interval
        tables). An empty object would read as a disclosure that looked
        and found nothing, which is a different claim."""
        run = _run(tmp_path, {"a.bst": 3_000_000, "b.bst": 4_000_000})
        assert analyze_run(run).duration_resolution == {}
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(run), "--format", "json"],
            capture_output=True, text=True, check=True)
        assert "duration_resolution" not in json.loads(done.stdout)


def test_the_predicate_is_not_duration_below_epsilon():
    """`spans_below_resolution` read directly, because the difference
    between the two predicates is the whole of this item: "under the
    epsilon" would name three of `macro_micro`'s spans, "erased by the
    epsilon" names none of them."""
    from bga.ingest.loader import load_all
    _rc, _g, trace = load_all(MACRO_MICRO)
    under_epsilon = [s for s in trace.spans if s.dur_us <= EPSILON]
    assert len(under_epsilon) == 2, "the fixture changed shape"
    assert spans_below_resolution(trace.spans, EPSILON) == []


@pytest.mark.parametrize("epsilon_us", [1_000, 50_000, 1_000_000])
def test_the_threshold_follows_the_capture_s_own_epsilon(tmp_path, epsilon_us):
    """Not the 50 ms default. A capture extracted at a finer grid erases
    less, and the disclosure has to be about the grid that ran."""
    run = _run(tmp_path, {"x.bst": epsilon_us // 2 - 1, "y.bst": 9_000_000},
               epsilon_us=epsilon_us)
    published = analyze_run(run).duration_resolution
    assert published["epsilon_us"] == epsilon_us
    assert published["elements"] == ["x.bst"]
