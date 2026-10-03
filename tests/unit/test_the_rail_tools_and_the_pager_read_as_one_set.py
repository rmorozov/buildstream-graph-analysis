"""UX-1203: the rail's tools and the pager read as one set; rail Next, Back and the card folds keep their order.

Measured on the 1,202-element page at `ce7e193c`: "Copy link to this
view" 93x81 on three lines beside a 15 px label; Prev and Next 0 px apart
in a 15 px pager; the sort glyph on the header, outside its button; rail
Next from `latent_heavies` landed on `wall_clock_share_us`; Back kept a
filter its entry lacked; Expand all pushed nothing; an opened Binaries
fold sat beside the closed one; the elided-elements line sat atop the report.
Next after a pressed `latent_heavies` entry also skipped `joint_saving`.
`UX-1209`: the Markdown checkbox was 24x24 beside a 20 px line; now 13x13 inside a 24 px label.

Styleguide §3l.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages

from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

SMALL_PX = 13

_LOOK = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const nav = document.querySelector(".toc");
  if (nav?.getAttribute("data-folded") === "true") nav.querySelector(".toc-title").click();
  await wait(100);
  const lines = (node) => {
    const tops = new Set();
    const walk = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
    for (let text = walk.nextNode(); text; text = walk.nextNode()) {
      if (!text.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(text);
      for (const r of range.getClientRects()) tops.add(Math.round(r.top));
    }
    return tops.size;
  };
  const px = (node) => parseFloat(getComputedStyle(node).fontSize);
  const tools = [...document.querySelectorAll(".toc-controls > *")]
    .map((n) => ({ text: n.textContent.trim(), px: px(n), lines: lines(n) }));
  for (const box of document.querySelectorAll("section.chapter")) box.setAttribute("data-open", "true");
  for (const s of document.querySelectorAll("section[data-section][hidden]")) s.removeAttribute("hidden");
  await wait(300);
  const pagers = [...document.querySelectorAll(".table-pager")].filter((p) => p.offsetParent).map((p) => {
    const [prev, next] = [p.querySelector(".page-prev"), p.querySelector(".page-next")];
    return { px: px(p), gap: next.getBoundingClientRect().left - prev.getBoundingClientRect().right };
  });
  const sorted = [...document.querySelectorAll("th[aria-sort]")].map((th) => ({
    th: getComputedStyle(th, "::after").content,
    button: getComputedStyle(th.querySelector("button.th-sort"), "::after").content }));
  return { tools, pagers, sorted };
})()
"""

_FOLDS = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const out = [];
  for (const card of document.querySelectorAll("section[data-element]")) {
    const [one, two] = [card.querySelector(":scope > .join-evidence"),
                        card.querySelector(':scope > details[data-fold="binaries"]')];
    if (!one || !two) continue;
    card.closest("section.chapter")?.setAttribute("data-open", "true");
    card.removeAttribute("hidden");
    for (const opened of [two, one]) {
      opened.open = true;
      await wait(50);
      out.push({ uid: card.getAttribute("data-element"), opened: opened.getAttribute("data-fold"),
                 dx: Math.round(two.getBoundingClientRect().left - one.getBoundingClientRect().left) });
      opened.open = false;
    }
  }
  return out;
})()
"""

_STEP = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const links = [...document.querySelectorAll(".toc [data-toc]")].map((a) => a.getAttribute("href"));
  const from = Math.max(0, links.indexOf("#latent_heavies") - 2);
  // Short, as on the 1,202-element page: the mark passes it once the step has landed.
  for (const n of document.querySelectorAll("#latent_heavies > :not(.section-head)")) n.style.display = "none";
  document.querySelector(`.toc [href="${links[from]}"]`).click();
  await wait(1000);
  const seen = [];
  for (let i = 0; i < 4; i += 1) {
    document.querySelector('[data-step="next"]').click();
    await wait(1000);
    seen.push(location.hash.split("~")[0]);
  }
  return { want: links.slice(from + 1, from + 5), seen };
})()
"""

#: The rail entry pressed directly, not stepped to: Next goes to the entry after it.
_CLICKED = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const links = [...document.querySelectorAll(".toc [data-toc]")].map((a) => a.getAttribute("href"));
  // Short, as `_STEP` makes it: the mark passes it once the press has landed.
  for (const n of document.querySelectorAll("#latent_heavies > :not(.section-head)")) n.style.display = "none";
  document.querySelector('.toc [href="#latent_heavies"]').click();
  await wait(1000);
  const mark = document.querySelector(".toc [data-toc][data-current]")?.getAttribute("href") ?? null;
  document.querySelector('[data-step="next"]').click();
  await wait(1000);
  return { want: links[links.indexOf("#latent_heavies") + 1], mark, seen: location.hash.split("~")[0] };
})()
"""

_HISTORY = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  const press = (text) => [...document.querySelectorAll(".toc-controls button")]
    .find((b) => b.textContent.trim() === text).click();
  const open = () => [...document.querySelectorAll("section.chapter")].map((c) => c.getAttribute("data-open")).join();
  // Padding, so a Back the page did not push stays in this document.
  for (let i = 0; i < 4; i += 1) history.pushState(null, "", location.href);
  const go = (step) => new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 800), { once: true });
    history.go(step);
  });
  const back = () => go(-1);
  // A mark on the entry, not `history.length`: a shared tab is capped at 50 entries.
  const mark = (name) => history.replaceState({ ...history.state, mark: name }, "");
  const out = { folds: open() };
  mark("start");
  press("Expand all");
  await wait(500);
  out.expand = history.state?.mark ?? "pushed";
  const expanded = open();
  mark("expanded");
  press("Collapse all");
  await wait(500);
  out.collapse = history.state?.mark ?? "pushed";
  const collapsed = open();
  await back();
  out.back = [history.state?.mark, open() === expanded];
  await back();
  out.back.push(history.state?.mark, open() === out.folds);
  // Forward re-applies each entry's folds: Collapse all left them shut.
  await go(1);
  out.forward = [open() === expanded];
  await go(1);
  out.forward.push(open() === collapsed);
  const box = document.querySelector(".table-tools input.table-filter");
  if (!box) return { ...out, box: null };
  const links = [...document.querySelectorAll(".toc [data-toc]")];
  links[0].click();
  await wait(500);
  const at = location.hash;
  box.value = "zzz-no-such-row";
  box.dispatchEvent(new Event("input", { bubbles: true }));
  await wait(300);
  out.filtered = location.hash !== at;
  // A followed link is no traversal: its filter stays, in the box and in the hash.
  links.find((a) => a.getAttribute("href") !== at.split("~")[0]).click();
  await wait(500);
  out.kept = [box.value, atob(location.hash.split("~")[1] ?? "").includes("zzz-no-such-row")];
  await back();
  await back();
  out.box = box.value;
  return out;
})()
"""

_NARROW = r"""
(async () => {
  const wait = (ms) => new Promise((done) => setTimeout(done, ms));
  for (let i = 0; i < 4; i += 1) history.pushState(null, "", location.href);
  const link = [...document.querySelectorAll(".toc [data-toc]")].at(-1);
  link.click();
  await wait(800);
  const anchor = document.getElementById(location.hash.slice(1).split("~")[0]);
  // The folded rail scrolls away, so a reader opens it from the page top.
  scrollTo(0, 0);
  document.querySelector(".toc-title").click();
  await wait(300);
  const down = Math.round(anchor.getBoundingClientRect().top);
  [...document.querySelectorAll(".toc-controls button")].find((b) => b.textContent.trim() === "Expand all").click();
  await wait(500);
  await new Promise((done) => {
    addEventListener("popstate", () => setTimeout(done, 800), { once: true });
    history.back();
  });
  return { down, height: innerHeight, back: Math.round(anchor.getBoundingClientRect().top) };
})()
"""

_NOTE = r"""
(() => {
  const note = document.querySelector("[data-elided]");
  const tables = [...document.querySelectorAll("table")].filter((t) => t.querySelector("[data-element]"));
  return { note: Boolean(note),
           card: note?.closest("section[data-element]")?.getAttribute("data-element") ?? null,
           last: [...document.querySelectorAll("section[data-element]")].at(-1)?.getAttribute("data-element"),
           above: tables.filter((t) => t.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING).length,
           tables: tables.length };
})()
"""


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    import tools.bga_view as view

    found = pages.pages(tmp_path_factory, "oneset")
    into = tmp_path_factory.mktemp("oneset-big")
    run = pages.two_plane_run(into, ("--layers", "20", "--width", "60"))
    page = into / "page.html"
    view.export(str(run), str(page))
    return {**found, "big": page.as_uri()}


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("label", ["golden", "macro_micro", "big"])
def test_the_rail_tools_and_the_pager_share_one_size_and_line(browser, uris, label, width):
    got = browser.measure(uris[label], _LOOK, width=width, height=844)
    assert len(got["tools"]) >= 4, got["tools"]
    assert [t for t in got["tools"] if t["px"] != SMALL_PX or t["lines"] != 1] == [], got["tools"]
    assert [p for p in got["pagers"] if p["px"] != SMALL_PX or p["gap"] <= 0] == [], got["pagers"]
    if label == "big":
        assert got["pagers"] and got["sorted"], got
    for head in got["sorted"]:
        assert head["th"] in ("none", '""') and head["button"].strip('"').strip() in "▲▼", head


_BOX = r"""
(async () => {
  const nav = document.querySelector(".toc");
  if (nav?.getAttribute("data-folded") === "true") nav.querySelector(".toc-title").click();
  await new Promise((done) => setTimeout(done, 100));
  const box = document.querySelector("input.copy-markdown");
  const label = box.closest("label");
  const b = box.getBoundingClientRect(), l = label.getBoundingClientRect();
  return { box: [b.width, b.height], label: [l.width, l.height],
           line: parseFloat(getComputedStyle(label).lineHeight) };
})()
"""


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
def test_the_markdown_box_is_its_label_s_line(browser, uris, label, width):
    got = browser.measure(uris[label], _BOX, width=width, height=844)
    assert got["box"][1] <= got["line"] + 0.01, got
    assert got["label"][1] >= 24, got


@needs_browser
def test_an_opened_card_fold_sits_under_its_sibling(browser, uris):
    got = browser.measure(uris["macro_micro"], _FOLDS, width=1440, height=900)
    assert got, "a card with both Plane 2 folds"
    assert [f for f in got if f["dx"] != 0] == [], got


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
def test_rail_next_visits_every_entry_in_order(browser, uris, width):
    got = browser.measure(uris["big"], _STEP, width=width, height=844)
    assert "#joint_saving" in got["want"], got
    assert got["seen"] == got["want"], got


@needs_browser
@pytest.mark.parametrize("width", [1440, 390])
def test_rail_next_after_a_pressed_entry_goes_to_the_entry_after_it(browser, uris, width):
    got = browser.measure(uris["big"], _CLICKED, width=width, height=844)
    assert got["want"] == "#joint_saving", got
    if width == 1440:  # the case: the mark has already passed the pressed entry
        assert got["mark"] == "#joint_saving", got
    assert got["seen"] == got["want"], got


@needs_browser
@pytest.mark.parametrize("label", ["golden", "macro_micro", "big"])
def test_expand_and_collapse_push_one_entry_and_back_drops_the_filter(browser, uris, label):
    got = browser.measure(uris[label], _HISTORY, width=1440, height=900)
    assert got["expand"] == got["collapse"] == "pushed", got
    assert got["back"] == ["expanded", True, "start", True], got
    assert got["forward"] == [True, True], got
    if label != "golden":  # golden has no table long enough for a filter
        assert got["filtered"] and got["kept"] == ["zzz-no-such-row", True], got
        assert got["box"] == "", got


@needs_browser
def test_back_after_the_narrow_rail_s_expand_all_lands_the_reader_s_anchor(browser, uris):
    got = browser.measure(uris["big"], _NARROW, width=390, height=844)
    assert got["down"] > 2 * got["height"], got
    assert 0 <= got["back"] < got["height"], got


@needs_browser
def test_the_elided_line_sits_under_the_tables_it_names(browser, uris):
    got = browser.measure(uris["big"], _NOTE, width=1440, height=900)
    assert got["note"] and got["card"] == got["last"], got
    assert got["above"] == got["tables"] > 0, got
