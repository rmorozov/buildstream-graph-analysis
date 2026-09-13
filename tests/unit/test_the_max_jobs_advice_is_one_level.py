"""UX-831 (styleguide §3a/§3d): the max-jobs advice row is one level.

`priced` used to be a column, so `max_jobs_advice.elements` folded a
table inside a table inside a table - round 115's field report read
`data-levels=4`, 114 px/row. The fix moved `bga:columns` onto the
`elements` array (`bga/schemas.py`) and added two flat columns,
`price_cost_us`/`price_refusal` (`bga/correlate.py`), so `priced`
itself is no longer *rendered* - it stays in the JSON, undisturbed.

**No committed fixture carries `capacity_recommendation.max_jobs_advice`**:
`compute_max_jobs_advice` needs a host CPU series *and* Plane 2 RSS
together, and no two-plane fixture has both (`host_cpu`'s README says
so for the series half). So this builds one the way `tests/pages.py`'s
`transfer_run`/`shared_resource_run` already do - inject a block, shaped
exactly as `bga/correlate.py` emits it, into a copy of a committed
fixture's `analyze.json` - rather than reading a hand-rolled proxy for
the renderer.

**`data-levels` measures the true value, not the rendered columns**
(`folded()`'s own comment: "the numbers are on the element so a walk
can check them against the value"). `shapeOf` gives any non-empty
array-of-records a floor of 2 (the array is a level, each row is a
level) before `priced` is even considered - measured directly:
`shapeOf([{a: 1}])` is `{levels: 2, rows: 1}`. With `priced` kept
nested per the contract, this table's own fold reads **3**, not the
Acceptance Test's `1` - measured below, and flagged rather than
resolved here (the Outcome states it as the open decision).
"""
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

CAPPED_BADGE = re.compile(r"^[\d,]+ of [\d,]+$")

ELEMENTS_TABLE_JS = r"""
(() => {
  const t = document.querySelector(
    'table[data-table="capacity_recommendation.max_jobs_advice.elements"]');
  if (!t) return null;
  const fold = t.closest("details[data-levels]");
  // A closed `<details>` lays out nothing - `getBoundingClientRect()`
  // on a row inside it reads all zeros, which is why a mutated,
  // four-level page also "passed" a `<= 40` check that never opened
  // the fold to measure a real row. `elements` sits inside its own
  // fold *and* `max_jobs_advice`'s own, so every ancestor `<details>`
  // opens, not only the nearest - and the section itself sits inside
  // a `section.chapter[data-open="false"]`, which `display: none`s it
  // by the same rule (`chapters.js`'s `makeBox`), so that opens too.
  for (let up = t; up; up = up.parentElement) {
    if (up.tagName === "DETAILS") up.open = true;
    if (up.classList?.contains("chapter")) up.setAttribute("data-open", "true");
  }
  const wrapper = t.parentElement;
  const badgeEl = wrapper
    ? [...wrapper.querySelectorAll(".badge")].find((b) => !t.contains(b))
    : null;
  const body = t.querySelector("tbody");
  const firstRow = body ? body.children[0] : null;
  return {
    levels: fold ? fold.getAttribute("data-levels") : null,
    foldPath: fold ? fold.getAttribute("data-fold-path") : null,
    nestedTables: t.querySelectorAll("table").length,
    headers: [...t.querySelectorAll("thead th")].map(
      (th) => th.textContent.trim()),
    badge: badgeEl ? badgeEl.textContent.trim() : null,
    hasFilter: !!(wrapper && wrapper.querySelector("input.table-filter")),
    rowHeight: firstRow ? firstRow.getBoundingClientRect().height : null,
    order: body ? [...body.children].map(
      (tr) => tr.querySelector('[data-column="element"]')?.getAttribute(
        "data-raw")) : [],
  };
})()
"""


def _priced(cost_us, duration_before_us=5_000_000):
    """`price_max_jobs_advice`'s own `priced` shape - the object the
    contract keeps nested and unrendered."""
    return {"replayed_baseline_us": 100_000_000,
            "projected_us": 100_000_000 + cost_us, "cost_us": cost_us,
            "duration_before_us": duration_before_us,
            "duration_floor_us": max(1, duration_before_us - cost_us),
            "kind": "floor"}


def _row(uid, current, recommended, local_max=3, samples=10, refusal=None,
         price_cost_us=None, price_refusal=None):
    row = {"element": uid, "current_max_jobs": current,
           "recommended_max_jobs": recommended,
           "max_jobs_change": (recommended - current)
               if recommended is not None and current is not None else None,
           "local_max_concurrency": local_max, "samples_in_span": samples,
           "refusal": refusal}
    if price_cost_us is not None:
        row["priced"] = _priced(price_cost_us)
        row["price_cost_us"] = price_cost_us
        row["price_kind"] = "floor"
    if price_refusal is not None:
        row["price_refusal"] = price_refusal
    return row


#: One of each input class the Decomposition names: a priced row, a
#: refused row (both the top-level `refusal` and `price_refusal`
#: shapes), an unchanged row. Left **unsorted** here - the export goes
#: through `bga/correlate.py`'s own `_advice_row_rank` state (mirrored
#: by hand: the JSON a page reads is already ranked by the time it is
#: committed, and this fixture stands in for that committed JSON, not
#: for the ranking function itself, which `test_the_max_jobs_price_
#: moves_with_the_recommendation.py` covers against the real code).
#: `libc.bst`/`libb.bst`/`liba.bst`/`core.bst` - 7-8 characters, the
#: length of every uid `tests/fixtures/golden`'s own graph carries
#: (`base.bst`, `lib.bst`, `app.bst`, `extra.bst`: 7-9). A longer,
#: more "readable" name (`lowered.bst`, tried first) wraps the
#: Element column into two lines at 9 columns wide and inflates every
#: row on that account alone - a fixture artifact, not the row's own
#: shape, so the fixture is the realistic length instead.
_ROWS = [
    _row("libc.bst", 4, 2, price_cost_us=3000),
    _row("libb.bst", 2, 2, price_cost_us=0),
    _row("liba.bst", 1, 4,
         price_refusal="this run has no evidence of how it scales up"),
    _row("core.bst", 4, None, local_max=None, samples=1,
         refusal="only 1 host CPU sample interval(s) fall inside this "
                 "element's BUILD span - 3 needed"),
]
# The rank `_advice_row_rank` would give: priced lowerings by cost
# ascending, then the rest, refusals last.
_RANKED = [_ROWS[0], _ROWS[1], _ROWS[2], _ROWS[3]]


def _advice_uri(into, rows, name="advice"):
    """A `with_timeline` copy with a synthetic `capacity_recommendation.
    max_jobs_advice` - `elements` in `bga/correlate.py`'s own published
    shape. `snapshot_copy` keeps `analyze.json` beside the run, which is
    where `published_analysis` (and so `view.export`'s default,
    non-reanalysing path) reads it."""
    import tools.bga_view as view

    run = pages.snapshot_copy(REPO / "tests/fixtures/with_timeline/run", into)
    doc_path = pathlib.Path(run).parent / "analyze.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    doc["capacity_recommendation"] = {
        "builders": 4, "host_cpu_count": 4,
        "constraints": [{"name": "CPU", "allows": 4, "reason": "4 cores"}],
        "binding_constraint": "CPU", "recommended_builders": 4,
        "builders_change": 0, "caveat": "a replay, not a prediction",
        "max_jobs_advice": {
            "min_samples_in_span": 3, "host_cores": 4, "elements": rows,
            "pricing_assumptions": ["dispatch sentence", "floor sentence"],
        },
    }
    doc_path.write_text(json.dumps(doc), encoding="utf-8")
    page = pathlib.Path(into) / f"{name}.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@needs_browser
@pytest.mark.medium
def test_the_advice_row_is_one_level_and_capped(tmp_path_factory, browser):
    uri = _advice_uri(tmp_path_factory.mktemp("advice-small"), _RANKED)
    result = browser.measure(uri, ELEMENTS_TABLE_JS)

    assert result is not None, "no capacity_recommendation.max_jobs_advice.elements table"
    assert result["nestedTables"] == 0, (
        "priced must not draw its own nested table: "
        f"{result['nestedTables']} found")
    assert "Price" in result["headers"], result["headers"]
    assert "Why not priced" in result["headers"], result["headers"]
    assert "Priced (floor)" not in result["headers"], (
        "priced must not itself be a column: " + str(result["headers"]))
    # The fold is opened before measuring (see the JS above) - a closed
    # `<details>` lays out nothing, so 0 <= 40 would pass whether or not
    # the row is really one level.
    assert result["rowHeight"] is not None and 0 < result["rowHeight"] <= 40, (
        f"{result['rowHeight']} px/row at 1440 wide, opened - either no "
        f"real row was measured or it is over the 40 px budget a "
        f"one-level row draws at")
    # The JSON order is the order drawn (§ Required Fix): priced
    # lowerings first, refusals last.
    assert result["order"] == [
        "libc.bst", "libb.bst", "liba.bst", "core.bst"], (
        result["order"])
    # `shapeOf`'s own floor for any non-empty array-of-records is 2 (the
    # array is a level, each row is a level); `priced` staying nested
    # per row (the contract) adds one more. See this task's Outcome.
    assert result["levels"] == "3", (  # shapeOf(elements), priced kept nested per the contract
        f"data-levels={result['levels']!r} - if this ever reads \"1\", "
        f"`priced` has left the row and the Outcome's flagged decision "
        f"has been resolved; update this assertion, don't relax it")


@needs_browser
@pytest.mark.medium
def test_over_the_cap_the_badge_and_a_filter_appear(tmp_path_factory, browser):
    # `TABLE_OPENS_BOUNDED_ABOVE` is 40 (structured.js); 45 priced
    # lowerings at distinct costs cross it while staying one input
    # class, which is what the badge and the filter are keyed off.
    rows = [_row(f"lowered-{n}.bst", 4, 2, price_cost_us=1000 + n)
            for n in range(45)]
    uri = _advice_uri(tmp_path_factory.mktemp("advice-scale"), rows,
                       name="advice-scale")
    result = browser.measure(uri, ELEMENTS_TABLE_JS)

    assert result is not None
    assert result["badge"] and CAPPED_BADGE.match(result["badge"]), (
        result["badge"])
    assert result["badge"].endswith("of 45"), result["badge"]
    assert result["hasFilter"], "no input.table-filter over the row cap"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
