"""UX-218: the next step is a command you can run.

The loop is where the repetition lives:

```text
capture -> analyze -> read -> change something -> capture again
                                ^                       |
                                +--- did that help? ----+
```

After reading the decision panel the reader's next action comes from a
small closed set — blast the top element, look inside it, measure
again, compare — and every round they retype it, copying the run path
and the element name by hand out of a page that holds both.

The branch is the more important half. *Which* step is right depends on
what the run measured, and that mapping lived in documentation prose.
A viewer that encoded it would be a second decision-maker — the thing
`UX-207` exists to prevent — so `next_steps` is decided in the pipeline
and the terminal, CI and the page then give the same answer.

The acceptance that matters is not "a command is shown" but **"the
command runs"**: every published `argv` is executed against the fixture
and required not to error.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import schemas
from bga.findings import compute_next_steps

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")
# `UX-477`: scheduler-bound by graph shape rather than by startup.
SCHEDULED = os.path.join(REPO, "tests", "fixtures", "shared_base_wide", "run")
REAL = os.path.join(
    REPO, "examples", "06-macro-micro-optimization", ".bga", "runs",
    "20260821T170127Z")
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
has_capture = pytest.mark.skipif(
    not os.path.isdir(REAL), reason="the examples/06 capture is not here")


def _report(run=GOLDEN, plane2=None):
    from bga.cli import main

    argv = ["analyze", run, "--format", "json"]
    if plane2:
        argv += ["--plane2", plane2]
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(argv)
    return json.loads(buffer.getvalue())


class TestTheStepIsDecidedInThePipeline:
    def test_the_report_publishes_it(self):
        report = _report()
        assert "next_steps" in report, (
            "a run with nothing to suggest publishes an empty list rather "
            "than dropping the key")
        assert isinstance(report["next_steps"], list)

    def test_it_validates_against_the_schema(self):
        jsonschema = pytest.importorskip("jsonschema")
        jsonschema.validate(_report(), schemas.schema(schemas.ANALYZE))

    def test_two_fixtures_that_measured_differently_answer_differently(self):
        """Asserted by value, not by presence. `shared_base_wide` is
        `scheduler_bound` and outside a store; `examples/06` is
        `chain_bound`, inside one, with a Plane 2 report - so the two
        should not share a first step, and a table that returned the
        same list for both would be no branch at all.

        `UX-477` moved the scheduler-bound half off the golden run.
        `UX-468`'s walk 3 is why it matters: the sweep was being offered
        on graphs that are strictly serial, because their verdict came
        from BuildStream's startup rather than from their shape. The
        golden run is one of those - four back-to-back tasks - and
        offering "more builders would help" on it was the defect, not
        the fixture."""
        scheduled = {s["id"] for s in _report(SCHEDULED)["next_steps"]}
        assert "sweep-the-capacity" in scheduled, scheduled
        assert "measure-again" not in scheduled, (
            "this fixture is not in a store; a step it cannot run "
            "must not be offered")

    def test_the_sweep_is_not_offered_on_a_chain(self):
        """`UX-468`'s walk 3, as a clause. More builders buy nothing on
        a graph whose elements run one after another, and the golden run
        is that graph."""
        golden = {s["id"] for s in _report()["next_steps"]}
        assert "sweep-the-capacity" not in golden, golden

    @has_capture
    def test_the_other_fixture_answers_the_other_way(self):
        steps = {s["id"] for s in _report(
            os.path.join(REAL, "run"),
            os.path.join(REAL, "plane2.json"))["next_steps"]}
        assert "sweep-the-capacity" not in steps, (
            "examples/06 is chain-bound - more builders is the wrong advice")
        assert {"measure-again", "compare-with-the-run-before"} <= steps
        assert "look-inside-the-element" in steps, (
            "Plane 2 measured this run, so the join is worth suggesting")

    def test_a_step_names_the_field_it_was_chosen_by(self):
        """So the advice can be checked against the number behind it -
        which is the difference between a recommendation and a slogan."""
        for step in _report()["next_steps"]:
            assert step.get("follows_from"), step

    def test_the_reason_carries_the_number_that_chose_it(self):
        report = _report(GOLDEN)
        blast = next(s for s in report["next_steps"]
                     if s["id"] == "blast-the-top-element")
        top = report["headline"]["top_actions"][0]
        assert top["element_uid"] in blast["reason"]


class TestNoStepIsOfferedThatCannotBeRun:
    """`UX-194`'s dead-button rule, applied to advice rather than
    controls. A step whose precondition this run does not meet is
    absent, not offered and broken."""

    def test_without_a_run_path_nothing_is_spelled_approximately(self):
        from bga.ingest.models import AnalysisResult

        result = AnalysisResult(run_id="r", total_duration_us=1)
        result.run_instance = {}
        assert compute_next_steps(result) == []

    def test_a_run_outside_a_store_is_offered_no_store_commands(self):
        steps = {s["id"] for s in _report()["next_steps"]}
        assert not ({"measure-again", "compare-with-the-run-before"} & steps)

    def test_a_run_with_no_plane2_is_not_told_to_look_inside(self):
        steps = {s["id"] for s in _report()["next_steps"]}
        assert "look-inside-the-element" not in steps

    def test_the_store_shape_is_read_from_the_path_not_the_disk(self):
        """`compute_next_steps` stays a pure function of the result -
        the store-shaped steps are decided by the *shape* of the
        published run path, so the pipeline does no IO to give
        advice."""
        from bga.findings import _store_paths

        assert _store_paths("proj/.bga/runs/20260101T000000Z/run") == (
            "proj", True)
        assert _store_paths("some/other/run") == (None, False)
        assert _store_paths("") == (None, False)


class TestTheCommandsActuallyRun:
    """The acceptance. Not "a command is shown" - `bga blast` with the
    arguments in the wrong order would show just as well."""

    # UX-326: derived, not written down. This list was two ids for six
    # rounds - `blast-the-top-element` and `sweep-the-capacity` - while
    # the block published four, and both of the two it never ran were
    # broken: `bga snapshot <project>` crashed and `bga compare … 
    # --project` named a flag that does not exist. The ids come from the
    # fixture's own report now, and the store-shaped steps (which this
    # fixture, being outside a store, does not offer) are executed by
    # `test_the_printed_sentences_are_contracts.py` against one that is.
    @pytest.mark.parametrize("step_id", sorted(
        {s["id"] for s in _report()["next_steps"]}))
    def test_every_published_argv_is_executable_as_spelled(self, step_id):
        steps = {s["id"]: s for s in _report()["next_steps"]}
        if step_id not in steps:
            pytest.skip(f"{step_id} is not offered for this fixture")
        argv = steps[step_id]["argv"]
        assert argv[0] == "bga", argv
        result = subprocess.run(
            [sys.executable, "-m", "bga.cli", *argv[1:]],
            capture_output=True, text=True, cwd=REPO, timeout=300)
        assert result.returncode == 0, (
            f"`{' '.join(argv)}` exited {result.returncode}:\n"
            f"{result.stderr[-800:]}")
        assert result.stdout.strip(), f"`{' '.join(argv)}` printed nothing"

    @has_capture
    def test_the_join_step_runs_on_the_capture_that_earned_it(self):
        steps = {s["id"]: s for s in _report(
            os.path.join(REAL, "run"),
            os.path.join(REAL, "plane2.json"))["next_steps"]}
        argv = steps["look-inside-the-element"]["argv"]
        result = subprocess.run(
            [sys.executable, "-m", "bga.cli", *argv[1:], "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=300)
        assert result.returncode == 0, result.stderr[-800:]
        assert json.loads(result.stdout)["schema"] == schemas.CORRELATE


class TestTheTerminalAndThePageSayTheSameThing:
    def test_the_text_report_ends_with_them(self):
        from bga.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["analyze", GOLDEN])
        text = buffer.getvalue()
        assert "\nNext:" in text, "the text report does not carry the steps"
        for step in _report()["next_steps"]:
            assert " ".join(step["argv"]) in text, step["id"]

    def test_a_section_projection_does_not_carry_them(self):
        """`bga floors` answers about floors. Every other full-report
        block is gated the same way."""
        from bga.cli import main

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(["floors", GOLDEN])
        assert "\nNext:" not in buffer.getvalue()

    @needs_node
    def test_the_panel_renders_the_published_steps_and_nothing_else(self):
        out = _node(_PANEL % json.dumps(_report()))
        published = _report()["next_steps"]
        assert out["steps"] == [
            {"id": s["id"], "from": s["follows_from"],
             "argv": " ".join(s["argv"])} for s in published]

    @needs_node
    def test_the_copy_button_puts_the_exact_command_on_the_clipboard(self):
        out = _node(_PANEL % json.dumps(_report()))
        first = _report()["next_steps"][0]
        assert out["copied"] == " ".join(first["argv"])
        assert out["label"] == "✓ copied"

    @needs_node
    def test_a_payload_with_no_steps_renders_no_next_block(self):
        payload = dict(_report(), next_steps=[])
        out = _node(_PANEL % json.dumps(payload))
        assert out["steps"] == []
        assert out["headings"] == 0


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=REPO,
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


_PANEL = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: t,
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
globalThis.setTimeout = () => 0;
const views = await import("./tests/viewer.mjs");
const payload = %s;
let copied = null;
const node = views.renderDecision(payload, null, (t) => { copied = t; });
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const steps = all(node, (n) => n.attrs["data-step"]).map((n) => ({
  id: n.attrs["data-step"], from: n.attrs["data-follows-from"],
  argv: all(n, (c) => c.attrs["data-argv"])[0]?.attrs["data-argv"] }));
const button = all(node, (n) => n.className === "copy-step")[0];
if (button) button.listeners.click[0]();
console.log(JSON.stringify({
  steps, copied, label: button?.textContent ?? null,
  headings: all(node, (n) => n.tagName === "h3"
    && n.textContent === "Next").length }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
