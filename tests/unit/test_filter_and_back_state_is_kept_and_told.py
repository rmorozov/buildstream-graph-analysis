"""UX-1158, UX-1165, UX-1171: a filter says when it matched nothing, and Back walks the rail.

A no-match filter's badge reads `none of M match` and nothing offers a
copy or a table sentence; the table's strip redraws over the kept rows
and its sentence counts K of M; three rail chapter presses take three
Backs to unwind at 1440 and 390, each restoring the open chapters and
the rail's mark, and Forward lands where the press did; at 390 a press
folds the rail; the hash's state is one opaque token, an untouched
page writes none, a readable hash from before still loads, and a
chapter's own fold and `All rows` survive a reload.
UX-1170: a threshold empties the tools as the text box does, a filter to
two rows draws no strip, a bound under a filter reads `K of N matched`
(one population, `UX-1195`), a cleared filter under `All rows` hides the badge again, and the Ask
and Jump boxes say when nothing matches.
Chromium (`tests/browser.py`) on `golden`, `macro_micro` and the
two-plane review page.

Styleguide §4c.
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
  const boxes = [...document.querySelectorAll("input.table-filter")];
  const holds = (node, what) => node.closest(".table-tools")?.querySelector(what);
  const box = boxes.find((node) => holds(node, ".density-label") && holds(node, ".uniform-columns"))
    ?? boxes.find((node) => holds(node, ".density-label"));
  if (!box) return null;
  const tools = box.closest(".table-tools");
  const table = tools.parentNode.querySelector("table[data-table]");
  // Opened, so what the tools offer is visible to read.
  const shut = tools.closest('section.chapter[data-open="false"]');
  shut?.querySelector("[data-chapter-open]").click();
  await turn();
  const rows = () => [...table.tBodies[0].rows].filter((tr) => !tr.hidden);
  const read = () => ({
    badge: tools.querySelector(".badge")?.textContent ?? null,
    // `UX-1176`: a badge at rest is mounted and empty, never `hidden`.
    quiet: tools.querySelector(".badge") ? !tools.querySelector(".badge").textContent : null,
    rows: Number(table.getAttribute("data-rows")),
    shown: rows().length,
    label: tools.querySelector(".density-label")?.textContent ?? null,
    sentence: tools.querySelector(".density-sentence")?.textContent ?? null,
    offered: [...tools.querySelectorAll(".copy-rows, .copy-as, .uniform-columns")]
      .filter((node) => node.checkVisibility()).map((node) => node.className.split(" ").at(-1)),
    hash: location.hash,
  });
  const type = async (value, into = box) => {
    into.value = value;
    into.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
    return read();
  };
  const preset = tools.querySelector("select.top-n");
  const choose = async (value) => {
    preset.value = value;
    preset.dispatchEvent(new Event("change", { bubbles: true }));
    await turn();
    return read();
  };
  const needle = table.querySelector("tbody td")?.textContent.trim();
  const before = read();
  // `UX-1170`: `All rows`, a filter, cleared - the badge hides again; and every row's text to count by.
  let all = null, texts = [];
  if ([...(preset?.options ?? [])].some((o) => o.value === "")) {
    const opening = preset.value;
    all = { rest: await choose("") };
    texts = rows().map((tr) => [...tr.children].map((td) => td.textContent).join(" ").toLowerCase());
    all.some = await type(needle);
    all.cleared = await type("");
    await choose(opening);
  }
  const count = (text) => texts.filter((row) => row.includes(text.trim().toLowerCase())).length;
  // The longest prefix of the needle with a shape, and the longest the bound cuts.
  const prefixes = [...needle].map((_, i) => needle.slice(0, needle.length - i));
  const pick = (ok) => prefixes.find((p) => p.trim() && ok(count(p)));
  const total = texts.length;
  const at = async (text) => text ? { text, matched: count(text), ...(await type(text)) } : null;
  const some = await at(pick((n) => n > 2 && n < total));
  const wide = await at(pick((n) => n > before.shown && n < total));
  const one = { matched: count(needle), ...(await type(needle)) };
  const none = await type("zz-no-such-row-qx");
  const cleared = await type("");
  // `UX-1191`: the threshold is the box's own grammar; a bare one reads the first quantity column.
  const threshold = /[<>]/.test(box.placeholder);
  const unmet = threshold ? await type("> 999999999999999") : null;
  const unset = threshold ? await type("") : null;
  const typed = await type(needle);
  await type("");
  return { key: table.getAttribute("data-table"), needle, total, before, all, some, wide, one, none,
           cleared, unmet, unset, hash: typed.hash };
})()
"""

_SEARCH = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 60));
  const type = async (box, value) => {
    box.value = value;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await turn();
  };
  const out = {};
  const ask = document.querySelector("input[data-role=query-element]");
  if (ask) {
    const read = () => ({ note: ask.parentNode.querySelector("p").textContent,
      sql: [...document.querySelectorAll("code[data-sql-for]")].map((code) => code.textContent).join("\n") });
    const value = ask.value;
    out.ask = { value, before: read() };
    await type(ask, "zzzq");
    out.ask.none = read();
    await type(ask, value);
    out.ask.back = read();
  }
  const jump = document.getElementById("jump");
  // `UX-1176`: the no-match line is the mounted `#jump-none` status, beside the hits.
  const hits = () => [...document.querySelectorAll(".jump-hits li, #jump-none")].map((n) => n.textContent)
    .filter(Boolean);
  await type(jump, "zzzq");
  out.jump = hits();
  await type(jump, "");
  out.jumpCleared = hits();
  return out;
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
  const forward = () => {
    const moved = new Promise((done) => window.addEventListener("popstate", done, { once: true }));
    history.forward();
    return moved.then(settled);
  };
  // The chapter with the most sections: its height estimates move the most.
  const count = (row) => row.querySelectorAll("a[data-toc]").length;
  const most = [...document.querySelectorAll("nav.toc li[data-chapter]")]
    .reduce((a, b) => (count(b) > count(a) ? b : a)).dataset.chapter;
  const into = () => {
    document.querySelector(`[data-toc-chapter="${most}"]`).click();
    return settled();
  };
  const link = (at) => {
    [...document.querySelectorAll(`nav.toc li[data-chapter="${most}"] a[data-toc]`)].at(at).click();
    return settled();
  };
  return { settled, press, back, forward, into, link, ids };
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
# UX-1171: the walk's own sequence - a chapter, its last section, its first - then Back x3, Forward x3.
_AHEAD = [
    {"read": _HELPERS},
    {"read": "__j.settled()"},
    {"read": "__j.into()"},
    {"read": "__j.link(-1)"},
    {"read": "__j.link(0)"},
    *[_BACK] * 3,
    *[{"read": "__j.forward()"}] * 3,
]
_AHEAD_NAMES = ["initial", "chapter", "far", "near", "b1", "b2", "b3", "f1", "f2", "f3"]
# UX-1171: at 390 the rail folds after a section link, a step or either "all" button; a chapter row keeps it open.
_RAIL = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 120));
  const nav = document.querySelector("nav.toc");
  const out = { initial: nav.dataset.folded };
  const presses = [["link", "a[data-toc]"], ["step", "[data-step]"], ["expand", '[data-all="false"]'],
                   ["collapse", '[data-all="true"]'], ["chapter", "[data-toc-chapter]:not([aria-current])"]];
  for (const [name, what] of presses) {
    const title = nav.querySelector(".toc-title");
    if (nav.dataset.folded === "true") title.click();
    await turn();
    const opened = nav.dataset.folded;
    nav.querySelector(what).click();
    await turn();
    out[name] = [opened, nav.dataset.folded];
  }
  return out;
})()
"""
_LINK = r"""
(async () => {
  const turn = () => new Promise((done) => setTimeout(done, 60));
  const read = () => ({
    open: [...document.querySelectorAll('section.chapter[data-open="true"]')]
      .map((box) => box.dataset.chapter).join(","),
    tops: Object.fromEntries([...document.querySelectorAll("select.top-n")].map((s) => [s.id, s.value])),
    hash: location.hash,
  });
  const before = read();
  if (location.hash) return { before };
  [...document.querySelectorAll("[data-chapter-open]")].at(-1).click();
  await turn();
  const folded = read();
  const bounded = [...document.querySelectorAll("select.top-n")].find(
    (s) => s.opening && [...s.options].some((o) => o.value === ""));
  if (bounded) {
    bounded.value = "";
    bounded.dispatchEvent(new Event("change", { bubbles: true }));
    await turn();
  }
  return { before, folded, all: bounded ? read() : null, id: bounded?.id ?? null };
})()
"""

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
            out[label] = {"back": {}, "ahead": {}, "rail": {}}
            for width, height in ((1440, 900), (390, 844)):
                walked = [v for v in browser.journey(uri, _STEPS, width, height) if v is not None]
                out[label]["back"][width] = dict(zip(_NAMES, walked, strict=True))
                ahead = browser.journey(uri, _AHEAD, width, height)[1:]
                out[label]["ahead"][width] = dict(zip(_AHEAD_NAMES, ahead, strict=True))
                out[label][width] = browser.measure(uri, _FILTER, width, height)
                out[label]["rail"][width] = browser.measure(uri, _RAIL, width, height)
            out[label]["search"] = browser.measure(uri, _SEARCH)
            pressed = browser.measure(uri, _LINK)
            last = pressed["all"] or pressed["folded"]
            # UX-1165: a query string, so the reload is a new document.
            reloaded = browser.measure(f"{uri}?ux1165{last['hash']}", _LINK)
            out[label]["link"] = {**pressed, "reloaded": reloaded}
            told = out[label][1440]
            if told:
                # A query string, so this is a new document and not a same-page hash move.
                old = f"{uri}?ux1158#{told['key']}~f.{told['key']}={quote((told['some'] or {'text': told['needle']})['text'])}"
                back = "const before = read(); return { ...before, value: box.value };"
                out[label]["old"] = browser.measure(old, _FILTER.replace("const before = read();", back))
    return out


def _walks(seen):
    """Every rail journey, at 1440 and at 390."""
    return [((label, width), walk) for label, out in seen.items() for width, walk in out["back"].items()]


def _total(before):
    """`UX-1185`: a bounded badge's `25 of 1,202`; `UX-1176`: an empty badge at rest leaves `data-rows`."""
    return re.findall(r"[\d,]+", before["badge"])[-1] if before["badge"] else f"{before['rows']:,}"


@needs_browser
class TestAFilterSaysWhatItKept:
    def test_a_no_match_filter_says_so(self, seen):
        told = [label for label in seen if seen[label][1440]]
        assert "two_plane" in told and "macro_micro" in told, {k: v[1440] for k, v in seen.items()}
        for label in told:
            for width in (1440, 390):
                out = seen[label][width]
                # `UX-1185`: a whole table's badge is `71 rows`, a bounded one's `25 of 1,202`.
                total = _total(out["before"])
                assert out["none"]["badge"] == f"none of {total} match", (label, width, out)
                # `UX-1170`: a threshold nothing passes says the same.
                assert out["unmet"]["badge"] == f"none of {total} match", (label, width, out)

    def test_the_strip_counts_the_filtered_rows(self, seen):
        for label in (k for k in seen if seen[k][1440]):
            for width in (1440, 390):
                out = seen[label][width]
                # `UX-1185`: a whole table's badge is `71 rows`, a bounded one's `25 of 1,202`.
                total = _total(out["before"])
                some = out["some"]
                assert some, (label, "no prefix of the needle keeps 3 to M-1 rows", out)
                # `UX-1156`: the label names the column; the badge and the strip's sentence count.
                assert out["before"]["sentence"].endswith(f"across {total} rows."), (label, out)
                assert some["label"] == out["before"]["label"], (label, out)
                assert re.search(rf"(?<![\d,]){some['matched']:,} of {total} rows\b", some["sentence"]), (label, out)
                assert out["none"]["label"] is None, (label, out)
                assert out["cleared"]["label"] == out["before"]["label"], (label, out)
                assert out["cleared"]["sentence"] == out["before"]["sentence"], (label, out)

    def test_two_rows_or_fewer_draw_no_strip(self, seen):
        """`UX-1170`: at rest or filtered, the rows are the values."""
        few = [
            (label, width)
            for label in seen
            if seen[label][1440]
            for width in (1440, 390)
            if seen[label][width]["one"]["matched"] <= 2
        ]
        assert ("two_plane", 1440) in few, {k: v[1440] for k, v in seen.items()}
        for label, width in few:
            one = seen[label][width]["one"]
            assert one["shown"] == one["matched"], (label, width, one)
            assert (one["label"], one["sentence"]) == (None, None), (label, width, one)

    def test_the_badge_says_shown_of_matched_then_of_all(self, seen):
        wide = [
            (label, width) for label in seen if seen[label][1440] for width in (1440, 390) if seen[label][width]["wide"]
        ]
        assert ("two_plane", 1440) in wide, {k: v[1440] for k, v in seen.items()}
        for label, width in wide:
            out = seen[label][width]
            shown, matched = out["wide"]["shown"], out["wide"]["matched"]
            assert shown < matched < out["total"], (label, width, out)
            assert out["wide"]["badge"] == f"{shown:,} of {matched:,} matched", (label, out)

    def test_a_cleared_filter_hides_the_badge_again(self, seen):
        """`UX-1163`'s M3b: under `All rows` the badge is empty, a filter fills it, clearing empties it."""
        unbounded = [
            (label, width) for label in seen if seen[label][1440] for width in (1440, 390) if seen[label][width]["all"]
        ]
        assert ("two_plane", 1440) in unbounded, {k: v[1440] for k, v in seen.items()}
        for label, width in unbounded:
            all_rows = seen[label][width]["all"]
            quiet = [all_rows[step]["quiet"] for step in ("rest", "some", "cleared")]
            assert quiet == [True, False, True], (label, width, all_rows)

    def test_an_empty_result_offers_no_copy_and_no_sentence(self, seen):
        assert "uniform-columns" in seen["two_plane"][1440]["before"]["offered"], seen["two_plane"]
        for label in (k for k in seen if seen[k][1440]):
            for width in (1440, 390):
                out = seen[label][width]
                # `UX-1189`: the Markdown box is page-wide now, not in the table's tools.
                assert "copy-rows" in out["before"]["offered"], (label, width, out)
                # `UX-1170`: a threshold too, not only a word.
                for empty, back in (("none", "cleared"), ("unmet", "unset")):
                    assert out[empty]["offered"] == [], (label, width, empty, out)
                    assert out[back]["offered"] == out["before"]["offered"], (label, width, back, out)


@needs_browser
class TestASearchBoxSaysWhenNothingMatches:
    def test_the_ask_box_says_nothing_matches(self, seen):
        asked = {label: seen[label]["search"]["ask"] for label in seen if seen[label]["search"].get("ask")}
        assert "two_plane" in asked, {k: v["search"] for k, v in seen.items()}
        for label, ask in asked.items():
            assert ask["none"]["sql"] == ask["before"]["sql"], (label, ask)
            assert ask["none"]["note"].startswith("Nothing in this run's "), (label, ask)
            assert ask["none"]["note"].endswith(f'matches "zzzq"; the queries still ask about {ask["value"]}.'), ask
            assert ask["back"] == ask["before"], (label, ask)

    def test_the_jump_box_says_nothing_matches(self, seen):
        for label, out in seen.items():
            assert out["search"]["jump"] == ['Nothing matches "zzzq".'], (label, out["search"])
            assert out["search"]["jumpCleared"] == [], (label, out["search"])


@needs_browser
class TestBackWalksTheRail:
    def test_each_press_moves_the_rail_and_opens_a_chapter(self, seen):
        """Non-vacuity: three presses, three different states to unwind."""
        for label, walk in _walks(seen):
            assert len(walk["ids"]) == 3, (label, walk)
            states = [json.dumps(walk[k]) for k in ("initial", "first", "second", "third")]
            assert len(set(states)) == 4, (label, walk)
            assert walk["third"]["rail"] == walk["ids"][2], (label, walk)

    def test_three_backs_restore_rail_and_chapters(self, seen):
        for label, walk in _walks(seen):
            for back, before in (("back_once", "second"), ("back_twice", "first"), ("back_thrice", "initial")):
                assert walk[back] == walk[before], (label, back, walk)

    def test_forward_lands_where_the_press_did(self, seen):
        for label, out in seen.items():
            for width, walk in out["ahead"].items():
                assert len({walk[k]["hash"] for k in ("initial", "chapter", "far", "near")}) == 4, (label, width, walk)
                for moved, pressed in (
                    ("b1", "far"),
                    ("b2", "chapter"),
                    ("b3", "initial"),
                    ("f1", "chapter"),
                    ("f2", "far"),
                    ("f3", "near"),
                ):
                    got, want = walk[moved], walk[pressed]
                    assert (got["hash"], got["open"]) == (want["hash"], want["open"]), (label, width, moved, walk)
                    assert abs(got["y"] - want["y"]) <= 3, (label, width, moved, got["y"], want["y"])


@needs_browser
class TestTheRailFoldsAfterAPress:
    def test_a_press_at_390_folds_the_rail(self, seen):
        for label, out in seen.items():
            rail = out["rail"][390]
            assert rail["initial"] == "true", (label, rail)
            for name in ("link", "step", "expand", "collapse"):
                assert rail[name] == ["false", "true"], (label, name, rail)

    def test_a_chapter_row_press_at_390_keeps_the_rail_open(self, seen):
        """The reader is still choosing a section; J2 presses one of its links next."""
        for label, out in seen.items():
            rail = out["rail"][390]
            assert rail["chapter"] == ["false", "false"], (label, rail)

    def test_at_1440_the_rail_never_folds(self, seen):
        for label, out in seen.items():
            rail = out["rail"][1440]
            assert set(map(tuple, (v for k, v in rail.items() if k != "initial"))) == {("false", "false")}, (
                label,
                rail,
            )


@needs_browser
class TestTheHashIsOpaqueOnPurpose:
    def test_an_untouched_page_writes_only_its_anchor(self, seen):
        for label, walk in _walks(seen):
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
            assert old["value"] == typed["some"]["text"], (label, old)
            assert old["badge"] == typed["some"]["badge"], (label, old)


@needs_browser
class TestEveryViewButtonWritesTheLink:
    def test_a_chapter_fold_survives_a_reload(self, seen):
        for label, out in seen.items():
            link = out["link"]
            assert link["folded"]["open"] != link["before"]["open"], (label, link)
            assert link["reloaded"]["before"]["open"] == link["folded"]["open"], (label, link)

    def test_all_rows_survives_a_reload(self, seen):
        bounded = [label for label in seen if seen[label]["link"]["all"]]
        # `UX-1185`: macro_micro's 71-row `binary_cost` opens whole now, so no table of its opens bounded.
        assert "two_plane" in bounded, {k: v["link"] for k, v in seen.items()}
        for label in bounded:
            link = seen[label]["link"]
            assert link["folded"]["tops"][link["id"]] != "", (label, link)
            assert link["reloaded"]["before"]["tops"][link["id"]] == "", (label, link)
