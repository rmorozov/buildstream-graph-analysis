"""UX-1179: print and find-in-page reach the content the page has.

Chromium on `macro_micro` and the 114-element two-plane run: in print
media at 794 px a folded paragraph prints once and a held-back count
prints as text, not a button; on screen every twin table and SQL paste
is `hidden="until-found"`, and a find opens the twin. On the
1,202-element two-plane run every element a bound left unmounted is a
Jump hit, a press on one - or on a ranked card's element in a shut
chapter - opens its card and lands on it, and a bounded element table's
filter placeholder names Jump.
"""

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
  const more = [...document.querySelectorAll("button.fold-more")].filter((b) => !b.hidden);
  return {
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


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    uris = pages.pages(tmp_path_factory, prefix="ux1179", labels=["golden", "macro_micro"])
    import tools.bga_view as view

    for label, shape in (("two_plane", pages.REVIEW_SHAPE), ("big", ("--layers", "20", "--width", "60"))):
        run = pages.two_plane_run(tmp_path_factory.mktemp(f"ux1179-{label}"), shape)
        page = tmp_path_factory.mktemp(f"ux1179-{label}-page") / "report.html"
        view.export(str(run), str(page))
        uris[label] = page.as_uri()
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

    def test_the_bounded_element_table_names_jump(self, seen):
        jump = seen["big"]["jump"]
        assert jump["bounded"] >= 1200, jump
        assert "Jump" in (jump["placeholder"] or ""), jump
