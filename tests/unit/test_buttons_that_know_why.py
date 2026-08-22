"""UX-204: buttons that know why you are going to Perfetto.

The viewer's job is not to draw the timeline - Perfetto draws it far
better - but to say *where to look and why*. "Open timeline in Perfetto"
was correct and context-free: the findings know an element uid and a
question, and none of it travelled.

Three things are asserted here, and one of them is a *deliberate
absence*. Perfetto's deep-link API takes a trace and a title; it has no
documented way to preload the Query pane. So the query is not faked into
a URL - the always-works floor is "open the trace, and put the right
query one paste away", and the paste appears whether the handoff
succeeds or not, because a blocked pop-up is exactly when the reader
needs the SQL most.
"""
import json
import os
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def _node(script):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _library():
    return _node(
        'const q = await import("./bga/viewer/questions.js");'
        "console.log(JSON.stringify({ ids: q.QUESTIONS.map((x) => x.id),"
        "  categories: q.CATEGORIES }));")


def _map():
    return _node(
        'const t = await import("./bga/viewer/trace_context.js");'
        "console.log(JSON.stringify({ map: t.FINDING_QUERIES,"
        "  referenced: t.referencedQueries() }));")


@needs_node
class TestTheContextTravels:
    def test_a_finding_carries_its_question_and_its_element(self):
        out = _node(
            'const t = await import("./bga/viewer/trace_context.js");'
            'console.log(JSON.stringify(t.investigationFor({'
            '  id: "time-concentration",'
            '  title: "Where the time is: 4 elements are 71.9%",'
            '  elements: ["core.bst", "lib-b.bst"] })));')
        assert out["queryId"] == "element-time"
        assert out["element"] == "core.bst"
        # The title is what Perfetto shows in its tab, so it carries the
        # reason rather than the file name.
        assert "Where the time is" in out["title"]
        assert "core.bst" in out["title"]
        assert out["sql"].strip().lower().startswith("select")

    def test_the_query_is_the_library_entry_its_id_references(self):
        """The linkage the acceptance names: not a copy of the SQL, the
        entry itself."""
        out = _node(
            'const t = await import("./bga/viewer/trace_context.js");'
            'const q = await import("./bga/viewer/questions.js");'
            'const ctx = t.investigationFor({ id: "criticality",'
            '  title: "The chain", elements: ["core.bst"] });'
            'console.log(JSON.stringify({ ctx,'
            '  entry: q.renderedSql({ ...q.byId(ctx.queryId), example: "core.bst" }) }));')
        assert out["ctx"]["sql"] == out["entry"]

    def test_the_element_is_substituted_not_appended(self):
        out = _node(
            'const t = await import("./bga/viewer/trace_context.js");'
            'console.log(JSON.stringify(t.traceContext({'
            '  element_uid: "libfoo.bst", reason: "why",'
            '  query: "element-commands" })));')
        # `UX-210` changed *how* an element is selected - by the
        # `args.element` both planes carry, rather than by a
        # `native: <uid>` lane name that is a process name and never
        # matched a track. The property this guards is unchanged: the
        # real uid is substituted, and the example does not leak.
        assert "'libfoo.bst'" in out["sql"], out["sql"]
        assert "{element}" not in out["sql"]
        assert "core.bst" not in out["sql"], "the example leaked past the real uid"

    def test_a_finding_no_query_answers_gets_no_button(self):
        out = _node(
            'const t = await import("./bga/viewer/trace_context.js");'
            'console.log(JSON.stringify({ v: t.investigationFor({'
            '  id: "confidence", title: "Confidence: 0.97", elements: [] }) }));')
        assert out["v"] is None

    def test_a_context_naming_a_query_that_does_not_exist_is_refused(self):
        """Rather than a button that opens the trace with no question -
        which is the context-free button this item exists to replace."""
        out = _node(
            'const t = await import("./bga/viewer/trace_context.js");'
            'console.log(JSON.stringify({ v: t.traceContext({'
            '  reason: "why", query: "no-such-query" }) }));')
        assert out["v"] is None


@needs_node
class TestTheLibraryAndTheFindingsAgree:
    """Coverage, asserted both directions."""

    def test_every_referenced_query_is_in_the_library(self):
        library, mapping = _library(), _map()
        missing = [q for q in mapping["referenced"] if q not in library["ids"]]
        assert not missing, (
            f"findings reference queries the library page does not list: "
            f"{missing} - the button would open the trace with nothing")

    def test_every_library_query_is_reachable_from_a_finding(self):
        """The other direction. A question nobody's report links to is a
        question nobody finds - the page is where it lives, but a
        finding is how a reader arrives."""
        library, mapping = _library(), _map()
        orphans = [q for q in library["ids"] if q not in mapping["referenced"]]
        assert not orphans, (
            f"library questions no finding points at: {orphans}")

    def test_every_mapped_finding_id_names_a_real_query(self):
        library, mapping = _library(), _map()
        for finding, query in mapping["map"].items():
            assert query in library["ids"], f"{finding} -> {query}"

    def test_the_library_covers_every_declared_category(self):
        library = _library()
        by_category = _node(
            'const q = await import("./bga/viewer/questions.js");'
            "console.log(JSON.stringify(Object.fromEntries("
            "  q.CATEGORIES.map((c) => [c, q.inCategory(c).length]))));")
        for category in library["categories"]:
            assert by_category[category] > 0, f"{category} has no questions"


@needs_node
class TestTheButtonsInThePage:
    """Driven through `renderFindings` under a DOM shim - the wiring is
    what breaks, not the pure functions above."""

    def _render(self, investigate="fn"):
        return _node(_HARNESS.replace("__INVESTIGATE__", investigate))

    def test_a_finding_gets_a_button_carrying_its_query(self):
        out = self._render()
        button = [b for b in out["buttons"]
                  if b["queryId"] == "element-time"]
        assert button, out["buttons"]
        assert button[0]["element"] == "core.bst"

    def test_clicking_hands_off_with_the_finding_s_title(self):
        out = self._render()
        assert out["handedOff"], "the click handed nothing over"
        assert "Where the time is" in out["handedOff"][0]["title"]

    def test_the_query_is_revealed_rather_than_faked_into_a_url(self):
        """Perfetto has no documented way to preload the Query pane, so
        the floor is one paste. It appears on click - including when the
        handoff fails, which is when it matters most."""
        out = self._render()
        assert out["revealed"], "the query stayed hidden after the click"
        assert out["revealed"][0].strip().lower().startswith("select")

    def test_no_timeline_means_no_buttons(self):
        """`UX-194`'s dead-button rule, applied to ten more buttons than
        it was written for."""
        out = self._render(investigate="null")
        assert out["buttons"] == [], out["buttons"]


_HARNESS = """
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "", listeners: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x : this.children.push(x); } },
  };
}
// `app.js` boots itself when `#report` exists; it must not here.
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };

const app = await import("./bga/viewer/app.js");

const handedOff = [];
const fn = (context) => { handedOff.push(context); return Promise.resolve({bytes: 2048}); };
const investigate = __INVESTIGATE__;

const findings = [
  { id: "time-concentration", severity: "high",
    title: "Where the time is: 4 elements are 71.9% of the path",
    detail: [], elements: ["core.bst", "lib-b.bst"] },
  { id: "confidence", severity: "info", title: "Confidence: 0.97",
    detail: [], elements: [] },
];
const section = app.renderFindings(findings, investigate);

const buttons = [], revealed = [];
(function walk(n) {
  if (!n) return;
  if (n.className === "investigate") {
    buttons.push({ queryId: n.attrs["data-query-id"] ?? null,
                   element: n.attrs["data-element"] || null });
    for (const child of n.children) {
      if (child.tagName === "button") (child.listeners.click ?? []).forEach((f) => f());
    }
    for (const child of n.children) {
      if (child.className === "query" && child.hidden === false) {
        revealed.push(child.children.map((c) => c.textContent).join(""));
      }
    }
  }
  (n.children ?? []).forEach(walk);
})(section);

// The handoff promise settles on a later turn; let it.
await new Promise((r) => setTimeout(r, 0));
console.log(JSON.stringify({ buttons, revealed, handedOff }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
