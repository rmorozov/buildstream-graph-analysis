"""UX-523: what the browser guards actually spend, and on what.

CI's reference says the forty browser-tier files are 685 of the suite's
1,330 serial seconds. `UX-523` was filed against the launch and the
export, and the measurement says neither:

```text
three browser files, serial, before
  DRIVES     70 in 112.3s      85.5 %
  EXPORTS     3 in   5.0s       3.8 %
  LAUNCHES    3 in   1.0s       0.8 %
```

A drive was 1.6s and **1.2s of it was `SETTLE_FLOOR_MS`** - a sleep
`UX-482` left beside the condition that replaced it, "so nothing
observes earlier than it used to". What the floor was covering is the
gap between `#report` filling and `boot()` finishing the wiring after
it, which no measurement of the report's size can see. So the page
says when it is done - `data-bga-booted` - and this file holds both
directions of that:

- a page that boots **late** is still measured whole - the claim the
  floor was protecting, and the one a size-watching driver breaks;
- a page that boots **at once** is not waited out - the claim the
  floor broke, and the reason the suite slept ~430 times for 1.2s.

The second guard is a duration, which fixing guide §5 says is usually
the wrong shape. It is the right one here because the *subject under
test is a wait*: an upper bound on a sleep cannot be asserted except in
seconds, and it is set at 4× the measured drive so a loaded runner does
not redden it.
"""
import os
import pathlib
import re
import sys
import time

import pytest

REPO = str(pathlib.Path(__file__).resolve().parents[2])
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

from browser import Browser, find_chrome, NO_BROWSER      # noqa: E402

chrome = find_chrome()
needs_chrome = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The page under test boots after this long. Comfortably past the
#: 150ms settle step, so a run that does not wait for the condition
#: measures an empty `#report` rather than racing it.
LATE_MS = 700

#: What one drive may take on a page that is finished when it loads.
#: Measured at 0.56s on the two committed exports; 4× that is the bound.
PROMPT_S = 2.4

#: The third miss, found on round 80's merge: the settle keyed on
#: `#report`, which is `index.html`'s section. `perfetto.html` has no
#: `#report` and two `fetch`es, so it went on settling on "the markup
#: stopped growing" - green alone, red under the suite. A page declares
#: it will speak (`data-bga-boots`) and this fixture has no `#report`,
#: so only the declaration can make the driver wait for it.
_HANDOFF = """<!doctype html><html lang="en" data-bga-boots="1">
<meta charset="utf-8"><title>t</title>
<body><div id="questions"></div>
<script>
  setTimeout(() => {
    document.getElementById("questions").innerHTML =
      Array.from({length: 40}, (_, i) => `<h4 id="q${i}">q ${i}</h4>`).join("");
    document.documentElement.dataset.bgaBooted = "1";
  }, %(late)d);
</script>
"""

_PAGE = """<!doctype html><meta charset="utf-8"><title>t</title>
<body><div id="report"></div>
<script>
  const late = %(late)d;
  const fill = () => {
    document.getElementById("report").innerHTML =
      Array.from({length: 40}, (_, i) => `<section id="s${i}">row ${i}</section>`)
        .join("");
    // What the shipped page's `boot()` does last, and the whole of
    // what the driver waits for.
    document.documentElement.dataset.bgaBooted = "1";
  };
  if (late) setTimeout(fill, late); else fill();
</script>
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    made = {}
    for label, late in (("late", LATE_MS), ("prompt", 0)):
        path = tmp_path_factory.mktemp(f"settle-{label}") / "page.html"
        path.write_text(_PAGE % {"late": late}, encoding="utf-8")
        made[label] = path.as_uri()
    path = tmp_path_factory.mktemp("settle-handoff") / "page.html"
    path.write_text(_HANDOFF % {"late": LATE_MS}, encoding="utf-8")
    made["handoff"] = path.as_uri()
    return made


@needs_chrome
class TestTheWaitIsAConditionAndNotADuration:
    def test_a_page_that_boots_late_is_measured_whole(self, browser, pages):
        """The claim `UX-482`'s floor was protecting. It must survive
        the floor's removal, or the removal bought speed with truth."""
        assert browser.measure(
            pages["late"], "document.querySelectorAll('section').length") == 40

    def test_a_page_with_no_report_is_waited_for_too(self, browser, pages):
        """The same claim on the page that has no `#report`. Without
        the declaration this measures 0 - the markup is stable and
        empty for the whole 700ms."""
        assert browser.measure(
            pages["handoff"], "document.querySelectorAll('h4').length") == 40

    def test_a_page_that_boots_at_once_is_not_waited_out(self, browser, pages):
        """And the claim the floor broke. Without this the condition
        can be satisfied by any sleep long enough, which is what was
        there before and what cost the suite its browser tier."""
        start = time.time()
        assert browser.measure(
            pages["prompt"], "document.querySelectorAll('section').length") == 40
        spent = time.time() - start
        assert spent < PROMPT_S, f"a finished page took {spent:.2f}s to measure"

    def test_the_driver_sleeps_before_nothing(self):
        """The mechanism, read rather than timed: no unconditional wait
        stands between the navigation and the settle loop. A guard on
        seconds alone would go green again the moment a runner got
        fast enough to hide a floor half the size."""
        source = open(os.path.join(REPO, "tests/cdp.mjs"), encoding="utf-8").read()
        after = source.split('await send("Page.navigate"')[1]
        before_loop = after.split("const state = async ()")[0]
        assert "setTimeout" not in before_loop, before_loop


@needs_chrome
class TestOneBrowserPerWorker:
    def test_a_second_open_is_the_same_browser(self):
        """`UX-523`'s other half. Thirty-eight files opened one each;
        one process drives one page at a time, so they can be one."""
        with Browser(chrome) as first:
            with Browser(chrome) as second:
                assert second.port == first.port

    def test_it_survives_the_with_that_opened_it(self, pages):
        """The shared browser outlives its block - otherwise the first
        guard file to finish takes it away from the next one.

        Driven from an empty `_SHARED` on purpose: reusing the one this
        module already holds gives a handle with **no process of its
        own**, whose `__exit__` is a no-op whatever it says. Measured -
        a mutation that closed on every exit left this file green until
        the launcher itself was the thing under test.
        """
        import browser as module

        held = module._SHARED.pop(chrome, None)
        try:
            with Browser(chrome) as launcher:
                port, process = launcher.port, launcher.process
            assert process.poll() is None, "the launcher closed its own browser"
            with Browser(chrome) as again:
                assert again.port == port
                assert again.measure(
                    pages["prompt"],
                    "document.querySelectorAll('section').length") == 40
            module._SHARED.pop(chrome, None)
            process.terminate()
        finally:
            if held is not None:
                module._SHARED[chrome] = held

    def test_the_shipped_page_says_when_it_is_booted(self):
        """The condition lives on both sides: a driver that waits for a
        flag no page sets waits out its ceiling on every load. `boot()`
        sets it in a `finally`, so the failure page - a finished page,
        not a slow one - is booted too."""
        source = open(os.path.join(REPO, "bga/viewer/app.js"),
                      encoding="utf-8").read()
        tail = source.split("async function boot()")[1].split("\n}")[0]
        assert "} finally {" in tail
        assert "dataset.bgaBooted" in tail.split("} finally {")[1]
        assert "documentElement?.dataset" in tail, (
            "unguarded: forty-eight shims model no documentElement")

    def test_the_shared_browser_is_closed_at_exit(self):
        """`atexit`, not `__exit__`. A worker that left a Chrome behind
        would leak one per xdist worker per run."""
        import browser as module

        assert chrome in module._SHARED
        source = open(os.path.join(REPO, "tests/browser.py"),
                      encoding="utf-8").read()
        assert re.search(r"@atexit\.register\s*\ndef _close_shared", source)

    def test_a_dead_shared_browser_is_replaced(self):
        """The input class a cached process has that a fresh one does
        not: it can die. The next `with` must launch rather than hand
        out a port nothing is listening on."""
        import browser as module

        was = module._SHARED.pop(chrome, None)
        try:
            stale = Browser(chrome)
            stale.port = 1
            module._SHARED[chrome] = stale
            with Browser(chrome) as opened:
                assert opened.port != 1
                fresh = opened
        finally:
            module._SHARED[chrome] = was if was is not None else fresh


class TestBothShippedPagesSpeak:
    """Read, not driven, and so **not** behind `needs_chrome`: a
    machine with no Chrome is exactly where a page could quietly stop
    declaring it, and the browser gate would hide that until CI."""

    def test_both_shipped_pages_declare_it_and_stamp_it(self):
        """Two pages boot from a module and both must speak. The
        handoff page did not, and settled on the heuristic instead -
        three clauses of `test_one_page_behind_the_button.py` red under
        the full suite and green alone."""
        for page, module in (("index.html", "app.js"),
                             ("perfetto.html", "perfetto_page.js")):
            markup = open(os.path.join(REPO, "bga/viewer", page),
                          encoding="utf-8").read()
            assert 'data-bga-boots="1"' in markup, (
                f"{page} does not declare that it will say when it has "
                f"booted, so the driver cannot know to wait")
            source = open(os.path.join(REPO, "bga/viewer", module),
                          encoding="utf-8").read()
            assert "dataset.bgaBooted" in source, (
                f"{module} never says it, so {page}'s declaration is a "
                f"promise nothing keeps and every drive waits the ceiling")
