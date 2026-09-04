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
