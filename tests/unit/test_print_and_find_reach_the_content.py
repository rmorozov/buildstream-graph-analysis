"""UX-1179: print and find-in-page reach the content the page has.

Chromium on `macro_micro` and the 114-element two-plane run: in print
media at 794 px a folded paragraph prints once and a held-back count
prints as text, not a button; on screen every twin table and SQL paste
is `hidden="until-found"`, and a find opens the twin. On the
1,202-element two-plane run every element a bound left unmounted is a
Jump hit, a press on one - or on a ranked card's element in a shut
chapter - opens its card and lands on it, and a bounded element table's
filter placeholder names Jump.
UX-1196: there the critical path's head-and-tail fold prints all 22 rows
and no stub at 794 and 390, copies 22 rows and no stub, and its card's
link lands a folded row in view; `macro_micro`'s 10-row listing sorts.
UX-1203: in print every `th` on golden and `macro_micro` has its label.
A row "Also in" or Jump to a binary lands is what sits at its centre, at 1440 and 390.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_PRINT = r"""
(() => {
  const shown = (node) => { const r = node.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const folds = [...document.querySelectorAll("details.long-text")];
  // `UX-1196`: a head-and-tail stub is no held-back count - its rows print.
  const more = [...document.querySelectorAll("button.fold-more")].filter((b) => !b.hidden && !b.closest("tr.fold-row"));
  // A header's text as paper renders it: text under a `display: none` node is not printed.
  const heads = [...document.querySelectorAll("table th")];
  const printed = (th) => [...th.querySelectorAll("*")].filter((n) => getComputedStyle(n).display === "none")
    .reduce((text, n) => text.replace(n.textContent, ""), th.textContent).trim();
  return {
    heads: heads.length, sorts: heads.filter((th) => th.querySelector("button.th-sort")).length,
    blank: heads.filter((th) => !printed(th)).map((th) => th.closest("table").getAttribute("data-table") ?? th.outerHTML.slice(0, 80)),
    folds: folds.length,
    twice: folds.filter((d) => [...d.querySelectorAll(".long-text-head, .full-text")].filter(shown).length !== 1).length,
    more: more.map((b) => ({ shown: shown(b), border: getComputedStyle(b).borderTopWidth,
                             background: getComputedStyle(b).backgroundColor,
                             said: getComputedStyle(b, "::after").content, folded: b.getAttribute("data-folded") })),
  };
})()
"""

_FIND = r"""
(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const twins = [...document.querySelectorAll("table.twin-table")];
  const pastes = [...document.querySelectorAll("pre.query")];
  document.querySelectorAll('section.chapter[data-open]').forEach((n) => n.setAttribute('data-open', 'true'));
  document.querySelectorAll('section.chapter > section[hidden="until-found"]').forEach((n) => n.removeAttribute('hidden'));
  await turn();
  const out = { twins: twins.length, pastes: pastes.length,
                shut: [...twins, ...pastes].filter((n) => n.getAttribute("hidden") !== "until-found").length,
                room: [...twins, ...pastes].filter((n) => n.getBoundingClientRect().height
                  + parseFloat(getComputedStyle(n).marginTop) > 0).length };
  // The event Chromium's find-in-page fires on an `until-found` match; `window.find` does not reveal one.
  const twin = twins[0];
  if (twin) {
    const toggle = twin.parentNode.querySelector("button.twin-toggle");
    twin.dispatchEvent(new Event("beforematch"));
    await turn();
    out.found = { open: toggle?.getAttribute("data-drawing-twin"), hidden: twin.getAttribute("hidden") };
  }
  return out;
})()
"""

_JUMP = r"""
(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const packed = document.getElementById("bga-report-gz");
  const report = JSON.parse(packed
    ? await new Response(new Blob([Uint8Array.from(atob(packed.textContent.trim()), (c) => c.charCodeAt(0))])
      .stream().pipeThrough(new DecompressionStream("gzip"))).text()
    : document.getElementById("bga-report")?.textContent ?? "null");
  const uids = Object.keys(report?.elements?.element_durations ?? {});
  const mounted = new Set([...document.querySelectorAll("[data-element]")].map((n) => n.getAttribute("data-element")));
  const detached = uids.filter((uid) => !mounted.has(uid));
  const jump = document.getElementById("jump");
  const hit = (uid) => {
    jump.value = uid;
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    return [...document.querySelectorAll(".jump-hits button[data-jump]")].find((b) => b.getAttribute("data-jump") === uid);
  };
  const missed = detached.filter((uid) => !hit(uid));
  // A card after a press: its height, its chapter's state and its top against the anchor margin.
  const land = async (uid) => {
    hit(uid)?.click();
    await turn(1200);
    const at = document.querySelector(`section[data-section^="element-"][data-element="${uid}"]`);
    const box = at?.getBoundingClientRect();
    return { uid, height: Math.round(box?.height ?? 0), top: Math.round(box?.top ?? -1),
             margin: Math.round(parseFloat(at ? getComputedStyle(at).scrollMarginTop : "0")),
             chapter: at?.closest("section.chapter")?.getAttribute("data-open") ?? null };
  };
  // A ranked card whose chapter is shut at rest, its element mounted in a table row.
  const shut = [...document.querySelectorAll('section.chapter[data-open="false"] section[data-section^="element-"]')]
    .map((card) => card.getAttribute("data-element")).find((uid) => mounted.has(uid) && !detached.includes(uid));
  const ranked = shut ? await land(shut) : null;
  const pressed = detached[0];
  const built = await land(pressed);
  const card = document.querySelector(`section[data-section^="element-"][data-on-demand="true"]`);
  const table = document.querySelector('table[data-table="elements"]');
  const filter = table?.closest("dd, section")?.querySelector("input.table-filter");
  return { uids: uids.length, detached: detached.length, missed: missed.slice(0, 5), missedCount: missed.length,
           ranked, built, pressed, hash: decodeURIComponent(location.hash), card: card?.getAttribute("data-section") ?? null,
           bounded: Number(table?.getAttribute("data-rows") ?? 0),
           placeholder: filter?.getAttribute("placeholder") ?? null };
})()
"""


#: `UX-1196`: the critical-path listing's own rows and stub, every chapter open.
_FOLD = r"""
(async () => {
  let copied = null;
  Object.defineProperty(navigator, "clipboard", { value: { writeText: async (t) => { copied = t; } }, configurable: true });
  // The copy is read as JSON, whatever format an earlier page in this worker's Chrome stored.
  localStorage.removeItem("bga.copy-format");
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  document.querySelectorAll("section.chapter[data-open]").forEach((n) => n.setAttribute("data-open", "true"));
  await turn();
  const table = document.querySelector('table[data-table="critical_path_detail"]');
  const shown = (node) => { const r = node.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const rows = [...table.querySelector("tbody").children];
  const out = { total: Number(table.getAttribute("data-rows")),
                rows: rows.filter((tr) => tr.hasAttribute("data-element") && shown(tr)).length,
                stubs: rows.filter((tr) => tr.classList.contains("fold-row") && shown(tr)).length,
                buttons: table.querySelectorAll("thead button.th-sort").length };
  if (!MEDIA_SCREEN) return out;
  const copy = table.parentNode.querySelector(".table-tools .copy-rows");
  out.label = copy.textContent;
  copy.click();
  await turn();
  out.copied = copied;
  const quantity = [...table.querySelectorAll("thead th")].find((th) => th.getAttribute("data-quantity")
    && th.querySelector("button.th-sort"));
  quantity?.querySelector("button").click();
  const column = quantity?.getAttribute("data-column");
  out.sorted = { column, sort: quantity?.getAttribute("aria-sort") ?? null,
                 values: [...table.querySelector("tbody").children].filter((tr) => tr.hasAttribute("data-element") && !tr.hidden)
                   .map((tr) => Number(tr.querySelector(`td[data-column="${column}"]`)?.getAttribute("data-raw"))) };
  return out;
})()
"""

#: `UX-1196`: Jump to an element, then its card's "Also in" link to the critical path: where its row lands.
_FOLD_JUMP = r"""
(async () => {
  const turn = (ms = 50) => new Promise((done) => setTimeout(done, ms));
  const uid = "layer12/mod058.bst";
  const jump = document.getElementById("jump");
  jump.value = uid;
  jump.dispatchEvent(new Event("input", { bubbles: true }));
  [...document.querySelectorAll(".jump-hits button[data-jump]")].find((b) => b.getAttribute("data-jump") === uid)?.click();
  await turn(1200);
  const card = document.querySelector(`section[data-section^="element-"][data-element="${uid}"]`);
  const link = card?.querySelector('a[data-where="critical_path_detail"]');
  link?.click();
  await turn(1500);
  const row = document.querySelector(`table[data-table="critical_path_detail"] tr[data-element="${uid}"]`);
  const box = row?.getBoundingClientRect();
  const hit = box && document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  return { link: Boolean(link), hidden: row ? row.hidden : null, top: Math.round(box?.top ?? -1),
           over: hit && !row.contains(hit) ? `${hit.tagName}.${hit.className}` : null,
           head: Math.round(document.querySelector("body > header")?.getBoundingClientRect().bottom ?? 0),
           height: Math.round(box?.height ?? 0), viewport: innerHeight, hash: decodeURIComponent(location.hash) };
})()
"""

#: N5: Jump to a binary mid-way down by_binary: what sits at its row's centre once landed.
_BINARY_JUMP = r"""
(async () => {
  const rows = [...document.querySelectorAll('table[data-table="by_binary"] tr[data-binary]')];
  const key = rows[Math.floor(rows.length / 2)]?.getAttribute("data-binary");
  const jump = document.getElementById("jump");
  jump.value = key;
  jump.dispatchEvent(new Event("input", { bubbles: true }));
  [...document.querySelectorAll(".jump-hits button[data-jump]")].find((b) => b.getAttribute("data-jump") === key)?.click();
  await new Promise((done) => setTimeout(done, 1500));
  const row = document.querySelector(`table[data-table="by_binary"] tr[data-binary="${CSS.escape(key)}"]`);
  const box = row?.getBoundingClientRect();
  const hit = box && document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  return { key, rows: rows.length, top: Math.round(box?.top ?? -1), height: Math.round(box?.height ?? 0),
           over: !hit ? "nothing" : row.contains(hit) ? null : `${hit.tagName}.${hit.className}` };
})()
"""


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1179", labels=["golden", "macro_micro"])
    import tools.bga_view as view

    for label, shape in (("two_plane", pages.REVIEW_SHAPE), ("big", ("--layers", "20", "--width", "60"))):
        run = pages.two_plane_run(tmp_path_factory.mktemp(f"ux1179-{label}"), shape)
        page = tmp_path_factory.mktemp(f"ux1179-{label}-page") / "report.html"
        view.export(str(run), str(page))
        uris[label] = page.as_uri()
    heavy = tmp_path_factory.mktemp("ux1179-heavy-page") / "report.html"
    view.export(str(pages.heavy_binary_run(tmp_path_factory.mktemp("ux1179-heavy"))), str(heavy))
    with Browser(find_chrome()) as browser:
        out = {
            label: {
                "print": browser.measure(uri, _PRINT, 794, 1123, media="print"),
                "find": browser.measure(uri, _FIND, 1440, 900),
            }
            for label, uri in uris.items()
            if label != "big"
        }
        out["big"] = {"jump": browser.measure(uris["big"], _JUMP, 1440, 900)}
        screen, paper = _FOLD.replace("MEDIA_SCREEN", "true"), _FOLD.replace("MEDIA_SCREEN", "false")
        out["fold"] = {
            "print": browser.measure(uris["big"], paper, 794, 1123, media="print"),
            "narrow": browser.measure(uris["big"], paper, 390, 844, media="print"),
            "screen": browser.measure(uris["big"], screen, 1440, 900),
            "jump": browser.measure(uris["big"], _FOLD_JUMP, 1440, 900),
            "jump390": browser.measure(uris["big"], _FOLD_JUMP, 390, 844),
            "binary": browser.measure(heavy.as_uri(), _BINARY_JUMP, 1440, 900),
            "binary390": browser.measure(heavy.as_uri(), _BINARY_JUMP, 390, 844),
            "short": browser.measure(uris["macro_micro"], screen, 1440, 900),
        }
        return out


@needs_browser
class TestPrintAndFindReachTheContent:
    def test_a_folded_paragraph_prints_once(self, seen):
        assert seen["two_plane"]["print"]["folds"] >= 1 and seen["macro_micro"]["print"]["folds"] >= 1, seen
        for label in ("golden", "macro_micro", "two_plane"):
            assert seen[label]["print"]["twice"] == 0, (label, seen[label]["print"])

    def test_a_held_back_count_prints_as_text_not_a_button(self, seen):
        more = seen["two_plane"]["print"]["more"]
        assert more, seen["two_plane"]["print"]
        for button in more:
            assert button["shown"] and button["border"] == "0px", button
            assert button["background"] in ("rgba(0, 0, 0, 0)", "transparent"), button
            assert "not printed" in button["said"], button

    def test_every_table_header_prints_its_label(self, seen):
        assert seen["macro_micro"]["print"]["sorts"] >= 1, seen["macro_micro"]["print"]
        for label in ("golden", "macro_micro"):
            got = seen[label]["print"]
            assert got["heads"] >= 1 and got["blank"] == [], (label, got["heads"], got["blank"])

    def test_twins_and_pastes_are_findable(self, seen):
        for label in ("golden", "macro_micro", "two_plane"):
            find = seen[label]["find"]
            assert find["shut"] == 0 and find["room"] == 0, (label, find)
        assert seen["two_plane"]["find"]["twins"] >= 1 and seen["two_plane"]["find"]["pastes"] >= 1, seen["two_plane"]

    def test_a_found_twin_says_it_is_open(self, seen):
        found = seen["two_plane"]["find"]["found"]
        assert found == {"open": "open", "hidden": None}, found

    def test_every_element_a_bound_leaves_out_is_a_jump_hit(self, seen):
        jump = seen["big"]["jump"]
        assert jump["uids"] >= 1200 and jump["detached"] >= 100, jump
        assert jump["missedCount"] == 0, jump

    def test_a_jump_to_an_unmounted_element_opens_its_card(self, seen):
        jump = seen["big"]["jump"]
        assert jump["hash"].startswith("#element-") and jump["card"] == jump["hash"][1:].split("~")[0], jump
        # Both a built card and a ranked one in a shut chapter: open, and landed at the anchor margin.
        for card in (jump["built"], jump["ranked"]):
            assert card and card["height"] > 100 and card["chapter"] == "true", jump
            assert abs(card["top"] - card["margin"]) <= 8, card

    def test_print_holds_every_folded_row_and_no_stub(self, seen):
        for media in ("print", "narrow"):
            got = seen["fold"][media]
            assert got["total"] == 22 and got["rows"] == 22 and got["stubs"] == 0, (media, got)

    def test_copy_takes_every_row_the_fold_holds_and_never_the_stub(self, seen):
        got = seen["fold"]["screen"]
        rows = json.loads(got["copied"])
        assert got["label"] == "Copy 22 rows" and len(rows) == 22, (got["label"], len(rows))
        assert all(row and row.get("element_uid") for row in rows), rows

    def test_a_folded_row_is_a_landing(self, seen):
        got = seen["fold"]["jump"]
        assert got["link"] and got["hidden"] is False and got["height"] > 0, got
        # Below the sticky header, not under it.
        assert 0 < got["head"] <= got["top"] < got["viewport"] - got["height"], got

    @pytest.mark.parametrize("case", ["jump", "jump390", "binary", "binary390"])
    def test_a_landed_row_is_not_under_the_table_tools(self, seen, case):
        got = seen["fold"][case]
        assert got["top"] >= 0 and got["over"] is None, got

    def test_a_short_listing_keeps_its_sort(self, seen):
        got = seen["fold"]["short"]
        values = got["sorted"]["values"]
        assert got["total"] <= 10 and got["buttons"] > 0 and got["sorted"]["sort"] == "descending", got
        assert len(values) == got["total"] and values == sorted(values, reverse=True), got

    def test_the_bounded_element_table_names_jump(self, seen):
        jump = seen["big"]["jump"]
        assert jump["bounded"] >= 1200, jump
        assert "Jump" in (jump["placeholder"] or ""), jump
