"""UX-1158: a filter says when it matched nothing, and Back walks the rail.

A no-match filter's badge reads `none of M match`; the table's strip
redraws over the kept rows and its sentence counts K; three rail
chapter presses take three Backs to unwind, each restoring the open
chapters and the rail's mark; the hash's state is one opaque token, an
untouched page writes none, and a readable hash from before still loads.
Chromium (`tests/browser.py`) on `golden`, `macro_micro` and the
two-plane review page.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_FILTER = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 60));
  const box = [...document.querySelectorAll("input.table-filter")].find(
    (node) => node.closest(".table-tools")?.querySelector(".density-label"));
  if (!box) return null;
  const tools = box.closest(".table-tools");
  const table = tools.parentNode.querySelector("table[data-table]");
  const read = () => ({
    badge: tools.querySelector(".badge")?.textContent ?? null,
    label: tools.querySelector(".density-label")?.textContent ?? null,
    sentence: tools.querySelector(".density-sentence")?.textContent ?? null,
    hash: location.hash,
  });
  const type = async (value) => {
    box.value = value;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
    return read();
  };
  const needle = table.querySelector("tbody td")?.textContent.trim();
  const before = read();
  const some = await type(needle);
  const none = await type("zz-no-such-row-qx");
  const cleared = await type("");
  const typed = await type(needle);
  await type("");
  return { key: table.getAttribute("data-table"), needle, before, some, none, cleared,
           hash: typed.hash };
})()
"""

_HELPERS = r"""
window.__j = (() => {
  const read = () => ({
    y: Math.round(scrollY),
    open: [...document.querySelectorAll('section.chapter[data-open="true"]')]
      .map((box) => box.dataset.chapter).join(","),
    rail: [...document.querySelectorAll("li[data-chapter][data-current]")]
      .map((row) => row.dataset.chapter).join(","),
    hash: location.hash,
  });
  const frame = () => new Promise((done) => requestAnimationFrame(done));
  const settled = async () => {
    let last = "", same = 0;
    for (let i = 0; i < 240 && same < 8; i += 1) {
      await frame();
      const now = JSON.stringify(read());
      same = now === last ? same + 1 : 0;
      last = now;
    }
    return read();
  };
  const ids = [...document.querySelectorAll("[data-toc-chapter]")]
    .map((button) => button.dataset.tocChapter).slice(1, 4);
  const press = (i) => {
    document.querySelector(`[data-toc-chapter="${ids[i]}"]`).click();
    return settled();
  };
  const back = () => {
    const step = navigation.currentEntry.index - 1;
    if (String(navigation.entries()[step]?.url).split("#")[0] !== location.href.split("#")[0]) {
      return { left: true };
    }
    const moved = new Promise((done) => window.addEventListener("popstate", done, { once: true }));
    history.back();
    return moved.then(settled);
  };
  return { settled, press, back, ids };
})();
null
"""

_BACK = {"read": "__j.back()"}
_STEPS = [
    {"read": _HELPERS},
    {"read": "__j.settled()"},
    *[step for i in range(3) for step in ({"key": "Enter"}, {"read": f"__j.press({i})"})],
    _BACK,
    _BACK,
    _BACK,
    {"read": "__j.ids"},
]
_NAMES = ["initial", "first", "second", "third", "back_once", "back_twice", "back_thrice", "ids"]


def _two_plane(into):
    return pages.in_place_uri(pages.two_plane_run(into, shape=pages.REVIEW_SHAPE), into)


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    made = pages.pages(tmp_path_factory, prefix="ux1158")
    made["two_plane"] = _two_plane(tmp_path_factory.mktemp("ux1158-two-plane"))
    return made


@pytest.fixture(scope="module")
def seen(uris):
    out = {}
    with Browser(find_chrome()) as browser:
        for label, uri in uris.items():
            walked = [v for v in browser.journey(uri, _STEPS, 1440, 900) if v is not None]
            out[label] = {"back": dict(zip(_NAMES, walked, strict=True))}
            for width, height in ((1440, 900), (390, 844)):
                out[label][width] = browser.measure(uri, _FILTER, width, height)
            told = out[label][1440]
            if told:
                # A query string, so this is a new document and not a same-page hash move.
                old = f"{uri}?ux1158#{told['key']}~f.{told['key']}={quote(told['needle'])}"
                back = "const before = read(); return { ...before, value: box.value };"
                out[label]["old"] = browser.measure(old, _FILTER.replace("const before = read();", back))
    return out


@needs_browser
class TestAFilterSaysWhatItKept:
    def test_a_no_match_filter_says_so(self, seen):
        told = [label for label in seen if seen[label][1440]]
        assert "two_plane" in told and "macro_micro" in told, {k: v[1440] for k, v in seen.items()}
        for label in told:
            for width in (1440, 390):
                out = seen[label][width]
                total = out["before"]["badge"].split()[-1]
                assert out["none"]["badge"] == f"none of {total} match", (label, width, out)

    def test_the_strip_counts_the_filtered_rows(self, seen):
        for label in (k for k in seen if seen[k][1440]):
            for width in (1440, 390):
                out = seen[label][width]
                total = out["before"]["badge"].split()[-1]
                shown = out["some"]["badge"].split()[0]
                # `UX-1156`: the label names the column; the badge and the strip's sentence count.
                assert out["before"]["sentence"].endswith(f"across {total} rows."), (label, out)
                assert shown != total and shown != "none", (label, out)
                assert out["some"]["label"] == out["before"]["label"], (label, out)
                assert re.search(rf"(?<![\d,]){shown} rows?\b", out["some"]["sentence"]), (label, out)
                assert out["none"]["label"] is None, (label, out)
                assert out["cleared"]["label"] == out["before"]["label"], (label, out)


@needs_browser
class TestBackWalksTheRail:
    def test_each_press_moves_the_rail_and_opens_a_chapter(self, seen):
        """Non-vacuity: three presses, three different states to unwind."""
        for label, out in seen.items():
            walk = out["back"]
            assert len(walk["ids"]) == 3, (label, walk)
            states = [json.dumps(walk[k]) for k in ("initial", "first", "second", "third")]
            assert len(set(states)) == 4, (label, walk)
            assert walk["third"]["rail"] == walk["ids"][2], (label, walk)

    def test_three_backs_restore_rail_and_chapters(self, seen):
        for label, out in seen.items():
            walk = out["back"]
            for back, before in (("back_once", "second"), ("back_twice", "first"), ("back_thrice", "initial")):
                assert walk[back] == walk[before], (label, back, walk)


@needs_browser
class TestTheHashIsOpaqueOnPurpose:
    def test_an_untouched_page_writes_only_its_anchor(self, seen):
        for label, out in seen.items():
            walk = out["back"]
            assert walk["first"]["hash"] == f"#chapter-{walk['ids'][0]}", (label, walk)

    def test_the_state_is_one_token(self, seen):
        for label in (k for k in seen if seen[k][1440]):
            out = seen[label][1440]
            token = out["hash"].partition("~")[2]
            assert token and not set(token) & set("=&.%"), (label, out)
            assert f"f.{out['key']}=" in pages.view_query(out["hash"]), (label, out)

    def test_a_readable_hash_from_before_still_loads(self, seen):
        for label in (k for k in seen if seen[k][1440]):
            old, typed = seen[label]["old"], seen[label][1440]
            assert old["value"] == typed["needle"], (label, old)
            assert old["badge"] == typed["some"]["badge"], (label, old)
