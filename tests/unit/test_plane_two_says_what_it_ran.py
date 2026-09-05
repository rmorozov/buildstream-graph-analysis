"""UX-370: what the build spent its time running reaches a reader.

Round 58 asked a concrete question — what does cmake configure cost,
in calls and in seconds? Plane 2 measures it.
`tests/fixtures/macro_micro/plane2.json` publishes:

```text
by_binary          cmake 248, sh 150, make 99, c++ 88, cc1plus 51, …
binary_cost[uid]   by_count and by_cpu, ranked, with a CPU share
configure_phase    configure_cpu_us 4,481,317 (6.42% of CPU) and a note
                   saying how a process is classified
```

Booted, the exported page carried the binary **names** — `cmake`,
`make`, `cc1plus` all appeared — and none of the numbers. No section
matched `binar` or `configure`.

**It was worse than "published and not rendered".** The Plane 2
document does not reach the viewer at all: `bga view` publishes
`report.json` and nothing else. `plane2_coverage` and `element_join`
are on the page because the *analysis* projects them into
`analyze/v4`; these three were never projected, so there was nothing
for the renderer to be blamed for.

So the fix is one projection beside the join, in the pass that already
holds the Plane 2 report, plus the schema saying what the numbers are.
The renderer needed no change: with `QUANTITY` declared, 4,481,317 µs
draws as `4.5 s` and 0.0642 as `6.4%`.

`configure_phase.note` is the caveat that makes the share a floor, and
it belongs on `UX-346`'s door rather than in the middle of the figures.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The three keys, and the scalars under each that a reader must be
#: able to reach. `UX-356`'s clause, pointed at Plane 2.
PUBLISHED = ("by_binary", "binary_cost", "configure_phase")

_LOOK = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const keys = [...document.querySelectorAll("section[data-section]")]
    .map((s) => s.getAttribute("data-section"));
  const text = (document.querySelector("main") || document.body).textContent;
  return { sections: keys, text: text.replace(/\s+/g, " ") };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(browser, tmp_path_factory):
    """`macro_micro` - the one committed fixture with a Plane 2 report
    beside its run (`UX-359` is why the whole snapshot is copied)."""
    uri = pages.export_uri(pages.FIXTURES["macro_micro"],
                           tmp_path_factory.mktemp("u370"))
    return browser.measure(uri, _LOOK, 1440, 900)


def _report():
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES["macro_micro"]))["report.json"]


class TestTheAnalysisCarriesWhatPlaneTwoMeasured:
    @pytest.mark.parametrize("key", PUBLISHED)
    def test_the_key_reaches_the_document_the_page_reads(self, key):
        """The half that was actually missing. `bga view` publishes
        `report.json` and nothing else, so a number left in
        `plane2.json` is a number no reader of the page can reach."""
        assert _report().get(key), (
            f"{key} is not in analyze/v4 - it is in the Plane 2 report "
            f"beside the run, which the viewer never loads")

    def test_every_measured_element_and_binary_has_a_row(self):
        """A projection into this document's shape, not a copy of the
        source's. The Plane 2 report nests element -> ranking -> row;
        publishing that verbatim broke four of this contract's rules at
        once (depth, one-population-once, table width, export size), so
        the two rankings become one row per (element, binary).

        The clause is that nothing is lost in the flattening.
        """
        import json

        rows = _report()["binary_cost"]
        native = json.loads(
            (pages.FIXTURES["macro_micro"].parent / "plane2.json")
            .read_text(encoding="utf-8"))["binary_cost"]
        expected = {
            (element, entry["binary"])
            for element, cost in native.items() if cost.get("available")
            for ranking in ("by_count", "by_cpu")
            for entry in cost.get(ranking) or []}
        published = {(row["element"], row["binary"]) for row in rows}
        assert published == expected, (
            f"missing {sorted(expected - published)[:5]}, "
            f"invented {sorted(published - expected)[:5]}")

    def test_the_numbers_are_the_source_s_numbers(self):
        """Up to one unit conversion. Plane 2 publishes wall-clock in
        seconds and this vocabulary carries one time member, in
        microseconds (`UX-341`), so the conversion happens at the
        boundary - `bga/units.py`'s own rule. Everything else is
        copied, because a number that disagreed with the document it
        came from would be a third answer to a question that already
        has one."""
        import json

        native = json.loads(
            (pages.FIXTURES["macro_micro"].parent / "plane2.json")
            .read_text(encoding="utf-8"))["binary_cost"]
        by_cpu = {(element, entry["binary"]): entry
                  for element, cost in native.items() if cost.get("available")
                  for entry in cost.get("by_cpu") or []}
        checked = 0
        for row in _report()["binary_cost"]:
            source = by_cpu.get((row["element"], row["binary"]))
            if not source:
                continue                    # ranked by count alone
            assert row["cpu_us"] == source["cpu_us"], row
            assert row["cpu_share"] == source["cpu_share"], row
            assert row["calls"] == source["count"], row
            assert row["wall_us"] == round(source["wall_s"] * 1_000_000), row
            checked += 1
        assert checked > 20, checked

    def test_a_binary_ranked_by_calls_alone_keeps_its_count(self):
        """The process-storm half. A binary too cheap to reach the CPU
        ranking is exactly the one a reader chasing call counts wants,
        and a flattening that dropped it would answer only half the
        question this item is about."""
        rows = _report()["binary_cost"]
        cheap = [row for row in rows if row["cpu_us"] is None]
        assert cheap, "no binary is ranked by count alone in this fixture"
        for row in cheap:
            assert row["calls"], row
            assert row["cpu_share"] is None, row

    def test_a_run_with_one_plane_carries_none_of_it(self):
        """`UX-321`: "not looked at" and "looked at and saw nothing"
        are different claims, so these are absent rather than empty on
        a run with no Plane 2 - the rule `plane2_coverage` follows."""
        from tools.bga_view import payloads

        golden = payloads(str(pages.FIXTURES["golden"]))["report.json"]
        present = [key for key in PUBLISHED if key in golden]
        assert present == [], present


@needs_browser
@pytest.mark.medium
class TestTheNumbersReachTheReader:
    @pytest.mark.parametrize("key", PUBLISHED)
    def test_each_one_is_a_section_on_the_page(self, booted, key):
        assert key in booted["sections"], (
            f"{key} draws no section; measured before this item: no "
            f"section matched `binar|configure`")

    def test_the_configure_cost_is_on_the_page_in_both_axes(self, booted):
        """The round's question, answered: what does configuring cost,
        as a share and as a time. Rendered through the declared
        quantities, so 4,481,317 us reads as seconds."""
        report = _report()
        share = report["configure_phase"]["configure_share"]
        assert f"{share * 100:.1f}%" in booted["text"], (
            f"the configure share ({share * 100:.1f}%) is not on the page")
        assert "4.5 s" in booted["text"], (
            "the configure CPU does not render as a duration")

    def test_the_frequency_half_is_on_the_page(self, booted):
        """`by_binary` is the count per binary for the whole run - the
        "how often" the question asks for."""
        counts = _report()["by_binary"]
        top = max(counts, key=counts.get)
        assert str(counts[top]) in booted["text"], (
            f"{top} ran {counts[top]} times and the count is not on the "
            f"page")
        assert len(counts) >= 5, counts

    def test_the_caveat_is_published_with_the_number(self, booted):
        """`UX-346`: the note says why the share is a floor. A share
        without it is a measurement claiming to be a total."""
        note = _report()["configure_phase"]["note"]
        assert note.strip(), "configure_phase publishes no note"
        assert "floor" in note.lower(), note
        head = " ".join(note.split()[:6])
        assert head in booted["text"], (
            f"the note is published and not rendered: {head!r}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
