"""
The CPU floor (UX-891): total_cpu_us // governing_cores, published
beside Part 16's LB and never folded into it. Every floor in Part 16
divides work by a *builder slot* count (capacity.py), so LB certifies
against the scheduler's width and never against the machine's. The CPU
the same capture measured is published a few sections further down the
same report and was joined to nothing.

Absent, never zero, without Plane 2 or without a governing core count -
`lb` and every other Part 16 term is untouched either way.
"""
from typing import Optional

# What this floor leans on, printed with the number the way
# bga/capacity_model.py's own ASSUMPTIONS are. A floor whose
# assumptions reach only the task file is a floor a reader takes.
ASSUMPTIONS = {
    "cpu_work_conserved":
        "The measured CPU work is assumed conserved under a different "
        "schedule - the same build rescheduled is assumed to cost the "
        "same CPU microseconds, not fewer.",
    "coverage_as_published":
        "The coverage share is published, not corrected for: the "
        "unmeasured processes' CPU is missing from the total, so the "
        "floor is a floor on the measured share.",
    "cores_are_the_whole_machine":
        "The governing cores are the whole machine (or the whole "
        "declared budget). A co-tenant on the same box is not "
        "modelled.",
}


# The same two sources under the names `_check_process_oversubscription`
# published before this module existed, which its violation rows and the
# capacity-model note both read. One derivation, two vocabularies - not
# two derivations.
CAPACITY_SOURCE = {
    'cpu_budget': 'declared_cpu_budget',
    'host_cpu_count': 'detected_host_cpu_count',
}


def governing_cores(run_context) -> tuple[Optional[int], str]:
    """The core count a CPU claim is divided by, and where it came from.

    A declared `cpu_budget` wins over the detected `host_cpu_count`:
    the operator's own ceiling is the one they asked to be held to.
    `is None` rather than truthiness - a declared 0 is real data
    (UX-16), not a missing value.

    Shared with the analyzer's `_check_process_oversubscription`, which
    wrote this same pair (UX-891's Required Fix asks for the term to be
    reused rather than recomputed).
    """
    if run_context is None:
        return None, "host_cpu_count"
    cpu_budget = getattr(run_context, 'cpu_budget', None)
    if cpu_budget is not None:
        return cpu_budget, 'cpu_budget'
    return getattr(run_context, 'host_cpu_count', None), 'host_cpu_count'


def compute_cpu_floor(
    native_report: Optional[dict], run_context, lb: Optional[int] = None,
) -> dict:
    """`total_cpu_us // governing_cores`, with its coverage and its divisor.

    Returns the keys to merge into `floors`, or `{}` when the run has no
    Plane 2 report or no governing core count - absence is the answer
    there, because a zero-microsecond floor reads as a measurement.

    `total_cpu_us` of 0 is *not* that case: it is a measured zero, so
    the floor is 0 and present.
    """
    cpu_time = (native_report or {}).get('cpu_time') or {}
    total_cpu_us = cpu_time.get('total_cpu_us')
    if total_cpu_us is None:
        return {}
    cores, cores_source = governing_cores(run_context)
    if not cores or cores <= 0:
        return {}

    measured = cpu_time.get('measured_processes') or 0
    unmeasured = cpu_time.get('unmeasured_processes') or 0
    seen = measured + unmeasured

    lb_cpu_us = int(total_cpu_us) // cores
    return {
        'lb_cpu_us': lb_cpu_us,
        'lb_cpu_coverage': (measured / seen) if seen else None,
        'lb_cpu_governing_cores': cores,
        'lb_cpu_cores_source': cores_source,
        'lb_cpu_binds': (lb_cpu_us > lb) if lb is not None else None,
    }
