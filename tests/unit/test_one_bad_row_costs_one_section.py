"""UX-335: a section that throws loses its section, not the page.

The user's field report was `Cannot read properties of undefined
(reading 'start_time')` in the viewer console on a real capture.

**The literal string is not ours.** `start_time` appears nowhere in
this repository and never has - zero hits across every served asset,
the built export, and `git log -S` over all history, and zero
exceptions booting every page live. It was thrown by something else
running on the localhost page, a browser extension's content script
being the likeliest. Recorded here so the next reader does not
re-hunt it; the check on a field machine is an incognito or
extension-free profile.

**The failure class is ours, and it is worse than the string.**
`boot()` wraps the whole render in one `try/catch`, so *any* one
renderer's throw replaced the entire report with a single sentence.
Reproduced by serving the golden run with one `null` row in
`store.json` - a shape a half-finished prune or an interrupted
snapshot can leave behind:

```text
before   refused : "Could not load this run
                    TypeError: Cannot read properties of null
                                (reading 'elements')"
         sections: 0
after    refused : null
         sections: 29          (the same 29 the healthy store renders)
```

Two things had to change and both are checked here. The two null-row
sites state the absence instead of indexing it, and containment moved
to the section boundary: a renderer that throws now yields an inline
card naming the payload it was drawn from, **and a `console.error`** -
which is what puts this class inside `UX-334`'s net. It was outside
it before, and invisibly so: the page-wide catch swallowed the throw,
so the boot came back with zero console errors while showing the
reader nothing at all.

**What this file cannot see**: the shim has no layout engine and its
`getElementById` returns null, so `boot()` never runs there. The
containment clauses are therefore browser-only and skip where there is
no Chrome; the absence-stating clauses run on the shim, where the
renderers can be fed directly.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome
from degenerate_store import SHAPES, damaged

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

node = shutil.which("node")
chrome = find_chrome()
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)


def _project(tmp_path, count=3):
    """A project whose store holds `count` analysable snapshots."""
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n",
                                           encoding="utf-8")
    runs = []
    for n in range(1, count + 1):
        run = tmp_path / ".bga" / "runs" / f"2026010{n}T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        runs.append(run)
    return runs[-1]


# --------------------------------------------------------- the shim half

_RENDERERS = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
shim.installDocument();
const views = await import("%(views)s");
const { readFileSync } = await import("node:fs");
const store = JSON.parse(readFileSync(%(store)s, "utf8"));

const text = (n) => (n.textContent ?? "") + (n.children ?? []).map(text).join("");
let threw = null, trend = null, history = null;
try {
  const drawn = views.renderTrend(store, null, null);
  trend = drawn && { text: text(drawn),
                     unreadable: drawn.getAttribute("data-unreadable-rows") };
  const block = views.renderElementHistory(store, "work-a.bst", null);
  history = block && { text: text(block),
                       unreadable: block.getAttribute("data-unreadable-rows") };
} catch (error) {
  threw = String(error);
}
console.log(JSON.stringify({ threw, trend, history }));
"""


def _renderers(store, tmp_path):
    """Feed a store straight to the two renderers that indexed its rows."""
    path = tmp_path / "store.json"
    path.write_text(json.dumps(store), encoding="utf-8")
    script = _RENDERERS % {"views": (REPO / "tests/viewer.mjs").as_uri(),
                           "store": json.dumps(str(path))}
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=120,
                          env={**os.environ, "BGA_DOM_SHIM":
                               (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def healthy_store(tmp_path_factory):
    from tools.bga_view import store_payload

    run = _project(tmp_path_factory.mktemp("store"))
    store = store_payload(str(run))
    assert store and len(store.get("snapshots") or []) >= 2, (
        "the fixture project produced no store to damage")
    return store


@needs_node
class TestTheRenderersStateTheAbsence:
    """The half a DOM can answer, on every shape the fixture offers."""

    @pytest.mark.parametrize("shape", SHAPES)
    def test_no_renderer_throws_on_a_row_it_cannot_read(
            self, shape, healthy_store, tmp_path):
        out = _renderers(damaged(healthy_store, shape), tmp_path)
        assert out["threw"] is None, (shape, out["threw"])

    def test_the_trend_says_how_many_rows_it_could_not_read(
            self, healthy_store, tmp_path):
        """Counted and stated, not silently dropped: a trend over 3 of 4
        snapshots that presents itself as a trend over 4 is the quiet
        wrong this states instead."""
        out = _renderers(damaged(healthy_store, "null_row"), tmp_path)
        assert out["trend"], "the trend did not render at all"
        assert out["trend"]["unreadable"] == "1", out["trend"]
        assert "1 row in this store could not be read and is not drawn" \
            in out["trend"]["text"], out["trend"]["text"]

    def test_the_history_names_the_damage_rather_than_the_wrong_reason(
            self, healthy_store, tmp_path):
        """Three absences, not two. "It has not been on the critical
        path" is a true sentence about a healthy store and a misleading
        one about a damaged store - it sends the reader to look at the
        element instead of at the store."""
        out = _renderers(damaged(healthy_store, "null_row"), tmp_path)
        assert out["history"]["unreadable"] == "1", out["history"]
        assert "could not be read" in out["history"]["text"], out["history"]

    def test_a_healthy_store_says_none_of_this(self, healthy_store, tmp_path):
        """The positive control. A guard that only ever sees the damaged
        store cannot tell a sentence that fires from one that is always
        there."""
        out = _renderers(healthy_store, tmp_path)
        assert out["threw"] is None, out["threw"]
        assert out["trend"]["unreadable"] is None, out["trend"]
        assert "could not be read" not in out["trend"]["text"], out["trend"]


# ------------------------------------------------------ the browser half

_BOOTED = """(() => {
  const root = document.getElementById("report");
  // The page-wide banner only. A contained section failure wears the
  // same refusal styling on purpose, and `.verdict.refused` alone would
  // read one section's card as the whole page having refused - which is
  // the exact confusion this file exists to remove.
  const refused = root.querySelector("[data-page-failed]");
  return {
    refused: refused ? refused.textContent.slice(0, 200) : null,
    sections: root.querySelectorAll("section[data-section]").length,
    failed: [...root.querySelectorAll("[data-section-failed]")]
              .map((n) => ({ section: n.getAttribute("data-section"),
                             payload: n.getAttribute("data-payload"),
                             text: n.textContent })),
  };
})()"""


def _boot(run, store, browser):
    """Serve `run` with `store` as its store document, and boot it."""
    from tools.bga_view import payloads, serve

    documents = dict(payloads(str(run)))
    documents["store.json"] = store
    httpd, url = serve(str(run), port=0, documents=documents)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        return browser.observe(url, _BOOTED)
    finally:
        httpd.shutdown()


@pytest.fixture(scope="module")
def booted(tmp_path_factory, healthy_store):
    if chrome is None or node is None:                   # pragma: no cover
        pytest.skip(NO_BROWSER)
    run = _project(tmp_path_factory.mktemp("boot"))
    with Browser(chrome) as opened:
        yield {
            "healthy": _boot(run, healthy_store, opened),
            "damaged": _boot(run, damaged(healthy_store, "null_row"), opened),
        }


@needs_browser
@needs_node
class TestOneBadRowCostsOneSection:
    def test_the_damaged_store_does_not_refuse_the_page(self, booted):
        assert booted["damaged"]["value"]["refused"] is None, (
            booted["damaged"]["value"]["refused"])

    def test_it_renders_every_section_the_healthy_store_renders(self, booted):
        """The measurement the item turns on: 0 sections before, and the
        *same* count as the healthy boot after. Equal rather than
        "some", because a fix that dropped six sections quietly would
        satisfy "did not collapse"."""
        assert booted["damaged"]["value"]["sections"] == \
            booted["healthy"]["value"]["sections"], (
                booted["damaged"]["value"], booted["healthy"]["value"])
        assert booted["healthy"]["value"]["sections"] > 20, (
            "the healthy boot renders almost nothing, so the equality "
            "above is not saying what it looks like")

    def test_no_section_had_to_be_contained(self, booted):
        """Containment is the net, not the fix. Both boots draw every
        section for real; a `data-section-failed` card here would mean
        a renderer is still throwing and the card is hiding it."""
        for name, got in booted.items():
            assert got["value"]["failed"] == [], (name, got["value"]["failed"])

    def test_neither_boot_says_anything_to_the_console(self, booted):
        """`UX-334`'s clause, on this fixture. The damaged store must be
        quiet *and* correct - a page that logged an error per row would
        pass every clause above and fail the round's other guard."""
        for name, got in booted.items():
            bad = [e for e in got["console"] if e["level"] in ("error", "assert")]
            assert not bad, (name, [e["text"][:200] for e in bad])
            assert not got["csp"], (name, got["csp"])


@needs_browser
@needs_node
class TestTheLoadFailureIsStillAPageFailure:
    """The half containment must **not** take away.

    A report that will not parse is not a report, and there is nothing
    to render around it - so `boot()`'s page-wide catch stays, and its
    banner is marked `data-page-failed` so a stylesheet and a guard can
    tell it from a section's card. Both wear `.verdict.refused`, which
    is right (they both say "this did not work") and is why the marker
    exists.

    Added because a mutation found nothing: removing the marker left
    every other clause in this file green. A distinction the page draws
    and no guard reads is a distinction the next round deletes.
    """

    def test_an_unparseable_report_refuses_the_page_and_says_which(
            self, tmp_path_factory, healthy_store):
        from tools.bga_view import payloads, serve

        run = _project(tmp_path_factory.mktemp("unparseable"))
        documents = dict(payloads(str(run)))
        # A `report.json` that is literally `null` - what a truncated
        # write or an empty file deserializes to. `boot()` reaches for
        # `payload.schema` on it before any section exists to contain.
        #
        # `{"not": "an analyze document"}` was tried first and is *not*
        # a load failure: the page rendered it without complaint,
        # because a document with no `schema` key renders as a document
        # with nothing in it. Worth knowing - a wrong-shaped report is
        # quietly empty rather than refused - but it is not this
        # clause's subject.
        documents["report.json"] = None
        documents["store.json"] = healthy_store
        httpd, url = serve(str(run), port=0, documents=documents)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        time.sleep(0.3)
        try:
            with Browser(chrome) as opened:
                got = opened.observe(url, """(() => {
                  const root = document.getElementById("report");
                  const page = root.querySelector("[data-page-failed]");
                  return {
                    page: page ? page.textContent.slice(0, 120) : null,
                    sectionCards:
                      root.querySelectorAll("[data-section-failed]").length,
                  };
                })()""")
        finally:
            httpd.shutdown()

        value = got["value"]
        assert value["page"], (
            "a report that will not render produced no page-wide refusal - "
            "containment swallowed the one failure that should stop the page")
        assert "Could not load this run" in value["page"], value["page"]
        assert value["sectionCards"] == 0, (
            "the load failure was reported as a section's failure, which "
            "tells the reader one section is missing when the answer is "
            "that none of them could be drawn")


@needs_browser
@needs_node
class TestTheContainmentItselfWorks:
    """A renderer that really throws. Nothing in the shipped page does
    any more - that is what the classes above establish - so this
    injects one, which is the only way to measure the net rather than
    the absence of anything to catch.
    """

    @staticmethod
    def _assets_with_a_throwing_renderer(tmp_path):
        """A **copy** of the viewer, with one renderer made to throw.

        The first draft wrote the probe into the checked-out
        `bga/viewer/views.js` and restored it in a `finally`. That is
        the shared-state race `UX-336`'s `-n auto` makes real, and it
        bit on the first full run: another worker booted a page while
        the probe was in the file, and the failure surfaced *here*
        rather than there. The same defect this round fixed in the
        contract-inventory probe, introduced two files away.

        Copying costs one directory and touches nothing another worker
        can see.
        """
        from tools.bga_view import ASSET_DIR

        assets = tmp_path / "viewer"
        shutil.copytree(ASSET_DIR, assets)
        views = assets / "views.js"
        source = views.read_text(encoding="utf-8")
        anchor = "export function renderOverview(payload) {"
        assert anchor in source, "renderOverview moved; re-anchor the probe"
        views.write_text(source.replace(
            anchor,
            anchor + '\n  throw new TypeError("UX-335 containment probe");',
            1), encoding="utf-8")
        return assets

    def test_a_throwing_renderer_loses_its_section_and_says_so(
            self, tmp_path_factory, healthy_store, monkeypatch):
        import tools.bga_view as view

        tmp = tmp_path_factory.mktemp("throw")
        run = _project(tmp)
        # In this process only: the server reads `ASSET_DIR` at request
        # time, and every other xdist worker is a process of its own
        # still reading the real directory.
        monkeypatch.setattr(view, "ASSET_DIR",
                            str(self._assets_with_a_throwing_renderer(tmp)))
        with Browser(chrome) as opened:
            got = _boot(run, healthy_store, opened)

        value = got["value"]
        assert value["refused"] is None, (
            "the page still refuses as a whole, so containment did not "
            "contain")
        assert [card["section"] for card in value["failed"]] == ["overview"], \
            value["failed"]
        assert value["sections"] > 20, (
            "the rest of the report went with it", value)
        # The card names the *payload*, because the section is the
        # consequence and the document is the cause - a reader told only
        # "overview failed" has nowhere to go next.
        [card] = value["failed"]
        assert card["payload"] == "report.json", card
        errors = [e["text"] for e in got["console"]
                  if e["level"] in ("error", "assert")]
        assert any("UX-335 containment probe" in t for t in errors), errors
        assert any('section "overview" failed on report.json' in t
                   for t in errors), errors
