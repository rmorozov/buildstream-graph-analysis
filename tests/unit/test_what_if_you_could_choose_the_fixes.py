"""UX-230: what if you could choose the fixes.

The fourth external review's sketch - checkboxes, pick your subset, see
the projected build - under its own warning: **this must not pretend to
simulate.** A page that summed per-element savings is wrong the moment
two fixes share a chain, which is exactly why the pipeline's projection
exists.

So there are three paths and no fourth: a prefix of the published
sequence is *read*, any other subset is *asked* of the server, and
offline the command is shown. The guards below check that the asked
answer is byte-identical to the CLI's, that the page never adds, and
that a refused selection renders the refusal.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _bga(args):
    result = subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())
    return result


def _report():
    out = _bga(["analyze", GOLDEN, "--format", "json"])
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


class TestTheProjectionIsThePipelines:
    def test_the_transport_and_the_cli_are_the_same_bytes(self):
        """The acceptance's own check. Not "close": the same document."""
        import tools.bga_view as view

        cli = _bga(["whatif", GOLDEN, "--element", "base.bst",
                    "--element", "lib.bst", "--format", "json"])
        assert cli.returncode == 0, cli.stderr
        served = view.whatif_answer(GOLDEN, ["base.bst", "lib.bst"])
        assert json.dumps(served, indent=2, default=str) == cli.stdout.strip()

    def test_the_joint_saving_is_not_the_sum(self):
        """The discriminating case, on the golden fixture rather than
        in prose: two elements on one chain are worth *less* together
        than their individual savings add up to. A page that added
        would be wrong here by 1 ms out of 11."""
        out = _bga(["whatif", GOLDEN, "--element", "base.bst",
                    "--element", "lib.bst", "--format", "json"])
        projected = json.loads(out.stdout)["projected"]
        assert projected["sum_of_individual_us"] == 11_000
        assert projected["joint_saving_us"] == 10_000
        assert projected["makespan_after_us"] == (
            projected["baseline_makespan_us"] - projected["joint_saving_us"])

    def test_the_convention_travels_with_every_answer(self):
        out = _bga(["whatif", GOLDEN, "--element", "base.bst",
                    "--format", "json"])
        document = json.loads(out.stdout)
        assert "instant" in document["convention"]
        assert "not a forecast" in document["convention"]

    @pytest.mark.parametrize("elements,check", [
        ([], "empty_selection"),
        (["ghost.bst"], "unknown_element"),
    ])
    def test_a_selection_it_cannot_project_is_refused_by_name(
            self, elements, check):
        argv = ["whatif", GOLDEN, "--format", "json"]
        for uid in elements:
            argv += ["--element", uid]
        document = json.loads(_bga(argv).stdout)
        assert document["projected"] is None
        assert [r["check"] for r in document["refusals"]] == [check]

    def test_a_refusal_is_an_answer_rather_than_a_failure(self):
        assert _bga(["whatif", GOLDEN, "--element", "ghost.bst"]).returncode == 0

    def test_the_document_validates_against_its_own_schema(self):
        jsonschema = pytest.importorskip("jsonschema")

        from bga import schemas

        document = json.loads(_bga(["whatif", GOLDEN, "--element", "base.bst",
                                    "--format", "json"]).stdout)
        jsonschema.validate(document, schemas.schema(schemas.WHATIF))
        assert document["schema"] == schemas.WHATIF


@needs_node
class TestThePageReadsAsksOrSaysTheCommand:
    def _render(self, payload, served=True, answer=None):
        script = (_HARNESS.replace("__PAYLOAD__", json.dumps(payload))
                          .replace("__SERVED__", "true" if served else "false")
                          .replace("__ANSWER__", json.dumps(answer)))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_a_prefix_is_read_from_the_payload(self):
        payload = _report_with_horizon()
        out = self._render(payload)
        first = payload["signals"]["optimization_horizon"][0]
        assert out["prefix"]["source"] == "published"
        assert out["prefix"]["makespan"] == str(first["makespan_after_us"])
        assert out["prefix"]["field"] == \
            "signals.optimization_horizon[0].makespan_after_us"

    def test_any_other_subset_is_asked_rather_than_computed(self):
        payload = _report_with_horizon()
        out = self._render(payload, answer={"projected": {
            "makespan_after_us": 4_000, "joint_saving_us": 10_000}})
        assert out["other"]["source"] == "server"
        assert out["other"]["makespan"] == "4000"
        assert out["asked"] == [["b.bst"]], out["asked"]

    def test_offline_it_shows_the_command_not_a_dead_control(self):
        payload = _report_with_horizon()
        out = self._render(payload, served=False)
        assert out["other"]["source"] == "command"
        assert out["other"]["text"] == (
            "bga whatif RUN --element b.bst")

    def test_a_refused_selection_renders_the_refusal(self):
        payload = _report_with_horizon()
        out = self._render(payload, answer={
            "projected": None,
            "refusals": [{"check": "unknown_element",
                          "sentence": "Not in this run's graph."}]})
        assert out["other"]["source"] == "refused"
        assert "Not in this run's graph." in out["other"]["text"]

    def test_the_page_never_publishes_a_number_it_added(self):
        """`UX-219`'s Out of Scope, as a guard. Whatever the section
        shows carries `data-source`, and every value it shows is either
        a published field or one bga answered - there is no branch that
        produces a figure the page computed."""
        payload = _report_with_horizon()
        for served, answer in ((True, {"projected": {
                "makespan_after_us": 4_000}}), (False, None)):
            out = self._render(payload, served=served, answer=answer)
            for state in (out["prefix"], out["other"]):
                assert state["source"] in (
                    "published", "server", "command", "refused", "none"), state


def _report_with_horizon():
    return {
        "schema": "analyze/v2",
        "total_duration_us": 10_000,
        "signals": {"optimization_horizon": [
            {"element_uid": "a.bst", "saving_us": 6_000,
             "makespan_after_us": 8_000, "cumulative_saving_us": 6_000},
            {"element_uid": "b.bst", "saving_us": 4_000,
             "makespan_after_us": 4_000, "cumulative_saving_us": 10_000},
        ]},
    }


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const views = await import("./tests/viewer.mjs");
const asked = [];
const ask = __SERVED__
  ? (elements) => { asked.push([...elements]); return Promise.resolve(__ANSWER__); }
  : null;
const section = views.renderWhatIf(__PAYLOAD__, ask, { run: "RUN" });
const find = (n) => {
  let hit = null;
  (function walk(m) { if (!m || hit) return;
    if (m.attrs["data-role"] === "whatif-answer") { hit = m; return; }
    (m.children ?? []).forEach(walk); })(n);
  return hit;
};
const boxes = [];
(function walk(n) { if (!n) return;
  if (n.attrs["data-whatif-element"]) boxes.push(n);
  (n.children ?? []).forEach(walk); })(section);
const state = () => {
  const answer = find(section);
  return { source: answer.attrs["data-source"],
           makespan: answer.attrs["data-makespan-us"] ?? null,
           field: answer.attrs["data-field"] ?? null,
           text: answer.textContent };
};
// Tick the first box: a prefix of the published sequence.
boxes[0].listeners.change[0]();
const prefix = state();
// Untick it and tick the second: a subset the payload does not answer.
boxes[0].listeners.change[0]();
boxes[1].listeners.change[0]();
await new Promise((r) => setTimeout(r, 0));
const other = state();
console.log(JSON.stringify({ prefix, other, asked }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
