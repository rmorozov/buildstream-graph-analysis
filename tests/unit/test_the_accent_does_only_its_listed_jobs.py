"""UX-1048: the accent does the eight jobs styleguide §4.2's table lists.

Static: the (grade, selector, channel) triples `style.css` spends
`var(--accent)`/`var(--accent-mark)` on equal the table's, both ways.
Booted: golden and `macro_micro` at 1440x900, dark, light and print -
every element whose computed colour, border, background, outline,
box-shadow, fill or stroke is an accent grade matches a table selector
for that grade and channel, and each at-rest job is seen on every page.
"""
import json
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome
from pages import FIXTURES, export_uri

CSS = (REPO / "bga/viewer/style.css").read_text()
GUIDE = (REPO / "docs/design/styleguide.md").read_text()

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")

TOKEN = re.compile(r"var\(--(accent(?:-mark)?)\)")
AT_REST = {1, 5, 7, 8}
MODES = ("dark", "light", "print")


def _channel(prop):
    """A declaration's property, as the channel the table names."""
    for family in ("border", "outline", "background"):
        if prop.startswith(family):
            return family
    return prop


def _selector(text):
    text = re.sub(r"\s*>\s*", " > ", text)
    return re.sub(r"\s+", " ", text).strip()


def _rules(text):
    """`(selector list, body)` for every style rule, at-rule blocks opened."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    pos = 0
    while (brace := text.find("{", pos)) != -1:
        prelude = text[pos:brace].rsplit(";", 1)[-1].strip()
        depth, end = 1, brace + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        body = text[brace + 1:end - 1]
        if prelude.startswith("@"):
            if "{" in body:
                yield from _rules(body)
        else:
            yield prelude, body
        pos = end


def css_uses():
    uses = set()
    for prelude, body in _rules(CSS):
        for decl in body.split(";"):
            prop, _, value = decl.partition(":")
            for grade in TOKEN.findall(value):
                for sel in prelude.split(","):
                    uses.add((grade, _selector(sel), _channel(prop.strip())))
    return uses


def table_rows():
    """`[(job, grade, [channel], [selector])]` from §4.2's table."""
    section = GUIDE.split("## 4. Color and emphasis", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not re.match(r"\d+ ", cells[0]):
            continue
        rows.append((int(cells[0].split()[0]), cells[1],
                     [c.strip() for c in cells[2].split(",")],
                     [_selector(s) for s in re.findall(r"`([^`]+)`", cells[3])]))
    return rows


def table_uses():
    return {(grade, sel, ch) for _, grade, chans, sels in table_rows()
            for ch in chans for sel in sels}


class TestTheStylesheetSpendsTheAccentOnlyOnListedJobs:

    def test_the_table_has_eight_jobs(self):
        assert {row[0] for row in table_rows()} == set(range(1, 9))

    def test_every_accent_declaration_is_a_listed_job(self):
        assert sorted(css_uses() - table_uses()) == []

    def test_every_listed_job_is_declared(self):
        assert sorted(table_uses() - css_uses()) == []


#: Every element's accent uses, checked against the table's rows in the
#: page itself; an inherited colour, fill or stroke is its parent's.
BOOTED = r"""
(() => {
  const rows = %s;
  if (%s) for (const sheet of document.styleSheets)
    for (const rule of sheet.cssRules)
      if (rule.media && /prefers-color-scheme:\s*light/.test(rule.media.mediaText))
        rule.media.mediaText = "not all";
  const probe = document.createElement("div");
  document.body.appendChild(probe);
  const tokens = {};
  for (const t of ["accent", "accent-mark"]) {
    probe.style.color = `var(--${t})`;
    tokens[t] = getComputedStyle(probe).color;
  }
  probe.remove();
  const sides = ["Top", "Right", "Bottom", "Left"];
  const inherited = new Set(["color", "fill", "stroke"]);
  const strays = new Set(), jobs = new Set();
  for (const el of document.querySelectorAll("body *")) {
    const s = getComputedStyle(el);
    const parent = el.parentElement ? getComputedStyle(el.parentElement) : null;
    const values = {
      color: [s.color], background: [s.backgroundColor],
      fill: [s.fill], stroke: [s.stroke], "box-shadow": [s.boxShadow],
      outline: s.outlineStyle === "none" ? [] : [s.outlineColor],
      border: sides.filter((k) => s[`border${k}Style`] !== "none"
                           && parseFloat(s[`border${k}Width`]) > 0)
                   .map((k) => s[`border${k}Color`]),
    };
    for (const [channel, seen] of Object.entries(values)) {
      for (const value of seen) {
        const grades = Object.keys(tokens).filter((t) => value.includes(tokens[t]));
        if (!grades.length) continue;
        const prop = {background: "backgroundColor"}[channel] ?? channel;
        if (inherited.has(channel) && parent && parent[prop] === value) continue;
        const hit = rows.filter(([, grade, chans, sels]) => grades.includes(grade)
          && chans.includes(channel) && sels.some((sel) => el.matches(sel)));
        if (!hit.length) {
          strays.add(`${el.tagName.toLowerCase()}${[...el.classList].map((c) => "." + c).join("")}`
                     + ` ${channel} ${grades.join("|")}`);
        }
        hit.forEach(([job]) => jobs.add(job));
      }
    }
  }
  return {strays: [...strays].sort(), jobs: [...jobs].sort()};
})()
"""


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    """`{(fixture, mode): {strays, jobs}}`, one browser for all six."""
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)
    rows = json.dumps(table_rows())
    out = {}
    with Browser(chrome) as opened:
        for name, fixture in FIXTURES.items():
            uri = export_uri(fixture, tmp_path_factory.mktemp(f"accent-{name}"))
            for mode in MODES:
                expression = BOOTED % (rows, json.dumps(mode == "dark"))
                out[name, mode] = opened.measure(
                    uri, expression, media="print" if mode == "print" else None)
    return out


@needs_browser
@needs_node
class TestTheBootedPageSpendsTheAccentOnlyOnListedJobs:

    def test_no_element_wears_an_unlisted_accent(self, booted):
        strays = {f"{name} {mode}": seen["strays"]
                  for (name, mode), seen in booted.items() if seen["strays"]}
        assert strays == {}

    def test_every_at_rest_job_is_seen(self, booted):
        """A page that drew no accent at all would pass the one above."""
        for page, seen in booted.items():
            assert set(seen["jobs"]) >= AT_REST, (page, seen["jobs"])
