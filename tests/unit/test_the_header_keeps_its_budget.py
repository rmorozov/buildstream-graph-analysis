"""UX-828 (styleguide §3i): the header is at most 72px and carries
identity only - a wordmark, the run's alias and start instant beside
the reader picker. Nothing else.

Measured before this item, on the golden export, 1440x900, header
`position: sticky`, pinned after `scrollTo(0, 2000)`:

```text
header    128.5 px    14.3% of 900
line 2    the run's absolute path, 149 chars, wrapping to two lines
```

The path moved to `run_instance` (`UX-285`) and onto the h1's `title`
(`UX-1047` moved the title from `#wordmark` once the h1 became the
run rather than the wordmark); the version line joined the footer.
This is what keeps it there: a header over budget, or a path back in
its text, reddens here rather than at the next design review.
"""

import os
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: §3i's own number.
HEADER_BUDGET_PX = 72

#: The widths the Acceptance Test names, plus the compact phone width
#: `UX-1047` measured the run's name wrapping the h1 onto its own row
#: at (390x844, the identity line's own wrap already priced into the
#: 72px budget - a second one from the h1 is not).
WIDTHS = ((1440, 900), (1024, 768), (390, 844))

_MEASURE = """
(() => {
  window.scrollTo(0, 2000);
  const header = document.querySelector("header");
  const box = header.getBoundingClientRect();
  // `UX-1047`: the `title` moved from `#wordmark` to the h1 (`#run-name`).
  const heading = document.getElementById("run-name");
  const sec = document.querySelector('[data-section="run_instance"]');
  return {
    header_px: Math.round(box.height),
    sticky: getComputedStyle(header).position,
    headerText: header.innerText,
    headingTitle: heading ? heading.getAttribute("title") : null,
    // `UX-1015`: a folded section is `hidden="until-found"`, whose innerText is "".
    runInstanceText: sec ? sec.textContent : null,
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module", params=["golden", "macro_micro"])
def measured(request, browser, tmp_path_factory):
    """`{width: out}` for one fixture, and the path it was exported
    from - `run.run`'s value, read the same way `app.js` reads it."""
    into = tmp_path_factory.mktemp(f"u828-{request.param}")
    uri = pages.export_uri(pages.FIXTURES[request.param], into)
    run_path = os.path.abspath(into / "snapshot" / pages.FIXTURES[request.param].name)
    return {width: browser.measure(uri, _MEASURE, width=width, height=height) for width, height in WIDTHS}, run_path


@needs_browser
class TestTheHeaderKeepsItsBudget:
    def test_the_height_is_within_budget_at_both_widths(self, measured):
        out, _ = measured
        over = {w: r["header_px"] for w, r in out.items() if r["header_px"] > HEADER_BUDGET_PX}
        assert not over, f"the header is over its {HEADER_BUDGET_PX}px budget (§3i) at: {over}"

    def test_it_stays_sticky(self, measured):
        out, _ = measured
        assert all(r["sticky"] == "sticky" for r in out.values()), out

    def test_the_path_is_absent_from_the_header_text(self, measured):
        out, run_path = measured
        leaked = {w: r["headerText"] for w, r in out.items() if run_path in r["headerText"]}
        assert not leaked, f"the run's absolute path is back in the header's text: {leaked}"

    def test_the_path_is_in_run_instance_and_the_heading_title(self, measured):
        out, run_path = measured
        for width, row in out.items():
            assert row["headingTitle"] == run_path, (width, row)
            assert row["runInstanceText"] is not None, f"no run_instance section at {width}"
            assert run_path in row["runInstanceText"], (width, row)


@needs_browser
def test_a_long_run_name_still_fits_the_budget_on_a_phone(browser, tmp_path_factory):
    """`UX-1047`: neither committed fixture's name is wide enough to
    force the h1 onto its own row - this one's is, deliberately, so a
    regression that drops `#run-name`'s truncation reds here."""
    from tools.bga_view import export

    long_name = "a-very-long-project-directory-name-that-is-quite-wide-indeed"
    run = tmp_path_factory.mktemp("u1047-long") / long_name
    shutil.copytree(pages.FIXTURES["golden"], run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("u1047-long-page") / "report.html"
    export(str(run), str(page))
    out = browser.measure(page.as_uri(), _MEASURE, width=390, height=844)
    assert out["header_px"] <= HEADER_BUDGET_PX, out
