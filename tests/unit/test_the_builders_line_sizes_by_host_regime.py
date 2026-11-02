"""UX-1368: the builders line sizes every approach for the host's regime and proposes one.

fdsdk run 41226762092 (4 cores, chain max-jobs 4) printed "Lower builders from 4 to 3" beside
"Builders: 1 with --jobserver auto"; a small host has no idle cores for auto to lend.
"""

import re
import subprocess
import sys

import pytest

from bga.cli import _builder_pool_text_lines
from bga.correlate import (
    compute_builder_pool_recommendation,
    host_regime,
    jobserver_label,
    size_by_regime,
    with_own_sweep,
)
from tests.fixtures.topologies import write_run_dir
from tests.unit.test_the_builders_line_reads_this_runs_sweep import _four_wide

#: `bga sweep` on captures/fdsdk/953683fb-cold-b4j4-41226762092, 1..5 builders, then flat.
FDSDK_SWEEP = ([17_273_800_000, 11_852_850_000, 11_150_550_000, 10_884_550_000] + [10_878_100_000] * 12, 3)
FAT_WALLS = [400_000_000 - i * 10_000_000 for i in range(32)] + [80_000_000] * 4


def _sized(ready, host, chain, sweep, configured, capacity=None, mode="off"):
    recommendation = with_own_sweep(compute_builder_pool_recommendation(ready, host, chain), sweep)
    if isinstance(capacity, int):
        capacity = {"recommended_builders": capacity}
    return size_by_regime(recommendation, host_regime(host, chain), (*configured, mode), capacity)


def _row(recommendation, name):
    return next(a for a in recommendation["approaches"] if a["name"] == name)


@pytest.mark.parametrize(
    ("host", "chain", "regime"),
    [(4, 4, "small"), (4, 8, "small"), (5, 4, "fat"), (16, 8, "fat"), (16, 1, "serial"), (4, None, None)],
)
def test_the_regime_is_the_host_against_the_chains_width(host, chain, regime):
    assert host_regime(host, chain) == regime


def test_fdsdk_proposes_the_capacity_builders_with_the_jobserver_off():
    sized = _sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity=3)
    lines = _builder_pool_text_lines(sized)
    assert (sized["regime"], sized["jobserver"], sized["builders"], sized["max_jobs"]) == ("small", "off", 3, 4)
    assert lines[0].startswith("Builders: 3 with --jobserver off, max-jobs 4 - a small host: 4 cores")
    assert "this run's replay puts 3 at 3.1 h against 4.8 h at 1, its knee at 3; more builders buy 2.4%" in lines[0]
    assert not any(line.startswith("Builders: 1") or "what-if" in line for line in lines)


def test_fdsdk_sizes_auto_and_the_defaults_without_proposing_them():
    sized = _sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity=3)
    lines = _builder_pool_text_lines(sized)
    assert [a["name"] for a in sized["approaches"] if a["proposed"]] == ["off"]
    assert (_row(sized, "auto")["builders"], _row(sized, "defaults")["builders"]) == (1, 4)
    assert any(
        line.startswith("    auto: --builders 1 --max-jobs 4 --jobserver auto - 4.8 h; a 4-vCPU") for line in lines
    )
    assert any(
        line.startswith("    defaults: --builders 4 --max-jobs 4 - 3.0 h;") and "16 jobs on 4 cores" in line
        for line in lines
    )
    assert any(line.startswith("    admission (BGA_ADMISSION=1): not proposed") for line in lines)


def test_a_small_host_takes_the_capacity_recommendation_over_the_knee():
    assert _sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity=2)["builders"] == 2
    assert _sized(17, 4, 4, FDSDK_SWEEP, (4, 4))["builders"] == 3


def test_a_small_host_clamps_max_jobs_to_its_cores():
    sized = _sized(17, 4, 8, FDSDK_SWEEP, (4, 8), capacity=3)
    assert (sized["max_jobs"], _row(sized, "configured")["max_jobs"]) == (4, 8)


def test_a_fat_host_keeps_the_safe_cap_under_auto():
    sized = _sized(40, 16, 8, (FAT_WALLS, 32), (8, 8), capacity=12)
    lines = _builder_pool_text_lines(sized)
    assert (sized["regime"], sized["jobserver"], sized["builders"], sized["graph_only_knee"]) == ("fat", "auto", 8, 32)
    assert lines[0].startswith("Builders: 8 with --jobserver auto - this run's replay puts 8 at 5.5 min")
    assert "    off: --builders 12 --max-jobs 8 - 4.8 min; the chain stays at 8 of 16 cores" in lines
    assert any(
        line.startswith("    auto: --builders 8 --max-jobs 8 --jobserver auto - 5.5 min; proposed;") for line in lines
    )


def test_a_serial_chain_on_a_fat_host_keeps_the_jobserver_off():
    sized = _sized(40, 16, 1, (FAT_WALLS, 32), (4, 1), capacity=12)
    assert (sized["regime"], sized["jobserver"], sized["builders"]) == ("serial", "off", 12)
    assert _builder_pool_text_lines(sized)[0].startswith(
        "Builders: 12 with --jobserver off, max-jobs 1 - a serial chain"
    )


def test_an_unknown_chain_width_sizes_no_approaches():
    recommendation = with_own_sweep(compute_builder_pool_recommendation(17, 4, 4), FDSDK_SWEEP)
    sized = size_by_regime(recommendation, None, (4, None, None), {"recommended_builders": 3})
    assert "approaches" not in sized and sized["builders"] == 1


def test_analyze_on_a_small_host_proposes_the_knee_with_the_jobserver_off(tmp_path):
    run_dir = write_run_dir(tmp_path, _four_wide(host_cpu_count=4))
    out = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run_dir)], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    at = next(index for index, line in enumerate(out) if line.startswith("Builders"))
    assert re.match(r"Builders: 4 with --jobserver off, max-jobs 4 - a small host", out[at]), out[at]
    assert out[at + 1] == "  Approaches sized for 4 cores (replay wall, durations held fixed):"


# Review of a185d5df: zero capacity, withheld capacity, serial clamp, unswept counts, the configured mode.
ZERO = {"recommended_builders": 0, "verdict": "no builders value fits: even one element peaks at ~20 GB"}


@pytest.mark.parametrize(("host", "chain"), [(4, 4), (16, 8)])
def test_a_zero_capacity_proposes_nothing(host, chain):
    sized = _sized(17, host, chain, FDSDK_SWEEP, (4, chain), capacity=ZERO)
    lines = _builder_pool_text_lines(sized)
    assert (sized["builders"], sized["jobserver"]) == (None, None)
    assert lines[0] == f"Builders: none proposed - {ZERO['verdict']}"
    assert not any(a["proposed"] for a in sized["approaches"])
    assert f"    off: none - {ZERO['verdict']}" in lines
    # Review 2: the rendered rows carry no proposal either, the fat auto row included.
    assert not any("; proposed" in line for line in lines), lines


def test_a_withheld_capacity_falls_back_to_the_knee_and_says_so():
    sized = _sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity={"recommended_builders": None, "withheld": {}})
    assert sized["builders"] == 3
    assert _builder_pool_text_lines(sized)[0].endswith("; builders from the knee, capacity withheld")


def test_a_serial_chain_clamps_max_jobs_to_its_cores():
    assert _sized(17, 4, 1, FDSDK_SWEEP, (4, 8), capacity=3)["max_jobs"] == 4


def test_a_count_past_the_sweep_has_no_replay_wall():
    walls = FAT_WALLS[:32]
    sized = _sized(400, 128, 8, (walls, 32), (64, 8), capacity=32)
    lines = _builder_pool_text_lines(sized)
    assert (_row(sized, "auto")["builders"], _row(sized, "auto")["replay_wall_us"]) == (120, None)
    assert _row(sized, "configured")["replay_wall_us"] is None
    assert lines[0].startswith(
        "Builders: 120 with --jobserver auto - this run's replay stops at 32 builders, so 120 is not swept, its knee at 32;"
    ), lines[0]
    assert any(
        line.startswith("    auto: --builders 120 --max-jobs 8 --jobserver auto - not swept (the replay stops at 32);")
        for line in lines
    )


def test_the_configured_row_keeps_its_jobserver_mode():
    sized = _sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity=3, mode="auto")
    lines = _builder_pool_text_lines(sized)
    assert _row(sized, "configured")["jobserver"] == "auto"
    assert any(line.startswith("    configured: --builders 4 --max-jobs 4 --jobserver auto - 3.0 h;") for line in lines)
    assert not any(line.startswith("    defaults:") and "as this run was configured" in line for line in lines)


def test_an_unrecorded_mode_is_said_and_never_called_off():
    lines = _builder_pool_text_lines(_sized(17, 4, 4, FDSDK_SWEEP, (4, 4), capacity=3, mode=None))
    assert any(
        line.startswith("    configured: --builders 4 --max-jobs 4 - 3.0 h;") and "not recorded" in line
        for line in lines
    )


@pytest.mark.parametrize(
    ("jobserver", "label"),
    [(None, None), ({"mode": "off"}, "off"), ({"mode": "auto"}, "auto"), ({"mode": "n", "ceiling": 6}, "6")],
)
def test_the_capture_mode_is_labelled(jobserver, label):
    assert jobserver_label(jobserver) == label


def test_an_off_headline_past_the_sweep_claims_no_wall_or_gain():
    walls = FAT_WALLS[:32]
    lines = _builder_pool_text_lines(_sized(400, 64, 64, (walls, 32), (64, 64), capacity=48))
    assert lines[0].startswith("Builders: 48 with --jobserver off, max-jobs 64 - a small host"), lines[0]
    assert "this run's replay stops at 32 builders, so 48 is not swept, its knee at 32" in lines[0]
    assert "more builders buy" not in lines[0]
