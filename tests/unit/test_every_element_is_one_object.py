"""UX-216: every element is one object, and its links resolve.

Clause 1 is a live defect, and it was mine. `UX-208` gave every row of
an element-column table a generic Inspect anchored at
`#${cssId(uid)}` — and nothing in the page ever set that id. Measured
on `examples/06` before this landed:

```text
inspect links         19
distinct targets      11   #element-core-bst, #element-lib-b-bst, …
ids present in page   21   every one a section key
unresolvable          11 of 11
```

The guards written for `UX-208` asserted that the affordance *exists*.
They never asserted that it *arrives*. So the acceptance here is
resolution, not presence: every `#element-…` href in the document must
name an id the same document carries, and it is checked by resolving
all of them.
"""
import json
import os
import subprocess
import shutil
import tempfile

import pytest

from bga import schemas

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")
REAL = os.path.join(
    REPO, "examples", "06-macro-micro-optimization", ".bga", "runs",
    "20260821T170127Z")
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
has_capture = pytest.mark.skipif(
    not os.path.isdir(REAL), reason="the examples/06 capture is not here")


def _report(run=GOLDEN, plane2=None):
    import contextlib
    import io

    from bga.cli import main

    argv = ["analyze", run, "--format", "json"]
    if plane2:
        argv += ["--plane2", plane2]
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(argv)
    return json.loads(buffer.getvalue())


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=REPO,
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _render(payload):
    """The whole page, the way `boot()` assembles it - including the
    views that are appended after `render()`, because those are where
    most element names are drawn and a harness that skipped them would
    be measuring the wrong document."""
    scratch = tempfile.mkdtemp()
    try:
        payload_path = os.path.join(scratch, "payload.json")
        schema_path = os.path.join(scratch, "schema.json")
        with open(payload_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        with open(schema_path, "w", encoding="utf-8") as handle:
            json.dump(schemas.schema(payload["schema"]), handle)
        return _node(_HARNESS % json.dumps([payload_path, schema_path]))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@needs_node
class TestEveryElementLinkResolves:
    """The acceptance. Not "an Inspect exists" - that was true while
    every one of them pointed at nothing."""

    def test_on_the_golden_fixture(self):
        out = _render(_report())
        assert out["element_links"] > 0, "no element link was rendered at all"
        assert out["unresolvable"] == [], (
            f"{len(out['unresolvable'])} of {out['distinct']} element "
            f"anchors resolve to nothing: {out['unresolvable'][:4]}")

    @has_capture
    def test_on_the_real_capture(self):
        out = _render(_report(os.path.join(REAL, "run"),
                              os.path.join(REAL, "plane2.json")))
        assert out["element_links"] > 0
        assert out["unresolvable"] == [], out["unresolvable"][:4]

    def test_the_inspect_affordance_is_among_them(self):
        """`UX-208`'s own affordance, which is what was broken."""
        out = _render(_report())
        assert out["inspect_links"] > 0, "no row got an Inspect"
        assert out["inspect_unresolvable"] == [], out["inspect_unresolvable"]

    def test_one_spelling_for_the_link_and_the_target(self):
        """The two expressions drifting apart *is* this defect, so
        there is one expression. Asserted by value on awkward uids, not
        by reading the source."""
        out = _node(
            'const a = await import("./bga/viewer/app.js");'
            'const v = await import("./bga/viewer/views.js");'
            # UX-235: `my_lib.bst` earns its place. The set had no
            # underscore, and `\w` includes one while `A-Za-z0-9` does
            # not - so `cssId` re-duplicated as `[^A-Za-z0-9-]+` differs
            # from `[^\w-]+` on exactly that character, survived every
            # guard here, and gave `my_lib.bst` a link that misses its
            # own section. The probe set is the guard.
            'const uids = ["core.bst", "sub/dir:thing.bst", "a b.bst", '
            '"my_lib.bst", "x"];'
            'console.log(JSON.stringify(uids.map((u) => '
            '  [a.cssId(u), v.elementAnchor(u)])));')
        for link, target in out:
            assert link == target, (link, target)


@needs_node
class TestTheElementIsAnObject:
    def test_it_has_a_section_of_its_own(self):
        out = _render(_report())
        assert out["element_sections"], "no element got a section"
        for section in out["element_sections"]:
            assert section["id"] == section["anchor"], section

    def test_it_carries_published_facts_and_no_others(self):
        """Every `data-raw` in an element section must be a value the
        payload carries for that element - which is what stops the
        section becoming a second analysis."""
        payload = _report()
        out = _render(payload)
        detail = {e["element_uid"]: e for e in
                  payload["signals"]["critical_path_detail"]}
        checked = 0
        for section in out["element_sections"]:
            entry = detail.get(section["element"])
            if not entry:
                continue
            for field, raw in section["fields"].items():
                if field in entry and entry[field] is not None:
                    assert str(entry[field]) == raw, (section["element"], field)
                    checked += 1
        assert checked > 0, "no published field was actually compared"

    def test_it_says_where_else_the_element_appears(self):
        """The cross-reference, read off the rendered document rather
        than from a list in the viewer - so a section added later joins
        it with no edit."""
        out = _render(_report())
        with_places = [s for s in out["element_sections"] if s["where"]]
        assert with_places, "no element section cross-references anything"
        for section in with_places:
            assert not any(k.startswith("element-") for k in section["where"]), (
                "an element section should not list itself")

    def test_a_finding_that_names_an_element_shows_on_its_section(self):
        payload = _report()
        named = {uid for finding in payload["findings"]
                 for uid in (finding.get("elements") or [])}
        if not named:
            pytest.skip("this fixture's findings name no elements")
        out = _render(payload)
        sections = {s["element"]: s for s in out["element_sections"]}
        assert any(sections.get(uid, {}).get("findings")
                   for uid in named), (
            "no element section carries the finding that names it")

    @has_capture
    def test_the_plane2_half_reaches_the_section(self):
        """`UX-215`'s join is what lets this section answer "is it
        compute-bound or badly built" - the whole reason that item came
        first."""
        payload = _report(os.path.join(REAL, "run"),
                          os.path.join(REAL, "plane2.json"))
        out = _render(payload)
        fields = {f for s in out["element_sections"] for f in s["fields"]}
        assert "cores_busy" in fields, sorted(fields)
        assert "requested_jobs" in fields, sorted(fields)


@needs_node
class TestItStaysASectionAndStaysBounded:
    def test_no_overlay_machinery_entered_the_page(self):
        """Declined deliberately: a drawer is the one part of this page
        that would not survive an export from a downloads folder, a
        print, `filter: grayscale`, or a pasted anchor. Asserted as an
        absence, because the whole value of the decision is that
        nothing was added."""
        source = open(os.path.join(REPO, "bga/viewer/views.js"),
                      encoding="utf-8").read()
        css = open(os.path.join(REPO, "bga/viewer/style.css"),
                   encoding="utf-8").read()
        # Not `z-index`: the sticky table header has used one since
        # `UX-205` and it is not an overlay. What is banned is the
        # thing that takes the element out of the document - a modal,
        # or a panel pinned to the viewport.
        for banned in ("dialog", "showModal", "position: fixed",
                       "position:fixed"):
            assert banned not in source, f"{banned} is overlay machinery"
            assert banned not in css, f"{banned} is overlay machinery"

    def test_the_element_sections_are_capped_with_a_named_elision(self):
        """`UX-187`'s rule. A 4,000-element report must not render
        4,000 sections, and the elision must name its own count."""
        out = _node(_ELISION)
        assert out["sections"] == out["shown"], out
        assert out["elided"] == out["total"] - out["shown"], out
        assert str(out["elided"]) in out["note"], out["note"]

    def test_the_sections_are_in_the_investigate_rail(self):
        out = _render(_report())
        for section in out["element_sections"]:
            assert section["rail"] == "investigate", section


_ELISION = """
globalThis.document = { createElement: (t) => make(t),
                        createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: t,
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
function _styleFor(node) {
  // A real DOM reflects `el.style.x = v` into the `style` attribute, and
  // serialises it as `x: v;` - measured in Chrome 141, not assumed. The
  // shims used to carry `style: {}`, which swallowed every write: the
  // four encodings `UX-263` fixed looked set here and were refused by
  // the browser. An instrument that cannot see the defect is how the
  // defect shipped (`UX-235`, `UX-262`, and now this).
  const decls = new Map();
  const kebab = (k) => String(k).startsWith("--")
    ? String(k) : String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
  const flush = () => {
    if (decls.size === 0) { delete node.attrs.style; return; }
    node.attrs.style = [...decls].map(([k, v]) => `${k}: ${v};`).join(" ");
  };
  return new Proxy({
    setProperty(name, value) { decls.set(String(name), String(value)); flush(); },
    getPropertyValue(name) { return decls.get(String(name)) ?? ""; },
    removeProperty(name) { decls.delete(String(name)); flush(); },
  }, {
    set(_t, prop, value) { decls.set(kebab(prop), String(value)); flush(); return true; },
    get(target, prop) {
      if (prop in target) return target[prop];
      return decls.get(kebab(prop)) ?? "";
    },
  });
}
function make(tag) {
  return { tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "",
    get style() { return this._style ??= _styleFor(this); },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x : this.children.push(x); } },
    querySelectorAll() { return []; } };
}
const views = await import("./bga/viewer/views.js");
const total = views.ELEMENTS_SHOWN + 7;
const payload = { signals: { critical_path_detail:
  Array.from({length: total}, (_, i) => ({ element_uid: `e-${i}.bst`,
    share_of_path: 0.01, duration_us: 1000 })) } };
const nodes = views.renderElementSections(payload, make("div"), {});
const sections = nodes.filter((n) => n.tagName === "section");
const note = nodes.find((n) => n.attrs["data-elided"]);
console.log(JSON.stringify({ total, shown: views.ELEMENTS_SHOWN,
  sections: sections.length, elided: Number(note?.attrs["data-elided"] ?? 0),
  note: note?.textContent ?? "" }));
"""

_SHIM = """
function _styleFor(node) {
  // A real DOM reflects `el.style.x = v` into the `style` attribute, and
  // serialises it as `x: v;` - measured in Chrome 141, not assumed. The
  // shims used to carry `style: {}`, which swallowed every write: the
  // four encodings `UX-263` fixed looked set here and were refused by
  // the browser. An instrument that cannot see the defect is how the
  // defect shipped (`UX-235`, `UX-262`, and now this).
  const decls = new Map();
  const kebab = (k) => String(k).startsWith("--")
    ? String(k) : String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
  const flush = () => {
    if (decls.size === 0) { delete node.attrs.style; return; }
    node.attrs.style = [...decls].map(([k, v]) => `${k}: ${v};`).join(" ");
  };
  return new Proxy({
    setProperty(name, value) { decls.set(String(name), String(value)); flush(); },
    getPropertyValue(name) { return decls.get(String(name)) ?? ""; },
    removeProperty(name) { decls.delete(String(name)); flush(); },
  }, {
    set(_t, prop, value) { decls.set(kebab(prop), String(value)); flush(); return true; },
    get(target, prop) {
      if (prop in target) return target[prop];
      return decls.get(kebab(prop)) ?? "";
    },
  });
}
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "", hidden: false, open: false, value: "", parentNode: null,
    listeners: {},
    get style() { return this._style ??= _styleFor(this); },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      if (typeof x === "string") { this.textContent += x; continue; }
      const at = this.children.indexOf(x);
      if (at !== -1) this.children.splice(at, 1);
      x.parentNode = this; this.children.push(x); } },
    prepend(...xs) { for (const x of [...xs].reverse()) { if (x == null) continue;
      const at = this.children.indexOf(x);
      if (at !== -1) this.children.splice(at, 1);
      x.parentNode = this; this.children.unshift(x); } },
    replaceChildren(...xs) { this.children = []; this.textContent = "";
      this.append(...xs); },
    querySelector(sel) { return this.querySelectorAll(sel)[0] ?? null; },
    querySelectorAll(sel) {
      const match = (n, part) => {
        const tag = part.match(/^[a-zA-Z][\\w-]*/);
        if (tag && n.tagName !== tag[0]) return false;
        for (const cls of part.match(/\\.[\\w-]+/g) ?? []) {
          if (!String(n.className ?? "").split(/\\s+/).includes(cls.slice(1)))
            return false;
        }
        for (const attr of part.match(/\\[[^\\]]+\\]/g) ?? []) {
          const [, name, value] = attr.match(
            /^\\[([\\w:-]+)(?:=["']?([^"'\\]]*)["']?)?\\]$/) ?? [];
          if (!name) return false;
          const held = n.getAttribute?.(name) ?? null;
          if (held === null) return false;
          if (value !== undefined && held !== value) return false;
        }
        return true;
      };
      let found = [this];
      for (const part of sel.trim().split(/\\s+/)) {
        const next = [];
        for (const root of found) {
          (function walk(n) { for (const c of n.children ?? []) {
            if (match(c, part)) next.push(c); walk(c); } })(root);
        }
        found = next;
      }
      return found;
    },
  };
}
// A text node carries `attrs` too - not because the DOM does, but
// because every walker here reads `attrs`, and a bare `{}` turns a
// missing-attribute question into a TypeError three frames deep.
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: t,
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
"""

_HARNESS = _SHIM + """
const app = await import("./bga/viewer/app.js");
const views = await import("./bga/viewer/views.js");
const nav = await import("./bga/viewer/nav.js");
const { readFileSync } = await import("node:fs");
const [payloadPath, schemaPath] = %s;
const payload = JSON.parse(readFileSync(payloadPath, "utf8"));
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));

const root = make("div");
app.render(payload, schema, root);
// The views `boot()` appends after `render()` - the chain, the
// decision panel, the blast tree - because those draw most of the
// element names and a harness that skipped them would measure the
// wrong document.
for (const node of [views.renderCriticalPath(payload),
                    views.renderDecision(payload, null),
                    views.renderBlastTree(payload)]) {
  if (node) root.append(node);
}
for (const node of views.renderElementSections(payload, root,
                                               { quantity: app.quantity })) {
  root.append(node);
}
nav.anchor(root);

const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const href = (n) => n.href ?? n.attrs.href ?? "";
const ids = new Set(all(root, (n) => n.attrs.id || n.id)
  .map((n) => n.attrs.id || n.id));
const links = all(root, (n) => href(n).startsWith("#element-")).map(href);
const inspects = all(root, (n) => n.className === "inspect").map(href);
const unresolved = (hs) =>
  [...new Set(hs.map((h) => h.slice(1)))].filter((t) => !ids.has(t));

const sections = all(root,
    (n) => (n.attrs["data-section"] ?? "").startsWith("element-"))
  .map((n) => ({
    element: n.attrs["data-element"],
    id: n.attrs.id,
    anchor: views.elementAnchor(n.attrs["data-element"]),
    rail: n.attrs["data-rail"],
    fields: Object.fromEntries(all(n, (c) => c.attrs["data-field"])
      .map((c) => [c.attrs["data-field"], c.attrs["data-raw"]])),
    findings: all(n, (c) => c.attrs["data-finding"])
      .map((c) => c.attrs["data-finding"]),
    where: all(n, (c) => c.attrs["data-where"]).map((c) => c.attrs["data-where"]),
  }));

console.log(JSON.stringify({
  element_links: links.length,
  distinct: [...new Set(links)].length,
  unresolvable: unresolved(links),
  inspect_links: inspects.length,
  inspect_unresolvable: unresolved(inspects),
  element_sections: sections,
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
