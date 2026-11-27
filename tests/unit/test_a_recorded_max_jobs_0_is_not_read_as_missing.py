"""UX-1396: a recorded `--max-jobs 0` is BuildStream's automatic `min(cores, 8)`, not a missing value."""

import subprocess
import sys

import pytest

from bga.floors.cpu import effective_max_jobs
from bga.tools_dispatch import _import_tool
from bga.utilisation import envelope
from tests.fixtures.topologies import _build, _dependency, _element, _span, write_run_dir
from tests.unit.test_the_cores_were_or_were_not_binding import FIXTURE

S = 1_000_000


@pytest.mark.parametrize(
    ("jobs", "cores", "width"),
    [(None, 16, None), (0, 16, 8), (0, 4, 4), (0, None, None), (3, 16, 3), (1, 4, 1)],
)
def test_a_recorded_zero_is_the_automatic_width_and_none_stays_unrecorded(jobs, cores, width):
    assert effective_max_jobs(jobs, cores) == width


def _envelope(native_max_jobs, cores=64, builders=2):
    read = _import_tool("tools.bst_native_build_tracer").read_host_samples(str(FIXTURE / "host-samples.jsonl"))
    read["samples"] = [dict(sample, cores=cores) for sample in read["samples"]]
    tasks = [{"element": "a.bst", "start_us": 0, "finish_us": 10 * S, "ready_us": 0}]
    run = {"builders": builders, "native_max_jobs": native_max_jobs, "tasks": tasks, "max_jobs": {}, "successors": {}}
    return envelope.compute(read, run)["envelope"]


def test_the_envelope_caps_a_zero_max_jobs_at_the_automatic_width():
    section = _envelope(0)
    assert (section["configured_capacity_cores"], section["capacity_cores"]) == (16, 16)


def test_the_envelope_keeps_an_unrecorded_max_jobs_unrecorded():
    section = _envelope(None)
    assert (section["configured_capacity_cores"], section["capacity_cores"]) == (None, 64)


def _auto_run(host_cpu_count, per_element=False):
    """A base and four dependents: `native_max_jobs: 0`, or no native value and `max_jobs: 0` on every element."""
    leaves = [f"leaf{i}.bst" for i in range(4)]
    elements = [_element("base.bst")] + [_element(uid, requested_target=True) for uid in leaves]
    if per_element:
        elements = [dict(element, max_jobs=0) for element in elements]
    dependencies = [_dependency("base.bst", uid) for uid in leaves]
    spans = [_span("base.bst", 0, 10 * S)] + [_span(uid, 10 * S, 60 * S) for uid in leaves]
    run_context, graph, trace = _build(elements, dependencies, spans, wall_end_us=70 * S, max_jobs=4)
    return dict(run_context, host_cpu_count=host_cpu_count, native_max_jobs=None if per_element else 0), graph, trace


@pytest.mark.parametrize("per_element", [False, True])
@pytest.mark.parametrize(
    ("host", "mode", "reading"), [(4, "off", "a small host"), (16, "auto", "critical path's max-jobs=8")]
)
def test_the_builders_line_sizes_a_zero_max_jobs_chain_by_its_automatic_width(
    tmp_path, host, mode, reading, per_element
):
    run_dir = write_run_dir(tmp_path, _auto_run(host, per_element))
    out = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run_dir)], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    line = next(line for line in out if line.startswith("Builders"))
    assert f"with --jobserver {mode}" in line and reading in line, line
    assert any(f"Approaches sized for {host} cores" in line for line in out), out
