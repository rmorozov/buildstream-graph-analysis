"""Tests for tools/bst_checkout_cost.py - a deliberately standalone tool
(not part of bga's core analyze pipeline - see its own module docstring
and docs/backlog/tasks/P4-15-stack-consolidation-heuristic.md) that reports real,
measured cost from `bst source checkout`/`bst artifact checkout` logs,
individually or compared against a consolidated (e.g. `kind: stack`)
checkout.

Real-world grounding (see the task file's Verification Log): checking
out a large `stack` element is *not* automatically cheaper - a real
1500-element project measurement showed a stack pulling in the whole
project's closure costs *more* pipeline overhead than 5 narrow individual
checkouts, while a same-closure stack (5 elements) showed no measurable
difference from 5 individual checkouts at this precision. The synthetic
logs here use explicit nonzero elapsed values specifically to pin down
the arithmetic in a case where the mechanism (N pipeline-overhead
payments vs. 1) actually is the dominant cost - real logs alone can't
exercise this deterministically given BuildStream's 1-second elapsed
precision without --verbose.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ._bst_env import isolated_bst_env

from tools.bst_checkout_cost import compare, summarize

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"
BST_AVAILABLE = shutil.which("bst") is not None

# Two individual-element checkout logs (same shape, same real elapsed
# costs) - each pays its own "Loading elements"/"Query cache" pipeline
# overhead (1s + 1s = 2s) plus its own two-phase checkout cost (1s + 1s
# = 2s) - 4s each, 8s combined.
# START lines show "--:--:--" (real BuildStream behavior - elapsed isn't
# known yet when an activity starts, and resets per-activity, not
# globally; see UX-06/docs/backlog/scenarios/UX-06-raw-log-timestamp-corruption.md)
# - only each terminal line's own elapsed is real, applied on top of the
# time in effect when *that* activity's own START was seen.
LOG_A = """\
[--:--:--][        ][    main:core activity   ] START   Loading elements
[00:00:01][        ][    main:core activity   ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity   ] START   Query cache
[00:00:01][        ][    main:core activity   ] SUCCESS Query cache
[--:--:--][aaaa1111][    main:elemA.bst        ] START   Staging dependencies
[00:00:01][aaaa1111][    main:elemA.bst        ] SUCCESS Staging dependencies
[--:--:--][aaaa1111][    main:elemA.bst        ] START   Checking out files in '/outA'
[00:00:01][aaaa1111][    main:elemA.bst        ] SUCCESS Checking out files in '/outA'
"""
LOG_B = """\
[--:--:--][        ][    main:core activity   ] START   Loading elements
[00:00:01][        ][    main:core activity   ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity   ] START   Query cache
[00:00:01][        ][    main:core activity   ] SUCCESS Query cache
[--:--:--][bbbb2222][    main:elemB.bst        ] START   Staging dependencies
[00:00:01][bbbb2222][    main:elemB.bst        ] SUCCESS Staging dependencies
[--:--:--][bbbb2222][    main:elemB.bst        ] START   Checking out files in '/outB'
[00:00:01][bbbb2222][    main:elemB.bst        ] SUCCESS Checking out files in '/outB'
"""
# One stack checkout covering both A and B - pipeline overhead paid
# once (2s), plus the stack's own two-phase checkout cost (2s) - 4s
# total vs. the 8s the two individual checkouts paid combined.
LOG_STACK = """\
[--:--:--][        ][    main:core activity   ] START   Loading elements
[00:00:01][        ][    main:core activity   ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity   ] START   Query cache
[00:00:01][        ][    main:core activity   ] SUCCESS Query cache
[--:--:--][cccc3333][    main:stack.bst        ] START   Staging dependencies
[00:00:01][cccc3333][    main:stack.bst        ] SUCCESS Staging dependencies
[--:--:--][cccc3333][    main:stack.bst        ] START   Checking out files in '/outStack'
[00:00:01][cccc3333][    main:stack.bst        ] SUCCESS Checking out files in '/outStack'
"""


def _write_log(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def test_summarize_extracts_pipeline_overhead_and_element_cost(tmp_path):
    log = _write_log(tmp_path, "a.log", LOG_A)
    result = summarize(log)

    assert result["pipeline_overhead_us"] == 2_000_000
    assert result["elements"] == {"elemA.bst": 2_000_000}
    assert result["elements_total_us"] == 2_000_000


def test_compare_matched_closure_shows_real_savings(tmp_path):
    log_a = _write_log(tmp_path, "a.log", LOG_A)
    log_b = _write_log(tmp_path, "b.log", LOG_B)
    log_stack = _write_log(tmp_path, "stack.log", LOG_STACK)

    result = compare([log_a, log_b], log_stack)

    assert result["individual"]["invocation_count"] == 2
    assert result["individual"]["pipeline_overhead_us"] == 4_000_000  # 2s x 2 invocations
    assert result["individual"]["elements_total_us"] == 4_000_000
    assert result["individual"]["total_us"] == 8_000_000

    assert result["consolidated"]["pipeline_overhead_us"] == 2_000_000  # paid once
    assert result["consolidated_total_us"] == 4_000_000

    assert result["savings_us"] == 4_000_000
    assert result["savings_fraction_of_individual"] == 0.5


def test_compare_reports_negative_savings_honestly(tmp_path):
    """Regression for the real 1500-element finding (see the task file's
    Verification Log): a consolidated target with a *larger* resolved
    closure than the individual invocations combined must report a real
    negative "savings" - never silently clamp to zero or hide the loss."""
    log_a = _write_log(tmp_path, "a.log", LOG_A)
    # A "consolidated" checkout whose own pipeline overhead alone (10s)
    # dwarfs what the single individual invocation paid (2s pipeline +
    # 2s element = 4s total) - a stand-in for "the stack pulls in a much
    # bigger closure than what was actually needed."
    expensive_consolidated = """\
[--:--:--][        ][    main:core activity   ] START   Loading elements
[00:00:04][        ][    main:core activity   ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity   ] START   Query cache
[00:00:06][        ][    main:core activity   ] SUCCESS Query cache
[--:--:--][dddd4444][    main:big.bst          ] START   Checking out files in '/outBig'
[00:00:00][dddd4444][    main:big.bst          ] SUCCESS Checking out files in '/outBig'
"""
    log_big = _write_log(tmp_path, "big.log", expensive_consolidated)

    result = compare([log_a], log_big)

    assert result["individual"]["total_us"] == 4_000_000
    assert result["consolidated_total_us"] == 10_000_000
    assert result["savings_us"] == -6_000_000
    assert result["savings_fraction_of_individual"] == -1.5


def test_compare_json_round_trips(tmp_path):
    log_a = _write_log(tmp_path, "a.log", LOG_A)
    log_b = _write_log(tmp_path, "b.log", LOG_B)
    log_stack = _write_log(tmp_path, "stack.log", LOG_STACK)

    result = compare([log_a, log_b], log_stack)
    # Everything in the result must be plain JSON-serializable data -
    # this is the tool's actual --json output path.
    reparsed = json.loads(json.dumps(result))
    assert reparsed["savings_us"] == 4_000_000


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
def test_real_end_to_end_against_a_real_build_and_checkouts(tmp_path):
    """Real `bst build` + two individual `bst artifact checkout`s + one
    `kind: stack` checkout (tests/fixtures/bst_show_project/elements/all.bst,
    added for this test) against a real BuildStream install. Asserts
    structure, not a particular savings sign - real timing at this
    trivial fixture scale is unpredictable (see the task file's
    Verification Log for the real, meaningful large-project numbers)."""
    env = isolated_bst_env(tmp_path)
    subprocess.run(
        ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "all.bst"],
        capture_output=True, text=True, env=env, check=True,
    )

    def _checkout(target, out_name):
        log_path = tmp_path / f"{out_name}.log"
        proc = subprocess.run(
            ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "artifact", "checkout",
             target, "--directory", str(tmp_path / out_name)],
            capture_output=True, text=True, env=env,
        )
        log_path.write_text(proc.stdout + proc.stderr)
        return str(log_path)

    log_base = _checkout("base.bst", "out_base")
    log_base2 = _checkout("base2.bst", "out_base2")
    log_stack = _checkout("all.bst", "out_all")

    stack_summary = summarize(log_stack)
    assert stack_summary["elements"] == {"all.bst": stack_summary["elements"]["all.bst"]}
    assert set(stack_summary["elements"]) == {"all.bst"}

    result = compare([log_base, log_base2], log_stack)
    assert result["individual"]["invocation_count"] == 2
    assert isinstance(result["savings_us"], int)
