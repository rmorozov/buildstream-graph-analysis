"""UX-568: which Part a guard holds, as an index the suite reads.

The spec's `# Part N` headings are read from the document; the files
under `tests/unit/` that name each Part are read from git. A heading
with neither a naming file nor an allowlist row reddens, so a Part
cannot be added, or a guard renamed away, unnoticed. The index asserts
that a guard *exists* - what it asserts is that guard's own business.

Two derivations Part 32's own guards leave unheld ride along, because
both are the same failure in miniature: a declared key list that no
guard reads against the code (32.4 vs `AnalysisResult`, 32.1 vs
`load_run_context`).
"""
import ast
import dataclasses
import re
import subprocess
from pathlib import Path

import pytest

from bga.ingest.models import AnalysisResult

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs/spec/specification.md"

# A Part with nothing to guard. The reason is the row.
PROSE_ONLY = {
    0: "Executive Summary - the document's own overview",
    2: "Three Semantic Layers - the vocabulary Parts 11 and 44 use",
    40: "Milestone Plan - superseded by the backlog rows, per 32.7.3",
    44: "Final Semantic Contract - restates Parts 2 and 11, both named",
}

# A Part that *is* implemented and that no file asserts. Capped below:
# this list may shrink, never grow.
UNGUARDED = {
    20: "the 1/n share integral. `wall_clock_share_us` is published and "
        "held by the golden fixture, but no file asserts the integral",
    22: "compute_average_concurrency and compute_peak_occupancy are "
        "reached only through the occupancy dict a fixture pins",
}

# Part 29 was here until `UX-565` landed in the same round: the
# analyzer reads the store's prior same-host runs, `signals` carries
# the block, and `test_part_29_reads_the_store_it_has.py` names it.
# `test_an_allowlisted_part_that_gained_a_guard_leaves_the_list` is
# what noticed, on the merge.

# 32.4 declares nine keys; `AnalysisResult` carries these too. 32.5's
# rule makes an addition an addition, so each is listed rather than
# silently tolerated.
ANALYSIS_ADDITIONS = {
    "structural", "run_id", "run_instance", "memory_envelope",
    "plane2_absence", "total_duration_us", "pipeline_overhead",
    "timestamp_agreement", "element_kind_summary", "capacity_verdict",
    "plane2_capacity", "capacity_recommendation",
}

# Likewise for 32.1's six against what `load_run_context` reads.
RUN_CONTEXT_ADDITIONS = {
    "native_max_jobs", "native_max_jobs_source", "host_cpu_count",
    "cpu_budget", "memory_budget_mb", "host_memory_mb",
    "estimated_job_memory_mb", "exclusive_resources", "pipeline_overhead",
    "run_identity", "host_manifest", "producer", "build_outcome",
    "queue_summary", "timestamp_agreement",
}


def _spec_text():
    return SPEC.read_text(encoding="utf-8")


def _part_headings():
    return sorted(int(m) for m in re.findall(r"^# Part (\d+) ", _spec_text(), re.M))


def _unit_test_paths():
    listed = subprocess.run(
        ["git", "ls-files", "tests/unit/*.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return [REPO / p for p in listed]


def _parts_named_by_a_file():
    """Part number -> the files naming it; a subsection reference names
    its Part. This file is excluded: an index is not its own evidence,
    and the reasons below quote the Parts they are about."""
    named = {}
    for path in _unit_test_paths():
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\bPart (\d+)", text):
            named.setdefault(int(match.group(1)), set()).add(path.name)
    return named


def _json_block_keys(section_heading):
    """The top-level keys of the one fenced JSON block under a `## 32.N`
    heading - the declaration, not the prose around it."""
    text = _spec_text()
    start = text.index(section_heading)
    block = text[text.index("```json", start) + len("```json"):]
    block = block[:block.index("```")]
    return [m.group(1) for m in re.finditer(r'^  "([^"]+)":', block, re.M)]


def _run_context_keys_the_loader_reads():
    """`data.get('X')` inside `load_run_context`'s RunContext(...) call,
    read from the syntax tree rather than grepped."""
    tree = ast.parse((REPO / "bga/ingest/loader.py").read_text(encoding="utf-8"))
    function = next(n for n in ast.walk(tree)
                    if isinstance(n, ast.FunctionDef) and n.name == "load_run_context")
    keys = set()
    for node in ast.walk(function):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "data"):
            keys.add(node.args[0].value)
    # `wall_clock` is read into a local first and then indexed twice.
    if "wall_clock" in {n.id for n in ast.walk(function) if isinstance(n, ast.Name)}:
        keys.add("wall_clock")
    return keys


class TestTheIndexReadsSomething:
    """A scan over an empty population agrees with everything."""

    def test_the_spec_yields_its_parts(self):
        parts = _part_headings()
        assert len(parts) >= 40, f"only {len(parts)} Part headings: {parts}"

    def test_the_scan_reads_a_real_population_of_test_files(self):
        assert len(_unit_test_paths()) >= 300

    def test_the_files_actually_name_parts(self):
        named = _parts_named_by_a_file()
        assert len(named) >= 30, f"only {sorted(named)} named by any file"


class TestEveryPartIsAccountedFor:

    def test_every_heading_has_a_guard_or_a_row(self):
        named = _parts_named_by_a_file()
        allowlisted = set(PROSE_ONLY) | set(UNGUARDED)
        orphans = [p for p in _part_headings()
                   if p not in named and p not in allowlisted]
        assert orphans == [], (
            f"Part(s) {orphans} have no file naming them and no allowlist "
            f"row - name the Part in the guard that holds it, or add the "
            f"row and its reason")

    def test_no_allowlist_row_names_a_part_the_spec_does_not_have(self):
        headings = set(_part_headings())
        stray = sorted((set(PROSE_ONLY) | set(UNGUARDED)) - headings)
        assert stray == [], f"allowlisted but not a heading: {stray}"

    def test_an_allowlisted_part_that_gained_a_guard_leaves_the_list(self):
        named = _parts_named_by_a_file()
        stale = sorted(p for p in (set(PROSE_ONLY) | set(UNGUARDED)) if p in named)
        assert stale == [], (
            f"Part(s) {stale} are allowlisted and also named by "
            f"{[sorted(named[p]) for p in stale]} - drop the row")

    def test_a_part_is_prose_only_or_unguarded_never_both(self):
        assert sorted(set(PROSE_ONLY) & set(UNGUARDED)) == []

    @pytest.mark.parametrize("part", sorted(set(PROSE_ONLY) | set(UNGUARDED)))
    def test_every_allowlist_row_carries_a_reason(self, part):
        reason = PROSE_ONLY.get(part) or UNGUARDED.get(part)
        assert reason and len(reason) > 20, f"Part {part}: {reason!r}"

    def test_the_debt_list_cannot_grow(self):
        """Three implemented Parts assert nothing. A fourth joining them
        is the thing this index exists to make loud."""
        assert len(UNGUARDED) <= 3, sorted(UNGUARDED)


class TestThirtyTwoFourAgainstTheResult:
    """32.4's `analysis/v9` block against `AnalysisResult`'s fields."""

    def test_every_declared_key_is_a_field_the_result_carries(self):
        fields = {f.name for f in dataclasses.fields(AnalysisResult)}
        phantom = sorted(k for k in _json_block_keys("## 32.4 analysis/v9")
                         if k not in fields)
        assert phantom == [], (
            f"32.4 declares {phantom}, which AnalysisResult does not carry")

    def test_every_field_32_4_omits_is_a_declared_addition(self):
        declared = set(_json_block_keys("## 32.4 analysis/v9"))
        fields = {f.name for f in dataclasses.fields(AnalysisResult)}
        undeclared = sorted(fields - declared - ANALYSIS_ADDITIONS)
        assert undeclared == [], (
            f"AnalysisResult carries {undeclared}, which 32.4 does not "
            f"declare and this list does not name as an addition")

    def test_the_addition_list_has_no_field_the_result_dropped(self):
        fields = {f.name for f in dataclasses.fields(AnalysisResult)}
        gone = sorted(ANALYSIS_ADDITIONS - fields)
        assert gone == [], f"listed as additions but no longer fields: {gone}"


class TestThirtyTwoOneAgainstTheLoader:
    """32.1's `run-context/v9` block against what the loader reads."""

    def test_every_declared_field_is_one_the_loader_reads(self):
        read = _run_context_keys_the_loader_reads()
        ignored = sorted(k for k in _json_block_keys("## 32.1 run-context/v9")
                         if k not in read)
        assert ignored == [], (
            f"32.1 declares {ignored}, which load_run_context never reads")

    def test_every_key_32_1_omits_is_a_declared_addition(self):
        declared = set(_json_block_keys("## 32.1 run-context/v9"))
        undeclared = sorted(
            _run_context_keys_the_loader_reads() - declared - RUN_CONTEXT_ADDITIONS)
        assert undeclared == [], (
            f"load_run_context reads {undeclared}, which 32.1 does not "
            f"declare and this list does not name as an addition")

    def test_the_addition_list_has_no_key_the_loader_stopped_reading(self):
        gone = sorted(RUN_CONTEXT_ADDITIONS - _run_context_keys_the_loader_reads())
        assert gone == [], f"listed as additions but no longer read: {gone}"
