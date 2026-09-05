"""UX-223: the jump box as an index over what the page can already do.

`wireJumpBox` searched section names and element uids and scrolled to
the hit. By the time a reader has typed `openssl`, the page knows six
things they might want to do with it and offered one.

Every row is a link or a control that exists elsewhere in the page. This
is an index over affordances, not a new capability - which is why it is
cheap and why it must not grow into one. No fuzzy matching, no ranking
heuristic, no search index: substring matching over a list the page
already holds.

The two rules with teeth:

* **an action whose precondition is absent is not listed.** UX-194's
  rule, applied to more buttons than it was written for - a Perfetto
  row on a run with no timeline is a dead affordance.
* **the numbers beside an element are read, never recomputed.**
"""
import json
import os
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PAYLOAD = {
    "total_duration_us": 100_000_000,
    "critical_path_detail": [
        {"element_uid": "openssl.bst", "duration_us": 672_000_000,
         "share_of_path": 0.186},
        {"element_uid": "zlib.bst", "duration_us": 12_000_000,
         "share_of_path": 0.02},
    ],
    "elements": {
        "element_durations": {"openssl.bst": 672_000_000,
                              "zlib.bst": 12_000_000,
                              "docs.bst": 900_000},
    },
    "headline": {
        "top_actions": [{"element_uid": "openssl.bst", "saving_us": 522_000_000}],
    },
}

_TARGETS = [
    {"kind": "element", "key": "openssl.bst", "text": "openssl.bst"},
    {"kind": "element", "key": "zlib.bst", "text": "zlib.bst"},
    {"kind": "element", "key": "docs.bst", "text": "docs.bst"},
    {"kind": "section", "key": "findings", "text": "Findings"},
    {"kind": "section", "key": "signals", "text": "Critical path"},
]


def _js(body):
    result = subprocess.run([node, "--input-type=module", "-e", body],
                            capture_output=True, text=True, cwd=REPO, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _palette(query, context=None):
    return _js(f'''
      const {{ paletteResults }} = await import("./bga/viewer/nav.js");
      console.log(JSON.stringify(paletteResults({json.dumps(_TARGETS)}, {json.dumps(query)}, {json.dumps(_PAYLOAD)}, {json.dumps(context or {})})));
    ''')


@needs_node
class TestTheResultsAreGrouped:

    def test_an_element_query_yields_its_element(self):
        out = _palette("openssl")
        assert [e["key"] for e in out["elements"]] == ["openssl.bst"]

    def test_sections_are_their_own_group(self):
        out = _palette("path")
        assert [s["key"] for s in out["sections"]] == ["signals"]
        assert out["elements"] == []

    def test_an_empty_query_offers_nothing(self):
        out = _palette("")
        assert out == {"elements": [], "actions": [], "sections": []}

    def test_a_query_matching_nothing_offers_no_actions(self):
        out = _palette("nothing-like-this")
        assert out["actions"] == []


@needs_node
class TestTheNumbersAreRead:

    def test_the_element_row_carries_its_published_numbers(self):
        out = _palette("openssl")
        facts = out["elements"][0]["facts"]
        assert facts["duration_us"] == 672_000_000
        assert facts["share_of_path"] == 0.186
        assert facts["saving_us"] == 522_000_000

    def test_they_are_the_payloads_and_not_derived(self):
        """The mutation this task names: compute the shown duration in
        the palette instead of reading it. This fixture separates the
        two - `total_duration_us` is 100 s while `openssl.bst` alone is
        672 s, so anything derived from the total cannot match."""
        out = _palette("openssl")
        assert out["elements"][0]["facts"]["duration_us"] == \
            _PAYLOAD["critical_path_detail"][0]["duration_us"]
        assert out["elements"][0]["facts"]["duration_us"] != \
            _PAYLOAD["total_duration_us"]

    def test_an_element_off_the_path_has_no_share_of_it(self):
        out = _palette("docs")
        facts = out["elements"][0]["facts"]
        assert facts["duration_us"] == 900_000
        assert facts["share_of_path"] is None, "zero would read as on the path"

    def test_an_element_with_nothing_published_has_no_facts(self):
        out = _js('''
          const { paletteFacts } = await import("./bga/viewer/nav.js");
          console.log(JSON.stringify(paletteFacts({}, "unknown.bst")));
        ''')
        assert out is None


@needs_node
class TestAnAbsentPreconditionIsNotOffered:

    def test_no_perfetto_row_without_a_timeline(self):
        """UX-194's rule. The fixture is a run with no timeline."""
        out = _palette("openssl", {"hasTimeline": False})
        assert "perfetto" not in [a["id"] for a in out["actions"]]

    def test_the_perfetto_row_appears_when_there_is_a_timeline(self):
        """Otherwise the guard above passes because nothing is offered."""
        out = _palette("openssl", {"hasTimeline": True})
        assert "perfetto" in [a["id"] for a in out["actions"]]

    def test_no_blast_row_in_an_export(self):
        """`bga blast` is a *transport* - it asks a server. An export is
        a `file://` document with no server."""
        out = _palette("openssl", {"hasBlast": False})
        assert "blast" not in [a["id"] for a in out["actions"]]

    def test_the_always_available_actions_are_always_there(self):
        out = _palette("openssl", {})
        assert [a["id"] for a in out["actions"]] == ["show", "focus"]

    def test_nothing_errors_on_a_run_with_no_preconditions_at_all(self):
        out = _palette("openssl", {})
        assert out["elements"], "the query still resolves"


@needs_node
class TestTheAnchorIsNotSpeltTwice:

    def test_the_show_action_points_at_the_element_section(self):
        out = _palette("openssl", {})
        show = next(a for a in out["actions"] if a["id"] == "show")
        assert show["href"].startswith("#element-")

    def test_it_is_the_same_expression_views_uses(self):
        """UX-216 made a link and its target one expression. A palette
        with its own spelling of the anchor would reopen exactly the
        defect that item closed."""
        out = _js('''
          const { paletteResults } = await import("./bga/viewer/nav.js");
          const { elementAnchor } = await import("./tests/viewer.mjs");
          const groups = paletteResults(
            [{kind: "element", key: "a/weird:name.bst", text: "a/weird:name.bst"}],
            "weird", {}, {});
          const show = groups.actions.find((a) => a.id === "show");
          console.log(JSON.stringify({
            href: show.href,
            expected: `#${elementAnchor("a/weird:name.bst")}`,
          }));
        ''')
        assert out["href"] == out["expected"]

    def test_nav_does_not_declare_its_own_anchor_function(self):
        source = open(os.path.join(REPO, "bga/viewer/nav.js"),
                      encoding="utf-8").read()
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("//"))
        assert "function cssId" not in code
        assert "function elementAnchor" not in code
        assert 'import { elementAnchor }' in code


class TestTheFlattenedExportHasNoDuplicateNames:
    """The failure this item hit: the export concatenates every module
    into one scope, so two modules exporting the same top-level name is
    a `SyntaxError` in the shipped page - UX-199's defect, by a new
    route. `paletteFacts` is named for its module for that reason.
    """

    def test_no_two_modules_export_the_same_top_level_name(self):
        import re

        import tools.bga_view as view

        seen = {}
        clashes = []
        for name in view._module_order():
            source = open(os.path.join(view.ASSET_DIR, name),
                          encoding="utf-8").read()
            for match in re.finditer(
                    r"^export\s+(?:async\s+)?(?:function|const|let|class)\s+(\w+)",
                    source, re.M):
                symbol = match.group(1)
                if symbol in seen:
                    clashes.append(f"{symbol}: {seen[symbol]} and {name}")
                seen[symbol] = name
        assert clashes == [], (
            "the export flattens every module into one scope, so these "
            f"would be a SyntaxError in the shipped page: {clashes}")
