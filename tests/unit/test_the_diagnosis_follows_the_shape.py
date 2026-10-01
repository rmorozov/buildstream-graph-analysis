"""UX-477: one graph gets one verdict, whatever its elements cost.

`diagnose()` decided chain-boundness by dividing the critical path by
**wall-clock**, and wall-clock carries a constant the graph cannot
explain: BuildStream's startup, cache query and initial staging, before
the first task begins. The run's own `wait-category` finding names that
span and says it is *"not a scheduling issue"* - and the diagnosis
divided by it anyway.

What that cost is a verdict that follows how *long* a build is rather
than what shape it is. `UX-468`'s walk 3 generated six elements in one
strict line, built them, and was told the build was "scheduler-bound,
not chain-bound ... the time is going somewhere other than the chain" -
on a graph where nothing can run beside anything else, with the sweep
offered as the next step.

So the denominator is the task horizon. These are the two properties
that makes true, and neither can be read off the source.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bga.findings import (
    CHAIN_BOUND_RATIO,
    DIAGNOSIS_CAPACITY_BOUND,
    DIAGNOSIS_CHAIN_BOUND,
    DIAGNOSIS_INCONCLUSIVE,
    DIAGNOSIS_SCHEDULER_BOUND,
    compute_headline,
    diagnose,
)

REPO = Path(__file__).resolve().parents[2]


class _Run:
    """The three fields `diagnose` reads, and nothing else."""

    def __init__(self, critical_path_us, wall_us, head_us=0, tail_us=0):
        self.floors = {"t_infinity_observed": critical_path_us}
        self.total_duration_us = wall_us
        self.attribution = {"untracked_head_us": head_us, "untracked_tail_us": tail_us}


class TestOneGraphGetsOneVerdict:
    #: `UX-468`'s walk 3, as numbers: six elements of `seconds` each in
    #: one strict chain, built by a real `bst`, with the same ~1.3s
    #: BuildStream head in front of both.
    WALK_THREE = [
        # (per link, critical path us, wall us, head us, tail us)
        ("1.5s", 8_950_000, 10_350_000, 1_250_000, 150_000),
        ("4.5s", 26_900_000, 28_310_000, 1_260_000, 150_000),
    ]

    def test_the_same_shape_at_two_scales_agrees(self):
        """The measurement this item was filed on. Against wall-clock
        these two read 0.865 and 0.950 - opposite sides of the line -
        for one graph whose only difference is how long its elements
        sleep."""
        verdicts = {
            label: diagnose(_Run(path, wall, head, tail))["diagnosis"]
            for label, path, wall, head, tail in self.WALK_THREE
        }
        assert len(set(verdicts.values())) == 1, verdicts
        assert set(verdicts.values()) == {DIAGNOSIS_CHAIN_BOUND}, verdicts

    def test_against_wall_clock_they_would_disagree(self):
        """The discriminating half: a guard that only asserted the
        clause above would still pass if the denominator went back to
        wall-clock *and* the threshold moved to catch both. This pins
        that the old arithmetic really does straddle the line, so the
        clause above is about the denominator and not about the
        constant."""
        against_wall = [path / wall for _, path, wall, _, _ in self.WALK_THREE]
        assert min(against_wall) < CHAIN_BOUND_RATIO <= max(against_wall), against_wall

    @pytest.mark.parametrize("head_us", [0, 1_000, 1_250_000, 5_000_000])
    def test_the_verdict_does_not_move_with_the_head(self, head_us):
        """The general statement: a chain is a chain however much
        startup sits in front of it. One graph, five heads."""
        run = _Run(9_000_000, 9_000_000 + head_us, head_us=head_us)
        answer = diagnose(run)
        assert answer["diagnosis"] == DIAGNOSIS_CHAIN_BOUND, (head_us, answer)
        assert answer["chain_share"] == pytest.approx(1.0)


class TestTheDenominatorSaysWhatItIs:
    def test_it_is_the_horizon_and_says_so(self):
        run = _Run(6_000_000, 10_000_000, head_us=1_000_000, tail_us=1_000_000)
        answer = diagnose(run)
        # 6 / (10 - 1 - 1), not 6 / 10.
        assert answer["chain_share"] == pytest.approx(0.75)
        assert answer["chain_share_of"] == "task_horizon"

    def test_a_capture_with_no_attribution_falls_back_and_says_so(self):
        """A run whose attribution never ran has no head to subtract.
        `analyzer.py` already sets `total_duration_us` to the horizon
        when a capture records no wall bounds, so the two agree there -
        but the field says which was used rather than leaving a reader
        to assume."""

        class NoAttribution:
            floors = {"t_infinity_observed": 6_000_000}
            total_duration_us = 10_000_000

        answer = diagnose(NoAttribution())
        assert answer["chain_share"] == pytest.approx(0.6)
        assert answer["chain_share_of"] == "wall_clock"

    def test_a_head_that_swallows_the_run_falls_back_rather_than_dividing(self):
        """A corrupted capture can report a head longer than its own
        wall-clock. Dividing by a non-positive span is a crash or a
        negative share; falling back is neither, and the field says it
        happened."""
        run = _Run(6_000_000, 10_000_000, head_us=12_000_000)
        answer = diagnose(run)
        assert answer["chain_share_of"] == "wall_clock"
        assert answer["chain_share"] == pytest.approx(0.6)

    def test_a_run_with_no_durations_is_still_inconclusive(self):
        class Empty:
            floors = {}
            total_duration_us = 0

        answer = diagnose(Empty())
        assert answer["diagnosis"] == DIAGNOSIS_INCONCLUSIVE
        assert answer["chain_share"] is None
        assert answer["chain_share_of"] is None

    def test_a_genuinely_scheduler_bound_graph_still_reads_that_way(self):
        """The other side. Removing the head must not turn every build
        chain-bound - a graph whose elements could have run together and
        did not still reads below the line, and its share is unchanged
        because it has no head to remove."""
        run = _Run(4_000_000, 16_000_000)
        answer = diagnose(run)
        assert answer["diagnosis"] == DIAGNOSIS_SCHEDULER_BOUND
        assert answer["chain_share"] == pytest.approx(0.25)


class TestTheSentenceNamesTheDenominator:
    @pytest.mark.parametrize(
        "run,expected",
        [
            (_Run(9_000_000, 10_000_000, head_us=1_000_000), DIAGNOSIS_CHAIN_BOUND),
            (_Run(4_000_000, 16_000_000), DIAGNOSIS_SCHEDULER_BOUND),
        ],
    )
    def test_neither_sentence_says_wall_clock_any_more(self, run, expected):
        """`UX-326`: the tool's own sentences are contracts. A sentence
        that still said "of wall-clock" would be describing arithmetic
        the tool stopped doing."""
        answer = diagnose(run)
        assert answer["diagnosis"] == expected
        assert "wall-clock" not in answer["sentence"], answer["sentence"]
        assert "the time tasks were running" in answer["sentence"], answer["sentence"]


class _CapacityRun:
    """`UX-1244`'s 2,402-element page as numbers: t-infinity 9.8% of the
    horizon, LB 47.0 of 47.2 min wall (`floors`, seed 1, 40x60, binaries)."""

    total_duration_us = 2_829_756_376
    floors = {"t_infinity_observed": 277_500_000, "lb": 2_817_875_000}
    attribution = {"untracked_head_us": 0, "untracked_tail_us": 0}
    capacity_verdict = {"checks_ran": True, "oversubscribed": False}
    signals = {"blast_radius": {"layer00/mod010.bst": {"downstream_count": 2194}}}


class TestACapacityBoundRunReadsCapacityBound:
    FINDINGS = [
        {"id": "capacity-recommendation"},
        {"id": "blast-radius-ranking", "elements": ["layer00/mod010.bst"]},
    ]

    def test_the_page_reads_capacity_bound_and_names_builders(self):
        answer = diagnose(_CapacityRun())
        assert answer["diagnosis"] == DIAGNOSIS_CAPACITY_BOUND, answer
        assert "builder" in answer["sentence"] and "99.6%" in answer["sentence"], answer["sentence"]

    def test_its_first_action_is_the_builders_step(self):
        actions = compute_headline(_CapacityRun(), self.FINDINGS)["top_actions"]
        assert actions[0]["finding_id"] == "capacity-recommendation" and "element_uid" not in actions[0], actions
        assert "--capacity" in actions[0]["step"], actions[0]
        assert actions[1]["element_uid"] == "layer00/mod010.bst", actions

    def test_a_host_cap_is_named_and_measured_above_not_raised(self):
        """The page's recommendation: builders 4 held at 4 host cores, the CPU could feed 18."""
        run = _CapacityRun()
        run.capacity_recommendation = {
            "binding_constraint": "host_cores",
            "host_cpu_count": 4,
            "recommended_builders": 4,
            "builders_change": 0,
            "constraints": [{"name": "host_cores", "allows": 4, "clamped_from": 18}],
        }
        sentence = diagnose(run)["sentence"]
        step = compute_headline(run, self.FINDINGS)["top_actions"][0]["step"]
        assert "held at the host's 4 cores by policy while the CPU could feed 18" in sentence, sentence
        assert step == "Measure builders above the host's 4-core cap with bga sweep", step
        assert "higher N" not in sentence + step and "`" not in sentence + step

    def test_an_unclamped_binding_names_the_recommended_count(self):
        run = _CapacityRun()
        run.capacity_recommendation = {
            "binding_constraint": "CPU",
            "host_cpu_count": 8,
            "recommended_builders": 6,
            "builders_change": 2,
            "constraints": [{"name": "CPU", "allows": 6}],
        }
        assert "CPU binds at 6 builders" in diagnose(run)["sentence"]
        assert compute_headline(run, self.FINDINGS)["top_actions"][0]["step"] == "Run with 6 builders and measure it"

    def test_a_chain_at_the_floor_stays_chain_bound(self):
        """LB above the line but equal to t-infinity: the chain check runs first."""
        run = _CapacityRun()
        run.floors = {"t_infinity_observed": 277_500_000, "lb": 277_500_000}
        run.total_duration_us = 290_000_000
        assert diagnose(run)["diagnosis"] == DIAGNOSIS_CHAIN_BOUND

    @pytest.mark.parametrize(
        "args",
        [
            ["tests/fixtures/golden/mixed_task_kinds"],
            ["tests/fixtures/macro_micro/run", "--plane2", "tests/fixtures/macro_micro/plane2.json"],
        ],
        ids=["golden", "macro_micro"],
    )
    def test_the_committed_fixtures_stay_chain_bound(self, args):
        out = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", *args, "--format", "json"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(out.stdout)["headline"]["diagnosis"] == DIAGNOSIS_CHAIN_BOUND
