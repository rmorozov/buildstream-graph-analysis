"""UX-682: change frequency and co-change from the kept Plane 3 logs.

`blast_weight` (`bga/blast.py`) has always had its second factor -
expected rebuild cost needs a first: how often an element changes. The
logs already record every build the project ran; this reads a
per-element rebuild count and a pairwise co-rebuild count out of them,
reusing `developer_tax`'s population and cause annotation rather than
re-deciding what a rebuild or its cause is.
"""
from datetime import datetime, timedelta, timezone

from tools.bst_cache_logs import (
    CO_CHANGE_MIN_REBUILDS,
    CO_CHANGE_WINDOW_US,
    change_frequency,
    format_report_text,
    scan_log_tree,
)


def _write_build(root, project, element, key, seconds, dt):
    """One build log, header date/time and filename stamp all read off
    `dt` (a UTC `datetime`) - the same convention `parse_element_log`
    reads back, so `started_us` lands exactly where the test put it."""
    directory = root / project / element.removesuffix(".bst")
    directory.mkdir(parents=True, exist_ok=True)
    header_date = dt.strftime("%d-%m-%Y")
    header_time = dt.strftime("%H:%M:%S")
    stamp = dt.strftime("%Y%m%d-%H%M%S")
    hh, rem = divmod(seconds, 3600)
    mm, ss = divmod(rem, 60)
    elapsed = f"{hh:02d}:{mm:02d}:{ss:02d}"
    (directory / f"{key}-build.{stamp}.log").write_text(
        f"BuildStream 2.7.0 - Someday, {header_date} at {header_time}\n"
        f"[--:--:--] START   [{key}] {element}: Build\n"
        f"[--:--:--] START   {element}: Running commands\n"
        f"[{elapsed}] SUCCESS {element}: Running commands\n"
        f"[{elapsed}] SUCCESS [{key}] {element}: Build\n"
    )


def _log_tree(tmp_path):
    """lib-a (30 one-second builds, 3 of them reusing a key), codegen
    (2 builds at 600s each - a larger blast, so ranking by total_us
    instead of rebuilds would put codegen first), pair-x/pair-y (always
    within the co-change window) and solo-p/solo-q (co-rebuild exactly
    once, below the floor). Groups sit months apart so no cross-group
    pair is accidental."""
    root = tmp_path / "logs"

    base = datetime(2026, 8, 1, tzinfo=timezone.utc)
    for i in range(30):
        # Builds 28-30 (index 27-29) reuse build 27's key - exactly
        # three unchanged-key rebuilds out of thirty.
        key_index = min(i, 26)
        _write_build(
            root, "p", "lib-a.bst", f"{key_index + 1:08x}", 1,
            base + timedelta(hours=2 * i),
        )

    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for i in range(2):
        _write_build(
            root, "p", "codegen.bst", f"c000000{i}", 600, base + timedelta(hours=i),
        )

    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for i in range(3):
        _write_build(
            root, "p", "pair-x.bst", f"a000000{i}", 5, base + timedelta(hours=i),
        )
        _write_build(
            root, "p", "pair-y.bst", f"b000000{i}", 5,
            base + timedelta(hours=i, minutes=5),
        )

    base = datetime(2026, 11, 1, tzinfo=timezone.utc)
    _write_build(root, "p", "solo-p.bst", "d0000000", 5, base)
    _write_build(root, "p", "solo-q.bst", "e0000000", 5, base + timedelta(minutes=5))

    # `reused-q` has one build within the window of *both* of
    # `reused-p`'s - greedy earliest-first claims only the first, so
    # this pair also lands below the floor (co_rebuilds == 1). A count
    # that lets one record pair twice would instead reach 2.
    base = datetime(2026, 12, 1, tzinfo=timezone.utc)
    _write_build(root, "p", "reused-p.bst", "f0000000", 5, base)
    _write_build(root, "p", "reused-p.bst", "f0000001", 5, base + timedelta(minutes=5))
    _write_build(root, "p", "reused-q.bst", "f1000000", 5, base + timedelta(minutes=2))

    # Two hours apart - outside the 30-minute window, well inside a day.
    base = datetime(2027, 1, 1, tzinfo=timezone.utc)
    _write_build(root, "p", "near-miss-a.bst", "aa000000", 5, base)
    _write_build(root, "p", "near-miss-a.bst", "aa000001", 5, base + timedelta(hours=3))
    _write_build(root, "p", "near-miss-b.bst", "bb000000", 5, base + timedelta(hours=2))
    _write_build(root, "p", "near-miss-b.bst", "bb000001", 5, base + timedelta(hours=5))

    return root


def test_lib_a_ranks_first_by_rebuilds(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    assert freq["elements"][0]["element"] == "lib-a.bst"
    assert freq["elements"][0]["rebuilds"] == 30


def test_codegens_row_says_two(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    codegen = next(row for row in freq["elements"] if row["element"] == "codegen.bst")
    assert codegen["rebuilds"] == 2


def test_the_unchanged_key_share_is_exact(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    lib_a = freq["elements"][0]
    assert lib_a["unchanged_key_rebuilds"] == 3
    assert lib_a["unchanged_key_share"] == 3 / 30


def test_pair_x_and_pair_y_are_the_top_co_change_row(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    top = freq["co_change"][0]
    assert {top["a"], top["b"]} == {"pair-x.bst", "pair-y.bst"}
    assert top["co_rebuilds"] == 3
    assert top["share_of_a"] == 1.0
    assert top["share_of_b"] == 1.0


def test_a_pair_seen_once_is_dropped_and_counted(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    pairs = [{row["a"], row["b"]} for row in freq["co_change"]]
    assert {"solo-p.bst", "solo-q.bst"} not in pairs
    # `reused-p`/`reused-q` also lands below the floor - see
    # `test_a_build_record_is_claimed_by_at_most_one_pair`.
    assert freq["pairs_below_floor"] == 2


def test_a_build_record_is_claimed_by_at_most_one_pair(tmp_path):
    """`reused-q`'s one build sits within the window of both of
    `reused-p`'s - greedy earliest-first claims only the first, so the
    pair co-rebuilds once and stays below the floor. Letting one record
    pair twice would instead reach 2 and put the pair in the list."""
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    pairs = [{row["a"], row["b"]} for row in freq["co_change"]]
    assert {"reused-p.bst", "reused-q.bst"} not in pairs


def test_two_hours_apart_is_outside_the_window(tmp_path):
    """`near-miss-a`/`near-miss-b` build two hours apart - inside a day,
    outside `CO_CHANGE_WINDOW_US` (30 minutes) - so the pair never
    co-rebuilds at all, not even below the floor."""
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    pairs = [{row["a"], row["b"]} for row in freq["co_change"]]
    assert {"near-miss-a.bst", "near-miss-b.bst"} not in pairs


def test_the_co_change_window_and_floor_are_named_constants(tmp_path):
    root = _log_tree(tmp_path)
    freq = change_frequency(scan_log_tree(str(root)))
    assert freq["co_change_window_us"] == CO_CHANGE_WINDOW_US
    assert CO_CHANGE_MIN_REBUILDS == 2


def test_the_text_report_names_lib_as_rebuild_count(tmp_path):
    root = _log_tree(tmp_path)
    from tools.bst_cache_logs import build_report

    text = format_report_text(build_report(scan_log_tree(str(root))))
    assert "lib-a.bst rebuilt 30 time(s)" in text


def test_no_records_yields_an_empty_payload():
    assert change_frequency([]) == {}
