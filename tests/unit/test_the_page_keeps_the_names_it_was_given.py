"""UX-374: a key that is data is rendered as it was published.

`format.js`'s `title()` capitalises the first character of every key,
replaces underscores with spaces and trims a declared unit suffix. All
three are right for a *schema* key — `element_durations` should read
"Element durations" — and all three were applied to map keys that are
**data**: the reader's own element uids and the programs their build
ran. Measured on `tests/fixtures/macro_micro`, before:

```text
published                          rendered
codegen.bst|BUILD|BUILD|0          Codegen.bst|BUILD|BUILD|0
cmake                              Cmake
cc1plus                            Cc1plus
```

Twenty-two data keys on that fixture and **every one renamed**. A
reader searching the page for `cmake` did not find the row; a reader
copying one pasted a name their project does not have. That is
`UX-326`'s rule — the tool's sentences are contracts — applied to the
one class of string the tool must never author: a name it was given.

**The schema already draws the line**, so no new hint was needed:
`childNode` has resolved a declared member through `properties` and a
data-keyed map's value through `additionalProperties` since `UX-343`.
`dataKeyed` reads the same node and says which branch applies.

**Both directions matter and this file holds both.** The cheap wrong
fix is to stop humanising: then `violation_count` reads
`violation_count` and the page is worse for every contract key on it.
`TestASchemaKeyStillReadsAsEnglish` is that half — 241 of them on
`macro_micro`, and they are still English.
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The maps this item is about, by the path their keys live at. Named
#: rather than discovered, because "every map with `additionalProperties`"
#: is the *implementation's* predicate and a guard that reuses it would
#: agree with the code by construction.
DATA_KEYED = (
    ("wall_clock_share_us", ()),
    ("by_binary", ()),
    ("element_durations", ("elements",)),
    ("slack", ("elements",)),
    ("downstream_count", ("elements",)),
)

#: A schema key that must still read as English, and what it must read
#: as. Two of them, because one could be satisfied by an accident.
HUMANISED = {"element_durations": "Element durations",
             "violation_count": "Violation count"}

#: What the reader sees against what the payload published. `data-key`
#: carries the key verbatim and always has; the label is the text node
#: before the `?` marker, so the two are directly comparable. Every
#: chapter and every fold is opened first - a key inside a closed
#: `details` is still in the DOM, and the ones this item is about are.
_LOOK = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  for (const d of document.querySelectorAll("details")) d.open = true;
  const label = (n) => ((n.childNodes[0] || {}).textContent || "").trim();
  const seen = [];
  for (const dt of document.querySelectorAll("dt[data-key]")) {
    seen.push({ key: dt.getAttribute("data-key"), shown: label(dt),
                where: (dt.closest("section[data-section]") || {})
                  .getAttribute?.("data-section") || null });
  }
  // `UX-374` labels an inline object's keys through the same call, so
  // the guard reads that site too rather than the one it was filed on.
  for (const span of document.querySelectorAll(".pair-key[data-key]")) {
    seen.push({ key: span.getAttribute("data-key"),
                shown: (span.textContent || "").trim(), where: "inline" });
  }
  return { seen };
})()
"""


def _payload(label):
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES[label]))["report.json"]


def _published(payload, name, under):
    at = payload
    for step in under:
        at = (at or {}).get(step) or {}
    return set((at or {}).get(name) or {})


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def looked(browser, tmp_path_factory):
    into = tmp_path_factory.mktemp("u374")
    return {label: browser.measure(
        pages.export_uri(pages.FIXTURES[label], into, name=f"{label}.html"),
        _LOOK, 1440, 900) for label in sorted(pages.FIXTURES)}


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestADataKeyIsRenderedAsPublished:
    def test_every_data_key_on_the_page_is_spelled_as_it_was_given(
            self, looked, label):
        """The clause the defect fails: it was 22 of 22 on
        `macro_micro`, 0 of 22 correct."""
        payload = _payload(label)
        data = set()
        for name, under in DATA_KEYED:
            data |= _published(payload, name, under)
        if not data:
            pytest.skip(f"{label} publishes none of the data-keyed maps")
        renamed = [row for row in looked[label]["seen"]
                   if row["key"] in data and row["shown"] != row["key"]]
        assert renamed == [], (
            f"{label}: the page renamed {len(renamed)} of the reader's own "
            f"names, e.g. {renamed[:3]}")

    @pytest.mark.parametrize("name", ["wall_clock_share_us", "by_binary"])
    def test_the_reader_can_find_what_they_searched_for(self, looked, label,
                                                        name):
        """Non-vacuity, and not against a round number. The clause above
        passes trivially if no data key reaches a `<dt>` at all, so
        these two maps - the ones that render as pair lists on both
        fixtures - must deliver **every** key they publish.

        Not all five of `DATA_KEYED`: `UX-268` merged the three
        element-keyed signals into one table, so on `golden` they reach
        no `<dt>` by design. A floor over the union would have been a
        number chosen to pass rather than a property."""
        published = _published(_payload(label), name, ())
        if not published:
            pytest.skip(f"{label} publishes no {name}")
        shown = {row["key"] for row in looked[label]["seen"]}
        missing = sorted(published - shown)
        assert missing == [], (
            f"{label}: {len(missing)} of {len(published)} {name} keys reach "
            f"no label at all, so the clause above is guarding an absence: "
            f"{missing[:3]}")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestASchemaKeyStillReadsAsEnglish:
    """The other direction, so the fix cannot be "stop humanising"."""

    def test_the_named_schema_keys_read_as_english(self, looked, label):
        by_key = {}
        for row in looked[label]["seen"]:
            by_key.setdefault(row["key"], row["shown"])
        checked = 0
        for key, reads in HUMANISED.items():
            if key not in by_key:
                continue
            checked += 1
            assert by_key[key] == reads, (
                f"{label}: {key!r} reads {by_key[key]!r}, not {reads!r} - "
                f"a contract key is not the reader's name")
        if not checked:
            pytest.skip(f"{label} renders neither of {sorted(HUMANISED)}")

    def test_most_of_the_page_is_still_humanised(self, looked, label):
        """The aggregate, because two named keys could survive a change
        that flattened everything else. Measured at 241 of 263 on
        `macro_micro` after this item."""
        payload = _payload(label)
        data = set()
        for name, under in DATA_KEYED:
            data |= _published(payload, name, under)
        schema = [row for row in looked[label]["seen"]
                  if row["key"] not in data]
        humanised = [row for row in schema if row["shown"] != row["key"]]
        assert len(humanised) > len(schema) * 0.5, (
            f"{label}: {len(humanised)} of {len(schema)} contract keys read "
            f"as English; the fix has become 'stop humanising'")


@needs_node
class TestThePredicateIsTheSchemas:
    """`dataKeyed` at the node level, driven directly.

    The browser clauses above run over whatever the two fixtures happen
    to publish. These name the shapes: `properties` wins, `additional
    Properties` means data, `items` is neither, and an absent schema
    says nothing - which is the status-quo branch and the one a reading
    of the diff would skip.
    """

    @staticmethod
    def _ask(script):
        import json
        import os

        result = subprocess.run(
            [node, "--input-type=module", "-e",
             'const f = await import("./bga/viewer/format.js");'
             f"console.log(JSON.stringify({script}));"],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_a_declared_property_is_not_data(self):
        assert self._ask(
            'f.dataKeyed({properties: {core: {type: "number"}}}, "core")'
        ) is False

    def test_a_map_declaring_its_value_once_is_data(self):
        assert self._ask(
            'f.dataKeyed({additionalProperties: {type: "number"}}, "core.bst")'
        ) is True

    def test_a_declared_property_wins_over_additional_ones(self):
        """Both present is the shape a partly-declared map has, and the
        named member is contract however the rest is keyed."""
        node = ('{properties: {total_us: {}}, '
                'additionalProperties: {type: "number"}}')
        assert self._ask(f'f.dataKeyed({node}, "total_us")') is False
        assert self._ask(f'f.dataKeyed({node}, "core.bst")') is True

    def test_an_array_is_neither(self):
        assert self._ask('f.dataKeyed({items: {properties: {}}}, "0")') is False

    def test_no_schema_says_nothing(self):
        """The status quo, asserted so it is a decision rather than an
        oversight: an undeclared node cannot tell the two apart, and
        guessing 'data' would strip English off contract keys."""
        assert self._ask('f.dataKeyed(undefined, "x")') is False
        assert self._ask('f.dataKeyed(null, "x")') is False
        assert self._ask('f.dataKeyed({type: "object"}, "x")') is False

    def test_title_leaves_a_published_key_entirely_alone(self):
        """All three transformations, not just the capital. `a_b.bst`
        is not "A b.bst", and a program called `x_us` keeps its tail."""
        assert self._ask('f.title("a_b.bst", null, true)') == "a_b.bst"
        assert self._ask('f.title("x_us", "duration_us", true)') == "x_us"
        assert self._ask('f.title("cmake", null, true)') == "cmake"

    def test_title_still_humanises_a_contract_key(self):
        assert self._ask('f.title("violation_count")') == "Violation count"
        assert self._ask('f.title("path_us", "duration_us")') == "Path"


#: The inline-object branch, driven without a browser. `renderStructured`
#: is reached through `tests/viewer.mjs`, the one namespace `UX-337` set
#: up for exactly this.
_INLINE = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
const make = (tag) => _makeNode(tag);
globalThis.document = { createElement: make,
                        createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const v = await import("./tests/viewer.mjs");
const out = v.renderStructured("m", __VALUE__, {}, __NODE__, 0, "m");
const keys = [];
(function walk(n) {
  if (!n) return;
  if (String(n.className || "").includes("pair-key")) {
    keys.push({ key: n.attrs["data-key"],
                shown: (n.textContent || "").trim() });
  }
  (n.children ?? []).forEach(walk);
})(out);
console.log(JSON.stringify(keys));
"""


@needs_node
class TestTheInlineObjectAsksToo:
    """`renderStructured`'s **inline object** branch, driven directly.

    A map of four or fewer scalars renders as one line of `pair-key`
    spans rather than a table (`shapes.js`'s `inlineFields`), through a
    second call to `title` - so it is a second place a name can be
    rewritten. Neither committed fixture publishes a data-keyed map
    small enough to reach it: mutation M6 removed the predicate from
    that call site and every browser clause above stayed green.

    That is the gap `UX-368` spent four rounds inside and `UX-372`'s own
    M6 hit again - a branch no fixture reaches is a branch asserted
    against nothing. This drives the renderer with the shape rather than
    waiting for a capture to produce one.
    """

    @staticmethod
    def _render(value, schema):
        """`schema`, not `node` - the module-level `node` is the
        interpreter this runs in, and shadowing it handed `subprocess`
        a dict."""
        import json
        import os

        script = (_INLINE.replace("__VALUE__", json.dumps(value))
                         .replace("__NODE__", json.dumps(schema)))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_a_small_data_keyed_map_keeps_its_names(self):
        keys = self._render({"cc1plus": 3, "cmake": 1},
                            {"type": "object",
                             "additionalProperties": {"type": "number"}})
        assert keys, "the inline-object branch drew no pair keys"
        # Named before it is used: without `data-key` the label has
        # nothing to be compared against, and the clause would fail as
        # a `KeyError` rather than as a sentence.
        blind = [k for k in keys if not k.get("key")]
        assert blind == [], (
            f"{len(blind)} pair key(s) publish no `data-key`, so what the "
            f"reader sees cannot be checked against what was given")
        renamed = [k for k in keys if k["shown"] != k["key"]]
        assert renamed == [], (
            f"the inline object renamed the reader's programs: {renamed}")

    def test_a_small_declared_map_still_reads_as_english(self):
        """The same shape, declared - so this cannot pass by the
        renderer having stopped humanising everywhere."""
        keys = self._render(
            {"violation_count": 3},
            {"type": "object",
             "properties": {"violation_count": {"type": "number"}}})
        assert keys, "the inline-object branch drew no pair keys"
        assert keys[0]["shown"] == "Violation count", keys


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
