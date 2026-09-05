#!/usr/bin/env python3
"""UX-665: the page's census, so a walk reads it instead of driving it.

Boots an export once through `tests/browser.py` and prints its
structure as JSON: sections (id, chapter, depth), rail entries,
controls grouped by selector class (selector, label, count, one
example section), tables with a nested table inside a cell (`UX-532`'s
shape), drawings and whether each carries its table twin (styleguide
§2a), which planes the run carries, and the counters
`test_the_page_has_a_volume_budget.py` already takes.

A walker or a design review reads this before touching the page and
drives one instance per class it names; this tool drives nothing.
"""
import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.browser import NO_BROWSER, Browser, find_chrome

#: Attributes whose *name* (not value) marks a control's kind when it
#: carries no class - `data-step="top"` and `data-step="next"` are the
#: same kind of button, three copies of a stepper.
_ROLE_ATTRS = ("data-step", "data-collapse", "data-all", "data-toc-chapter",
              "data-run-jump", "data-fold", "type")

CENSUS_JS = r"""
(() => {
  const main = document.querySelector("main") || document.body;

  const nearestSection = (el) =>
    el.closest("[data-section]")?.getAttribute("data-section") || null;

  const depthOf = (el) => {
    let d = 0, node = el.parentElement;
    while (node) {
      if (node.matches?.("section[data-section]")) d += 1;
      node = node.parentElement;
    }
    return d;
  };

  const sections = [...main.querySelectorAll("section[data-section]")].map((s) => ({
    id: s.getAttribute("data-section"),
    chapter: s.closest("section.chapter")?.getAttribute("data-section") || null,
    depth: depthOf(s),
  }));

  const rail = [...document.querySelectorAll("[data-toc]")].map((a) => ({
    toc: a.getAttribute("data-toc"),
    rail: a.getAttribute("data-rail"),
    label: (a.textContent || "").trim(),
  }));

  // `UX-334`: a `select` or `input`'s own text is empty or every
  // option concatenated - its accessible name is the `<label for=>`.
  const label = (el) => {
    const owned = el.id
      && document.querySelector(`label[for="${el.id}"]`)?.textContent.trim();
    return owned || (el.textContent || "").trim().slice(0, 60)
      || el.getAttribute("aria-label") || el.getAttribute("title") || "";
  };

  const signature = (el) => {
    const tag = el.tagName.toLowerCase();
    const cls = [...el.classList].sort();
    if (cls.length) return `${tag}.${cls.join(".")}`;
    for (const attr of __ROLE_ATTRS__) {
      if (el.hasAttribute(attr)) {
        return attr === "type" ? `${tag}[type=${el.getAttribute("type")}]`
                                : `${tag}[${attr}]`;
      }
    }
    return tag;
  };

  // Document-wide, not `main`: the stepper (Top/Prev/Next), the jump
  // box and the run selector live in the rail beside `main`, and a
  // control census scoped to the report body cannot see them - found
  // by the falsify mutation below missing a control planted there.
  // Rail links themselves are counted as `rail`, not `controls` - a
  // walker drives a control class, and the rail is navigation the
  // census already lists by name.
  const controlEls = [...document.querySelectorAll("button, select, input, a[href]")]
    .filter((el) => !el.hasAttribute("data-toc")
                   && !el.hasAttribute("data-toc-chapter")
                   && !el.hasAttribute("data-toc-sub"));

  const byClass = new Map();
  for (const el of controlEls) {
    const key = signature(el);
    if (!byClass.has(key)) {
      byClass.set(key, { selector: key, label: label(el), count: 0,
                         example_section: nearestSection(el) });
    }
    byClass.get(key).count += 1;
  }
  const controls = [...byClass.values()].sort(
    (a, b) => a.selector.localeCompare(b.selector));

  const tablesWithNested = [...main.querySelectorAll("table")]
    .filter((t) => t.querySelector("td table, th table"))
    .map((t) => ({ section: nearestSection(t),
                   nested: t.querySelectorAll("td table, th table").length }));

  // `UX-316` (§2a): the grade is on the drawing's own element - the
  // `svg` for a bespoke one, its wrapping `div` for a sparkline or
  // density strip - and its table twin sits a few ancestors up, in the
  // wrapper the renderer built both into.
  const nearestTwin = (drawn) => {
    let node = drawn.parentElement;
    for (let hop = 0; hop < 2 && node; hop += 1) {
      const twin = node.querySelector(".draw-twin");
      if (twin) return twin;
      node = node.parentElement;
    }
    return null;
  };
  const drawings = [...main.querySelectorAll("[data-grade]")].map((drawn) => ({
    grade: drawn.getAttribute("data-grade"),
    role: drawn.getAttribute("data-role") || drawn.tagName.toLowerCase(),
    section: nearestSection(drawn),
    has_twin: nearestTwin(drawn) !== null,
  }));

  const statusText = document.querySelector('[data-role="status"]')?.textContent || "";
  const trace = document.querySelector("#perfetto-questions [data-planes]")
    ?.getAttribute("data-planes") || null;

  return {
    sections, rail, controls,
    tables_with_nested: tablesWithNested,
    drawings,
    planes: {
      plane2: statusText.includes("Plane 2:")
             && !statusText.includes("Plane 2 not captured"),
      trace,
    },
    // The same instrument `test_the_page_has_a_volume_budget.py` reads,
    // at the page's landed state - this boots once and drives nothing.
    counters: {
      height: document.documentElement.scrollHeight,
      words: (main.textContent || "").trim().split(/\s+/).filter(Boolean).length,
      controls: document.querySelectorAll("button, input, select, a").length,
      nodes: document.querySelectorAll("*").length,
      sections: sections.length,
    },
  };
})()
""".replace("__ROLE_ATTRS__", json.dumps(_ROLE_ATTRS))


def census(url, browser=None):
    """The census of the export at `url` (a `file://` or `http://` URI).

    `browser`, if given, is a live `Browser` a caller already opened -
    a guard measuring several pages pays for one Chromium, not one per
    page. Without one, this opens and closes its own.
    """
    if browser is not None:
        return browser.measure(url, CENSUS_JS)
    chrome = find_chrome()
    if chrome is None:
        raise RuntimeError(NO_BROWSER)
    with Browser(chrome) as opened:
        return opened.measure(url, CENSUS_JS)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", help="an exported page's path or URI")
    args = parser.parse_args(argv)

    target = args.export
    if "://" not in target:
        target = pathlib.Path(target).resolve().as_uri()
    try:
        result = census(target)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
