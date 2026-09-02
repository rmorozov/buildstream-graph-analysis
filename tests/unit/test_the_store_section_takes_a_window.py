"""UX-528: the store exhibit and the run picker grew with every snapshot.

The sparklines beside them got a window (`element.js`'s
`HISTORY_POINTS_MAX = 12`); the exhibit, its table twin and the picker
did not, and `UX-394` was filed with two runs in the store. Measured
here on a project whose store holds N copies of the golden run, served
by `bga view` and read at 1440x900:

```text
                      N=2      N=12     N=100     N=100 windowed
picker options          2        12       100                 12
twin rows               2        12       100                 12
svg marks               5        27       203                 27
store-trend nodes      29        92       620                 94
store-trend text      250     1,296    10,451              1,522
store.json            745     4,121    34,056              4,206
```

`--aggregate --format json` is a second document and a **CLI** one: it
runs over the whole listing, so the page's window does not bound it and
`store_aggregate.STAMPS_MAX` does. At 100 snapshots, 3,884 B become
1,948 - against 1,931 at twelve.

The two nodes and 226 characters N=100 does not share with N=12 are the
sentence that says it is a window and the control that opens the rest -
`UX-419`'s badge, one drawing over. A window that does not say how deep
it goes is §3a's defect, so they are the point rather than the residue.
"""
import json
import pathlib
import shutil
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

#: The two sizes the claim is made across: one at the window and one
#: well past it. A single size cannot tell a window from a small store.
AT_THE_WINDOW, PAST_IT = 12, 100

_LOOK = r"""
(() => {
  const deadline = Date.now() + 5000;
  const read = () => {
    const trend = document.querySelector('[data-section="store-trend"]');
    const select = document.getElementById("bga-run");
    const box = select ? select.closest(".run-picker") : null;
    return {
      options: select ? select.options.length : 0,
      typed: box ? box.querySelectorAll("[data-run-typed]").length : 0,
      rows: trend ? trend.querySelectorAll("tbody tr").length : 0,
      nodes: trend ? trend.querySelectorAll("*").length : 0,
      text: trend ? (trend.textContent || "").length : 0,
      marks: trend ? trend.querySelectorAll("svg *").length : 0,
      heading: trend ? (trend.querySelector("h2")?.textContent ?? "") : "",
      window: trend
        ? (trend.querySelector('[data-role="store-window"]')?.textContent ?? "")
        : "",
    };
  };
  return new Promise((done) => {
    const tick = () => {
      const now = read();
      if (now.options || Date.now() > deadline) done(now);
      else setTimeout(tick, 50);
    };
    tick();
  });
})()
"""

#: The §3a focus path, driven. Pressing the control has to *deliver* the
#: rest - a button that loads nothing is the window with a decoration on
#: it, and `data-store-all` is written only after rows arrive.
_SHOW_ALL = r"""
(() => {
  const deadline = Date.now() + 8000;
  const trend = () => document.querySelector('[data-section="store-trend"]');
  return new Promise((done) => {
    const press = () => {
      const button = trend()?.querySelector('[data-role="store-show-all"]');
      if (!button) {
        if (Date.now() > deadline) done({ pressed: false, rows: 0 });
        else setTimeout(press, 50);
        return;
      }
      button.click();
      const settle = () => {
        const all = trend()?.getAttribute("data-store-all");
        if (all || Date.now() > deadline) {
          done({ pressed: true, all: all ? Number(all) : 0,
                 rows: trend().querySelectorAll("tbody tr").length,
                 hidden: button.hidden === true });
        } else setTimeout(settle, 50);
      };
      settle();
    };
    press();
  });
})()
"""


def _project(into, count):
    """A project whose store holds `count` analysable snapshots."""
    into.mkdir(parents=True, exist_ok=True)
    (into / "project.conf").write_text("name: p\nmin-version: 2.0\n",
                                       encoding="utf-8")
    last = None
    for n in range(1, count + 1):
        run = into / ".bga" / "runs" / f"2026{n:04d}01T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        last = run
    return last


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def stores(browser, tmp_path_factory):
    """`{count: reading}` for both sizes, each served once."""
    from tools.bga_view import (payloads, serve, store_aggregate_payload,
                                store_payload)
    from tools.bga_snapshot import store_listing
    from bga import run_store

    out = {}
    for count in (AT_THE_WINDOW, PAST_IT):
        run = _project(tmp_path_factory.mktemp(f"store{count}"), count)
        project = run_store.project_root(str(run))
        store = store_payload(str(run))
        reading = {
            "store": store,
            "whole": store_listing(project),
            "aggregate": store_aggregate_payload(store),
            # The **CLI**'s aggregate: `--aggregate --format json` runs
            # over the whole listing, so the page's window does not
            # bound it and the cap has to.
            "cli_aggregate": store_aggregate_payload(store_listing(project)),
            "store_bytes": len(json.dumps(store).encode()),
        }
        httpd, url = serve(str(run), port=0,
                           documents=dict(payloads(str(run))))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        time.sleep(0.3)
        try:
            reading["page"] = browser.measure(url, _LOOK, 1440, 900)
            reading["shown_all"] = browser.measure(url, _SHOW_ALL, 1440, 900)
        finally:
            httpd.shutdown()
        out[count] = reading
    return out


@needs_browser
@pytest.mark.large
class TestThePageCostsTheSameAtAHundredAsAtTwelve:
    """The Acceptance Test, as clauses."""

    def test_the_picker_offers_the_window_and_not_the_store(self, stores):
        for count in (AT_THE_WINDOW, PAST_IT):
            offered = stores[count]["page"]["options"]
            assert offered == AT_THE_WINDOW, (
                f"N={count}: the run picker offers {offered} runs")

    def test_the_drawing_and_its_twin_are_the_same_size(self, stores):
        small, big = stores[AT_THE_WINDOW]["page"], stores[PAST_IT]["page"]
        for measure in ("rows", "marks"):
            assert big[measure] == small[measure], (
                f"{measure}: {big[measure]} at {PAST_IT} snapshots against "
                f"{small[measure]} at {AT_THE_WINDOW}")

    def test_the_section_grows_by_its_own_sentence_and_nothing_else(
            self, stores):
        """Not "the same", which would be a window that hides that it is
        one. Two nodes - the sentence and the control that opens the
        rest - and the clause names them rather than allowing a
        tolerance something else could grow into."""
        small, big = stores[AT_THE_WINDOW]["page"], stores[PAST_IT]["page"]
        assert big["nodes"] - small["nodes"] == 2, (
            f"{big['nodes']} nodes at {PAST_IT} against {small['nodes']} at "
            f"{AT_THE_WINDOW}; the difference should be the window's own "
            f"sentence and its button")
        assert big["window"], "the window says nothing about itself"

    def test_it_says_which_runs_it_is_drawing(self, stores):
        big = stores[PAST_IT]["page"]
        assert f"last {AT_THE_WINDOW} of {PAST_IT}" in big["heading"], (
            big["heading"])
        small = stores[AT_THE_WINDOW]["page"]
        assert "last" not in small["heading"], (
            f"a store the page holds entire calls itself a window: "
            f"{small['heading']}")
        assert not small["window"], small["window"]


@needs_browser
@pytest.mark.large
class TestTheRestAreReachable:
    """A window that cannot be opened is a store with rows deleted."""

    def test_show_all_loads_every_snapshot(self, stores):
        out = stores[PAST_IT]["shown_all"]
        assert out["pressed"], "no control offers the rest of the store"
        assert out["all"] == PAST_IT, out
        assert out["rows"] == PAST_IT, (
            f"the twin lists {out['rows']} rows after 'show all'")
        assert out["hidden"], "the control is still offering what it gave"

    def test_a_stamp_past_the_window_can_be_typed(self, stores):
        assert stores[PAST_IT]["page"]["typed"] == 1, (
            "no way to open a run the menu does not list")
        assert stores[AT_THE_WINDOW]["page"]["typed"] == 0, (
            "a store the menu holds entire still offers a text box")


@pytest.mark.large
class TestTheDocumentsAreWindowedAtTheSource:
    """The page cannot be light while the document it reads is heavy."""

    def test_the_listing_command_keeps_every_row(self, stores):
        """A listing is O(N) by definition - that is this item's Out of
        Scope, and the clause that holds it."""
        whole = stores[PAST_IT]["whole"]
        assert len(whole["snapshots"]) == PAST_IT, len(whole["snapshots"])
        assert whole["shown"] == PAST_IT

    def test_the_page_s_copy_is_windowed_and_says_so(self, stores):
        store = stores[PAST_IT]["store"]
        assert len(store["snapshots"]) == AT_THE_WINDOW
        assert store["shown"] == AT_THE_WINDOW
        assert store["count"] == PAST_IT, (
            "the windowed document forgot how big the store is, so the "
            "page cannot say what it is a window of")
        assert stores[PAST_IT]["store_bytes"] < 2 * stores[
            AT_THE_WINDOW]["store_bytes"], (
            f"store.json is {stores[PAST_IT]['store_bytes']} B at "
            f"{PAST_IT} snapshots against "
            f"{stores[AT_THE_WINDOW]['store_bytes']} B at "
            f"{AT_THE_WINDOW}")

    def test_the_window_keeps_the_latest_runs(self, stores):
        """The *last* twelve. A window over the oldest runs would meet
        every count above and answer the drift question backwards."""
        store = stores[PAST_IT]["store"]
        whole = stores[PAST_IT]["whole"]
        assert [row["stamp"] for row in store["snapshots"]] == [
            row["stamp"] for row in whole["snapshots"][-AT_THE_WINDOW:]]

    def test_the_aggregate_caps_its_stamps(self, stores):
        from bga.store_aggregate import STAMPS_MAX

        aggregate = stores[PAST_IT]["cli_aggregate"]
        classes = aggregate["host_classes"]
        assert classes, aggregate
        for entry in classes:
            assert len(entry["stamps"]) <= STAMPS_MAX, (
                f"{entry.get('host_class')} names {len(entry['stamps'])} "
                f"runs")
            assert entry["stamps_total"] == PAST_IT, entry["stamps_total"]
        assert aggregate["snapshots"] == PAST_IT, (
            "the CLI's aggregate is over the whole store, and the cap is "
            "on the stamp list rather than on the population")

    def test_the_two_windows_are_the_same_number(self):
        """`element.js` windows the sparklines and `bga_view` windows the
        store; they answer the same question - the last dozen runs of
        this project - and two of them disagreeing about "recent" is
        worse than either."""
        from tools.bga_view import STORE_WINDOW

        source = (REPO / "bga/viewer/element.js").read_text(encoding="utf-8")
        history = int(source.split("HISTORY_POINTS_MAX = ", 1)[1]
                      .split(";", 1)[0].strip())
        assert STORE_WINDOW == history, (
            f"the store window is {STORE_WINDOW} and the history window "
            f"{history}; one of them is not 'the last dozen runs'")
        assert STORE_WINDOW == AT_THE_WINDOW


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
