"""UX-1005 track C, end to end: `bga analyze` shrinks a BUILD span's
duration by its own recorded admission wait, reading `jobserver_ledger`
off the sibling Plane 2 report before `Analyzer.normalize()` runs
(`bga.cli._resolve_admission_wait`, `bga.cli.analyzed`). Real fixture
data (`macro_micro`), not hand-built spans, so the wiring is proven on
the actual pipeline entry a user reaches through `bga analyze`."""
import json
import shutil

from bga.cli import analyzed, create_parser

FIXTURE_RUN = "tests/fixtures/macro_micro/run"
FIXTURE_PLANE2 = "tests/fixtures/macro_micro/plane2.json"


def _codegen_build(result):
    for task in result.normalized_tasks:
        if task.task_key.element_uid == "codegen.bst" and \
                task.task_key.task_kind.value == "BUILD":
            return task
    raise AssertionError("codegen.bst BUILD span not found")


def _analyze(run_dir, plane2_path):
    args = create_parser().parse_args(
        ["analyze", str(run_dir), "--plane2", str(plane2_path), "--format", "json"])
    return analyzed(args)


def test_a_recorded_admission_wait_shortens_the_reported_build_span(tmp_path):
    run_dir = tmp_path / "run"
    shutil.copytree(FIXTURE_RUN, run_dir)
    plane2 = json.loads(open(FIXTURE_PLANE2, encoding="utf-8").read())
    plane2_no_wait = tmp_path / "plane2_no_wait.json"
    plane2_no_wait.write_text(json.dumps(plane2))

    baseline = _analyze(run_dir, plane2_no_wait)
    baseline_build = _codegen_build(baseline)

    plane2_with_wait = dict(plane2)
    plane2_with_wait["jobserver_ledger"] = [
        {"event": "admission_wait", "element": "codegen.bst", "wait_us": 500_000},
    ]
    plane2_wait_path = tmp_path / "plane2_wait.json"
    plane2_wait_path.write_text(json.dumps(plane2_with_wait))

    with_wait = _analyze(run_dir, plane2_wait_path)
    waited_build = _codegen_build(with_wait)

    assert waited_build.finish_us == baseline_build.finish_us, "finish is immutable"
    assert waited_build.start_us > baseline_build.start_us, (
        "the recorded admission wait must move the reported BUILD start later")
