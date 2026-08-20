"""UX-54: a build that failed must not be scored as if it succeeded.

Measured on a real `freedesktop-sdk` capture taken on a GitHub-hosted
runner whose sandbox could not start: four elements were attempted, all
four **failed**, and the report led with

    Efficiency Score: 1.00 (scheduling is near the certified floor ...)

and never mentioned the failures. Four failed builds are four spans like
any other, and nothing downstream of the log read the terminal status
BuildStream had already printed for each of them.

The information was never missing - `bst_log_to_chrome_trace.py` already
carried `Status: FAILURE` into the chrome trace's End events. It was
dropped at the next hop, and no fixture in this repository contained a
failed task, so nothing could notice.
"""
import argparse

from bga.compare import ComparisonResult
from bga.ingest.models import RunContext
from tools.chrome_trace_to_bga_trace import failed_elements


def _end(element, status):
    return {
        "cat": "bst-builder",
        "ph": "E",
        "ts": 0,
        "args": {"Status": status, "element": element, "action": "build"},
    }


# --- the producer: reading the status the log already stated -----------


def test_a_failed_element_is_reported():
    assert failed_elements([_end("core.bst", "FAILURE")]) == ["core.bst"]


def test_successful_and_cached_elements_are_not():
    events = [
        _end("a.bst", "SUCCESS"),
        _end("b.bst", "CACHED"),
        _end("c.bst", "SKIPPED"),
    ]

    assert failed_elements(events) == []


def test_the_four_real_failures_are_all_named():
    """The real capture: four attempted, four failed."""
    events = [
        _end("components/openssl.bst", "FAILURE"),
        _end("components/which.bst", "FAILURE"),
        _end("components/ninja.bst", "FAILURE"),
        _end("components/_private/python3-flit-core.bst", "FAILURE"),
    ]

    assert failed_elements(events) == [
        "components/_private/python3-flit-core.bst",
        "components/ninja.bst",
        "components/openssl.bst",
        "components/which.bst",
    ]


def test_the_invocation_wrapper_is_not_an_element():
    """BuildStream's own top-level bracket is `cat: bst-invocation` and
    carries no element - it must not become a phantom failure."""
    events = [{"cat": "bst-invocation", "ph": "E", "ts": 0, "args": {"Status": "FAILURE"}}]

    assert failed_elements(events) == []


def test_one_element_failing_twice_is_named_once():
    events = [_end("core.bst", "FAILURE"), _end("core.bst", "FAILURE")]

    assert failed_elements(events) == ["core.bst"]


# --- the model: absent is "unknown", not "succeeded" --------------------


def test_absent_build_outcome_reports_no_failures_but_stays_distinguishable():
    """Every capture taken before this field existed omits it. Those runs
    must not be presented as known-good on that basis, so the raw field
    stays `None` while the convenience accessor is empty."""
    context = RunContext()

    assert context.failed_elements == []
    assert context.build_outcome is None


def test_a_recorded_clean_build_is_distinguishable_from_an_unrecorded_one():
    context = RunContext(build_outcome={"failed_elements": [], "failed_count": 0})

    assert context.failed_elements == []
    assert context.build_outcome is not None


def test_recorded_failures_are_read_back():
    context = RunContext(
        build_outcome={"failed_elements": ["core.bst"], "failed_count": 1}
    )

    assert context.failed_elements == ["core.bst"]


# --- the gate: a failed build fails closed ------------------------------


def _comparison(**kwargs):
    defaults = dict(
        baseline_run_id="b", candidate_run_id="c",
        baseline_metrics={}, candidate_metrics={}, deltas={},
        baseline_confidence=1.0, candidate_confidence=1.0,
        attribution_deltas={}, verdict="no significant change",
        low_confidence=False,
    )
    defaults.update(kwargs)
    return ComparisonResult(**defaults)


def _args(**kwargs):
    defaults = dict(fail_on_regression=True, fail_on_efficiency_regression=False,
                    min_efficiency=None, fail_on_low_confidence=False,
                    regression_threshold=None)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_a_failed_candidate_fails_the_gate():
    """UX-156 changed the code from 4 to 6, deliberately.

    `UX-54` made this fail *closed*, which was right, and that is
    unchanged. What it borrowed was 4 - "your build got slower" - to say
    "your build did not finish". Those are different findings for
    different people: a pipeline blocks on 4 and investigates 6, and 6
    (`EXIT_CODE_MISMATCHED_RUNS`) already means "these runs were not
    comparable", which is exactly the case here.
    """
    from bga.cli import EXIT_CODE_MISMATCHED_RUNS, _compare_exit_code

    comparison = _comparison(failed_runs=["candidate"])

    assert _compare_exit_code(_args(), comparison) == EXIT_CODE_MISMATCHED_RUNS


def test_a_failed_run_fails_closed_even_at_low_confidence():
    """The ordering that matters. Low confidence fails *open* by design
    (UX-40), and the real failed capture scored 0.14 - so had the failure
    check come second, the gate would have reported green on a build that
    did not complete."""
    from bga.cli import EXIT_CODE_MISMATCHED_RUNS, _compare_exit_code

    comparison = _comparison(failed_runs=["candidate"], low_confidence=True)

    # Still closed, still ordered ahead of the low-confidence fail-open.
    # Only the code changed, in UX-156 - see the test above.
    assert _compare_exit_code(_args(), comparison) == EXIT_CODE_MISMATCHED_RUNS


def test_no_failures_leaves_the_existing_gate_behaviour_alone():
    from bga.cli import _compare_exit_code

    assert _compare_exit_code(_args(), _comparison()) == 0


def test_the_gate_stays_off_when_no_gating_flag_was_passed():
    """`bga compare` without a gate flag always exits 0 - a failed build
    does not change that, because the user did not ask for a gate."""
    from bga.cli import _compare_exit_code

    comparison = _comparison(failed_runs=["candidate"])
    args = _args(fail_on_regression=False)

    assert _compare_exit_code(args, comparison) == 0


def test_failed_runs_appear_in_the_serialized_comparison():
    assert _comparison(failed_runs=["baseline"]).to_dict()["failed_runs"] == ["baseline"]
