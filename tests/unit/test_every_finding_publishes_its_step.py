"""UX-1256: every finding publishes its step - a sentence and a command, or why it has none."""

import contextlib
import io
import json
import pathlib
import re

import pytest

from bga import findings, schemas
from bga.cli import main
from bga.report._shared import resolve_attribution_hint, resource_wait_advice

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNS = {
    "golden": (REPO / "tests/fixtures/golden/mixed_task_kinds", None),
    "macro_micro": (REPO / "tests/fixtures/macro_micro/run", REPO / "tests/fixtures/macro_micro/plane2.json"),
    "shared_base_wide": (REPO / "tests/fixtures/shared_base_wide/run", None),
}
ACTED_ON = {"critical", "high", "medium"}
ENUM_WORD = re.compile(r"\b(PROCESS|DOWNLOAD|UPLOAD)\b")
BARE_CAPACITY = re.compile(r"(?<!bga analyze )--capacity\b")


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
        saturated, said = wait["step"]["text"].split(" — ", 1)
        assert saturated.startswith("builder slots were saturated ("), wait["step"]
        assert said == resource_wait_advice(document["capacity_verdict"])[0], wait["step"]
        assert wait["step"]["command"].startswith("bga sweep "), wait["step"]
    else:
        assert wait["step"]["text"] == resolve_attribution_hint(category, document["capacity_verdict"])
    assert "hint" not in wait["evidence"]


def test_no_finding_says_an_enum_word_or_a_bare_flag(document):
    """UX-1271: reader words, and `--capacity` only with `bga analyze` before it."""
    said = [(f["id"], text) for f in document["findings"] for text in [f["title"], *f["detail"], *f["step"].values()]]
    said += [("attribution_hints", text) for text in (document.get("attribution_hints") or {}).values()]
    assert not [(fid, text) for fid, text in said if ENUM_WORD.search(text) or BARE_CAPACITY.search(text)]


@pytest.mark.parametrize("verdict", [{}, {"checks_ran": True}, {"checks_ran": True, "oversubscribed": True}])
def test_every_resource_wait_hint_is_in_reader_words(verdict):
    hint = resolve_attribution_hint("resource_wait_us", verdict)
    assert not ENUM_WORD.search(hint) and not BARE_CAPACITY.search(hint), hint


def test_a_fixture_leads_with_resource_wait():
    wait = findings.findings_by_id(_analysed("shared_base_wide")["findings"])["wait-category"]
    assert wait["evidence"]["category"] == "resource_wait_us"


def test_the_text_report_prints_the_step():
    finding = findings._finding("x", "high", "t", step=findings._step("do it", ["bga", "sweep", "r"]))
    assert findings.render_findings([finding]) == ["  t", "    -> do it", "       bga sweep r"]


def test_a_finding_without_a_step_does_not_construct():
    with pytest.raises(TypeError):
        findings._finding("x", "info", "t")


def test_the_schema_declares_the_step():
    item = schemas.schema(schemas.ANALYZE)["properties"]["findings"]["items"]
    assert set(item["properties"]["step"]["properties"]) == {"text", "command", "why_none"}
