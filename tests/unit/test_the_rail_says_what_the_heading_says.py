"""UX-640: the rail named the key, the heading asked the question.

Two label functions, nothing tying them: the rail used
`data-toc-label || label(key)` and the body `heading(key, hint).label`.
Counted on both committed fixtures, rail entries whose text differs
from the label of the section they lead to:

```text
                  entries   differing   after
golden               46         39        0
macro_micro          66         52        0
```

`Wall clock share us`, `Cpu time` and `Plane2 coverage` were rail
entries for sections headed "How much of the run did each task hold?",
"What did the whole build cost in CPU?" and "How much of this run came
from the second plane?".

The rail reads the destination's own `h2` now, so there is one label
authority and a question added to a heading reaches the rail without
anyone remembering to. This file is what holds them together.

**A browser guard**, because `tests/dom_shim.mjs` keeps a node's text
in one string and has no `childNodes`: the heading's own text cannot be
told from its controls' there, and `headingLabel` returns `null`.

`UX-648` extends it to the palette, which `UX-640` did not reach and
which went on naming sections `label(key)`. Sections a reader finds by
typing what the page calls the section, on both fixtures:

```text
                sections   reached before   reached after
golden              46            0              46
macro_micro         66            0              65
```

Every one of the 46 and the 66 had a `label(key)` differing from its
heading, so the palette was searchable only by the mangled key.
`macro_micro`'s `summary` is headed `Run`, three characters that put it
past `matches`' eight-row limit - which is `UX-223`'s ranking and out
of this item's scope, so the floor below is a floor and not equality.
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

#: One row per rail entry: what the rail calls it, and what the section
#: it points at calls itself.
#:
#: The heading's **own** text. `sectionHead` writes `heading().label`
#: into the `h2` as text and everything else in there is an element -
#: the collapse control, the `section-key` span, the JSON toggle - so
#: the text nodes are the label and nothing else is. Read positionally
#: rather than by subtracting the controls' strings: `cache`'s key span
#: reads `cache` and its label ends `...from the cache?`, and a search
#: takes the wrong one.
_LABELS = """
(() => {
  const own = (node) => [...node.childNodes]
    .filter((child) => child.nodeType === 3)
    .map((child) => child.textContent || "").join("").trim();
  return [...document.querySelectorAll("nav.toc [data-toc]")].map((link) => {
    const key = link.getAttribute("data-toc");
    const section = document.querySelector(`[data-section="${key}"]`);
    const head = section && section.querySelector("h2");
    return {
      key,
      rail: (link.textContent || "").trim(),
      heading: head && head.parentElement === section ? own(head) : null,
    };
  });
})()
"""


#: No `skip` of its own: every consumer is `needs_browser`, and a
#: `skipif` mark is evaluated before a fixture is set up - so a second
#: `NO_BROWSER` here would be a reason that never fires and one more
#: line `tests/skip_reasons.py` cannot read (`UX-449`).
@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    with Browser(chrome) as opened:
        return {label: opened.measure(uri, _LABELS, 1440, 900)
                for label, uri in pages.pages(tmp_path_factory, "rail").items()}


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheRailAsksWhatTheHeadingAsks:
    def test_every_entry_leads_to_a_section_that_names_itself(self, booted,
                                                              label):
        """The population, so nothing below can pass on an empty rail or
        on a rail whose entries all fell back to the key."""
        rows = booted[label]
        assert len(rows) >= 40, len(rows)
        headed = [row for row in rows if row["heading"]]
        assert len(headed) == len(rows), (
            [row["key"] for row in rows if not row["heading"]])
        asking = [row for row in rows if row["heading"].endswith("?")]
        assert len(asking) >= 25, (
            f"only {len(asking)} of {len(rows)} headings ask a question; the "
            f"agreement below would be about labels nobody renamed")

    def test_the_rail_entry_reads_its_destinations_heading(self, booted,
                                                           label):
        """The whole item, over every rendered section at once."""
        rows = booted[label]
        differ = [(row["key"], row["rail"], row["heading"])
                  for row in rows if row["rail"] != row["heading"]]
        assert not differ, (
            f"{len(differ)} of {len(rows)} rail entries name their section "
            f"something the section does not: {differ[:5]}")


#: `UX-648`: one row per section, driven through the palette itself.
#:
#: The export ships the modules inside a `<script type="module">`, so
#: `jumpTargets` is not reachable from an evaluated expression - the
#: population is read the way a reader reaches it, by typing. The query
#: is the section's own heading: if the palette carries the label
#: authority the rail does, typing what the page calls a section finds
#: it, and `palette` comes back equal to `heading`.
#:
#: Only the `SECTIONS` group is read - an element uid and a section key
#: can both appear as `data-jump`, and the groups tell them apart.
_PALETTE = """
(() => {
  const own = (node) => [...node.childNodes]
    .filter((child) => child.nodeType === 3)
    .map((child) => child.textContent || "").join("").trim();
  const box = document.getElementById("jump");
  const rail = new Map([...document.querySelectorAll("nav.toc [data-toc]")]
    .map((link) => [link.getAttribute("data-toc"),
                    (link.textContent || "").trim()]));
  const offered = () => {
    const head = document.querySelector('.jump-hits li[data-group="SECTIONS"]');
    const rows = [];
    for (let node = head && head.nextElementSibling; node;
         node = node.nextElementSibling) {
      if (node.classList.contains("palette-group")) break;
      const button = node.querySelector("button[data-jump]");
      if (button) rows.push([button.getAttribute("data-jump"),
                             (button.textContent || "").trim()]);
    }
    return rows;
  };
  const out = [];
  for (const section of document.querySelectorAll("section[data-section]")) {
    const key = section.getAttribute("data-section");
    const head = section.querySelector("h2");
    const heading = head && head.parentElement === section ? own(head) : null;
    if (!heading) { out.push({ key, heading: null, palette: null }); continue; }
    box.value = heading;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    const hit = offered().find(([jump]) => jump === key);
    out.push({ key, heading, palette: hit ? hit[1] : null,
               rail: rail.get(key) ?? null });
  }
  box.value = "";
  box.dispatchEvent(new Event("input", { bubbles: true }));
  return out;
})()
"""


@pytest.fixture(scope="module")
def palette(tmp_path_factory):
    with Browser(chrome) as opened:
        return {label: opened.measure(uri, _PALETTE, 1440, 900)
                for label, uri in pages.pages(tmp_path_factory,
                                              "palette").items()}


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestThePaletteAsksWhatTheHeadingAsks:
    def test_a_section_is_reachable_by_what_the_page_calls_it(self, palette,
                                                              label):
        """The population, so the agreement below cannot pass on a
        palette offering no sections at all: 0 of 46 and 0 of 66 before
        this item, 46 and 65 after."""
        rows = palette[label]
        assert len(rows) >= 40, len(rows)
        reached = [row for row in rows if row["palette"] is not None]
        assert len(reached) >= 40, (
            f"only {len(reached)} of {len(rows)} sections are reachable by "
            f"typing their own heading: "
            f"{[row['key'] for row in rows if row['palette'] is None][:5]}")

    def test_the_palette_entry_reads_its_destinations_heading(self, palette,
                                                              label):
        """The item: one string per section over rail, palette and
        heading."""
        rows = [row for row in palette[label] if row["palette"] is not None]
        differ = [(row["key"], row["palette"], row["heading"], row["rail"])
                  for row in rows
                  if row["palette"] != row["heading"]
                  or row["palette"] != row["rail"]]
        assert not differ, (
            f"{len(differ)} of {len(rows)} palette entries name their section "
            f"something the section or the rail does not: {differ[:5]}")
