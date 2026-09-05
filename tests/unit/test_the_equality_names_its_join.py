"""UX-572: the counter's equality is a join's consequence, and says so.

`docs/spec/trace-dictionary.md` and `tools/bga_timeline.py` both stated
the concurrency counter's peak equals the report's `max_concurrency`
"by construction". Round 64 measured that false with the spine on;
`UX-406`'s emit-time join made it true again. Neither sentence was
amended, so a construction was published where a guarded consequence
was meant.

Two subjects here, both narrow so a guard cannot match the argument for
itself: the dictionary's `## Counter tracks` section, and the comment
block directly above `CONCURRENCY_COUNTER`. Everything else in either
file is out of view.

The fourth clause is why the wording matters rather than a style point:
on the committed dual-mechanism fixture the unjoined stream peaks at 4
and the joined one at 2. `test_one_process_is_one_slice.py` holds the
joined half; this holds the counterfactual.
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_one_process_is_one_slice import _RAW, PEAK_CONCURRENCY

from tools.bga_timeline import concurrency_series
from tools.bst_native_build_tracer import (
    compute_max_concurrency,
    merge_record_streams,
    parse_trace_lines,
    stream_records,
)

DICTIONARY = REPO / "docs/spec/trace-dictionary.md"
TIMELINE = REPO / "tools/bga_timeline.py"

#: The join, and the guard that holds the equality. Named here once so
#: a rename has one place to fail rather than four.
JOIN = "merge_record_streams"
JOIN_ITEM = "UX-406"
GUARD_FILE = "test_one_process_is_one_slice.py"
GUARD_TEST = "test_the_counter_peak_is_the_reports_max_concurrency"

#: The claim that is now wrong. It is checked as a *phrase in the
#: subject*, not anywhere in the file: `bga_timeline.py` has an unrelated
#: and correct "by construction" 300 lines further down.
RETIRED = "by construction"


def _counter_section():
    """The dictionary's `## Counter tracks`, heading to next heading."""
    text = DICTIONARY.read_text(encoding="utf-8")
    match = re.search(r"^## Counter tracks$(.*?)^## ", text,
                      re.MULTILINE | re.DOTALL)
    assert match, "the dictionary has no `## Counter tracks` section"
    return match.group(1)


def _counter_comment():
    """The `#` block directly above `CONCURRENCY_COUNTER = `.

    Read upward from the assignment so the subject is the comment that
    explains *this* constant and nothing adjacent to it.
    """
    lines = TIMELINE.read_text(encoding="utf-8").splitlines()
    index = next(i for i, line in enumerate(lines)
                 if line.startswith("CONCURRENCY_COUNTER = "))
    start = index
    while start > 0 and lines[start - 1].lstrip().startswith("#"):
        start -= 1
    assert start < index, "no comment block above CONCURRENCY_COUNTER"
    return "\n".join(lines[start:index])


def _joined(raw_text):
    records = sorted(
        stream_records(iter(parse_trace_lines(raw_text.splitlines()))),
        key=lambda record: record["start_ts"])
    return records, merge_record_streams(list(records))


def test_the_dictionary_sentence_names_the_join_and_its_guard():
    """The published sentence, in the section that carries the track."""
    section = _counter_section()
    assert "max_concurrency" in section
    assert JOIN in section, (
        f"the counter-track section states the equality without naming "
        f"`{JOIN}`, which is what makes it hold")
    assert JOIN_ITEM in section, section
    assert GUARD_FILE in section and GUARD_TEST in section, (
        f"the section states a guarded consequence without naming the "
        f"guard ({GUARD_FILE}::{GUARD_TEST})")
    assert RETIRED not in section, (
        f"the counter-track section still says {RETIRED!r}; round 64 "
        f"measured the peak at 44 against a published 24, so it is a "
        f"consequence of the join and not a construction")


def test_the_timeline_comment_names_the_join_and_its_guard():
    """The same sentence where the constant is defined."""
    comment = _counter_comment()
    assert "max_concurrency" in comment
    assert JOIN in comment, comment
    assert JOIN_ITEM in comment, comment
    assert GUARD_TEST in comment, (
        f"the comment states the equality without naming {GUARD_TEST}")
    assert RETIRED not in comment, comment


def test_the_named_guard_exists_and_reads_the_counter_peak():
    """A named guard that has been renamed away is a dangling promise.

    The name is resolved to a `def` in that file and the body is
    checked to mention `counter_peak`, so this fails on a rename and on
    a clause gutted to something else.
    """
    path = REPO / "tests/unit" / GUARD_FILE
    assert path.is_file(), path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == GUARD_TEST]
    assert len(found) == 1, (
        f"{GUARD_FILE} does not define {GUARD_TEST}, which both sentences "
        f"now name as the guard")
    assert "counter_peak" in ast.unparse(found[0]), (
        f"{GUARD_TEST} no longer reads the counter's peak")


def test_the_equality_is_false_without_the_join():
    """The counterfactual, on the committed dual-mechanism fixture.

    `UX-406`'s guard holds the joined half; this holds the half that
    makes the wording load-bearing. Two of the three processes are
    recorded by both mechanisms, so unjoined both copies are alive at
    the same instant.
    """
    raw, joined = _joined(_RAW)
    unjoined_peak = max(value for _ts, value in concurrency_series(raw))
    joined_peak = max(value for _ts, value in concurrency_series(joined))
    assert joined_peak == compute_max_concurrency(joined) == PEAK_CONCURRENCY
    assert unjoined_peak == 4, unjoined_peak
    assert unjoined_peak != joined_peak, (
        f"the unjoined stream peaks at {unjoined_peak} and the joined one "
        f"at {joined_peak}; if these agreed the equality would be a "
        f"construction after all and both sentences should say so")
