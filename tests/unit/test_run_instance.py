"""UX-95: the report names the run *instance* as well as the run
*identity*.

The identity hash is stable across captures of the same project,
targets and graph - that is its whole job (`UX-07`), and nothing here
changes it. What it means in practice is that two freedesktop-sdk
captures taken 13 hours apart, of different workflow runs and 208
seconds apart in total duration, both print
`Run: f12a845e2327de7a...` and nothing else distinguishes them. With
`UX-81` retaining a per-run ref every week, that directory of
indistinguishable captures is now the normal case.
"""
import json

from bga.analyzer import _run_instance
from bga.ingest.models import AnalysisResult, RunContext
from bga.report.json import format_json
from bga.report.text import _format_instance


def test_the_instance_carries_the_captures_own_clock():
    instance = _run_instance(RunContext(wall_start_us=1787046535857000), '/runs/a')
    assert instance['started_at'] == '2026-08-18 09:48:55 UTC'
    assert instance['started_at_us'] == 1787046535857000
    assert instance['run_dir'] == '/runs/a'


def test_utc_is_stated_rather_than_localised():
    """The field holds a wall clock and the capture was taken on a CI
    runner in a zone this process knows nothing about. Rendering it in
    the reader's local time would be a fiction dressed as precision."""
    instance = _run_instance(RunContext(wall_start_us=1787046535857000), None)
    assert instance['started_at'].endswith(' UTC')


def test_a_zero_wall_start_is_treated_as_absent_not_as_1970():
    """Most fixtures in this suite set `wall_start_us=0`, and no real
    capture starts at the epoch. Printing `1970-01-01` there would put a
    confidently wrong date in every synthetic report."""
    assert _run_instance(RunContext(wall_start_us=0), '/runs/a') == {'run_dir': '/runs/a'}


def test_a_run_that_recorded_no_clock_gets_no_invented_one():
    """Absent, not "unknown": a run directory with no wall clock has no
    capture time, and a placeholder beside a real path reads worse than
    the path alone."""
    instance = _run_instance(RunContext(), '/runs/a')
    assert instance == {'run_dir': '/runs/a'}
    assert _format_instance(instance) == '/runs/a'


def test_a_run_with_nothing_to_say_renders_no_line():
    assert _run_instance(None, None) == {}
    assert _format_instance({}) == ''


def test_the_json_omits_the_key_entirely_rather_than_emitting_an_empty_object():
    """An empty object invites a consumer to render a blank line where
    there is no fact."""
    result = AnalysisResult()
    assert 'run_instance' not in json.loads(format_json(result))
    result.run_instance = {'run_dir': '/runs/a'}
    assert json.loads(format_json(result))['run_instance'] == {'run_dir': '/runs/a'}


def test_the_identity_hash_is_untouched():
    """The fix is additive by construction: `run_id` keeps its meaning
    and its value, because comparability logic reads it and nothing
    about comparability changed."""
    result = AnalysisResult()
    result.run_id = 'f12a845e'
    result.run_instance = {'started_at': '2026-08-18 09:48:55 UTC'}
    data = json.loads(format_json(result))
    assert data['run_id'] == 'f12a845e'
    assert data['run_instance']['started_at'] == '2026-08-18 09:48:55 UTC'
