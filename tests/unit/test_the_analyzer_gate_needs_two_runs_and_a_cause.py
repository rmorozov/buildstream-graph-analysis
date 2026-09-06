"""UX-702: `bga analyze` was measured superlinear (UX-531) and nothing
read whether a round made it slower. This holds `tools/dev_perf_ratchet.py`
to the three rules its own Required Fix states, each one this
repository has already been burned by not having:

- **absolute margin, not a ratio** (`UX-420`'s Motivation - a ratio at
  small magnitude is noise, seconds and MB are not);
- **two consecutive runs**, not one sample (`UX-442`'s lesson, on a
  different quantity);
- **the diff has to touch the analyzer**, or a slower runner reads as a
  slower analyzer.

All synthetic: the real reading is CI's own clock and does not travel
here (Out of Scope), so every case below is a fabricated
`/usr/bin/time -v` report or a pinned diff, never a live `bga analyze`.
"""
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_perf_ratchet as ratchet
from tools import dev_tier_drift as drift
from tools import dev_touching

WORKFLOW = REPO / ".github/workflows/ci.yml"

_TIME_V = """\
\tCommand being timed: "{cmd}"
\tUser time (seconds): 1.00
\tSystem time (seconds): 0.10
\tPercent of CPU this job got: 99%
\tElapsed (wall clock) time (h:mm:ss or m:ss): {wall}
\tMaximum resident set size (kbytes): {kb}
\tExit status: 0
"""


def _report(tmp_path, name, wall, kb, cmd="bga analyze"):
    path = tmp_path / name
    path.write_text(_TIME_V.format(cmd=cmd, wall=wall, kb=kb),
                    encoding="utf-8")
    return path


def test_parse_time_v_reads_wall_and_peak_rss(tmp_path):
    path = _report(tmp_path, "a.time", "0:11.49", 736000)
    wall, rss = ratchet.parse_time_v(path.read_text(encoding="utf-8"))
    assert wall == 11.49
    assert rss == 736000 / 1024


def test_parse_time_v_reads_the_hour_form(tmp_path):
    path = _report(tmp_path, "a.time", "1:02:03.45", 1000)
    wall, _rss = ratchet.parse_time_v(path.read_text(encoding="utf-8"))
    assert wall == (1 * 60 + 2) * 60 + 3.45


def test_parse_time_v_refuses_a_foreign_report():
    """`CLAUDE.md`'s own warning, on this document instead of
    `tests/ci_reference.json`: a probe that assumes a shape a text does
    not have must not return a misleading zero."""
    try:
        ratchet.parse_time_v("not a time report at all")
    except ValueError:
        return
    raise AssertionError("a non-report text must raise, not read as 0")


def test_measured_takes_the_worse_axis_independently(tmp_path):
    """`bga analyze` and `bga view --export` are two separate cold
    paths into the analyzer; a regression reachable through either one
    must be caught by the single reading this writes."""
    slow_wall = _report(tmp_path, "analyze.time", "0:20.00", 100000)
    slow_rss = _report(tmp_path, "export.time", "0:05.00", 900000)
    readings = ratchet.measured([slow_wall, slow_rss])
    assert readings["analyze_wall_s"] == 20.0
    assert readings["analyze_rss_mb"] == round(900000 / 1024, 1)


class TestTheMarginIsAbsoluteNotARatio:
    """`UX-420`'s Motivation, on this gate's own two numbers."""

    def test_a_huge_ratio_under_the_margin_is_not_over(self):
        # 0.02s -> 0.09s is x4.5, and 0.07s added - nowhere near 5s.
        wall_over, _rss = ratchet.exceeded(
            {"analyze_wall_s": 0.09, "analyze_rss_mb": 600.0},
            {"analyze_wall_s": 0.02, "analyze_rss_mb": 600.0})
        assert wall_over is False

    def test_a_tiny_ratio_over_the_margin_is_over(self):
        # x1.02 on 300s is a ratio nobody would flag; 6s is real.
        wall_over, _rss = ratchet.exceeded(
            {"analyze_wall_s": 306.0, "analyze_rss_mb": 600.0},
            {"analyze_wall_s": 300.0, "analyze_rss_mb": 600.0})
        assert wall_over is True

    def test_rss_margin_is_megabytes_not_a_fraction(self):
        _wall, rss_over = ratchet.exceeded(
            {"analyze_wall_s": 10.0, "analyze_rss_mb": 10100.0},
            {"analyze_wall_s": 10.0, "analyze_rss_mb": 10000.0})
        assert rss_over is True   # +100 MB clears the 50 MB margin
        _wall, rss_over = ratchet.exceeded(
            {"analyze_wall_s": 10.0, "analyze_rss_mb": 620.0},
            {"analyze_wall_s": 10.0, "analyze_rss_mb": 600.0})
        assert rss_over is False  # +20 MB does not


def test_an_unrecorded_axis_reports_nothing():
    """`UX-503`'s shape, on a scalar: the run that meets a key the
    reference does not carry yet has nothing to be slower than."""
    wall_over, rss_over = ratchet.exceeded(
        {"analyze_wall_s": 50.0, "analyze_rss_mb": 5000.0}, {})
    assert wall_over is None and rss_over is None


def test_one_axis_can_be_bootstrapped_while_the_other_is_not():
    wall_over, rss_over = ratchet.exceeded(
        {"analyze_wall_s": 50.0, "analyze_rss_mb": 5000.0},
        {"analyze_wall_s": 10.0})
    assert wall_over is True
    assert rss_over is None


class TestTwoConsecutiveRunsAreRequired:
    """`UX-442`'s lesson: a single excursion does not repeat."""

    def test_one_sample_alone_confirms_nothing(self):
        wall, rss = ratchet.confirmed(True, True, {})
        assert (wall, rss) == (False, False)

    def test_agreement_on_both_runs_confirms(self):
        wall, rss = ratchet.confirmed(True, False, {"wall": True, "rss": True})
        assert (wall, rss) == (True, False)

    def test_this_run_recovering_does_not_confirm(self):
        """The run before it excursed; this run did not - so the
        excursion did not repeat, whatever the carry says."""
        wall, rss = ratchet.confirmed(False, False, {"wall": True, "rss": True})
        assert (wall, rss) == (False, False)

    def test_the_run_before_it_not_excursing_does_not_confirm(self):
        """This run excursed; the one before it did not - one sample,
        not two."""
        wall, rss = ratchet.confirmed(True, True, {"wall": False, "rss": False})
        assert (wall, rss) == (False, False)


class TestTheDiffHasToNameTheAnalyzer:
    def test_no_base_reads_as_unknown_not_as_no(self, monkeypatch):
        """A gate that goes quiet on a failed fetch is worse than one
        that reports - `dev_tier_drift.explained_by`'s own choice."""
        assert ratchet.touches_analyzer(None) is None

    def test_the_diff_names_the_analyzer(self, monkeypatch):
        monkeypatch.setattr(dev_touching, "changed_files",
                            lambda base: [ratchet.ANALYZER_FILE])
        monkeypatch.setattr(ratchet.subprocess, "run",
                            lambda *a, **k: type("R", (), {"returncode": 0})())
        assert ratchet.touches_analyzer("HEAD") is True

    def test_the_diff_names_something_else(self, monkeypatch):
        monkeypatch.setattr(dev_touching, "changed_files",
                            lambda base: ["bga/report.py"])
        monkeypatch.setattr(ratchet.subprocess, "run",
                            lambda *a, **k: type("R", (), {"returncode": 0})())
        assert ratchet.touches_analyzer("HEAD") is False


def test_the_reference_carries_the_two_keys_beside_the_files():
    """The Acceptance Test's own shape - the reference document is not
    a flat map (`CLAUDE.md`), so these two scalars sit beside `files`,
    not instead of it."""
    reference = {"files": {"a.py": 1.0}}
    candidate = {"files": {"a.py": 1.0}, "analyze_wall_s": 12.0,
                "analyze_rss_mb": 700.0}
    document, added = drift.adopt(reference, candidate)
    assert document["analyze_wall_s"] == 12.0
    assert document["analyze_rss_mb"] == 700.0
    assert document["files"] == {"a.py": 1.0}
    assert added == {"analyze_wall_s": 12.0, "analyze_rss_mb": 700.0}


def test_adopt_never_rewrites_an_entry_it_already_has():
    """`UX-503`'s add-only rule, on the two new keys: a reference that
    already carries a reading is not silently replaced by whatever a
    run measured."""
    reference = {"files": {"a.py": 1.0}, "analyze_wall_s": 9.0}
    candidate = {"files": {"a.py": 1.0}, "analyze_wall_s": 999.0,
                "analyze_rss_mb": 700.0}
    document, added = drift.adopt(reference, candidate)
    assert document["analyze_wall_s"] == 9.0
    assert document["analyze_rss_mb"] == 700.0
    assert added == {"analyze_rss_mb": 700.0}


def test_the_keys_are_adopted_even_with_no_file_population_to_shift_by():
    """The two scalars have no per-file shift to be divided by, so
    they must not be dropped just because the file population could
    not supply one."""
    document, added = drift.adopt({}, {"analyze_wall_s": 12.0,
                                       "analyze_rss_mb": 700.0})
    assert added == {"analyze_wall_s": 12.0, "analyze_rss_mb": 700.0}
    assert document["analyze_wall_s"] == 12.0


def test_the_workflow_asks_the_ratchet_for_an_annotation():
    """`UX-621`'s route, on this gate too: a job's own API entry carries
    no output field, so a red run needs `--annotate` the same way
    `dev_tier_drift`'s does (`test_a_slow_file_says_which_file.py`'s own
    `test_the_workflow_asks_the_gate_for_one` - kept from reading this
    step by name only, since both tools share the `--against` flag)."""
    steps = [step.get("run") or ""
             for job in yaml.safe_load(
                 WORKFLOW.read_text(encoding="utf-8"))["jobs"].values()
             for step in job.get("steps") or []
             if "dev_perf_ratchet.py" in (step.get("run") or "")
             and "--against" in (step.get("run") or "")]
    assert steps, "no CI step checks the analyzer gate"
    for script in steps:
        assert "--annotate" in script, (
            f"the analyzer gate runs without --annotate: {script!r}")


def _test_job_steps():
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    return jobs["test"]["steps"]


def test_the_ci_steps_are_gated_to_the_3_11_runner():
    """The Required Fix names one CI step on the 3.11 runner - every
    step this feature adds, not only the one invoking the tool by name:
    a fixture-generation step left ungated would run the analyzer's own
    cold path on all four interpreters, four times the cost for the
    same reading (`fixing-guide` §5's "an instrument that runs more
    than it needs to").
    """
    steps = _test_job_steps()
    perf_related = [step for step in steps
                    if "perf_analyze" in (step.get("run") or "")
                    or "perf_export" in (step.get("run") or "")
                    or "dev_perf_ratchet.py" in (step.get("run") or "")]
    assert perf_related, "no CI step in the `test` job touches the fixture"
    for step in perf_related:
        assert step.get("if", "").find("3.11") != -1, (
            f"{step.get('name')!r} is not gated to the 3.11 runner: "
            f"if: {step.get('if')!r}")


def test_the_ratchet_never_runs_inside_make_test():
    """The Required Fix's own words. `make test` never shells out to
    `dev_perf_ratchet.py` or to a live `bga analyze` on the xl fixture -
    the reading is CI's own clock, produced by a `run:` step, not by
    anything pytest collects."""
    for step in _test_job_steps():
        script = step.get("run") or ""
        if "make test" in script:
            assert "dev_perf_ratchet.py" not in script
            assert "perf_analyze" not in script and "perf_export" not in script
