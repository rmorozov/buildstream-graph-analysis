"""UX-899: the seconds a review build owes are judged against a band.

The gate a growing project ships judges the diff alone, precisely
because a whole-build number is noisy: five captures of one unchanged
`freedesktop-sdk` commit span **33%** against a 1% significance rule. A
seconds claim from one build against one predecessor is a coin toss with
a decimal point on it.

`--band-from-class` points the instrument the tool already has - a
baseline *set* and its noise band - at the population the candidate
belongs to: the last N runs of this store declaring its own
`build_class` (`UX-898`). Four claims, one per case the row names: a
candidate inside the band passes and says so, one outside reports the
delta in seconds and fails, a store with too few runs of that class
refuses with its own exit code rather than falling back to the rule the
band replaces, and runs of another class are refused rather than pooled.
"""
import contextlib
import io
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import buildclass
from bga.compare import DEFAULT_BAND_WINDOW, MIN_BASELINE_RUNS
from bga.exceptions import EXIT_BAND_UNAVAILABLE, EXIT_OK, EXIT_REGRESSION

# The golden fixture carries a complete `run_identity`, so a comparison
# built from copies of it is HIGH confidence - without that the gate
# fails open on `low_confidence` and no exit code below is reachable.
# The same reason `test_compare.py` copies it.
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

SECOND = 1_000_000
REVIEW = {"arch": "x86_64", "sanitizer": "address"}


def _run_dir(path: pathlib.Path, duration_us: int, build_type, variant=None):
    """One run of `duration_us`, declaring a class.

    `app.bst`'s span carries the duration and `wall_clock.end_us`
    follows it, keeping Part 13's wall_clock >= horizon containment -
    the same shape `_golden_variant_dir` uses, because the band reads
    the wall clock and the analysis reads the trace and the two must
    agree.
    """
    path.mkdir(parents=True)
    trace = json.loads((GOLDEN / "trace.json").read_text())
    for span in trace["spans"]:
        if span["task_key"].startswith("app.bst"):
            span["dur_us"] = duration_us
    horizon = max(s["ts_us"] + s["dur_us"] for s in trace["spans"])

    context = json.loads((GOLDEN / "run-context.json").read_text())
    context["wall_clock"]["end_us"] = horizon
    declared = buildclass.declare(build_type, variant)
    if declared:
        context["build_class"] = declared

    (path / "graph.json").write_text((GOLDEN / "graph.json").read_text())
    (path / "trace.json").write_text(json.dumps(trace))
    (path / "run-context.json").write_text(json.dumps(context))
    return path


def _store(tmp_path, members, candidate_us, candidate_class=("review", REVIEW)):
    """A project store: `members` as `(build_type, variant, seconds)`,
    then the baseline and the candidate, newest last.

    Returns `(project, baseline_dir, candidate_dir)`. The two principals
    are the newest two stamps, so a window that reached them would be
    letting a run vote on the band it is judged against.
    """
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.conf").write_text("name: ux899\n", encoding="utf-8")
    runs = project / ".bga" / "runs"

    for index, (build_type, variant, seconds) in enumerate(members):
        _run_dir(runs / f"202609{index + 1:02d}T000000Z" / "run",
                 int(seconds * SECOND), build_type, variant)
    baseline = _run_dir(runs / "20260920T000000Z" / "run",
                        100 * SECOND, *candidate_class)
    candidate = _run_dir(runs / "20260921T000000Z" / "run",
                         int(candidate_us), *candidate_class)
    return project, baseline, candidate


def _compare(baseline, candidate, *extra):
    """One in-process `bga compare`, returning `(exit_code, output)`."""
    from bga.cli import main

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            code = main(["compare", str(baseline), str(candidate), *extra])
        except SystemExit as raised:
            code = raised.code
    return (code or EXIT_OK), sink.getvalue()


# Five members at 98..102s: median 100s, scaled MAD 1.4826s, so the band
# is 100 +- 4.4s - wider than the fixed 1% rule (1s), which is the point:
# the rule would call a 1s difference a regression.
_FIVE_REVIEW_RUNS = [("review", REVIEW, seconds) for seconds in (98, 99, 100, 101, 102)]


class TestTheBandIsTheCandidatesOwnClass:

    def test_a_candidate_inside_the_band_passes_and_says_so(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=101 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression", "--format", "ci-comment")

        assert code == EXIT_OK, output
        assert "+1.0s" in output
        assert "— within the band from 5 baseline run(s)" in output

    def test_the_band_decides_the_gate_where_the_fixed_rule_would_not(self, tmp_path):
        """`UX-180`'s open seam, closed for this flag. +3s on 100s is a
        3% regression under the fixed rule and well inside a band whose
        own members span 98..102s - so a pipeline asking for the band
        must be gated by the band, or the flag buys nothing."""
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=103 * SECOND)

        with_band, output = _compare(baseline, candidate, "--band-from-class",
                                     "--fail-on-regression")
        without_band, _ = _compare(baseline, candidate, "--fail-on-regression")

        assert with_band == EXIT_OK, output
        assert without_band == EXIT_REGRESSION

    def test_a_candidate_outside_the_band_reports_the_seconds_and_fails(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=130 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression", "--format", "ci-comment")

        assert code == EXIT_REGRESSION, output
        assert "+30.0s" in output
        assert "— outside the band from 5 baseline run(s)" in output

    def test_the_comment_says_which_runs_formed_the_band(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=101 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--format", "ci-comment")

        assert code == EXIT_OK, output
        # The count, so a reviewer can weigh the claim at all.
        assert "band from 5 baseline run(s)" in output
        # And which five, so a window that reached across a toolchain
        # bump is visible rather than hidden inside the number.
        for index in range(1, 6):
            assert f"`202609{index:02d}T000000Z`" in output
        # Neither principal votes on the band it is judged against.
        assert "20260920T000000Z`" not in output
        assert "20260921T000000Z`" not in output

    def test_too_few_runs_of_the_class_refuse_rather_than_guess(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS[:2], candidate_us=130 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression")

        assert code == EXIT_BAND_UNAVAILABLE, output
        assert "Band gate REFUSED" in output
        assert "review · arch=x86_64 · sanitizer=address" in output
        assert "holds 2 other run(s) of that class" in output
        # A refusal is not a verdict: no comparison may be printed beside it.
        assert "Verdict:" not in output

    def test_runs_of_another_class_are_not_pooled(self, tmp_path):
        """The mutation the row names: pool by recency, not by class."""
        nightlies = [("night", REVIEW, seconds) for seconds in (98, 99, 100, 101, 102)]
        project, baseline, candidate = _store(
            tmp_path, nightlies, candidate_us=130 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression")

        assert code == EXIT_BAND_UNAVAILABLE, output
        assert "holds 0 other run(s) of that class" in output

    def test_a_variant_alone_separates_two_populations(self, tmp_path):
        """A review build under a sanitizer is not a review build: the
        class is the pair (`UX-903`), so the type matching is not enough."""
        coverage = [("review", {"arch": "x86_64", "coverage": "on"}, seconds)
                    for seconds in (98, 99, 100, 101, 102)]
        project, baseline, candidate = _store(
            tmp_path, coverage, candidate_us=130 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression")

        assert code == EXIT_BAND_UNAVAILABLE, output


class TestTheFlagSaysWhatItSelected:

    def test_the_window_is_the_flags_argument(self, tmp_path):
        """Ten runs in the store, a window of four, four in the band -
        the oldest runs are the ones describing a different tree."""
        members = [("review", REVIEW, 100) for _ in range(10)]
        project, baseline, candidate = _store(
            tmp_path, members, candidate_us=101 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class", "4",
                                "--format", "ci-comment")

        assert code == EXIT_OK, output
        assert "band from 4 baseline run(s)" in output

    def test_a_window_below_the_minimum_is_refused_as_an_argument(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=101 * SECOND)

        code, output = _compare(baseline, candidate, "--band-from-class", "2")

        assert code == 1, output
        assert f"fewer than {MIN_BASELINE_RUNS} runs" in output

    def test_the_flag_and_an_explicit_baseline_set_are_not_both_the_band(self, tmp_path):
        project, baseline, candidate = _store(
            tmp_path, _FIVE_REVIEW_RUNS, candidate_us=101 * SECOND)
        member = project / ".bga" / "runs" / "20260901T000000Z" / "run"

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--baseline-run", str(member))

        assert code == 1, output
        assert "both name the band's members" in output

    def test_no_store_to_select_from_refuses_with_the_band_code(self, tmp_path):
        """No enclosing project means no population, and a gate that
        asked for one may not quietly compare a pair instead."""
        baseline = _run_dir(tmp_path / "baseline", 100 * SECOND, "review", REVIEW)
        candidate = _run_dir(tmp_path / "candidate", 130 * SECOND, "review", REVIEW)

        code, output = _compare(baseline, candidate, "--band-from-class",
                                "--fail-on-regression")

        assert code == EXIT_BAND_UNAVAILABLE, output
        assert "no BuildStream project" in output

    def test_the_default_window_is_the_published_constant(self):
        """The flag's help is what a CI owner reads before running it."""
        from bga.cli import create_parser

        parser = create_parser()
        with io.StringIO() as sink, contextlib.redirect_stdout(sink):
            with pytest.raises(SystemExit):
                parser.parse_args(["compare", "--help"])
            help_text = sink.getvalue()
        assert f"default {DEFAULT_BAND_WINDOW}" in help_text
