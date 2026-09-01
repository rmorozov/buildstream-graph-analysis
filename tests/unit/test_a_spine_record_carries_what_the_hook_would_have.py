"""UX-487: the spine's fault and I/O counts, held against the hook's.

`UX-379` gave the hook six `rusage` counters on the argument that they
are "the only measurement bga has of the two axes it otherwise only
models - what a process actually read and wrote, and whether it was
waiting or being preempted". The spine got none of them, and the spine
is the plane that exists for the processes the hook **cannot see**. So
the population Plane 2 is blindest about had no I/O and no faults:
measured on a real mixed capture, 71 of 71 hook records carried
`minflt` and 0 of 87 spine records did.

Two mechanisms, one quantity, and that is what makes this file
possible: the hook reads `getrusage` inside the process and the spine
reads `/proc` from outside it. Where they describe the same counter
they must agree on a real process - and the run below is one workload
under both planes at once, which is the only way to ask.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (  # noqa: E402
    compile_hook, compile_spine, parse_trace_lines, stream_records)

needs_cc = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None,
    reason="no C compiler on PATH")

pytestmark = needs_cc

#: Writes 8 MiB and fsyncs it, so the block-layer counters are non-zero
#: on the process that did it and zero on the shell that spawned it -
#: which is the pair the mis-read below confused.
WORKLOAD = ("dd if=/dev/urandom of={path} bs=1M count=8 2>/dev/null; sync")


def _records(tmp_path, both_planes=True):
    """One workload, traced by the spine and preloaded with the hook."""
    build = tmp_path / "build"
    build.mkdir()
    spine = compile_spine(str(build))
    log = tmp_path / "plane2.log"
    env = dict(os.environ, BST_TRACE_LOG=str(log),
               BST_TRACE_ELEMENT="probe.bst", BST_TRACE_INVOCATION="inv")
    if both_planes:
        env["LD_PRELOAD"] = compile_hook(str(build))
    done = subprocess.run(
        [spine, "--", "sh", "-c",
         WORKLOAD.format(path=tmp_path / "probe.bin")],
        env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr[-400:]
    lines = log.read_text(encoding="utf-8").splitlines()
    return lines, list(stream_records(iter(parse_trace_lines(lines))))


def _ends(lines):
    """`(pid, src)` -> the record line's keys, for the END records."""
    out = {}
    for line in lines:
        if not line.startswith("END"):
            continue
        head = line.split(" cmd=", 1)[0]
        keys = dict(re.findall(r"(\w+)=([^\s]+)", head))
        out[(keys["pid"], keys.get("src", "hook"))] = keys
    return out


@pytest.fixture(scope="module")
def traced(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("both-planes")
    lines, records = _records(tmp)
    return {"lines": lines, "records": records, "ends": _ends(lines)}


class TestTheSpineRecordsWhatItCouldAllAlong:

    def test_every_spine_end_carries_the_fault_counts(self, traced):
        """The gap this item was filed for. `read_cpu_times` had these
        in the buffer it already read and skipped them with `%*u`."""
        spine = [keys for (_pid, src), keys in traced["ends"].items()
                 if src == "spine"]
        assert spine, "the spine wrote no END record at all"
        for keys in spine:
            assert "minflt" in keys and "majflt" in keys, keys

    def test_every_spine_end_carries_the_block_counts(self, traced):
        spine = [keys for (_pid, src), keys in traced["ends"].items()
                 if src == "spine"]
        for keys in spine:
            assert "inblock" in keys and "oublock" in keys, keys


class TestTheTwoMechanismsAgree:
    """The clause that makes the numbers believable rather than merely
    present. `getrusage` from inside the process and `/proc` from
    outside it are independent; on the process that did the work they
    have to produce the same figures."""

    def _worker(self, traced):
        """The pid both planes recorded, that actually wrote."""
        both = {}
        for (pid, src), keys in traced["ends"].items():
            both.setdefault(pid, {})[src] = keys
        did_work = [pid for pid, seen in both.items()
                    if len(seen) == 2 and int(seen["hook"].get("oublock", 0))]
        assert did_work, (
            f"no pid was recorded by both planes with non-zero output "
            f"blocks, so this file is asserting nothing: {both}")
        return both[did_work[0]]

    def test_the_block_counts_are_identical(self, traced):
        seen = self._worker(traced)
        for key in ("inblock", "oublock"):
            assert seen["hook"][key] == seen["spine"][key], (
                f"{key}: hook {seen['hook'][key]}, spine "
                f"{seen['spine'][key]}. `ru_inblock` is "
                f"`read_bytes >> 9` and the spine reads the same "
                f"counter, so a difference is a different quantity")

    def test_the_fault_counts_are_identical(self, traced):
        seen = self._worker(traced)
        for key in ("minflt", "majflt"):
            assert seen["hook"][key] == seen["spine"][key], (
                f"{key}: hook {seen['hook'][key]}, spine "
                f"{seen['spine'][key]}")

    def test_the_shell_that_spawned_it_is_not_charged_for_it(self, traced):
        """The defect the comparison caught before it shipped.
        `/proc/<pid>/io` folds in **reaped children**, the way
        `RUSAGE_CHILDREN` does, so reading it credited a shell that
        wrote nothing with everything its children wrote - measured at
        `oublock=16408` against the worker's 16392 plus `sync`'s 16.
        `/proc/<pid>/task/<pid>/io` is the task's own."""
        worker = self._worker(traced)["spine"]
        parent = worker["ppid"]
        shell = [keys for (pid, src), keys in traced["ends"].items()
                 if src == "spine" and pid == parent]
        assert shell, (
            f"the worker's parent {parent} has no spine record, so this "
            f"clause cannot ask the question it exists for")
        # The shell forked the worker and reaped it. Under
        # `/proc/<pid>/io` it read the worker's blocks plus `sync`'s -
        # 16408 against the worker's own 16392. Under the task's own
        # file it wrote nothing and reads nothing.
        assert int(shell[0]["oublock"]) < int(worker["oublock"]), (
            f"the shell that spawned the worker carries "
            f"oublock={shell[0]['oublock']} against the worker's own "
            f"{worker['oublock']}, so the spine is reading the "
            f"whole-process file - which folds in reaped children - "
            f"rather than /proc/<pid>/task/<pid>/io")


class TestTheParserNeedsNoSecondVocabulary:
    """The reason the spine writes the hook's key names and units: the
    keys flow through `bst_native_build_tracer` unchanged, so a
    spine-only process reaches every reader that already reads a
    hook-recorded one."""

    def test_a_spine_record_reaches_the_parser_with_the_same_fields(
            self, traced):
        spine = [r for r in traced["records"] if r.get("src") == "spine"]
        assert spine, "the parser produced no spine record"
        wrote = [r for r in spine if r.get("written_bytes")]
        assert wrote, (
            f"no spine record reached the parser with written_bytes, so "
            f"the keys are not the ones it converts: "
            f"{sorted(spine[0]) if spine else None}")
        for record in spine:
            assert "minor_faults" in record and "major_faults" in record, (
                sorted(record))

    def test_the_bytes_are_the_blocks_converted_once(self, traced):
        """512-byte blocks in the record, bytes at the parser - the
        conversion `_IO_BLOCK_BYTES` does, applied to the spine's
        figures because they are in the same units."""
        from tools.bst_native_build_tracer import _IO_BLOCK_BYTES

        by_pid = {str(r["pid"]): r for r in traced["records"]
                  if r.get("src") == "spine"}
        for (pid, src), keys in traced["ends"].items():
            if src != "spine" or pid not in by_pid:
                continue
            record = by_pid[pid]
            assert record.get("written_bytes", 0) == (
                int(keys["oublock"]) * _IO_BLOCK_BYTES), (pid, keys, record)
