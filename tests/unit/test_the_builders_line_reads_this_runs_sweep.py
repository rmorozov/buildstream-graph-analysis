"""UX-1363: the builders line cites this run's own sweep; a knee above the safe cap is a graph-only what-if.

fdsdk printed "Builders: 1 ... (13-mixed-graph, 16 cores: 143.6s -> 118.3s)" while its own sweep read
21330 s at 1 builder against 13607 s at the knee, 3. The replay holds durations fixed, so its knee is no
evidence that --jobserver auto without admission can widen past the cap (review 2).
"""

import re
import subprocess
import sys

from bga.cli import _builder_pool_text_lines
from bga.correlate import compute_builder_pool_recommendation, with_own_sweep
from tests.fixtures.topologies import _build, _dependency, _element, _span, write_run_dir

S = 1_000_000
FDSDK_SWEEP = ([21_330_500_000, 14_641_100_000, 13_606_900_000, 13_267_100_000], 3)


WHAT_IF = (
    "  Graph-only what-if (not a recommendation): the replay, which does not model contention, keeps shortening to"
)


def test_the_line_keeps_the_safe_cap_and_names_this_runs_knee_as_a_graph_only_what_if():
    lines = _builder_pool_text_lines(with_own_sweep(compute_builder_pool_recommendation(17, 4, 4), FDSDK_SWEEP))
    assert lines[0].startswith("Builders: 1 with --jobserver auto - this run's replay puts 1 at 5.9 h;")
    assert "is 1, a rule read on another fixture (13-mixed-graph" in lines[0]
    assert lines[1].startswith(f"{WHAT_IF} 3 builders (3.8 h)")


def test_a_replay_knee_of_32_never_lifts_a_safe_cap_of_8_without_admission():
    walls = [400_000_000 - i * 10_000_000 for i in range(32)] + [80_000_000] * 4
    recommendation = with_own_sweep(compute_builder_pool_recommendation(40, 16, 8), (walls, 32))
    lines = _builder_pool_text_lines(recommendation)
    assert recommendation["builders"] == 8 and recommendation["graph_only_knee"] == 32
    assert lines[0].startswith(
        "Builders: 8 with --jobserver auto - this run's replay puts 8 at 5.5 min against 6.7 min at 1;"
    )
    assert lines[1].startswith(f"{WHAT_IF} 32 builders")
    assert not any(line.startswith("Builders: 32") for line in lines)


def test_a_safe_cap_above_the_knee_still_cites_this_run():
    lines = _builder_pool_text_lines(with_own_sweep(compute_builder_pool_recommendation(17, 16, 4), FDSDK_SWEEP))
    assert lines[0].startswith("Builders: 12 with --jobserver auto - this run's replay puts 12 at 3.7 h")
    assert ", its knee at 3;" in lines[0]
    assert not any("what-if" in line for line in lines)


def test_without_this_runs_sweep_no_builder_count_is_recommended():
    lines = _builder_pool_text_lines(with_own_sweep(compute_builder_pool_recommendation(17, 4, 4), None))
    assert lines[0].startswith("Builders (ready-set width): 17")
    assert not any("13-mixed-graph" in line for line in lines)


def _four_wide():
    """A base and four equal dependents: the replay's knee is 4 builders; 4 cores less max-jobs 4 is a cap of 1."""
    leaves = [f"leaf{i}.bst" for i in range(4)]
    elements = [dict(_element("base.bst"), max_jobs=4)]
    elements += [dict(_element(uid, requested_target=True), max_jobs=4) for uid in leaves]
    dependencies = [_dependency("base.bst", uid) for uid in leaves]
    spans = [_span("base.bst", 0, 10 * S)] + [_span(uid, 10 * S, 60 * S) for uid in leaves]
    run_context, graph, trace = _build(elements, dependencies, spans, wall_end_us=70 * S, max_jobs=4)
    return dict(run_context, host_cpu_count=4, native_max_jobs=4), graph, trace


def test_analyze_on_a_run_keeps_the_safe_cap_and_names_its_knee_as_a_what_if(tmp_path):
    run_dir = write_run_dir(tmp_path, _four_wide())
    out = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run_dir)], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    at = next(index for index, line in enumerate(out) if line.startswith("Builders"))
    assert int(re.match(r"Builders: (\d+) ", out[at]).group(1)) == 1, out[at]
    assert "this run's replay puts 1 at 4.2 min;" in out[at]
    assert out[at + 1].startswith(f"{WHAT_IF} 4 builders (70.0 s)")
