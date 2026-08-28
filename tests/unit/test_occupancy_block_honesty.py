"""Tests for UX-36: the report rendered task-*occupancy* seconds under a
`CPU Utilisation` heading with an `Effective CPUs` line, on every run
produced by the documented pipeline (none of which carries real CPU
accounting).

Real repro from the doc: the same project built twice - once serialized,
once correctly parallelized - reported `Useful 40.25s` then `Useful
61.45s`. Read as CPU time that says the faster build burned 53% more CPU
for identical source; what actually happened is that tasks which used to
run one after another now overlap, so total slot-occupancy rose.

P1-33 established the honest meaning inside `bga/utilisation/`; it never
reached `bga/report/text.py`. Note the discriminator: UX-17 deliberately
widened `cpu_accounting_available` to mean "some real capacity value is
available" (including a merely *detected* host core count), so
`effective_cpus_source == "measured"` is what actually distinguishes a
real CPU measurement.
"""
from bga.report.text import format_text


class _Result:
    run_id = "t"
    total_duration_us = 27_500_000
    signals = {}
    floors = {}
    attribution = {}
    confidence = {}
    violations = []
    structural = {}
    occupancy = {}
    pipeline_overhead = {}

    def __init__(self, utilisation):
        self.utilisation = utilisation


_BUCKETS = {"useful": 61_450_000, "idle_no_tasks": 48_550_000}


def _detected_host_run():
    """What the documented ingestion pipeline actually produces: a real
    detected core count, no real CPU accounting."""
    return _Result({
        "cpu_accounting_available": True,
        "effective_cpus": 4.0,
        "effective_cpus_source": "detected_host_cpu_count",
        "reconciliation_error_share": 0.0,
        "buckets": dict(_BUCKETS),
    })


def _measured_run():
    return _Result({
        "cpu_accounting_available": True,
        "effective_cpus": 4.0,
        "effective_cpus_source": "measured",
        "reconciliation_error_share": 0.0012,
        "buckets": dict(_BUCKETS),
    })


def test_run_without_real_cpu_accounting_is_not_titled_cpu_utilisation():
    out = format_text(_detected_host_run(), section="utilisation")
    assert "Dispatch Occupancy (no real CPU accounting in this run):" in out
    assert "CPU Utilisation:" not in out


def test_capacity_is_shown_with_its_provenance():
    out = format_text(_detected_host_run(), section="utilisation")
    assert "Capacity: 4.0 (source: detected_host_cpu_count)" in out
    assert "Effective CPUs" not in out


def test_vacuous_reconciliation_error_is_replaced_by_an_honest_statement():
    """`Reconciliation Error: 0.00%` implied something was reconciled.
    I9 reconciliation needs a real CPU measurement, which this run has
    no source for."""
    out = format_text(_detected_host_run(), section="utilisation")
    assert "Reconciliation: not performed (I9 needs real CPU accounting, absent here)" in out
    assert "Reconciliation Error" not in out


def test_buckets_are_labelled_as_occupancy_even_when_cpu_is_measured():
    """The bucket totals come from each task's real job-slot occupancy
    (`task.dur_us`) in *every* case (P1-33) - real CPU accounting changes
    the capacity/reconciliation numbers, not what the buckets are."""
    for result in (_detected_host_run(), _measured_run()):
        out = format_text(result, section="utilisation")
        assert "task slot-time (occupancy), not CPU time" in out
        # ...and in slot-seconds, which is not the unit the rest of the
        # report prints: 4 builders over a 3261s build have 13044 of them
        # to spend, so an "8626.73s idle" on a bare `s` read as
        # impossible rather than as a different quantity.
        assert "slot-seconds" in out
        assert "slot-s" in out


def test_measured_run_keeps_the_cpu_labels_and_its_reconciliation():
    out = format_text(_measured_run(), section="utilisation")
    assert "CPU Utilisation:" in out
    assert "Effective CPUs: 4.0 (source: measured)" in out
    assert "Reconciliation Error: 0.12%" in out
