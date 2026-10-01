"""UX-1205: a real capture of `UX-1182`'s fake binaries counts what the plan says.

The plan is `workload_plan`, the one the synthetic `--workload binaries`
records are drawn from, at test size: one element of 200 distinct
binaries, two of 3-10, 1-3 calls each. The bst half builds it under the
LD_PRELOAD hook in CI's `bst-tests` job; the rest runs anywhere.
"""

import collections
import os
import pathlib
import random
import shutil
import subprocess
from datetime import datetime, timezone

import pytest
import yaml

from tools import bga_gen_project as gen
from tools import gen_synthetic_scale_run as synth

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLCHAIN = REPO / "examples/05-cmake-cpp-toolchain/files/toolchain"
HEAVY, LIGHT = "w-heavy.bst", ("w-light-a.bst", "w-light-b.bst")
SLEEP = shutil.which("sleep") or "/usr/bin/sleep"


def _plan():
    building = [HEAVY, *LIGHT]
    return synth.workload_plan(random.Random("UX-1205"), building, {HEAVY}, spans=((200, 200), (3, 10)))


def test_the_plan_has_the_test_size_shape():
    calls = synth.workload_calls(_plan())
    assert len(calls[HEAVY]) == 200
    assert all(3 <= len(calls[uid]) <= 10 for uid in LIGHT)
    assert {n for per in calls.values() for n in per.values()} <= {1, 2, 3}


def test_the_synthetic_records_are_the_plans_calls():
    """`_workload_records` reads `workload_plan`: same rng, same calls per element per binary."""
    elements = [{"uid": f"e{i}.bst", "element_kind": "manual"} for i in range(10)]
    durations = {e["uid"]: 60_000_000 + i for i, e in enumerate(elements)}
    placement = {uid: (0, durations[uid]) for uid in durations}
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    text = synth._workload_records(placement, durations, started, elements, random.Random(7))
    counted = collections.defaultdict(collections.Counter)
    for line in text.splitlines():
        fields = dict(f.split("=", 1) for f in line.split(" cmd=")[0].split()[1:])
        cmd = line.split(" cmd=", 1)[1]
        if line.startswith("START") and cmd.startswith("/opt/fakebin/"):
            counted[fields["element"]][cmd.split()[0].rsplit("/", 1)[1]] += 1
    heavy = {e["uid"] for e in elements[-8:]}
    plan = synth.workload_plan(random.Random(7), sorted(durations), heavy)
    assert {uid: dict(c) for uid, c in counted.items()} == synth.workload_calls(plan)


def test_a_static_binary_is_refused(tmp_path):
    """The hook does not load into a static binary; a project built of one would capture nothing."""
    static = tmp_path / "static"
    static.write_bytes(b"\x7fELF\x02" + b"\0" * 59)
    with pytest.raises(gen.SpecError, match="not a dynamic ELF"):
        gen.write_workload_project({HEAVY: {"a": 1}}, tmp_path / "p", tmp_path / "toolchain", static)


def test_the_written_project_execs_each_planned_call(tmp_path):
    """The YAML parses, and its commands, run against counting stand-ins, exec the plan's calls exactly."""
    calls = synth.workload_calls(_plan())
    toolchain = tmp_path / "toolchain"
    (toolchain / "usr/bin").mkdir(parents=True)
    project = gen.write_workload_project(calls, tmp_path / "project", toolchain, SLEEP)
    assert len(list((project / "files/fakebin/opt/fakebin").iterdir())) == len({b for p in calls.values() for b in p})
    stand_ins = tmp_path / "bin"
    stand_ins.mkdir()
    log = tmp_path / "calls.log"
    for binary in {b for per in calls.values() for b in per}:
        script = stand_ins / binary
        script.write_text(f'#!/bin/sh\necho "$ELEMENT $(basename "$0")" >> {log}\n', encoding="utf-8")
        script.chmod(0o755)
    for uid in calls:
        element = yaml.safe_load((project / "elements" / uid).read_text(encoding="utf-8"))
        assert [d["filename"] for d in element["depends"]] == ["toolchain.bst", "fakebin.bst"]
        (command,) = element["config"]["install-commands"]
        subprocess.run(
            ["sh", "-e", "-c", command.replace(gen.FAKEBIN, str(stand_ins))],
            check=True,
            env={**os.environ, "ELEMENT": uid},
        )
    counted = collections.defaultdict(collections.Counter)
    for line in log.read_text(encoding="utf-8").splitlines():
        uid, binary = line.split()
        counted[uid][binary] += 1
    assert {uid: dict(c) for uid, c in counted.items()} == calls
    target = yaml.safe_load((project / "elements/all.bst").read_text(encoding="utf-8"))
    assert sorted(target["depends"]) == sorted(calls)


@pytest.mark.bst
@pytest.mark.skipif(
    not (shutil.which("bst") and shutil.which("bwrap") and (shutil.which("cc") or shutil.which("gcc"))),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_a_real_capture_counts_every_planned_call(tmp_path):
    """Plane 2's records per element per binary equal the plan's calls; the heavy element shows 200 binaries."""
    if not (TOOLCHAIN / "usr/bin").is_dir():
        pytest.skip("examples/05-cmake-cpp-toolchain's toolchain isn't staged - run stage_cpp_toolchain.sh first")
    from tests.unit._bst_env import bst_env
    from tools.bst_native_build_tracer import pair_events, parse_trace_log, run_traced_build

    calls = synth.workload_calls(_plan())
    project = gen.write_workload_project(calls, tmp_path / "project", TOOLCHAIN, SLEEP)
    raw_log = tmp_path / "raw.log"
    with bst_env(tmp_path / "home"):
        returncode = run_traced_build(str(project), ["bst", "--no-colors", "build", "all.bst"], str(raw_log))
    assert returncode == 0
    records = pair_events(parse_trace_log(raw_log.read_text(encoding="utf-8")))
    counted = collections.defaultdict(collections.Counter)
    for record in records:
        argv0 = (record.get("cmd") or "").split(" ")[0]
        if argv0.startswith(gen.FAKEBIN + "/"):
            counted[record["element"]][argv0.rsplit("/", 1)[1]] += 1
    assert len(counted[HEAVY]) >= 200, f"the hook saw {len(counted[HEAVY])} distinct binaries in {HEAVY}"
    assert {uid: dict(c) for uid, c in counted.items()} == calls
