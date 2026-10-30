"""UX-1363: the builders line cites this run's own sweep, and never goes under its knee on another fixture's word.

fdsdk printed "Builders: 1 ... (13-mixed-graph, 16 cores: 143.6s -> 118.3s)" while its own sweep read
21330 s at 1 builder against 13607 s at the knee, 3.
"""

import re
import subprocess
import sys

from bga.cli import _builder_pool_text_lines
from bga.correlate import compute_builder_pool_recommendation, with_own_sweep
from tests.fixtures.topologies import _build, _dependency, _element, _span, write_run_dir

S = 1_000_000
FDSDK_SWEEP = ([21_330_500_000, 14_641_100_000, 13_606_900_000, 13_267_100_000], 3)


def _line(recommendation):
    return _builder_pool_text_lines(recommendation)[0]


def test_the_line_recommends_this_runs_knee_over_the_safe_cap_and_cites_its_replay():
    line = _line(with_own_sweep(compute_builder_pool_recommendation(17, 4, 4), FDSDK_SWEEP))
    assert line.startswith("Builders: 3 with --jobserver auto - this run's replay puts 3 at 3.8 h against 5.9 h at 1")
    assert "is 1, a rule read on another fixture (13-mixed-graph" in line


def test_a_safe_cap_above_the_knee_still_cites_this_run():
    line = _line(with_own_sweep(compute_builder_pool_recommendation(17, 16, 4), FDSDK_SWEEP))
    assert line.startswith("Builders: 12 with --jobserver auto - this run's replay puts 12 at 3.7 h")


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


def test_analyze_on_a_run_never_recommends_fewer_builders_than_its_knee(tmp_path):
    run_dir = write_run_dir(tmp_path, _four_wide())
    out = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run_dir)], capture_output=True, text=True, check=True
    ).stdout
    line = next(line for line in out.splitlines() if line.startswith("Builders"))
    builders = int(re.match(r"Builders: (\d+) ", line).group(1))
    assert builders >= 4, line
    assert "this run's replay puts 4 at 70.0 s against 4.2 min at 1, its knee at 4" in line
