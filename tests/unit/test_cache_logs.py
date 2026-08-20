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
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/spec/ingestion-pipeline.md")
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


# --- UX-99: the sandbox tax --------------------------------------------

def test_the_toll_and_the_work_are_split_per_element(log_tree):
    """`REAL_LOG` is a real bst 2.7.0 log and it already carries the
    split: 2s staging dependencies, 14s running commands, 1s caching the
    artifact, 17s total. The toll is 3 of those 17 seconds, and before
    this it was booked as part of `core.bst`'s work."""
    from tools.bst_cache_logs import phase_breakdown

    row = phase_breakdown(scan_log_tree(str(log_tree)))[0]
    assert row["work_us"] == 14_000_000
    assert row["toll_us"] == 3_000_000
    assert round(row["toll_share"], 4) == round(3 / 17, 4)


def test_the_project_wide_tax_is_the_headline(log_tree):
    from tools.bst_cache_logs import sandbox_tax

    tax = sandbox_tax(scan_log_tree(str(log_tree)))
    assert tax["toll_us"] == 3_000_000
    assert tax["work_us"] == 14_000_000
    assert tax["build_logs"] == 1
    assert [p["phase"] for p in tax["by_phase"]] == [
        "Staging dependencies", "Caching artifact", "Staging sources",
    ]


def test_the_staging_path_does_not_split_one_phase_into_many(log_tree):
    """BuildStream writes the staging path into the activity name
    (`Staging dependencies at: /`), so on a project that stages at
    several prefixes the aggregate would otherwise carry one row per
    prefix and none of them would be the phase."""
    from tools.bst_cache_logs import _phase_family

    assert _phase_family("Staging dependencies at: /usr") == "Staging dependencies"
    assert _phase_family("Caching artifact") == "Caching artifact"


def test_the_unaccounted_remainder_is_published_not_folded_into_the_toll(log_tree):
    """The enclosing `Build` total need not equal the sum of the phases
    it contains. Adding the difference to the toll would inflate exactly
    the number this feature exists to report, so it goes in its own
    field."""
    from tools.bst_cache_logs import sandbox_tax

    tax = sandbox_tax(scan_log_tree(str(log_tree)))
    assert tax["unaccounted_us"] == tax["total_us"] - tax["work_us"] - tax["toll_us"]
    assert tax["total_us"] == 17_000_000


def test_the_resolution_limit_travels_in_the_payload(log_tree):
    """Measured on `examples/06`: every overhead phase rounds to 0.0s at
    BuildStream's one-second resolution, so the project-wide toll there
    is 0.0s of 70.0s. That is a floor, not a measurement, and a consumer
    must be able to tell which it has without reading this file."""
    from tools.bst_cache_logs import LOG_RESOLUTION_US, sandbox_tax

    tax = sandbox_tax(scan_log_tree(str(log_tree)))
    assert tax["resolution_us"] == LOG_RESOLUTION_US == 1_000_000
    assert "floor rather than a measurement" in tax["caveat"]
    assert "accumulates across builds" in tax["caveat"]


def test_the_top_payer_is_ranked_by_toll_seconds_not_by_share(tmp_path):
    """A 90% toll on a 0.4s element is arithmetic; a 40s toll on a 90s
    element is a finding. Ranking by share puts the arithmetic first."""
    from tools.bst_cache_logs import sandbox_tax

    def _log(element, key, staging, commands, total):
        return (
            f"BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
            f"[--:--:--] START   [{key}] {element}: Build\n"
            f"[--:--:--] START   [{key}] {element}: Staging dependencies at: /\n"
            f"[00:00:{staging:02d}] SUCCESS [{key}] {element}: Staging dependencies at: /\n"
            f"[--:--:--] START   {element}: Running commands\n"
            f"[00:00:{commands:02d}] SUCCESS {element}: Running commands\n"
            f"[00:00:{total:02d}] SUCCESS [{key}] {element}: Build\n"
        )

    root = tmp_path / "logs"
    for element, key, staging, commands, total in (
        ("tiny.bst", "aaaaaaaa", 9, 1, 10),   # 90% toll, 9s
        ("big.bst", "bbbbbbbb", 40, 50, 90),  # 44% toll, 40s
    ):
        directory = root / "p" / element.removesuffix(".bst")
        directory.mkdir(parents=True)
        (directory / f"{key}-build.20260818-115322.log").write_text(
            _log(element, key, staging, commands, total)
        )

    payers = sandbox_tax(scan_log_tree(str(root)))["top_payers"]
    assert [p["element"] for p in payers] == ["big.bst", "tiny.bst"]


def test_the_tax_renders_in_the_text_report(log_tree):
    text = format_report_text(build_report(scan_log_tree(str(log_tree))))
    assert "Sandbox tax: 3.0s of 17.0s element time (17.6%)" in text
    # UX-138: one concept, one name. The report prints "Sandbox tax" as
    # its heading and used to say "toll" in the rows beneath it, which is
    # where the docs' own alternating variant came from.
    assert "Who paid it (by tax seconds, not by share):" in text
    assert "toll" not in text, "the report mixes tax and toll for one concept"


# --- UX-102: the configure tax, from one plane and from two -------------

def test_the_self_reported_configure_time_is_totalled(log_tree):
    """`REAL_LOG` carries cmake's own `-- Configuring done (0.8s)` and
    `-- Generating done (0.0s)`. Plane 3's whole configure measurement is
    those lines: the tool timed itself, so the number is real, and
    nothing here infers one."""
    from tools.bst_cache_logs import configure_tax

    tax = configure_tax(scan_log_tree(str(log_tree)))
    assert tax["configure_us"] == 800_000
    assert tax["elements_reporting"] == 1
    assert round(tax["configure_share"], 4) == round(0.8 / 17, 4)


def test_a_build_system_that_does_not_report_itself_yields_a_floor_of_zero(tmp_path):
    """The limit that decides how much Plane 3 alone is worth: autotools'
    `configure` prints no total and meson prints none either, so on the
    projects where elements are most often majority-configure this
    measurement is zero. Stated in the payload, not just here."""
    from tools.bst_cache_logs import configure_tax

    directory = tmp_path / "logs" / "p" / "auto"
    directory.mkdir(parents=True)
    (directory / "abc12345-build.20260818-115322.log").write_text(
        "BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
        "[--:--:--] START   [abc12345] auto.bst: Build\n"
        "[--:--:--] START   auto.bst: Running commands\n"
        "+ sh -c -e ./configure --prefix=/usr\n"
        "[00:00:30] SUCCESS auto.bst: Running commands\n"
        "[00:00:30] SUCCESS [abc12345] auto.bst: Build\n"
    )
    tax = configure_tax(scan_log_tree(str(tmp_path / "logs")))
    assert tax["configure_us"] == 0
    assert "floor of zero" in tax["caveat"]


def test_the_two_planes_are_shown_side_by_side_and_never_summed(log_tree):
    """A quantity computed twice is a free test - but only if the two
    computations are kept apart. Plane 3's is cmake's self-reported wall
    time; Plane 2's is kernel CPU over the traced process tree. The join
    publishes both per element and adds neither to the other."""
    from tools.bst_cache_logs import build_report

    native = {"configure_phase": {
        "available": True,
        "per_element": {"core.bst": {
            "configure_cpu_us": 650_000, "build_cpu_us": 7_000_000,
            "configure_processes": 36, "build_processes": 40,
            "configure_share": 0.085, "coverage": 0.81,
        }},
    }}
    report = build_report(scan_log_tree(str(log_tree)), native_report=native)
    row = report["configure_views"]["elements"][0]
    assert row["element"] == "core.bst"
    assert row["plane3_configure_us"] == 800_000
    assert row["plane2_configure_cpu_us"] == 650_000
    assert row["self_report_missing"] is False
    assert "never summed" in report["configure_views"]["note"]


def test_traced_configure_work_with_no_self_report_is_named(log_tree):
    """The case the pair exists for: Plane 2 finds a large configure
    subtree under an element Plane 3 heard nothing about. That is an
    autotools element, and it is where the prize is largest and the
    self-report blindest."""
    from tools.bst_cache_logs import build_report

    native = {"configure_phase": {
        "available": True,
        "per_element": {"auto.bst": {
            "configure_cpu_us": 30_000_000, "build_cpu_us": 5_000_000,
            "configure_processes": 900, "build_processes": 100,
            "configure_share": 0.857, "coverage": 0.9,
        }},
    }}
    views = build_report(scan_log_tree(str(log_tree)), native_report=native)["configure_views"]
    assert views["elements_without_a_self_report"] == 1
    assert views["elements"][0]["self_report_missing"] is True


def test_the_project_wide_finding_names_the_prize_and_the_payers(tmp_path):
    """`REAL_LOG` deliberately does *not* trigger this - 0.8s of 17s is
    4.7%, under the bar - so the finding gets a log that is genuinely
    majority-configure, which is the shape the task was filed about."""
    from tools.bst_cache_logs import build_report

    directory = tmp_path / "logs" / "p" / "small"
    directory.mkdir(parents=True)
    (directory / "abc12345-build.20260818-115322.log").write_text(
        "BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
        "[--:--:--] START   [abc12345] small.bst: Build\n"
        "[--:--:--] START   small.bst: Running commands\n"
        "-- Configuring done (6.0s)\n"
        "[00:00:10] SUCCESS small.bst: Running commands\n"
        "[00:00:10] SUCCESS [abc12345] small.bst: Build\n"
    )
    findings = build_report(scan_log_tree(str(tmp_path / "logs")))["findings"]
    assert [f["id"] for f in findings] == ["configure-tax"]
    assert "small.bst" in findings[0]["title"]
    assert findings[0]["evidence"]["plane3_configure_us"] == 6_000_000
    assert findings[0]["severity"] == "medium"


def test_a_configure_share_below_the_bar_is_not_a_finding(tmp_path):
    """`CONFIGURE_SHARE_NOTABLE` is not decoration: a report that names
    every 3% is a report nobody reads."""
    from tools.bst_cache_logs import build_report

    directory = tmp_path / "logs" / "p" / "big"
    directory.mkdir(parents=True)
    (directory / "abc12345-build.20260818-115322.log").write_text(
        "BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
        "[--:--:--] START   [abc12345] big.bst: Build\n"
        "[--:--:--] START   big.bst: Running commands\n"
        "-- Configuring done (1.0s)\n"
        "[00:01:00] SUCCESS big.bst: Running commands\n"
        "[00:01:00] SUCCESS [abc12345] big.bst: Build\n"
    )
    assert build_report(scan_log_tree(str(tmp_path / "logs")))["findings"] == []


# --- UX-101: the longitudinal ranking ------------------------------------

def _tax_tree(tmp_path, builds):
    """`builds` is a list of (element, key, seconds, stamp) tuples."""
    root = tmp_path / "logs"
    for element, key, seconds, stamp in builds:
        directory = root / "p" / element.removesuffix(".bst")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{key}-build.{stamp}.log").write_text(
            f"BuildStream 2.7.0 - Tuesday, 18-08-2026 at "
            f"{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}\n"
            f"[--:--:--] START   [{key}] {element}: Build\n"
            f"[--:--:--] START   {element}: Running commands\n"
            f"[00:00:{seconds:02d}] SUCCESS {element}: Running commands\n"
            f"[00:00:{seconds:02d}] SUCCESS [{key}] {element}: Build\n"
        )
    return root


def test_the_ranking_is_by_total_seconds_across_the_tree(tmp_path):
    """The point of the task: an element fourth on today's critical path
    but rebuilding in most builds taxes the team more than today's
    first, which rebuilds monthly. Total is what says so."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("heavy.bst", "aaaa0001", 30, "20260818-160000"),   # once, 30s
        ("frequent.bst", "eeee0001", 20, "20260818-160100"),
        ("frequent.bst", "eeee0002", 20, "20260818-160200"),
        ("frequent.bst", "eeee0003", 20, "20260818-160300"),
    ])
    ranking = developer_tax(scan_log_tree(str(root)))['ranking']
    assert [row['element'] for row in ranking] == ["frequent.bst", "heavy.bst"]
    assert ranking[0]['total_us'] == 60_000_000
    assert ranking[0]['mean_us'] == 20_000_000


def test_an_unchanged_key_rebuild_keeps_ux93s_label(tmp_path):
    """A rebuild with the same key is a retention question, not a
    project one, and the tax breakdown must not blur that back."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("a.bst", "aaaa0001", 5, "20260818-160000"),
        ("a.bst", "aaaa0001", 5, "20260818-160100"),
    ])
    causes = developer_tax(scan_log_tree(str(root)))['ranking'][0]['causes']
    assert causes == {'unchanged_key': 1, 'own_key_changed': 0, 'rooted_upstream': 0}


def test_without_a_graph_an_upstream_cause_is_not_invented(tmp_path):
    """These logs carry no dependency edges. Reporting `rooted_upstream`
    without them would be a claim the data cannot support, so the
    category is absent from `causes_available` and the rebuild counts as
    the element's own change - stated in the output rather than folded
    in silently."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("dep.bst", "dddd0001", 5, "20260818-160000"),
        ("dep.bst", "dddd0002", 5, "20260818-160100"),
        ("app.bst", "eeee0001", 5, "20260818-160010"),
        ("app.bst", "eeee0002", 5, "20260818-160110"),
    ])
    tax = developer_tax(scan_log_tree(str(root)))
    assert 'rooted_upstream' not in tax['causes_available']
    app = next(row for row in tax['ranking'] if row['element'] == 'app.bst')
    assert app['causes']['own_key_changed'] == 1


def test_with_a_graph_the_upstream_root_is_named(tmp_path):
    """The headline the task exists for: one volatile key near the root
    *is* the top developer tax, and naming it is the number that proves
    it."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("dep.bst", "dddd0001", 5, "20260818-160000"),
        ("dep.bst", "dddd0002", 5, "20260818-160100"),
        ("app.bst", "eeee0001", 5, "20260818-160010"),
        ("app.bst", "eeee0002", 7, "20260818-160110"),
    ])
    tax = developer_tax(
        scan_log_tree(str(root)),
        dependencies=[{"predecessor": "dep.bst", "successor": "app.bst"}],
    )
    assert 'rooted_upstream' in tax['causes_available']
    app = next(row for row in tax['ranking'] if row['element'] == 'app.bst')
    assert app['causes'] == {'unchanged_key': 0, 'own_key_changed': 0, 'rooted_upstream': 1}
    assert app['upstream_roots'] == [{'element': 'dep.bst', 'downstream_us': 7_000_000}]


def test_the_build_count_is_a_lower_bound_and_says_so(tmp_path):
    """Measured, not assumed: a log's header timestamp equals its own
    filename stamp, so it is the *task's* start and nothing in the tree
    says which logs belonged to one `bst build`. The largest per-element
    count is a lower bound on the number of builds, and calling it a
    count would be a number this data cannot produce."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("a.bst", "aaaa0001", 5, "20260818-160000"),
        ("a.bst", "aaaa0002", 5, "20260818-160100"),
        ("b.bst", "bbbb0001", 5, "20260818-160010"),
    ])
    tax = developer_tax(scan_log_tree(str(root)))
    assert tax['builds_lower_bound'] == 2
    assert tax['build_logs'] == 3
    assert 'lower bound' in tax['caveat']


def test_a_short_window_is_declared_weak_rather_than_withheld(tmp_path):
    """A three-build tree is what most developers have, and it does say
    something - so it is printed with the count and labelled, not
    suppressed."""
    from tools.bst_cache_logs import developer_tax

    root = _tax_tree(tmp_path, [
        ("a.bst", f"aaaa000{i}", 5, f"20260818-1600{i:02d}") for i in range(3)
    ])
    assert developer_tax(scan_log_tree(str(root)))['weak_window'] is True


def test_an_empty_command_block_is_not_a_repeated_operation(tmp_path):
    """BuildStream writes a `+ sh -c -e $'\\n'` line for an element whose
    command block is empty. On the real freedesktop-sdk log tree eight
    elements share one, and the repeated-operation report called it an
    operation repeated across eight elements. It is the absence of one.
    """
    directory = tmp_path / "logs" / "p"
    records = []
    for index in range(4):
        element_dir = directory / f"e{index}"
        element_dir.mkdir(parents=True)
        (element_dir / f"abc1234{index}-build.20260818-115322.log").write_text(
            f"BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
            f"[--:--:--] START   [abc1234{index}] e{index}.bst: Build\n"
            f"[--:--:--] START   e{index}.bst: Running commands\n"
            "+ sh -c -e $'\\n'\n"
            "+ sh -c -e make -j4\n"
            f"[00:00:05] SUCCESS e{index}.bst: Running commands\n"
            f"[00:00:05] SUCCESS [abc1234{index}] e{index}.bst: Build\n"
        )
        records.append(element_dir)
    findings = repeated_operations(scan_log_tree(str(tmp_path / "logs")))
    assert [f['command'] for f in findings] == ["make -j4"]


# --- UX-127: the front door takes the project you have ------------------

from tools.bst_cache_logs import (  # noqa: E402
    is_project_dir, main, project_name_from_dir, summarize_log_tree,
)


@pytest.fixture
def project_dir(tmp_path):
    """A minimal BuildStream project whose declared name is the log
    tree's directory name - the correspondence UX-127 is about."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text(
        "# a comment first, so the parser cannot rely on line 1\n"
        "name: my-project\n"
        "min-version: 2.0\n"
        "element-path: elements\n"
    )
    return root


class TestTheProjectDirectoryIsTheObviousArgument:
    def test_the_name_is_read_from_project_conf(self, project_dir):
        assert project_name_from_dir(str(project_dir)) == "my-project"

    def test_a_directory_with_no_project_conf_is_not_a_project(self, tmp_path):
        assert not is_project_dir(str(tmp_path))
        assert project_name_from_dir(str(tmp_path)) is None

    def test_a_project_directory_renders_that_projects_report(
            self, project_dir, log_tree, monkeypatch, capsys):
        """The Motivation's whole point: `bga cache-logs PROJECT` used to
        report "nothing to report on" about a project whose logs sit two
        directories away, because the positional was the *log root*."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(log_tree.parent))
        (log_tree.parent / "buildstream").mkdir(exist_ok=True)
        shutil.copytree(log_tree, log_tree.parent / "buildstream" / "logs")

        assert main([str(project_dir)]) == 0

        assert "my-project" in capsys.readouterr().out

    def test_a_project_whose_conf_declares_no_name_says_so(self, tmp_path, capsys):
        root = tmp_path / "nameless"
        root.mkdir()
        (root / "project.conf").write_text("min-version: 2.0\n")

        assert main([str(root)]) == 1

        assert "declares no `name:`" in capsys.readouterr().err

    def test_a_log_root_still_works(self, log_tree, capsys):
        """The old positional meaning is not withdrawn - a path that is
        not a project is still read as the log root."""
        assert main([str(log_tree)]) == 0
        assert "Cached Build Logs" in capsys.readouterr().out


class TestDiscoveryIsTheToolsJob:
    def test_a_bare_invocation_lists_the_tree(self, log_tree, monkeypatch, capsys):
        """It used to report over every project the machine had ever
        built, which is never one user's question."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(log_tree.parent))
        (log_tree.parent / "buildstream").mkdir(exist_ok=True)
        shutil.copytree(log_tree, log_tree.parent / "buildstream" / "logs")

        assert main([]) == 0

        out = capsys.readouterr().out
        assert "BuildStream log tree" in out
        assert "my-project" in out

    def test_the_listing_carries_counts_and_a_span(self, log_tree):
        [entry] = summarize_log_tree(str(log_tree))

        assert entry["project"] == "my-project"
        assert entry["logs"] == 1
        assert entry["elements"] == 1
        assert entry["first_us"] is not None and entry["last_us"] is not None

    def test_all_restores_the_report_over_everything(self, log_tree, capsys):
        assert main([str(log_tree), "--all"]) == 0
        assert "Cached Build Logs" in capsys.readouterr().out

    def test_the_listing_is_machine_readable_too(self, log_tree, capsys):
        assert main([str(log_tree), "--list", "--format", "json"]) == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["projects"][0]["project"] == "my-project"


class TestTheWrongArgumentRedirects:
    def test_a_project_with_no_logs_names_what_was_derived_and_where(
            self, tmp_path, log_tree, monkeypatch, capsys):
        """UX-127 item 3. "Nothing to report on" is a confidently wrong
        answer when the tool looked in the right place for the wrong
        name - and the user has no way to tell those apart."""
        other = tmp_path / "other"
        other.mkdir()
        (other / "project.conf").write_text("name: not-built-here\n")
        monkeypatch.setenv("XDG_CACHE_HOME", str(log_tree.parent))
        (log_tree.parent / "buildstream").mkdir(exist_ok=True)
        shutil.copytree(log_tree, log_tree.parent / "buildstream" / "logs")

        assert main([str(other)]) == 1

        err = capsys.readouterr().err
        assert "not-built-here" in err
        assert "declares `name: not-built-here`" in err
        assert "The tree holds: my-project" in err
        assert "--list" in err

    def test_an_empty_tree_says_no_build_has_written_here(
            self, tmp_path, monkeypatch, capsys):
        empty = tmp_path / "cache" / "buildstream" / "logs"
        empty.mkdir(parents=True)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        project = tmp_path / "p"
        project.mkdir()
        (project / "project.conf").write_text("name: p\n")

        assert main([str(project)]) == 1

        assert "no build has written logs here yet" in capsys.readouterr().err

    def test_project_name_still_works_unchanged(self, log_tree, capsys):
        assert main([str(log_tree), "--project", "my-project"]) == 0
        assert "Cached Build Logs" in capsys.readouterr().out


class TestThePlane2ReportTakesASnapshotNameToo:
    """UX-134: this command is dispatched straight to `tools/`, so it
    never passes through `bga.cli`'s alias resolution — which made
    `--native-report` the one Plane 2 argument the store could not name.
    A seam one command wide is still a seam.
    """

    def _project_with_a_snapshot(self, tmp_path, with_plane2=True):
        from bga import run_store

        project = tmp_path / "proj"
        project.mkdir()
        (project / "project.conf").write_text("name: my-project\nmin-version: 2.0\n")
        snapshot = run_store.new_snapshot_dir(str(project))
        os.makedirs(os.path.join(snapshot, "run"))
        if with_plane2:
            with open(os.path.join(snapshot, "plane2.json"), "w") as handle:
                json.dump({"by_element": {}, "configure_phase": {}}, handle)
        return project, snapshot

    def test_an_alias_names_the_snapshots_report(
            self, tmp_path, log_tree, monkeypatch, capsys):
        project, snapshot = self._project_with_a_snapshot(tmp_path)
        monkeypatch.setenv("XDG_CACHE_HOME", str(log_tree.parent))
        (log_tree.parent / "buildstream").mkdir(exist_ok=True)
        shutil.copytree(log_tree, log_tree.parent / "buildstream" / "logs")
        monkeypatch.chdir(project)

        assert main([str(project), "--native-report", "@last"]) == 0

        assert "my-project" in capsys.readouterr().out

    def test_an_alias_with_no_report_fails_by_name_not_as_a_missing_file(
            self, tmp_path, monkeypatch, capsys):
        project, _snapshot = self._project_with_a_snapshot(tmp_path, with_plane2=False)
        monkeypatch.chdir(project)

        assert main([str(project), "--native-report", "@last"]) == 1

        assert "no plane2.json" in capsys.readouterr().err

    def test_an_explicit_path_is_unchanged(self, tmp_path, monkeypatch, capsys):
        project, snapshot = self._project_with_a_snapshot(tmp_path)
        monkeypatch.chdir(tmp_path)

        assert main([str(project), "--native-report",
                     os.path.join(snapshot, "plane2.json")]) == 1

        assert "no plane2.json" not in capsys.readouterr().err
