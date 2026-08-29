"""UX-395: `--format chrome` silently dropped the flows and counters.

`bga timeline` emits two formats. Measured on the same snapshot when
this was filed:

```text
                    slices   flows   counters
trackevent             826     836        538
chrome                 663       0          0
```

The chrome JSON carries slices and nothing else, and two of the
fourteen canned questions read exactly what it lacks -
`waited-on-flow` reads the `flow` table, `concurrency-curve` reads
`counter` and `counter_track`. Against a chrome trace both return zero
rows, and the reader concludes the build had no concurrency and that
nothing waited on anything.

That is a wrong answer produced silently, which is the class `UX-107`
exists to prevent: *nobody could look* rendered as *looked and found
nothing*. The command's own summary is where it should have been
caught, and the chrome path **omitted** the two rows rather than
printing them as zero - so the output did not even hint that two
thirds of the trace's structure was gone.

**The shipped path is sound.** The page's embedded handoff is the
trackevent protobuf, so a reader who clicks through from the report
gets the complete trace. This is the documented
`bga timeline --format chrome` invocation, taken by hand.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                       # noqa: E402

QUESTIONS = (REPO / "bga/viewer/questions.js").read_text(encoding="utf-8")

#: The two the filing names, and the table each one reads.
NEEDS = {"waited-on-flow": "flow", "concurrency-curve": "counter"}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Both formats from one snapshot, with their summaries."""
    from tools.bga_timeline import describe, render

    into = tmp_path_factory.mktemp("formats")
    run = pages.two_plane_snapshot(into)
    snapshot = str(run.parent)
    out = {}
    for fmt in ("trackevent", "chrome"):
        path = str(into / f"timeline.{fmt}")
        result = render(snapshot, path, fmt=fmt, quiet=True)
        out[fmt] = {"result": result, "said": describe(result, path),
                    "path": path}
    return out


class TestTheSummaryReportsWhatIsThere:
    def test_the_chrome_summary_reports_all_three_counts(self, rendered):
        """Zeroes printed, not omitted.

        A row a summary leaves out is a row a reader assumes was fine.
        """
        result = rendered["chrome"]["result"]
        for key in ("slices", "flows", "counters"):
            assert key in result, (key, sorted(result))
        assert result["flows"] == 0 and result["counters"] == 0, result
        said = rendered["chrome"]["said"]
        assert "0 flows" in said and "0 counters" in said, said

    def test_the_counts_are_the_trace_s_own(self, rendered):
        """Counted from the file, not from the converter's bookkeeping.

        This path calls two converters that have always written this
        shape; what the summary should report is what landed on disk.
        """
        with open(rendered["chrome"]["path"], encoding="utf-8") as handle:
            events = json.load(handle)
        rows = events.get("traceEvents") if isinstance(events, dict) else events
        slices = sum(1 for event in rows
                     if isinstance(event, dict) and event.get("ph") in ("X", "B"))
        assert rendered["chrome"]["result"]["slices"] == slices
        assert not any(event.get("ph") in ("s", "t", "f", "C")
                       for event in rows if isinstance(event, dict)), (
            "the chrome writer started emitting flow or counter events, so "
            "the zeroes this file asserts are no longer true - re-measure "
            "before changing them")

    def test_both_summaries_report_the_same_three(self, rendered):
        """One shape, so the two formats can be compared at a glance."""
        for fmt in ("trackevent", "chrome"):
            said = rendered[fmt]["said"]
            assert "slices," in said and "flows," in said, (fmt, said)
            assert "counters" in said, (fmt, said)

    def test_the_trackevent_trace_carries_what_chrome_does_not(self, rendered):
        """The premise, re-measured on the committed fixture.

        If the two formats ever carried the same structure this whole
        item would be describing something that is not there.
        """
        rich = rendered["trackevent"]["result"]
        assert rich.get("counters", 0) > 0, rich
        assert rendered["chrome"]["result"]["counters"] == 0


class TestTheChoiceSaysWhatItCosts:
    def test_the_summary_names_the_price(self, rendered):
        said = rendered["chrome"]["said"]
        assert "no flows and no counters" in said, said
        assert "waited-on-flow" in said and "concurrency-curve" in said, said

    def test_the_help_names_it_too(self):
        """At the moment the choice is made, not only after."""
        source = (REPO / "tools/bga_timeline.py").read_text(encoding="utf-8")
        help_text = source.split('"--format"', 1)[1].split("parser.add_argument", 1)[0]
        assert "no flows and no counters" in help_text, help_text


class TestTheQueryLibraryNamesItsRequirement:
    def test_both_queries_that_need_a_table_declare_it(self):
        for query, table in NEEDS.items():
            block = QUESTIONS.split(f'id: "{query}"', 1)[1].split("sql:", 1)[0]
            assert f'reads: "{table}"' in block, (
                f"`{query}` reads the `{table}` table and does not say so, "
                f"so the page cannot tell a reader why it came back empty")

    def test_every_declared_table_has_a_sentence(self):
        """A declaration the renderer has no wording for is silent."""
        from re import findall

        declared = set(findall(r'reads: "([a-z_]+)"', QUESTIONS))
        block = QUESTIONS.split("export const NEEDS_TRACKEVENT = {", 1)[1]
        block = block.split("};", 1)[0]
        worded = set(findall(r"^\s*([a-z_]+):", block, flags=8))
        assert declared <= worded, (
            f"declared and unworded: {sorted(declared - worded)}")

    def test_the_sentence_says_which_format_and_why_it_is_empty(self):
        block = QUESTIONS.split("export function requirementLine", 1)[1]
        block = block.split("\n}", 1)[0]
        assert "trackevent" in block and "--format chrome" in block, block
        assert "not the build lacking it" in block, (
            "the sentence must say the *format* is missing the structure - "
            "a reader who reads it as the build having none is exactly the "
            "wrong answer this item was filed on")
