"""UX-55: the two CI scenarios, and why a cached element is not a gap.

`bga` has to serve two clearly different CI shapes:

- a **nightly with caches off**, where every element builds and every
  signal is about the whole project;
- a **pre-commit run with caches on**, where BuildStream skips whatever
  it has already built and the analysis is only about the few elements
  that rebuilt.

Before this, the second was judged as a broken version of the first: a
cached critical-path element read as "no matching task found - genuine
coverage gap, worth investigating", which failed the
`critical_path_coverage_full` hard gate, which dropped confidence, which
made `UX-03`/`UX-39`'s regression gate fail *open*. The better the cache
worked - the entire point of BuildStream - the less `bga` gated.

Measured on the real `freedesktop-sdk` capture (25 built, 65 skipped,
126 elements): confidence 0.82 with a failed hard gate, before; 1.00 with
none, after.
"""
import pytest

from bga.ingest.models import RunContext


def _context(processed=None, skipped=None, failed=(), **kwargs):
    queue_summary = None
    if processed is not None:
        queue_summary = {
            "build": {"processed": processed, "skipped": skipped, "failed": 0}
        }
    return RunContext(
        queue_summary=queue_summary,
        build_outcome={"failed_elements": list(failed), "failed_count": len(failed)},
        **kwargs,
    )


# --- classifying the run ------------------------------------------------


def test_a_caches_off_nightly_is_a_full_run():
    assert _context(processed=126, skipped=0).run_mode == "full"


def test_a_pre_commit_run_with_caches_on_is_incremental():
    """The real capture's own numbers."""
    context = _context(processed=25, skipped=65)

    assert context.run_mode == "incremental"
    assert context.built_element_count == 25
    assert context.cached_element_count == 65


def test_a_capture_that_does_not_say_is_unknown_not_full():
    """Every capture predating this field omits the summary. Guessing
    `full` would silently re-introduce the defect; guessing `incremental`
    would weaken the gate for real full builds."""
    context = RunContext()

    assert context.run_mode == "unknown"
    assert context.built_element_count is None
    assert context.cached_element_count is None


# --- the coverage gate --------------------------------------------------


def _coverage(context, critical_path, elements_with_tasks):
    """Drive the real gate through `compute_confidence`."""
    from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
    from bga.validation.invariants import compute_confidence

    tasks = [
        NormalizedTask(
            task_key=TaskKey(element_uid=uid, task_kind=TaskKind.BUILD, phase="EXECUTION"),
            ready_us=0, start_us=0, finish_us=1_000_000,
        )
        for uid in elements_with_tasks
    ]
    confidence, violations = compute_confidence(
        normalized_tasks=tasks,
        run_context=context,
        trace=None,
        graph=None,
        violations=[],
        attribution_segments=[],
        graph_analysis={"critical_path": critical_path, "dominators": {}},
        attribution={},
        floors={},
    )
    return confidence, violations


CHAIN = ["a.bst", "cached.bst", "c.bst"]


def test_a_cached_critical_path_element_is_not_a_coverage_gap():
    confidence, violations = _coverage(
        _context(processed=2, skipped=1), CHAIN, ["a.bst", "c.bst"]
    )

    assert confidence["critical_path_coverage"] == 1.0
    assert confidence["hard_gates"]["critical_path_coverage_full"] is True
    assert confidence["critical_path_cached"] == ["cached.bst"]
    assert not [v for v in violations if v.get("gate") == "critical_path_coverage"]


def test_a_full_run_still_fails_on_a_missing_element():
    """The caches-off nightly keeps today's behaviour exactly: nothing
    was skipped, so an element with no task really is a lost
    measurement."""
    confidence, violations = _coverage(
        _context(processed=3, skipped=0), CHAIN, ["a.bst", "c.bst"]
    )

    assert confidence["critical_path_coverage"] == pytest.approx(2 / 3)
    assert confidence["hard_gates"]["critical_path_coverage_full"] is False
    assert [v for v in violations if v.get("gate") == "critical_path_coverage"]


def test_a_capture_without_a_summary_keeps_the_old_behaviour():
    confidence, _ = _coverage(RunContext(), CHAIN, ["a.bst", "c.bst"])

    assert confidence["critical_path_coverage"] == pytest.approx(2 / 3)
    assert confidence["run_mode"] == "unknown"


def test_a_failed_build_is_never_given_the_benefit_of_the_doubt():
    """A failed build's missing tasks may genuinely be lost, so absence
    must not be read as 'cached' there (UX-54 supplies the signal)."""
    confidence, _ = _coverage(
        _context(processed=2, skipped=1, failed=["x.bst"]), CHAIN, ["a.bst", "c.bst"]
    )

    assert confidence["critical_path_coverage"] == pytest.approx(2 / 3)
    assert confidence["critical_path_cached"] == []


def test_a_count_mismatch_is_never_given_the_benefit_of_the_doubt():
    """The checksum: BuildStream said it processed 3 elements but only 2
    produced tasks, so something really was lost in extraction and the
    gate must still fire."""
    confidence, _ = _coverage(
        _context(processed=3, skipped=1), CHAIN, ["a.bst", "c.bst"]
    )

    assert confidence["critical_path_coverage"] == pytest.approx(2 / 3)
    assert confidence["critical_path_cached"] == []


def test_an_entirely_cached_critical_path_is_not_a_failure():
    """A pre-commit run that rebuilt nothing on the chain measured
    nothing on it - which is a fact about the run, not a gap."""
    confidence, _ = _coverage(_context(processed=0, skipped=3), CHAIN, [])

    assert confidence["critical_path_coverage"] == 1.0
    assert confidence["critical_path_cached"] == CHAIN


# --- comparing across the two scenarios ---------------------------------


class _Result:
    def __init__(self, mode):
        self.confidence = {"run_mode": mode} if mode else {}


def test_a_nightly_and_a_pre_commit_run_are_flagged_as_incomparable():
    from bga.compare import _check_run_modes

    warning = _check_run_modes(_Result("full"), _Result("incremental"))

    assert warning is not None
    assert "full" in warning and "incremental" in warning


def test_two_runs_of_the_same_kind_are_not_flagged():
    from bga.compare import _check_run_modes

    assert _check_run_modes(_Result("incremental"), _Result("incremental")) is None
    assert _check_run_modes(_Result("full"), _Result("full")) is None


def test_an_unknown_mode_is_not_flagged():
    """Warning on every capture predating this field would train the
    reader to ignore the field."""
    from bga.compare import _check_run_modes

    assert _check_run_modes(_Result("unknown"), _Result("full")) is None
    assert _check_run_modes(_Result(None), _Result("full")) is None


# --- the producer -------------------------------------------------------


def test_the_real_pipeline_summary_lines_parse():
    """Verbatim from the real freedesktop-sdk log, trailing whitespace
    and uneven spacing included."""
    from tools.bst_log_to_chrome_trace import WrapperTraceConverter

    converter = WrapperTraceConverter()
    converter._check_header_lines("    Fetch Queue: processed 0,  skipped 90, failed 0 ")
    converter._check_header_lines("    Build Queue: processed 25, skipped 65, failed 0 ")

    assert converter.queue_summary == {
        "fetch": {"processed": 0, "skipped": 90, "failed": 0},
        "build": {"processed": 25, "skipped": 65, "failed": 0},
    }


def test_a_log_without_a_summary_records_nothing():
    from tools.bst_log_to_chrome_trace import WrapperTraceConverter

    converter = WrapperTraceConverter()
    converter._check_header_lines("Targets:       all.bst")

    assert converter.queue_summary == {}
