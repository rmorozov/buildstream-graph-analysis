"""UX-1117: properties of the Plane 1 reader over generated log lines.

Under TZ=UTC: `parse_timestamp` reads the wrapper's UTC stamp as local time.
"""

import os
import re
import time
from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tools.bst_log_to_chrome_trace import (
    WrapperTraceConverter,
    parse_elapsed_to_seconds,
)

PROFILE = settings(derandomize=True, database=None, max_examples=100, suppress_health_check=[HealthCheck.too_slow])


@pytest.fixture(autouse=True, scope="module")
def _utc():
    old = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


PADS = st.sampled_from(["", " ", "  "])
TERMINALS = st.sampled_from(["SUCCESS", "FAILURE"])


@st.composite
def interleavings(draw):
    """Balanced START/terminal lines over distinct hashes: each hash's
    first slot is its START, its second the terminal."""
    n = draw(st.integers(1, 6))
    hashes = draw(st.lists(st.text("0123456789abcdef", min_size=8, max_size=8), min_size=n, max_size=n, unique=True))
    order = draw(st.permutations(list(range(n)) * 2))
    seen = set()
    events = []
    for i in order:
        first = i not in seen
        seen.add(i)
        events.append((hashes[i], "START" if first else draw(TERMINALS), f"e{i}.bst" + draw(PADS)))
    return events


def _line(elapsed, h, element, status):
    return f"[{elapsed}][{h}][   build:{element}] {status} Building"


def _spans(conv, hashes):
    by_tid = {}
    for ev in conv.trace_events:
        if ev.get("cat") == "bst-builder":
            by_tid.setdefault(ev["tid"], []).append(ev)
    assert len(by_tid) == len(hashes)
    for evs in by_tid.values():
        assert [e["ph"] for e in evs] == ["B", "E"]
        assert evs[1]["ts"] >= evs[0]["ts"]


@PROFILE
@given(events=interleavings(), elapsed=st.integers(0, 3599))
def test_raw_mode_gives_one_ordered_span_per_hash(events, elapsed):
    conv = WrapperTraceConverter(raw_start_time_us=0)
    stamp = f"00:{elapsed // 60:02d}:{elapsed % 60:02d}"
    for h, status, element in events:
        conv.process_line_raw(_line("--:--:--" if status == "START" else stamp, h, element, status))

    _spans(conv, {h for h, _, _ in events})


@PROFILE
@given(
    events=interleavings(),
    start=st.datetimes(min_value=datetime(2026, 1, 1), max_value=datetime(2026, 12, 30)),
    midnight=st.booleans(),
    gaps=st.lists(st.integers(0, 40_000_000), min_size=12, max_size=12),
)
def test_wrapped_mode_gives_one_ordered_span_per_hash(events, start, midnight, gaps):
    if midnight:
        start = start.replace(hour=23, minute=59, second=50)
    conv = WrapperTraceConverter()
    now = start

    def stamp():
        return now.strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

    conv.process_line(f"[wrapper][{stamp()}] INFO: Executing command: bst build x.bst")
    for (h, status, element), gap in zip(events, gaps):
        now += timedelta(microseconds=gap)
        conv.process_line(f"[wrapper][{stamp()}] INFO: " + _line("00:00:00", h, element, status))

    _spans(conv, {h for h, _, _ in events})
    ts = [e["ts"] for e in conv.trace_events if e.get("ph") in ("B", "E")]
    assert ts == sorted(ts)


# The grammar as specified, held here so loosening the reader's own regex
# does not also loosen which lines this test treats as unmatched.
GRAMMAR = re.compile(
    r"\[([^\]]*)\]\[([^\]]+)\]\[\s*(\w+):([^\]]+)\]\s+"
    r"(START|SUCCESS|FAILURE|FAIL|CACHED|SKIPPED|SKIP)\s+(.*)"
)


@st.composite
def _near_miss(draw):
    """A valid line with one thing wrong: a bracket dropped or doubled, an
    unknown status, an empty hash, a truncated elapsed field."""
    elapsed = draw(st.sampled_from(["00:00:01", "--:--:--", "00:0", ""]))
    h = draw(st.sampled_from(["", "abc12345"]))
    status = draw(st.sampled_from(["START", "SUCCESS", "STARTED", "BOGUS", "start", ""]))
    sep = draw(st.sampled_from([" ", "", "\t"]))
    line = f"[{elapsed}][{h}][   build:x.bst] {status}{sep}Building"
    slots = [i for i, c in enumerate(line) if c in "[]"]
    i = draw(st.sampled_from(slots))
    return draw(st.sampled_from([line[:i] + line[i + 1 :], line[:i] + line[i] + line[i:], line]))


# No control characters: an ANSI escape would be stripped before matching.
RANDOM = st.text(st.characters(blacklist_categories=("Cc", "Cs")), max_size=80)
UNMATCHED = st.one_of(RANDOM, _near_miss()).filter(lambda s: GRAMMAR.search(s) is None)


@PROFILE
@given(line=UNMATCHED)
def test_a_line_the_grammar_does_not_match_adds_no_span(line):
    raw = WrapperTraceConverter(raw_start_time_us=0)
    raw.process_line_raw(line)
    wrapped = WrapperTraceConverter()
    wrapped.process_line("[wrapper][2026-08-13 09:00:00,000] INFO: Executing command: bst build x.bst")
    wrapped.process_line(f"[wrapper][2026-08-13 09:00:01,000] INFO: {line}")
    wrapped.process_line(line)

    for conv in (raw, wrapped):
        assert not [e for e in conv.trace_events if e.get("cat") == "bst-builder"]


@PROFILE
@given(
    h=st.integers(0, 99),
    m=st.integers(0, 99),
    s=st.integers(0, 99),
    micros=st.one_of(st.none(), st.integers(0, 999_999)),
)
def test_an_elapsed_string_round_trips(h, m, s, micros):
    text = f"{h:02d}:{m:02d}:{s:02d}" + ("" if micros is None else f".{micros:06d}")

    got = parse_elapsed_to_seconds(text)

    want = h * 3600 + m * 60 + s + (micros or 0) / 1_000_000
    assert got == pytest.approx(want, abs=1e-9)


def test_an_unknown_elapsed_is_zero():
    assert parse_elapsed_to_seconds("--:--:--") == 0.0
