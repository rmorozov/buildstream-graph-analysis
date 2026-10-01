"""UX-1256: every finding publishes its step - a sentence and a command, or why it has none."""

import contextlib
import io
import json
import pathlib

import pytest

from bga import findings, schemas
from bga.cli import main
from bga.report import ATTRIBUTION_CATEGORY_HINTS_BY_KEY

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNS = {
    "golden": (REPO / "tests/fixtures/golden/mixed_task_kinds", None),
    "macro_micro": (REPO / "tests/fixtures/macro_micro/run", REPO / "tests/fixtures/macro_micro/plane2.json"),
}
ACTED_ON = {"critical", "high", "medium"}


def _analysed(name):
    run, plane2 = RUNS[name]
    argv = ["analyze", str(run), "--format", "json"] + (["--plane2", str(plane2)] if plane2 else [])
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(argv)
    return json.loads(buffer.getvalue())


@pytest.fixture(scope="module", params=sorted(RUNS))
def document(request):
    return _analysed(request.param)


def test_every_finding_carries_one_step(document):
    for finding in document["findings"]:
        step = finding.get("step")
        assert isinstance(step, dict), finding["id"]
        assert ("text" in step) != ("why_none" in step), (finding["id"], step)
        if finding["severity"] in ACTED_ON:
            assert step.get("text"), f"{finding['id']} ({finding['severity']}) has no step: {step}"


def test_the_wait_category_step_is_the_resolved_hint(document):
    wait = findings.findings_by_id(document["findings"]).get("wait-category")
    assert wait is not None, "the fixture no longer has a wait-category finding"
    category = wait["evidence"]["category"]
    if category == "resource_wait_us":
        pytest.skip("resource wait is conditioned on Plane 2; test_plane2_conditioned_capacity_advice holds it")
    assert wait["step"]["text"] == ATTRIBUTION_CATEGORY_HINTS_BY_KEY[category]
    assert "hint" not in wait["evidence"]


def test_the_text_report_prints_the_step():
    finding = findings._finding("x", "high", "t", step=findings._step("do it", ["bga", "sweep", "r"]))
    assert findings.render_findings([finding]) == ["  t", "    -> do it", "       bga sweep r"]


def test_a_finding_without_a_step_does_not_construct():
    with pytest.raises(TypeError):
        findings._finding("x", "info", "t")


def test_the_schema_declares_the_step():
    item = schemas.schema(schemas.ANALYZE)["properties"]["findings"]["items"]
    assert set(item["properties"]["step"]["properties"]) == {"text", "command", "why_none"}
