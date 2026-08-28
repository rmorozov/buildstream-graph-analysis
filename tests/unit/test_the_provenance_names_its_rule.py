"""UX-357: the provenance showed the claim and withheld the rule.

`UX-229` published the tool's reasoning: for every claim, the rule that
produced it, the evidence it read, the threshold it compared against,
and the inputs it wanted and did not have. `provenance` is drawn as a
section on both fixtures. Round 55 measured which of its fields reach a
rendered node:

```text
macro_micro, provenance (12 entries)          on page / not
  claim / kind / evidence[].value                  12 / 0
  evidence[].path                                   7 / 22
  rule.threshold                                    1 / 2
  rule.sentence                                     1 / 11
  rule.module                                       0 / 12
  rule.name                                         0 / 5
  rule.observed_path                                0 / 5
  unpublished_inputs[]                              0 / 3
```

The cause is a declaration, not a renderer. The schema gives
`provenance` a `bga:columns` of `claim` and `kind`, so the section
renders as a two-column table - and a table takes the scalar columns
and drops everything nested. Every field that makes a provenance record
*provenance* is nested:

- **`rule.name` and `rule.module`** - which rule fired and where it
  lives. `CHAIN_BOUND_RATIO` in a named module is the difference
  between "the tool says so" and a claim a reader can go and read.
- **`rule.sentence`** - the rule stated in words.
- **`rule.observed_path`** - which published number it compared.
- **`evidence[].path`** - where each number came from. The value was
  shown; the address that lets a reader check it was not.
- **`unpublished_inputs[]`** - the inputs the rule wanted and this run
  does not have. The one field whose whole purpose is to be read by a
  sceptic, drawn zero times of three.

The fix is the page's own shape, not a new one: an **index table plus a
detail block per row**, which is exactly what `elements` and the
element sections are. `renderProvenance` has existed since `UX-229`;
nothing reached it from the section path.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The one field this rule does not reach, and why it is not a finding.
#:
#: `trace_query` is a Perfetto query id (`element-time`), and what it
#: names is a query in the handoff's own library - so it belongs beside
#: the timeline, not inside the reason for a claim. It is carried on the
#: block as `data-query` so the handoff can find it, which is a
#: machine's channel and not a reader's; this file counts it withheld
#: and exempts it here rather than pretending an attribute is rendered.
EXEMPT = {"trace_query"}

_LOOK = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  const section = document.querySelector('[data-section="provenance"]');
  const main = document.querySelector("main") || document.body;
  return {
    exists: Boolean(section),
    tables: section ? section.querySelectorAll("table").length : 0,
    blocks: [...(section?.querySelectorAll("details.provenance") ?? [])]
      .map((block) => ({
        claim: block.getAttribute("data-provenance"),
        levels: block.getAttribute("data-levels"),
        rows: block.getAttribute("data-rows"),
        summary: (block.querySelector("summary")?.textContent || "").trim(),
        refs: block.querySelectorAll("dl.evidence-refs dt").length,
        rule: (block.querySelector("p.rule")?.textContent || "").trim(),
        observed: block.querySelector("p.rule")
          ?.getAttribute("data-observed") ?? null,
        why: (block.querySelector("p.why")?.textContent || "").trim(),
        unpublished: (block.querySelector("p.unpublished")?.textContent
                      || "").trim(),
      })),
    text: main.textContent || "",
    raws: [...main.querySelectorAll("[data-raw]")]
      .map((n) => n.getAttribute("data-raw")),
  };
})()
"""


def _leaves(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _leaves(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value, f"{prefix}[]")
    else:
        yield prefix, node


def _records(label):
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES[label]))["report.json"].get(
        "provenance") or []


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    return pages.pages(tmp_path_factory, "provenance")


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestThePopulationIsThePublishedRecords:
    def test_both_fixtures_publish_provenance(self, label):
        assert len(_records(label)) >= 5, len(_records(label))

    def test_the_records_carry_a_rule(self, label):
        """The nested half is what this file is about; a payload whose
        records were flat would make every clause below vacuous."""
        ruled = [record for record in _records(label) if record.get("rule")]
        assert len(ruled) == len(_records(label)), (
            f"{len(ruled)} of {len(_records(label))} records carry a rule")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestEveryPublishedFieldReachesAReader:
    def test_no_field_is_withheld(self, browser, booted, label):
        """The rule, asserted against the payload rather than a list of
        field names - so a field added to `analyze/v5` joins the check
        without an edit here."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        reachable = set(out["raws"])
        withheld = {}
        for record in _records(label):
            for field, value in _leaves(record):
                if value is None or isinstance(value, bool):
                    continue
                spelled = str(value)
                if len(spelled) < 2:
                    continue
                if spelled in reachable or spelled in out["text"]:
                    continue
                withheld.setdefault(field, 0)
                withheld[field] += 1
        unexpected = {field: count for field, count in withheld.items()
                      if field.split(".")[-1].rstrip("[]") not in EXEMPT}
        assert unexpected == {}, (
            f"{label}: provenance field(s) that reach no rendered node: "
            f"{unexpected}")

    def test_the_exemption_is_still_withheld(self, browser, booted, label):
        """An exemption for a field the page draws anyway is an
        exemption that quietly covers the next thing to fall under it.
        `trace_query` is out of scope *because* it is a machine's
        channel; if it starts rendering, this should say so."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        queries = {record.get("trace_query") for record in _records(label)
                   if record.get("trace_query")}
        assert queries, f"{label}: no record carries a trace_query"
        shown = [query for query in queries if query in out["text"]]
        assert len(shown) < len(queries), (
            f"{label}: every trace_query renders now - EXEMPT is covering "
            f"a field the page draws")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheSectionIsAnIndexAndItsRecords:
    def test_one_block_per_published_claim(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["exists"], f"{label}: no provenance section"
        claims = [record.get("claim") for record in _records(label)]
        assert [block["claim"] for block in out["blocks"]] == claims, (
            f"{label}: the blocks do not match the published claims")

    def test_the_index_table_survives(self, browser, booted, label):
        """`UX-338`'s relationship, not its violation: the two-column
        index over the claims is what the schema declares and what a
        reader scans, and the blocks are the detail under it. A fix
        that replaced the table would be a different design and should
        say so rather than arrive."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        assert out["tables"] == 1, out["tables"]

    def test_each_block_names_its_rule_and_where_it_lives(
            self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        named = 0
        for block, record in zip(out["blocks"], _records(label)):
            rule = record["rule"]
            # A record can publish a module and a sentence and no named
            # threshold - six of macro_micro's twelve do, because the
            # claim is computed rather than gated. The module is on the
            # page either way; the name is where there is one.
            assert rule.get("module") or "", rule
            assert rule["module"] in block["rule"], (block, rule)
            assert record["rule"].get("sentence", "") == block["why"], block
            if rule.get("name"):
                named += 1
                assert rule["name"] in block["rule"], (block, rule)
            else:
                assert "No named threshold" in block["rule"], block
            if rule.get("observed_path"):
                # In the *text*, not only in `data-observed`. A
                # mutation that dropped the path from the rendered
                # comparison and left the attribute passed the first
                # draft of this clause - and the value is reachable
                # elsewhere on the page as an `evidence[].path`, so the
                # coverage clause could not see it either. The claim is
                # that the block says which number the rule compared.
                assert rule["observed_path"] in block["rule"], (block, rule)
                assert block["observed"] == rule["observed_path"], block
        assert named, f"{label}: no record publishes a named rule"

    def test_each_evidence_row_carries_its_path(
            self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for block, record in zip(out["blocks"], _records(label)):
            assert block["refs"] == len(record.get("evidence") or []), (
                block, record.get("evidence"))

    def test_the_unpublished_inputs_are_stated(self, browser, booted, label):
        """`UX-329`'s rule - absence is stated, never drawn - on the one
        field whose whole purpose is to be read by a sceptic. And the
        other direction: a record with none draws no sentence, so the
        clause is a distinction rather than a decoration."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        seen = 0
        for block, record in zip(out["blocks"], _records(label)):
            missing = record.get("unpublished_inputs") or []
            if not missing:
                assert block["unpublished"] == "", block
                continue
            seen += 1
            for name in missing:
                assert name in block["unpublished"], (block, name)
        if label == "macro_micro":
            assert seen, "no record on this page names an unpublished input"


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheBlockAnnouncesItsDepth:
    """§3a.1 reaches this fold like every other. Twelve folds reading
    "Why" name nothing; each says whose claim it is and how much is
    behind it."""

    def test_each_block_counts_its_evidence(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        for block, record in zip(out["blocks"], _records(label)):
            rows = len(record.get("evidence") or [])
            assert block["levels"] == "1", block
            assert int(block["rows"]) == rows, block
            assert f"{rows} row" in block["summary"], block
            assert record.get("claim", "") in block["summary"], block


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
