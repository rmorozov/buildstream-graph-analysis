"""UX-91: BuildStream's own persisted logs, read as a third data plane.

Everything `bga` ingests today has to be decided on *before* the build:
Plane 1 needs the wrapped log, Plane 2 needs the tracer. BuildStream
already writes a per-element log for every task it runs, keeps them
across builds, and nothing read them. They are the only source that can
say anything about a build nobody captured.

What these tests pin is mostly what the logs **cannot** do, because that
is what was measured and it is what stops the next reader over-claiming:
there are no timestamps inside `Running commands`, so no
configure-vs-compile split exists here however much the task description
wanted one; the clock is one-second resolution and carries no offset;
and there is no scheduler context at all, so nothing here may reach a
certified floor.

The fixture below is a real bst 2.7.0 log, trimmed - not a hand-invented
format.
"""
import json
import os
import shutil

import pytest

from tools.bst_cache_logs import (
    REPEATED_MIN_ELEMENTS, build_report, format_report_text, parse_element_log,
    repeated_operations, scan_log_tree,
)

BST_AVAILABLE = shutil.which("bst") is not None

REAL_LOG = """BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22
[--:--:--] START   [84331b67] core.bst: Build
[--:--:--] LOG     [84331b67] core.bst: Build environment for element core.bst

    JOBS: -j1
[--:--:--] START   [84331b67] core.bst: Staging dependencies at: /
[--:--:--] STATUS  [f81ed53b] toolchain.bst: Staging toolchain.bst/f81ed53b
[00:00:02] SUCCESS [84331b67] core.bst: Staging dependencies at: /
[--:--:--] START   [84331b67] core.bst: Staging sources
[00:00:00] SUCCESS [84331b67] core.bst: Staging sources
[--:--:--] START   core.bst: Running commands

    cmake -B_builddir -H"." \\
    -DCMAKE_INSTALL_PREFIX:PATH="/usr"
    cmake --build _builddir -- ${JOBS}
+ sh -c -e cmake -B_builddir -H"." \\
-DCMAKE_INSTALL_PREFIX:PATH="/usr"

-- Configuring done (0.8s)
-- Generating done (0.0s)
+ sh -c -e cmake --build _builddir -- ${JOBS}

[00:00:14] SUCCESS core.bst: Running commands
[--:--:--] START   [84331b67] core.bst: Caching artifact
[00:00:01] SUCCESS [84331b67] core.bst: Caching artifact
[00:00:17] SUCCESS [84331b67] core.bst: Build
"""


@pytest.fixture
def log_tree(tmp_path):
    root = tmp_path / "logs"
    element_dir = root / "my-project" / "core"
    element_dir.mkdir(parents=True)
    (element_dir / "84331b67-build.20260818-115322.log").write_text(REAL_LOG)
    return root


# --- parsing ------------------------------------------------------------

def test_a_real_log_yields_its_phases_and_their_durations(log_tree):
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert record["element"] == "core.bst"
    assert record["cache_key"] == "84331b67"
    assert record["action"] == "build"
    assert record["outcome"] == "SUCCESS"
    assert record["total_us"] == 17_000_000
    assert [(p["name"], p["duration_us"]) for p in record["phases"]] == [
        ("Staging dependencies at: /", 2_000_000),
        ("Staging sources", 0),
        ("Running commands", 14_000_000),
        ("Caching artifact", 1_000_000),
    ]


def test_the_enclosing_activity_is_the_total_not_a_phase(log_tree):
    """`Build` encloses every other activity, so counting it among them
    would double the element's time."""
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert "Build" not in [p["name"] for p in record["phases"]]
    assert sum(p["duration_us"] for p in record["phases"]) == record["total_us"]


def test_another_elements_status_line_is_not_this_elements_phase(log_tree):
    """A build log contains STATUS lines about *dependencies* being
    staged. Attributing `toolchain.bst`'s line to `core.bst` would
    invent a phase."""
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert all("toolchain" not in p["name"] for p in record["phases"])


def test_a_command_wrapped_across_lines_is_rejoined(log_tree):
    """Truncating at the backslash would make two genuinely different
    `cmake` invocations compare equal, which is exactly the false match
    that would make the repeated-operation report worthless."""
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert record["commands"] == [
        'cmake -B_builddir -H"." \\ -DCMAKE_INSTALL_PREFIX:PATH="/usr"',
        "cmake --build _builddir -- ${JOBS}",
    ]


def test_a_tools_own_reported_timing_is_kept_and_labelled(log_tree):
    """cmake measured its own configure step. That is a real number and
    is kept - but as `self_timed`, never mixed in with the phases, since
    nothing in the log timed it for us."""
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert {t["what"]: t["duration_us"] for t in record["self_timed"]} == {
        "Configuring": 800_000, "Generating": 0,
    }


def test_a_junction_qualified_element_name_survives(tmp_path):
    """`subproj-junction.bst:libfoo.bst` is a real element name and the
    colon inside it is not the separator - the separator is the colon
    *followed by a space*.

    This is not hypothetical. Running the parser over logs a real
    `bst build` had just written failed immediately on the fixture
    project's junction: the original pattern split at the first colon,
    found no whitespace after it, and matched nothing at all, so every
    junction element parsed as nameless. `junction-name:element-name` is
    the qualified naming this project's own ingestion docs call the
    contract between planes, so getting it wrong here would have made
    Plane 3 unjoinable to the other two.
    """
    element_dir = tmp_path / "logs" / "subproj" / "libfoo"
    element_dir.mkdir(parents=True)
    (element_dir / "00a7aa29-build.20260818-120539.log").write_text(
        "BuildStream 2.7.0 - Tuesday, 18-08-2026 at 12:05:39\n"
        "[--:--:--] START   [00a7aa29] subproj-junction.bst:libfoo.bst: Build\n"
        "[00:00:03] SUCCESS [00a7aa29] subproj-junction.bst:libfoo.bst: Build\n"
    )
    record = parse_element_log(str(element_dir / "00a7aa29-build.20260818-120539.log"))
    assert record["element"] == "subproj-junction.bst:libfoo.bst"
    assert record["total_us"] == 3_000_000


def test_an_activity_containing_a_colon_still_splits_at_the_element(tmp_path):
    """`Staging dependencies at: /` has a colon-space of its own. The
    element is the *first* such split, which is why the pattern is
    non-greedy rather than greedy."""
    element_dir = tmp_path / "logs" / "p" / "core"
    element_dir.mkdir(parents=True)
    (element_dir / "abc123-build.20260818-120539.log").write_text(
        "BuildStream 2.7.0 - Tuesday, 18-08-2026 at 12:05:39\n"
        "[--:--:--] START   [abc123] core.bst: Build\n"
        "[00:00:02] SUCCESS [abc123] core.bst: Staging dependencies at: /\n"
        "[00:00:02] SUCCESS [abc123] core.bst: Build\n"
    )
    record = parse_element_log(str(element_dir / "abc123-build.20260818-120539.log"))
    assert record["element"] == "core.bst"
    assert [p["name"] for p in record["phases"]] == ["Staging dependencies at: /"]


def test_a_non_log_file_is_skipped_rather_than_guessed_at(tmp_path):
    """`_casd/` sits beside the project directories and holds daemon
    logs in a different format. Skipped by shape, not by name, so a
    future sibling needs no new special case."""
    (tmp_path / "1787054229.69.log").write_text("not an element log\n")
    assert parse_element_log(str(tmp_path / "1787054229.69.log")) is None


def test_the_clock_is_recorded_as_written_as_well_as_parsed(log_tree):
    """BuildStream writes this header in the runner's local time with no
    offset. The parsed value is only comparable against logs from the
    same machine, so the literal string is kept beside it rather than
    the parse being the only record."""
    record = parse_element_log(
        str(log_tree / "my-project" / "core" / "84331b67-build.20260818-115322.log")
    )
    assert record["started_at"] == "18-08-2026 11:53:22"
    assert record["started_us"] is not None


# --- reports ------------------------------------------------------------

def _record(element, commands):
    return {
        "element": element, "action": "build", "commands": commands,
        "project": "p", "cache_key": "k", "total_us": 1, "phases": [],
        "self_timed": [], "started_at": None, "started_us": 0, "path": element,
    }


def test_an_operation_in_too_few_elements_is_not_a_pattern():
    """Two is not a pattern - almost every cmake project runs
    `cmake --build`, and a report that says so is noise."""
    records = [_record(f"e{i}.bst", ["shared"]) for i in range(REPEATED_MIN_ELEMENTS - 1)]
    assert repeated_operations(records) == []


def test_an_operation_across_enough_elements_is_reported():
    records = [_record(f"e{i}.bst", ["shared"]) for i in range(REPEATED_MIN_ELEMENTS)]
    found = repeated_operations(records)
    assert len(found) == 1
    assert found[0]["element_count"] == REPEATED_MIN_ELEMENTS


def test_the_same_command_in_one_element_twice_is_not_a_cross_element_repeat():
    """The question is whether *elements* share work, not whether one
    element ran something twice."""
    records = [_record("only.bst", ["shared"] * 10)]
    assert repeated_operations(records) == []


def test_the_report_carries_its_own_caveat_in_the_payload(log_tree):
    """Said in the data, not only in the docs: a consumer that reads
    this must not mistake it for a capture."""
    report = build_report(scan_log_tree(str(log_tree)))
    caveat = report["provenance"]["caveat"]
    assert "no --builders" in caveat
    assert "certified floor" in caveat
    assert "configure-vs-compile" in caveat


def test_two_scans_of_one_tree_are_identical(log_tree):
    """The task's own determinism requirement. Sorted explicitly rather
    than relying on directory order, which differs by filesystem."""
    first = json.dumps(build_report(scan_log_tree(str(log_tree))), sort_keys=False)
    second = json.dumps(build_report(scan_log_tree(str(log_tree))), sort_keys=False)
    assert first == second


def test_the_text_report_renders(log_tree):
    text = format_report_text(build_report(scan_log_tree(str(log_tree))))
    assert "Cached Build Logs (Plane 3)" in text
    assert "core.bst [84331b67]" in text
    assert "Running commands" in text


# --- against real logs this machine actually has ------------------------

@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_a_real_buildstream_log_tree_parses(tmp_path):
    """The format is BuildStream's, not ours, and a version bump can
    change it - so this reads logs a real `bst build` just wrote.

    It runs the build itself rather than reading whatever this machine
    happens to have lying in `~/.cache/buildstream/logs`. Two reasons,
    and the second is the load-bearing one: ambient state makes the test
    non-deterministic, and a test that *skips* when the machine is clean
    would trip the `bst-tests` job's own "nothing was skipped" assertion
    - which exists precisely so this tier cannot quietly stop running.
    """
    import subprocess

    from ._bst_env import isolated_bst_env

    home = tmp_path / "home"
    home.mkdir()
    project = (
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        + "/fixtures/bst_show_project"
    )
    proc = subprocess.run(
        ["bst", "-C", project, "--no-colors", "build", "app.bst"],
        capture_output=True, text=True, env=isolated_bst_env(home),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]

    records = scan_log_tree(str(home / ".cache" / "buildstream" / "logs"))
    assert records, "a real build wrote no element logs this parser could read"

    builds = [r for r in records if r["action"] == "build"]
    assert builds, f"no build logs among {[r['action'] for r in records]}"
    assert {r["element"] for r in builds} >= {"app.bst", "base.bst"}

    for record in records:
        assert record["element"], record["path"]
        assert record["cache_key"]
        assert record["started_at"], "every real log carries a parseable header"
        if record["total_us"] is not None:
            # The enclosing activity contains the phases, so they cannot
            # sum past it. A parser that mistook the enclosing line for a
            # phase would fail here rather than silently double-count.
            assert sum(p["duration_us"] or 0 for p in record["phases"]) <= record["total_us"]

    # And the report builds from real data without raising.
    report = build_report(records)
    assert report["provenance"]["build_logs"] == len(builds)
