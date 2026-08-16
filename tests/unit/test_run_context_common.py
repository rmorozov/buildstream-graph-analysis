"""Tests for tools/_run_context_common.py (UX-18): the shared piece
tools/bst_run_context.py and tools/bst_extract_run.py both call, so the
two producer paths documented in docs/ingestion-pipeline.md can't
silently diverge in their native_max_jobs/host_cpu_count/cpu_budget
(and, UX-21, memory_budget_mb/estimated_job_memory_mb) support again
the way they did before this fix.
"""
from tools._run_context_common import add_cpu_capacity_fields, add_memory_capacity_fields, host_cpu_count


def test_host_cpu_count_returns_a_positive_int():
    count = host_cpu_count()
    assert isinstance(count, int)
    assert count > 0


def test_add_cpu_capacity_fields_adds_all_three_when_given():
    run_context = {}
    add_cpu_capacity_fields(run_context, native_max_jobs=4, cpu_budget=6)

    assert run_context["native_max_jobs"] == 4
    assert run_context["cpu_budget"] == 6
    assert isinstance(run_context["host_cpu_count"], int)


def test_add_cpu_capacity_fields_omits_optional_fields_when_not_given():
    """native_max_jobs/cpu_budget are purely operator-supplied - must be
    omitted, not defaulted to a guessed value, when absent. host_cpu_count
    is always auto-detected regardless."""
    run_context = {}
    add_cpu_capacity_fields(run_context)

    assert "native_max_jobs" not in run_context
    assert "cpu_budget" not in run_context
    assert "host_cpu_count" in run_context


def test_add_cpu_capacity_fields_distinguishes_zero_from_absent():
    """native_max_jobs=0/cpu_budget=0 are real, meaningful values (UX-16:
    BuildStream's own --max-jobs 0 auto sentinel) - must not be treated
    as falsy-and-therefore-omitted."""
    run_context = {}
    add_cpu_capacity_fields(run_context, native_max_jobs=0, cpu_budget=0)

    assert run_context["native_max_jobs"] == 0
    assert run_context["cpu_budget"] == 0


def test_add_memory_capacity_fields_adds_both_when_given():
    run_context = {}
    add_memory_capacity_fields(run_context, memory_budget_mb=8000, estimated_job_memory_mb=1000)

    assert run_context["memory_budget_mb"] == 8000
    assert run_context["estimated_job_memory_mb"] == 1000


def test_add_memory_capacity_fields_omits_both_when_not_given():
    """Unlike host_cpu_count, there is no auto-detection tier here at
    all (UX-21) - both fields must be fully absent, not defaulted."""
    run_context = {}
    add_memory_capacity_fields(run_context)

    assert "memory_budget_mb" not in run_context
    assert "estimated_job_memory_mb" not in run_context


def test_add_memory_capacity_fields_distinguishes_zero_from_absent():
    run_context = {}
    add_memory_capacity_fields(run_context, memory_budget_mb=0, estimated_job_memory_mb=0)

    assert run_context["memory_budget_mb"] == 0
    assert run_context["estimated_job_memory_mb"] == 0
