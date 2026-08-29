"""UX-394: nothing in the page moved between runs.

Round 63 ran the capture cycle twice, so the store held two runs of one
project while the report was open:

```text
runs in the store                        2
controls in the page reaching another    0
```

`bga view` was a single-run window. The tool already speaks about more
than one run - `bga compare`, `@prev`, `@last`, the store's own
listing - and all of it is CLI vocabulary, so a reader in a browser had
to go back to a terminal, work out which run identity they wanted, and
re-invoke. That is the largest gap between what the store holds and
what the page offers, and it falls on the tool's own use case: *did my
change make the build faster*.

**A navigation, not a re-render.** The page reads its payload once at
boot (`UX-296`: it parses nothing), so `?run=<stamp>` *is* the state -
choosing a run loads that URL, and sending someone the URL sends them
the same view of the same run (`UX-211`).

**Absent, not empty.** An export carries one run's payload and can
reach no other, so it renders no selector rather than a control that
fails - which is what the Falsification's other direction forbids. The
list comes from `store.json`, which only a served page has.
"""
import pathlib
import shutil
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

_PICKER = """(() => {
  const box = document.querySelector("nav.toc .run-picker");
  if (!box) return { found: false, sections: document.title };
  const select = box.querySelector("select");
  return {
    found: true,
    inRail: Boolean(box.closest("nav.toc")),
    options: [...select.options].map((o) => o.value),
    labels: [...select.options].map((o) => o.textContent),
    selected: select.value,
    jumps: [...box.querySelectorAll("[data-run-jump]")].map(
      (b) => [b.getAttribute("data-run-jump"), b.getAttribute("data-run")]),
  };
})()"""

#: Where each control *goes*, read off the control. Driving the change
#: would navigate the page and take the evaluation with it, so the URL
#: is written on the option and the guard loads it itself - which
#: `test_the_other_run_s_payload_is_what_comes_back` does.
_SWITCH = """(() => {
  const box = document.querySelector("nav.toc .run-picker");
  const select = box.querySelector("select");
  return {
    urls: [...select.options].map(
      (o) => [o.value, o.getAttribute("data-run-url")]),
    jumpUrls: [...box.querySelectorAll("[data-run-jump]")].map(
      (b) => b.getAttribute("data-run-url")),
  };
})()"""


def _project(into, count=3):
    """A project whose store holds `count` analysable snapshots."""
    (into / "project.conf").write_text("name: p\nmin-version: 2.0\n",
                                       encoding="utf-8")
    runs = []
    for n in range(1, count + 1):
        run = into / ".bga" / "runs" / f"2026010{n}T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        (run / "expected_output.json").unlink(missing_ok=True)
        runs.append(run)
    return runs[-1]


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """The latest of three runs, served, with the store behind it."""
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    from tools.bga_view import payloads, serve

    run = _project(tmp_path_factory.mktemp("runs"))
    httpd, url = serve(str(run), port=0, documents=dict(payloads(str(run))))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(find_chrome()) as browser:
            yield browser, url, httpd
    finally:
        httpd.shutdown()


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheSelectorIsThere:
    def test_it_lists_the_store_s_runs(self, served):
        browser, url, _ = served
        seen = browser.measure(url, _PICKER, 1440, 900)
        assert seen["found"], "the page still reaches no other run"
        assert seen["inRail"]
        assert seen["options"] == ["20260101T000000Z", "20260102T000000Z",
                                   "20260103T000000Z"], seen["options"]

    def test_the_identity_is_what_the_run_is(self, served):
        """`UX-95`: the alias a reader types and what the run measured,
        never a directory name."""
        browser, url, _ = served
        seen = browser.measure(url, _PICKER, 1440, 900)
        joined = " ".join(seen["labels"])
        assert "@last" in joined and "@prev" in joined, seen["labels"]
        assert "s" in seen["labels"][0], seen["labels"][0]
        assert "/" not in joined, seen["labels"]

    def test_the_current_run_is_the_selected_one(self, served):
        browser, url, _ = served
        seen = browser.measure(url, _PICKER, 1440, 900)
        assert seen["selected"] == "20260103T000000Z", seen["selected"]

    def test_the_two_neighbours_are_one_click(self, served):
        """Previous and latest, from the aliases the store publishes."""
        browser, url, _ = served
        seen = browser.measure(url, _PICKER, 1440, 900)
        names = dict(seen["jumps"])
        assert names.get("previous") == "20260102T000000Z", seen["jumps"]
        # On the latest run there is no "latest" to offer - a control
        # that goes where you are is the dead affordance `UX-194` ruled
        # out.
        assert "latest" not in names, seen["jumps"]


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestSwitchingReachesTheOtherRun:
    def test_the_selection_travels_in_the_url(self, served):
        """`UX-211`: the state is the URL, so it can be sent to someone.

        Every option, and every one-click neighbour, carries the URL it
        opens - which is what the next clause then loads.
        """
        browser, url, _ = served
        seen = browser.measure(url, _SWITCH, 1440, 900)
        assert seen["urls"] == [
            [stamp, f"?run={stamp}"] for stamp, _ in seen["urls"]], seen
        assert all(link and link.startswith("?run=")
                   for link in seen["jumpUrls"]), seen

    def test_the_other_run_s_payload_is_what_comes_back(self, served):
        """The server builds it on request, from the store it lists.

        A selector that changed the URL and served the same document
        would pass every clause above.
        """
        browser, url, _ = served
        look = """(() => ({
          run: (document.querySelector("#run-path")?.textContent ?? ""),
          selected: document.querySelector(
            "nav.toc .run-picker select")?.value ?? null,
        }))()"""
        here = browser.measure(url, look, 1440, 900)
        there = browser.measure(f"{url}?run=20260101T000000Z", look, 1440, 900)
        assert here["run"] != there["run"], (here, there)
        assert "20260101T000000Z" in there["run"], there["run"]
        assert there["selected"] == "20260101T000000Z", there

    def test_an_unknown_stamp_falls_back_rather_than_refusing(self, served):
        """The selector only offers stamps from this store, so an
        unknown one is a hand-edited URL - and the page it lands on is
        a real report of a real run rather than an error."""
        browser, url, _ = served
        look = '(() => document.querySelectorAll("section[data-section]").length)()'
        assert browser.measure(f"{url}?run=nope", look, 1440, 900) > 5


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestAnExportOffersNothingItCannotReach:
    """`UX-195`: an export is one self-contained file."""

    def test_it_renders_no_selector(self, tmp_path_factory):
        uri = pages.export_uri(pages.FIXTURES["macro_micro"],
                               tmp_path_factory.mktemp("no-store"))
        with Browser(find_chrome()) as browser:
            seen = browser.measure(uri, _PICKER, 1440, 900)
        assert seen["found"] is False, (
            "the export offers a run selector it cannot follow, which is "
            "the one thing the Falsification says it must not do")
