"""UX-388: an empty population disappeared without a word.

Round 63 ran the capture cycle twice - a cold build and the incremental
one beside it - and diffed the two exported pages:

```text
                        run 1 (full)   run 2 (incremental)
page height                  9,316 px            3,347 px
sections                           71                  36
payload keys                       51                  30
```

Six named populations emptied out and their sections vanished entirely:

```text
optimization_horizon      5 rows -> []       section gone
latent_heavies            1 row  -> []       section gone
joint_saving              object -> null     section gone
violations                []     -> []       never present
consolidation_candidates  []     -> absent   never present
```

Every one of those was `return null` in `renderSection`.

The reader was left unable to tell three facts the **payload keeps
apart**: the analysis ran and found nothing; the key is absent because
this version of bga does not compute it; and there is something here.
`UX-107` made that distinction law for Plane 2's coverage blocks;
nothing had applied it to a population, and the incremental run - the
common case - is where it bites.

**Absent stays absent.** A key the payload does not carry renders
nothing, because nothing was computed and inventing a heading for it
would be the opposite error. What decides which is which is the
*contract*: a declared collection with nothing in it is an empty
population; a scalar with no value is not and never was a section.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

node = __import__("shutil").which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The three shapes an empty population arrives in, and the two that
#: must stay invisible. `joint_saving` really is `null` when its input
#: set is empty (`bga/analyzer.py`), which is why `null` on a declared
#: collection counts as empty rather than as absent.
_PROBE = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");

const LIST = { type: "array", items: { type: "object" },
               description: "What this section would have shown." };
const MAP = { type: "object", additionalProperties: { type: "number" } };
const SCALAR = { type: "string" };

const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const find = (n, pred) => {
  if (!n) return null;
  if (pred(n)) return n;
  for (const c of n.children ?? []) { const hit = find(c, pred); if (hit) return hit; }
  return null;
};
const describe = (section) => section && ({
  tag: section.tagName,
  key: section.attrs["data-section"],
  empty: section.attrs["data-empty"],
  heading: text(find(section, (n) => n.tagName === "h2")),
  line: text(find(section, (n) => (n.attrs.class || "") === "empty-population")),
  sentence: text(find(section, (n) => (n.attrs["data-describes"]) === "horizon")),
});

console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  emptyList: describe(app.renderSection("horizon", [], {}, LIST)),
  nullCollection: describe(app.renderSection("horizon", null, {}, LIST)),
  emptyMap: describe(app.renderSection("shares", {}, {}, MAP)),
  // `Boolean(...)`, not the node: a mutation that turns these into
  // sections would otherwise hand `JSON.stringify` a circular DOM node
  // and kill the probe, so the mutation would "go red" by crashing the
  // harness rather than by failing a clause that says what is wrong.
  nullScalar: Boolean(app.renderSection("section", null, {}, SCALAR)),
  undeclared: Boolean(app.renderSection("unknown_key", [], {}, undefined)),
  populated: Boolean(app.renderSection("horizon", [{ a: 1 }], {}, LIST)),
  populatedIsNotMarked: Boolean(
    app.renderSection("horizon", [{ a: 1 }], {}, LIST).attrs["data-empty"]),
}));
"""


@pytest.fixture(scope="module")
def probed():
    result = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


@needs_node
class TestAnEmptyPopulationIsRendered:
    def test_an_empty_list_keeps_its_heading(self, probed):
        seen = probed["emptyList"]
        assert seen, "an empty declared collection rendered nothing at all"
        assert seen["key"] == "horizon" and seen["tag"] == "section"
        assert "Horizon" in seen["heading"], seen["heading"]

    def test_it_says_it_is_empty_in_words(self, probed):
        """A heading over nothing is a worse answer than no heading."""
        assert "found none" in probed["emptyList"]["line"], probed["emptyList"]

    def test_it_does_not_smuggle_the_schema_sentence_in(self, probed):
        """The convenience this section does *not* take.

        An empty section is exactly where a reader would want the
        contract's sentence - and `UX-346` says a description renders
        beside its value only when the contract declares it inline,
        while `UX-317` says every described value carries a `?` marker.
        A bare paragraph under the heading satisfies neither. The first
        version of this section did it anyway and reddened four clauses
        of those two items; this clause is what stops it coming back.
        """
        assert not probed["emptyList"]["sentence"], (
            "the schema sentence is beside the heading again, which is "
            "the rule UX-346 and UX-317 landed against")

    def test_the_rail_can_see_it(self, probed):
        """`data-empty` is what `nav.js` reads to mark the entry.

        Before this the section was not in the document at all, so the
        rail listed whatever happened to be non-empty on this run and a
        reader comparing two runs had nothing to compare.
        """
        assert probed["emptyList"]["empty"] == "true"

    def test_a_null_on_a_declared_collection_counts_as_empty(self, probed):
        """`joint_saving` is `null` when its input set is empty.

        The emitter writes `None` there rather than `{}` - so a rule
        that looked only at `[]` would have left one of the six sections
        the round found still vanishing.
        """
        assert probed["nullCollection"], "a null collection rendered nothing"
        assert probed["nullCollection"]["empty"] == "true"

    def test_an_empty_map_counts_too(self, probed):
        assert probed["emptyMap"] and probed["emptyMap"]["empty"] == "true"


@needs_node
class TestAbsentStaysAbsent:
    """The other direction, and the reason the contract decides."""

    def test_a_scalar_with_no_value_is_not_a_section(self, probed):
        """`section: null` is a string field, and never was a section.

        A rule that rendered every null would have put a heading over
        every unset scalar in the payload.
        """
        assert probed["nullScalar"] is False

    def test_a_key_the_schema_does_not_declare_renders_nothing(self, probed):
        assert probed["undeclared"] is False, (
            "with no schema node there is nothing to say the key is a "
            "population, so an empty value is not evidence of one")

    def test_a_populated_section_is_unchanged_and_unmarked(self, probed):
        assert probed["populated"]
        assert probed["populatedIsNotMarked"] is False, (
            "a section with rows must not carry the empty mark")
