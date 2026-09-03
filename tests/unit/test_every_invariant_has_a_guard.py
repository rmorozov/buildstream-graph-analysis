"""UX-567: a fourteenth invariant cannot arrive unguarded.

Part 34's `## I#` headings are read from the spec, not restated here.
Every one is either in `GUARDS`, pointing at a file under `tests/unit/`
that names it, or in `WAIVERS` with the reason and the Part 32 registry
row that decided it. Round 83 found four of thirteen held by nothing:
I6 had no code at all, I10 was true on every fixture and asserted on
none, I7 was I4 under another name, and I13 was held by behaviour under
a name no reader could grep for.
"""
import re
import subprocess
from pathlib import Path

import pytest

from bga.validation.invariants import compute_confidence

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs/spec/specification.md"

# I# -> the file under tests/unit/ that names it. Where several name an
# invariant this is the one whose claim *is* that invariant.
GUARDS = {
    "I1": "test_capacity_lower_bound.py",
    "I2": "test_capacity_lower_bound.py",
    "I3": "test_i3_and_span_status.py",
    "I4": "test_attribution_identity_across_topologies.py",
    "I5": "test_normalize.py",
    "I6": "test_occupancy_within_capacity.py",
    "I8": "test_run_identity.py",
    "I9": "test_cpu_reconciliation.py",
    "I10": "test_attribution_identity_across_topologies.py",
    "I11": "test_determinism.py",
    "I12": "test_cold_floor.py",
    "I13": "test_cold_floor.py",
}

# I# -> (reason, the Part 32 registry heading that decided it).
WAIVERS = {
    "I7": ("blame_chain_coverage is I4's own sum over I4's own horizon",
           "### 32.7.4"),
}

_HORIZON_KEYS = (
    "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
    "scheduler_wait_us", "idle_us", "retry_wait_us",
)


def _spec_text():
    return SPEC.read_text(encoding="utf-8")


def _part_34():
    """Part 34's own body, subject only - a `## I#` heading anywhere
    else in the spec is not one of the core invariants."""
    text = _spec_text()
    start = text.index("# Part 34 — Core Invariants")
    return text[start:text.index("\n# Part 35", start)]


def _invariant_ids():
    return [m.group(1) for m in re.finditer(r"^## (I\d+) — ", _part_34(), re.M)]


def _unit_test_files():
    listed = subprocess.run(
        ["git", "ls-files", "tests/unit/*.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return {Path(p).name for p in listed}


class TestThePopulationIsNotEmpty:
    """A scan over nothing passes every claim below it."""

    def test_part_34_declares_the_invariants_this_map_is_about(self):
        ids = _invariant_ids()
        assert len(ids) >= 13, f"Part 34 yielded {ids} - the heading form moved"
        assert ids == sorted(ids, key=lambda i: int(i[1:])), ids

    def test_the_scan_reads_a_real_population_of_test_files(self):
        files = _unit_test_files()
        assert len(files) >= 300, f"only {len(files)} files under tests/unit/"


class TestEveryInvariantIsAccountedFor:

    def test_every_declared_invariant_is_guarded_or_waived(self):
        accounted = set(GUARDS) | set(WAIVERS)
        unaccounted = [i for i in _invariant_ids() if i not in accounted]
        assert unaccounted == [], (
            f"Part 34 declares {unaccounted} with neither a guard nor a "
            f"waiver - add the file, or the waiver and its 32.7 row")

    def test_the_map_names_no_invariant_the_spec_does_not_declare(self):
        declared = set(_invariant_ids())
        stray = sorted((set(GUARDS) | set(WAIVERS)) - declared)
        assert stray == [], f"mapped but not in Part 34: {stray}"

    def test_no_invariant_is_both_guarded_and_waived(self):
        both = sorted(set(GUARDS) & set(WAIVERS))
        assert both == [], f"{both} claim a guard and a waiver at once"


class TestEachGuardExistsAndNamesItsInvariant:
    """A map entry pointing at a file that never mentions the id is a
    row nobody could have followed back."""

    @pytest.mark.parametrize("invariant", sorted(GUARDS, key=lambda i: int(i[1:])))
    def test_the_named_file_is_one_the_repository_tracks(self, invariant):
        assert GUARDS[invariant] in _unit_test_files(), (
            f"{invariant} is mapped to {GUARDS[invariant]}, which git does "
            f"not track under tests/unit/")

    @pytest.mark.parametrize("invariant", sorted(GUARDS, key=lambda i: int(i[1:])))
    def test_the_named_file_names_the_invariant(self, invariant):
        path = REPO / "tests/unit" / GUARDS[invariant]
        text = path.read_text(encoding="utf-8")
        assert re.search(rf"\b{invariant}\b", text), (
            f"{GUARDS[invariant]} is {invariant}'s guard but never names "
            f"{invariant} - a reader cannot get from the report line back "
            f"to the test")


class TestAWaiverCitesTheDecisionThatMadeIt:

    @pytest.mark.parametrize("invariant", sorted(WAIVERS))
    def test_the_waiver_names_a_registry_row_the_spec_carries(self, invariant):
        _reason, heading = WAIVERS[invariant]
        assert heading in _spec_text(), (
            f"{invariant} is waived against {heading}, which Part 32 does "
            f"not carry")

    def test_i7_is_i4s_sum_over_i4s_horizon(self):
        """32.7.4's claim, on the code: a run whose attribution misses H
        by a known amount reports exactly that ratio, so I7 adds no
        quantity I4 does not already carry."""
        attribution = {k: 0 for k in _HORIZON_KEYS}
        attribution["execution_on_chain_us"] = 3
        confidence, _ = compute_confidence(
            normalized_tasks=[_task(0, 4)], run_context=None, trace=None,
            graph=None, violations=[], attribution_segments=[],
            graph_analysis={}, attribution=attribution, floors={})

        assert confidence["blame_chain_coverage"] == 3 / 4
        assert confidence["hard_gates"]["blame_chain_coverage_full"] is False

    def test_the_alias_holds_at_one_too(self):
        attribution = {k: 0 for k in _HORIZON_KEYS}
        attribution["execution_on_chain_us"] = 4
        confidence, _ = compute_confidence(
            normalized_tasks=[_task(0, 4)], run_context=None, trace=None,
            graph=None, violations=[], attribution_segments=[],
            graph_analysis={}, attribution=attribution, floors={})

        assert confidence["blame_chain_coverage"] == 1.0
        assert confidence["hard_gates"]["blame_chain_coverage_full"] is True


def _task(start_us, finish_us):
    from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
    return NormalizedTask(
        task_key=TaskKey("a.bst", TaskKind.BUILD, "BUILD", 0),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
    )
