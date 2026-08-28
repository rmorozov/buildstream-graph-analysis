"""UX-227: why is this ranked first.

The page could already say `openssl.bst` is worth 522 s, sits at 18.6%
of the path, has 14 consumers and moved since the last capture - in
five different sections. What it could not do was say them together, as
the reason.

The property asserted here is that the block *gathers* rather than
derives: every value it shows carries the path it was read from, that
path resolves in the published payload, and the value there equals the
one shown. The paths are walked through **both** resolvers - the page's
`resolvePath` and `bga/provenance.py`'s - so the two implementations of
one grammar cannot drift apart quietly.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import provenance

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _report(run=GOLDEN):
    result = subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))"
         % (["analyze", run, "--format", "json"],)],
        capture_output=True, text=True, cwd=os.getcwd())
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _render(payload, store=None):
    script = (_HARNESS.replace("__PAYLOAD__", json.dumps(payload))
                      .replace("__STORE__", json.dumps(store)))
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True,
                            cwd=os.getcwd(), timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def payload():
    return _report()


@needs_node
class TestEveryValueIsTraceable:
    def test_each_action_gets_its_own_block(self, payload):
        out = _render(payload)
        shown = [block["element"] for block in out["blocks"]]
        assert shown == [action["element_uid"]
                         for action in payload["headline"]["top_actions"]]

    def test_every_shown_value_resolves_to_the_field_it_cites(self, payload):
        """`UX-202`'s rule at the claim level: `data-field` is a path,
        and walking it must land on `data-raw`."""
        wrong = []
        for block in _render(payload)["blocks"]:
            for row in block["rows"]:
                found = provenance.resolve(payload, row["field"])
                if found is provenance.UNRESOLVED:
                    wrong.append(f"{row['field']} does not resolve")
                elif str(found) != row["raw"]:
                    wrong.append(
                        f"{row['field']} shows {row['raw']!r}, payload has "
                        f"{found!r}")
        assert wrong == [], wrong

    def test_the_two_resolvers_agree_on_every_path(self, payload):
        """Two implementations of one grammar is a risk. The page walks
        each path itself and reports what it found; this compares that
        against `bga/provenance.py` walking the same path."""
        out = _render(payload)
        for block in out["blocks"]:
            for row in block["rows"]:
                assert row["resolved"] == row["raw"], (
                    f"the page's own resolver disagrees with what it shows: "
                    f"{row}")
                assert str(provenance.resolve(payload, row["field"])) == \
                    row["resolved"], row["field"]

    def test_a_block_carries_at_least_one_traceable_value(self, payload):
        for block in _render(payload)["blocks"]:
            assert block["rows"], block["element"]

    def test_the_rule_that_ranked_it_comes_from_the_provenance_record(
            self, payload):
        """UX-229's contract, reached by the `finding_id` the action
        carries. The composition this item was filed with is the
        interim; the record is the destination.

        `UX-344`: one published list keyed by claim, so the lookup is by
        id rather than through a `see` path into a nested copy."""
        out = _render(payload)
        for block, action in zip(out["blocks"],
                                 payload["headline"]["top_actions"]):
            record = provenance.for_claim(payload, action["finding_id"])
            assert record is not None
            assert block["why"] == record["rule"]["sentence"]

    def test_an_element_no_source_knows_gets_no_block(self):
        """The block renders nothing rather than guessing - the same
        dead-control rule `UX-194` applies to buttons."""
        out = _render({
            "schema": "analyze/v4",
            "headline": {"diagnosis": "inconclusive", "sentence": "s",
                         "top_actions": [{"element_uid": "ghost.bst",
                                          "finding_id": "nope"}]},
        })
        assert out["blocks"] == []

    def test_a_dotted_element_uid_still_resolves(self):
        """Element uids contain dots. `[element_uid=layer07/mod084.bst]`
        is nonsense the moment the path separator is taken literally -
        which is exactly what both resolvers did until this item."""
        payload = {
            "schema": "analyze/v4",
            "critical_path_detail": [
                {"element_uid": "layer07/mod084.bst", "share_of_path": 0.25,
                 "duration_us": 9_000_000}],
            "headline": {"diagnosis": "chain_bound", "sentence": "s",
                         "top_actions": [
                             {"element_uid": "layer07/mod084.bst",
                              "finding_id": "time-concentration"}]},
        }
        block = _render(payload)["blocks"][0]
        for row in block["rows"]:
            assert row["raw"] == row["resolved"], row
            assert str(provenance.resolve(payload, row["field"])) == row["raw"]

    def test_the_history_line_appears_only_with_a_store(self, payload):
        assert _render(payload)["blocks"][0]["history"] is None
        store = {"schema": "store/v1", "snapshots": [
            {"stamp": "a", "total_duration_us": 10, "elements": [
                {"element_uid": payload["headline"]["top_actions"][0][
                    "element_uid"], "duration_us": 5}]}]}
        assert _render(payload, store)["blocks"][0]["history"] is not None


class TestTheExportCarriesIt:
    def test_the_explanations_need_no_server(self, tmp_path):
        """The block is rendered from the inlined payload, so it works
        from `file://` - `UX-195`'s rule for everything that survives an
        export."""
        import tools.bga_view as view

        project = tmp_path / "p"
        (project).mkdir()
        (project / "project.conf").write_text("name: p\nmin-version: 2.0\n")
        run = project / ".bga" / "runs" / "20260101T000000Z" / "run"
        run.parent.mkdir(parents=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        out = tmp_path / "r.html"
        view.export(str(run), str(out))
        html = out.read_text(encoding="utf-8")
        assert "renderWhyRanked" in html, (
            "the export dropped the module that renders the explanation")
        assert "why-ranked" in html


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const views = await import("./tests/viewer.mjs");
const payload = __PAYLOAD__;
const store = __STORE__;
const panel = views.renderDecision(payload, null, null, { store });
const blocks = [];
(function walk(n) {
  if (!n) return;
  if (n.className === "why-ranked") {
    const rows = [], findings = [];
    let why = null, history = null;
    (function inner(m) {
      if (!m) return;
      if (m.tagName === "dd" && m.attrs["data-field"]) {
        rows.push({ field: m.attrs["data-field"], raw: m.attrs["data-raw"],
                    // The page walks its own path back, so the guard can
                    // compare two resolvers rather than one.
                    resolved: String(
                      views.resolvePath(payload, m.attrs["data-field"])) });
      }
      if (m.className === "why" && why === null) why = m.textContent;
      if (m.attrs["data-role"] === "element-history") history = m.attrs["data-history"];
      if (m.className === "muted why-finding") findings.push(m.attrs["data-finding"]);
      (m.children ?? []).forEach(inner);
    })(n);
    blocks.push({ element: n.attrs["data-why"], rows, findings, why, history });
    return;
  }
  (n.children ?? []).forEach(walk);
})(panel);
console.log(JSON.stringify({ blocks }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
