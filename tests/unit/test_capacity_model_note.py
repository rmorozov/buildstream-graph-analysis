"""Tests for UX-13: `LB`/`Efficiency Score` are correctly computed per
spec Part 16, but only ever certify against a run's *recorded* resource
capacities (builders/fetchers/pushers) - not real host CPU cores. Before
this fix, the Certified Floors report block (text and JSON alike) never
said so - a reader had no way to know from the report itself that a high
Efficiency Score doesn't rule out real, unmodeled CPU contention (see
UX-09's own real evidence this can matter).

docs/backlog/scenarios/UX-0013-lb-report-conflates-scheduling-and-cpu-capacity.md's
own acceptance test requires this in both `--format text` and
`--format json` output - `AnalysisResult.floors['capacity_model_note']`
is the single source of truth both formatters read from.
"""
import json

from bga import BuildEfficiencyAnalyzer
from bga.report.json import format_json
from bga.report.text import format_text


def _write_run_dir(tmp_path, name, run_context):
    run_dir = tmp_path / name
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": "a.bst", "requested_target": True}],
        "dependencies": [],
    }
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 1000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyze(tmp_path, name, builders=4, native_max_jobs=None, host_cpu_count=None):
    run_context = {"trace_epsilon_us": 100, "resource_capacities": {"PROCESS": builders}}
    if native_max_jobs is not None:
        run_context["native_max_jobs"] = native_max_jobs
    if host_cpu_count is not None:
        run_context["host_cpu_count"] = host_cpu_count
    run_dir = _write_run_dir(tmp_path, name, run_context)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_generic_note_present_when_ux12_fields_are_unavailable(tmp_path):
    """The common case today - most run-context.json files predate UX-12
    and have neither native_max_jobs nor host_cpu_count. Must still get a
    real caveat, not silence."""
    result = _analyze(tmp_path, "run")
    note = result.floors.get("capacity_model_note")
    assert note
    assert "recorded resource capacities" in note
    assert "not real host CPU cores" in note


def test_note_is_enriched_with_real_numbers_when_oversubscribed(tmp_path):
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)
    note = result.floors.get("capacity_model_note")
    assert "real resource oversubscription" in note
    assert "builders=8" in note
    assert "native max-jobs=8" in note
    assert "4-core host" in note


def test_note_stays_generic_when_not_oversubscribed(tmp_path):
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=4)
    note = result.floors.get("capacity_model_note")
    assert "real resource oversubscription" not in note
    assert "recorded resource capacities" in note


def test_text_report_certified_floors_block_includes_the_note(tmp_path):
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)
    text = format_text(result)
    assert "Certified Floors:" in text
    assert "Note:" in text
    assert "real resource oversubscription" in text


def test_json_report_floors_section_includes_the_note(tmp_path):
    result = _analyze(tmp_path, "run", builders=8, native_max_jobs=8, host_cpu_count=4)
    data = json.loads(format_json(result))
    assert "capacity_model_note" in data["floors"]
    assert "real resource oversubscription" in data["floors"]["capacity_model_note"]


def test_floors_only_json_section_also_includes_the_note(tmp_path):
    """`bga floors`'s own narrower json output (section='floors') shares
    the same floors dict, not a separately-computed one."""
    result = _analyze(tmp_path, "run", builders=4, native_max_jobs=4, host_cpu_count=4)
    data = json.loads(format_json(result, section="floors"))
    assert "capacity_model_note" in data["floors"]
