"""UX-83: the two planes gave contradictory advice on the same run.

Measured on one dual-plane capture of `examples/06`'s macro-fixed
variant, 4-core host:

- `bga analyze`: *"31.9% of wall-clock time is RESOURCE WAIT — try
  `--capacity N` with a higher N"*;
- `bga sweep`: *"Knee point (PROCESS): capacity 5"*, on a host whose four
  cores were already runnable at 16 potential compiler processes;
- `bga correlate`, **same capture**: `core.bst` *"runs at only 0.90 cores
  busy … asked for -j1: remove `notparallel`"* — the actual fix, worth
  −32.4% and costing no extra capacity.

The capacity axis being unmodeled is a known gap (`UX-09`). What was new
is that when the missing information is present in the same capture, the
Plane 1 advice did not consult it.
"""
from bga.correlate import summarize_plane2_capacity
from bga.findings import compute_findings, findings_by_id
from bga.ingest.models import AnalysisResult
from bga.report.text import _plane2_knee_caveat


def _resource_wait_result(plane2_capacity=None):
    return AnalysisResult(
        attribution={
            'execution_on_chain_us': 68_000_000,
            'resource_wait_us': 32_000_000,
        },
        floors={'t_infinity_observed': 50_000_000, 'efficiency_score': 0.8},
        total_duration_us=100_000_000,
        confidence={'primary': 1.0},
        signals={'critical_path': [], 'critical_path_detail': []},
        plane2_capacity=plane2_capacity or {},
    )


def _hint(result):
    return findings_by_id(compute_findings(result))['wait-category']['evidence']['hint']


# --- the summary Plane 2 supplies --------------------------------------


def test_the_summary_reports_measured_cores_busy_against_the_host():
    native = {
        'wall_span_s': 100.0,
        'cpu_time': {'per_element': {'a.bst': {'cpu_us': 325_000_000}}},
        'per_element_parallelism': [],
    }

    summary = summarize_plane2_capacity(native, host_cpu_count=4)

    assert round(summary['cores_busy'], 2) == 3.25
    assert summary['saturated'] is True


def test_an_unsaturated_host_is_not_reported_as_saturated():
    native = {
        'wall_span_s': 100.0,
        'cpu_time': {'per_element': {'a.bst': {'cpu_us': 100_000_000}}},
        'per_element_parallelism': [],
    }

    assert summarize_plane2_capacity(native, host_cpu_count=4)['saturated'] is False


def test_a_pinned_element_is_named():
    native = {
        'wall_span_s': 10.0,
        'cpu_time': {'per_element': {}},
        'per_element_parallelism': [
            {'element': 'core.bst', 'findings': ['pinned_to_one_job']},
            {'element': 'lib-a.bst', 'findings': []},
        ],
    }

    assert summarize_plane2_capacity(native, 4)['pinned_elements'] == ['core.bst']


def test_plane_2_that_cannot_answer_leaves_everything_unset():
    assert summarize_plane2_capacity({}, None) == {
        'cores_busy': None, 'host_cpu_count': None,
        'saturated': False, 'pinned_elements': [],
    }


# --- what it changes ----------------------------------------------------


def test_without_plane_2_the_hint_is_unchanged():
    """`UX-83`'s own Out of Scope: no change when only Plane 1 exists."""
    hint = _hint(_resource_wait_result())

    assert 'a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated' in hint
    assert 'UX-83' not in hint
    assert 'do NOT raise capacity' not in hint


def test_a_saturated_host_is_told_not_to_raise_capacity():
    hint = _hint(_resource_wait_result({
        'cores_busy': 3.9, 'host_cpu_count': 4, 'saturated': True,
        'pinned_elements': [],
    }))

    assert 'do NOT raise capacity' in hint
    assert '3.90 of 4 cores busy' in hint


def test_a_pinned_element_is_named_before_anything_about_capacity():
    """Intra-element parallelism is free capacity that `--builders` is
    not, so it goes first."""
    hint = _hint(_resource_wait_result({
        'cores_busy': 3.9, 'host_cpu_count': 4, 'saturated': True,
        'pinned_elements': ['core.bst'],
    }))

    assert hint.index('core.bst') < hint.index('capacity you already have')
    assert 'remove `notparallel`' in hint


def test_only_the_resource_wait_hint_is_conditioned():
    """Every other category keeps today's text: Plane 2 says nothing
    about whether a dependency wait is real."""
    result = _resource_wait_result({
        'cores_busy': 3.9, 'host_cpu_count': 4, 'saturated': True,
        'pinned_elements': ['core.bst'],
    })
    result.attribution = {
        'execution_on_chain_us': 68_000_000, 'dependency_wait_us': 32_000_000,
    }

    assert 'core.bst' not in _hint(result)


# --- and the sweep's knee line -----------------------------------------


def test_the_knee_line_is_annotated_with_what_was_measured():
    lines = _plane2_knee_caveat(
        {'cores_busy': 3.25, 'host_cpu_count': 4, 'saturated': True,
         'pinned_elements': ['core.bst']},
        knee=5,
    )
    text = "\n".join(lines)

    assert '3.25 of 4 cores busy' in text
    assert 'adds contention, not throughput' in text
    assert 'core.bst' in text


def test_the_knee_line_is_untouched_without_plane_2():
    assert _plane2_knee_caveat(None, knee=5) == []
    assert _plane2_knee_caveat({'cores_busy': None}, knee=5) == []
