"""UX-168: capacity, and the six one-liners that trailed round 17.

The headline is memory: the trace parse used to hold the whole log as
one string beside the event list it produced. The rest is the census's
own time, the store's repeated stat-walk, and five small edges the
round-17 review listed by line number.

Every measurement quoted here was taken on this repo's own machine and
is reproduced by the test that quotes it; the numbers in the assertions
are deliberately loose, because the point of the guard is the *shape*
(streaming beats slurping, memo beats re-walking), not a byte count
that would go red on a faster disk.
"""
import json
import os
import re
import struct
import subprocess
import sys
import textwrap
import time

import pytest

from bga import run_store
from tools import bst_native_build_tracer as tracer
from tools.native_trace import bwrap_shim

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _static_elf(path):
    """A structurally real, statically-linked ELF executable.

    Same hand-built header as `tests/unit/test_static_census.py` uses,
    for the same reason: a checked-in binary would make this a test
    about one machine's `/bin`.
    """
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2  # 64-bit
    header[5] = 1  # little-endian
    struct.pack_into("<H", header, 16, 2)  # ET_EXEC
    struct.pack_into("<Q", header, 32, 64)  # e_phoff
    struct.pack_into("<HH", header, 54, 56, 1)  # e_phentsize, e_phnum
    program_header = bytearray(56)
    struct.pack_into("<I", program_header, 0, 1)  # PT_LOAD, i.e. no PT_INTERP
    path.write_bytes(bytes(header) + bytes(program_header))
    path.chmod(0o755)
    return path


def _write_trace(path, events):
    with open(path, "w", encoding="utf-8") as handle:
        for i in range(events):
            handle.write(
                f"START pid={1000 + i} ppid={1000 + i // 2} ts={1000000 + i} "
                f"element=core.bst cmd=/usr/bin/cc -c file{i}.c -o file{i}.o\n"
            )
            handle.write(f"END pid={1000 + i} ts={1000100 + i}\n")


def _peak_mb(source, *args):
    """Run `source` in a fresh interpreter and report its allocation peak.

    `tracemalloc`, not `ru_maxrss`. Linux does not reset the resident
    high-water mark across `exec`, so a child forked from a pytest
    process that has already peaked at 300 MB reports *that* number and
    the comparison silently becomes 300 == 300. Found the honest way:
    this test passed alone and failed in the full suite, with both sides
    reading 298.52734375 MB exactly.
    """
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source), *args],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


class TestTheTraceParseStreams:
    """The reader, not the format (UX-168's Out of Scope says so)."""

    def test_a_file_handle_costs_less_than_the_same_bytes_as_a_string(self, tmp_path):
        """A measurement, not a mutation guard.

        It states the price of the string the caller used to build, and
        it holds by construction: whatever `parse_trace_lines` costs,
        the slurping side pays it *plus* the file. The guard that a
        revert reddens is the next test; this one is here so the number
        UX-168 claims is reproduced rather than quoted.
        """
        # 120k events is ~17 MB - large enough for the difference to be
        # unmistakable, small enough to parse in a couple of seconds.
        log = tmp_path / "trace.log"
        _write_trace(str(log), 120_000)
        size_mb = os.path.getsize(log) / 1024 ** 2

        streaming = _peak_mb('''
            import json, sys, tracemalloc
            from tools.bst_native_build_tracer import parse_trace_lines
            tracemalloc.start()
            with open(sys.argv[1]) as handle:
                events = parse_trace_lines(handle)
            assert len(events) == 120_000, len(events)
            print(json.dumps(tracemalloc.get_traced_memory()[1] / 1024 ** 2))
        ''', str(log))
        slurping = _peak_mb('''
            import json, sys, tracemalloc
            from tools.bst_native_build_tracer import parse_trace_log
            tracemalloc.start()
            text = open(sys.argv[1]).read()
            events = parse_trace_log(text)
            assert len(events) == 120_000, len(events)
            print(json.dumps(tracemalloc.get_traced_memory()[1] / 1024 ** 2))
        ''', str(log))

        # Measured on the development machine at 400k events / 56 MB:
        # 215 MB streaming against 365 MB slurped (tracemalloc; 243 vs
        # 395 by RSS). The guard asks only that the whole file is not
        # being held twice over - one file's worth of headroom, which a
        # `read()` cannot satisfy.
        assert streaming + size_mb < slurping, (
            f"streaming peak {streaming:.0f} MB vs slurped {slurping:.0f} MB "
            f"on a {size_mb:.0f} MB log - the string copy is back"
        )

    def test_the_report_path_itself_never_builds_that_string(self, tmp_path, monkeypatch):
        """The guard where the fix lives.

        `parse_trace_log` is still exported and still correct; what UX-168
        changed is that `load_and_summarize` stopped going through it.
        Making it fatal proves the caller streams, which a test that only
        exercised `parse_trace_lines` directly would not.
        """
        def refuse(_text):
            raise AssertionError("load_and_summarize read the whole trace into a string")

        monkeypatch.setattr(tracer, "parse_trace_log", refuse)
        log = tmp_path / "trace.log"
        _write_trace(str(log), 50)
        report = tracer.load_and_summarize(str(log))
        assert report["process_count"] == 50


class TestTheCensusReadsEachElementOnce:
    def _project(self, tmp_path, count, fan_in=5):
        project = tmp_path / "proj"
        (project / "elements").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: censusscale\nmin-version: 2.0\nelement-path: elements\n"
        )
        for i in range(count):
            body = ["kind: manual"]
            deps = [f"e{j:04d}.bst" for j in range(max(0, i - fan_in), i)]
            if deps:
                body.append("depends:")
                body.extend(f"- filename: {d}\n  type: build" for d in deps)
            (project / "elements" / f"e{i:04d}.bst").write_text("\n".join(body) + "\n")
        return str(project)

    def test_one_parse_per_element_not_two(self, tmp_path, monkeypatch):
        """UX-168: the dependency read and the source read are one read.

        This is the whole of the census's cost - 5.0s of its 5.9s under
        cProfile on 1,000 elements was inside PyYAML.
        """
        import yaml

        project = self._project(tmp_path, 40)
        tracer._ELEMENT_YAML_CACHE.clear()
        parsed = []
        real_load = yaml.load

        def counting_load(stream, *args, **kwargs):
            parsed.append(getattr(stream, "name", "?"))
            return real_load(stream, *args, **kwargs)

        monkeypatch.setattr(yaml, "load", counting_load)
        tracer.census_project(project, tracer.discover_element_names(project))
        assert len(parsed) == len(set(parsed)) == 40, (
            f"{len(parsed)} parses for {len(set(parsed))} distinct element files"
        )

    def test_an_edited_element_is_re_read_not_remembered(self, tmp_path):
        project = self._project(tmp_path, 3)
        tracer._ELEMENT_YAML_CACHE.clear()
        elements = tracer.discover_element_names(project)
        first = tracer.read_declared_build_deps(project, elements)
        assert first["e0002.bst"] == ["e0000.bst", "e0001.bst"]

        path = os.path.join(project, "elements", "e0002.bst")
        os.utime(path, (0, 0))  # force a distinct mtime from the write below
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("kind: manual\ndepends:\n- filename: e0000.bst\n  type: build\n")
        again = tracer.read_declared_build_deps(project, elements)
        assert again["e0002.bst"] == ["e0000.bst"], "the memo outlived its file"

    def test_a_thousand_elements_is_seconds_not_minutes(self, tmp_path):
        """UX-168's acceptance bound, kept deliberately generous.

        Measured here: 2.04s before the memo, 1.19s after, for 1,000
        elements each depending on the previous five. The bound is 30s
        because CI is slower than this machine and the claim being
        guarded is "not minutes".
        """
        project = self._project(tmp_path, 1000)
        tracer._ELEMENT_YAML_CACHE.clear()
        started = time.perf_counter()
        census = tracer.census_project(project, tracer.discover_element_names(project))
        elapsed = time.perf_counter() - started
        assert len(census["per_element"]) == 1000
        assert elapsed < 30, f"census took {elapsed:.1f}s on 1,000 elements"


class TestTheClosureMemoIsStillCorrect:
    """A memo that is fast and wrong is worse than the walk it replaced."""

    def _project(self, tmp_path, graph, static_in=()):
        """A project where `static_in` elements stage a static binary.

        The binary matters: without something for the closure to
        propagate, every element's answer is zero and a closure that
        returned nothing at all would pass.
        """
        project = tmp_path / "proj"
        (project / "elements").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: closure\nmin-version: 2.0\nelement-path: elements\n"
        )
        for name, deps in graph.items():
            body = ["kind: manual"]
            if name in static_in:
                stem = name.replace(".bst", "")
                staged = project / "files" / stem / "bin"
                staged.mkdir(parents=True)
                _static_elf(staged / "busybox")
                body.append(f"sources:\n- kind: local\n  path: files/{stem}")
            if deps:
                body.append("depends:")
                body.extend(f"- filename: {d}\n  type: build" for d in deps)
            (project / "elements" / name).write_text("\n".join(body) + "\n")
        return str(project)

    def test_a_diamond_propagates_the_shared_dependency_to_the_top(self, tmp_path):
        project = self._project(tmp_path, {
            "base.bst": [],
            "left.bst": ["base.bst"],
            "right.bst": ["base.bst"],
            "top.bst": ["left.bst", "right.bst"],
        }, static_in={"base.bst"})
        tracer._ELEMENT_YAML_CACHE.clear()
        per_element = tracer.census_project(
            project, sorted(os.listdir(os.path.join(project, "elements")))
        )["per_element"]
        # Reached twice, counted once, and reached at all - which is the
        # memo's whole job.
        assert per_element["top.bst"]["static_count"] == 1
        assert per_element["top.bst"]["own_static"] == []
        assert per_element["base.bst"]["static_count"] == 1

    def test_a_dependency_cycle_does_not_lose_reachable_elements(self, tmp_path):
        """bst rejects cycles; the memo must not corrupt on one anyway.

        A post-order memo would store a half-finished set for whichever
        member it popped first, and `a.bst` would never learn about the
        static binary `c.bst` stages behind `b.bst`. This memo only ever
        stores a *completed* reachable set, so both members see it.
        """
        project = self._project(tmp_path, {
            "a.bst": ["b.bst"],
            "b.bst": ["a.bst", "c.bst"],
            "c.bst": [],
        }, static_in={"c.bst"})
        tracer._ELEMENT_YAML_CACHE.clear()
        elements = sorted(os.listdir(os.path.join(project, "elements")))
        assert tracer.read_declared_build_deps(project, elements)["a.bst"] == ["b.bst"]
        per_element = tracer.census_project(project, elements)["per_element"]
        assert set(per_element) == set(elements)
        assert per_element["a.bst"]["static_count"] == 1, "the cycle swallowed c.bst"
        assert per_element["b.bst"]["static_count"] == 1


class TestTheStoreStopsRewalkingItself:
    def _store(self, tmp_path, snapshots=3, files=20):
        project = tmp_path / "proj"
        for s in range(snapshots):
            logs = project / ".bga" / "runs" / f"2026081{s}T120000Z-000{s}" / "run" / "logs"
            logs.mkdir(parents=True)
            for i in range(files):
                (logs / f"build-{i}.log").write_text("x" * 1000)
        return str(project)

    def test_the_second_answer_costs_no_file_stats(self, tmp_path, monkeypatch):
        project = self._store(tmp_path)
        first = run_store.store_size_bytes(project)
        assert first == 3 * 20 * 1000

        def refuse(path):
            raise AssertionError(f"re-stat of {path} - the memo was not used")

        monkeypatch.setattr(run_store.os.path, "getsize", refuse)
        assert run_store.store_size_bytes(project) == first

    def test_the_memo_is_not_counted_as_capture_output(self, tmp_path):
        project = self._store(tmp_path, snapshots=1, files=3)
        snapshot = run_store.list_snapshots(project)[0]
        assert run_store.snapshot_size_bytes(snapshot) == 3000
        assert os.path.exists(os.path.join(snapshot, run_store.SIZE_CACHE_NAME))
        # Second call: the memo file now exists on disk and must not have
        # made the snapshot look bigger than its own contents.
        assert run_store.snapshot_size_bytes(snapshot) == 3000
        assert run_store.snapshot_size_bytes(snapshot, use_cache=False) == 3000

    def test_a_file_added_deep_in_the_tree_drops_the_memo(self, tmp_path):
        project = self._store(tmp_path, snapshots=1, files=3)
        snapshot = run_store.list_snapshots(project)[0]
        assert run_store.snapshot_size_bytes(snapshot) == 3000
        with open(os.path.join(snapshot, "run", "logs", "late.log"), "w") as handle:
            handle.write("y" * 777)
        assert run_store.snapshot_size_bytes(snapshot) == 3777

    def test_a_store_it_cannot_write_to_still_reports_sizes(self, tmp_path, monkeypatch):
        project = self._store(tmp_path, snapshots=1, files=3)
        snapshot = run_store.list_snapshots(project)[0]
        real_open = open

        def read_only(path, mode="r", *args, **kwargs):
            if "w" in mode and os.path.basename(str(path)) == run_store.SIZE_CACHE_NAME:
                raise OSError(30, "Read-only file system")
            return real_open(path, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", read_only)
        assert run_store.snapshot_size_bytes(snapshot) == 3000
        assert not os.path.exists(os.path.join(snapshot, run_store.SIZE_CACHE_NAME))


class TestTheSixOneLiners:
    def test_1_the_tee_gives_up_on_a_descendant_that_outlives_bwrap(self, tmp_path):
        """A process that daemonizes past bwrap's exit holds the write end.

        Without the read timeout this blocks until that process dies -
        for a real daemon, forever, with the build wedged behind it.
        """
        fake_bwrap = tmp_path / "bwrap"
        fake_bwrap.write_text(textwrap.dedent('''\
            #!/bin/sh
            echo "sandbox said something" >&2
            # A grandchild that keeps stderr open long past this exit.
            sleep 30 &
            exit 3
        '''))
        fake_bwrap.chmod(0o755)
        stderr_path = tmp_path / "invocation.stderr"

        started = time.perf_counter()
        status = bwrap_shim.run_teed(str(fake_bwrap), [str(fake_bwrap)], str(stderr_path))
        elapsed = time.perf_counter() - started

        assert elapsed < 20, f"run_teed waited {elapsed:.1f}s on an orphan holding the pipe"
        assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 3, status
        assert "sandbox said something" in stderr_path.read_text()

    def test_2_a_pre_ux148_record_renders_instead_of_raising(self, tmp_path):
        """The elided branch used to index `row['stderr_path']`."""
        diagnostics = tmp_path / "diagnostics.jsonl"
        stderr_dir = tmp_path / "diagnostics.jsonl.stderr"
        stderr_dir.mkdir()
        (stderr_dir / "4242.stderr").write_text("".join(f"line {i}\n" for i in range(40)))
        row = {"invocation": 7, "pid": 4242, "element": "core.bst"}  # no stderr_path
        diagnostics.write_text(json.dumps(row) + "\n")

        rendered = tracer.format_sandbox_stderr(str(diagnostics))
        assert rendered is not None
        assert "earlier line(s)" in rendered
        assert "core.bst" in rendered

    def test_3_the_self_test_sentinel_is_assigned_once(self):
        source = open(bwrap_shim.__file__, encoding="utf-8").read()
        assignments = [line for line in source.splitlines()
                       if line.startswith("SELF_TEST_ARGV")]
        assert assignments == ['SELF_TEST_ARGV = "--bga-shim-self-test"'], assignments

    def test_4_the_interrupt_notice_points_at_what_comes_after_it(self):
        source = open(tracer.__file__, encoding="utf-8").read()
        # The sentence is split across source lines by the line length,
        # so join adjacent string literals before looking for it - and
        # drop comments, since the one recording this fix quotes the
        # wording it replaced.
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("#"))
        joined = re.sub(r'"\s*\n\s*"', "", code)
        assert "every figure that follows" in joined
        assert "analyzed above" not in joined, (
            "the notice prints before the report it describes"
        )

    def test_5_a_census_with_no_static_binaries_does_not_pose_a_riddle(self, tmp_path):
        project = tmp_path / "proj"
        (project / "elements").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: riddle\nmin-version: 2.0\nelement-path: elements\n"
        )
        (project / "elements" / "only.bst").write_text("kind: manual\n")
        summary = tracer.format_census_coverage(
            str(project), tracer.census_spine_verdicts(str(project))
        )
        assert "the spine is not needed" in summary
        assert "spine traced" not in summary

    def test_6_the_size_warning_walks_the_store_once(self, tmp_path, monkeypatch):
        """Covered by TestTheStoreStopsRewalkingItself; this is the
        end-to-end half - `_warn_if_large` must go through the memo."""
        from tools import bga_snapshot

        project = tmp_path / "proj"
        logs = project / ".bga" / "runs" / "20260819T120000Z-0001" / "run"
        logs.mkdir(parents=True)
        (logs / "big.json").write_text("x" * 4096)
        run_store.store_size_bytes(str(project))

        def refuse(path):
            raise AssertionError(f"re-stat of {path} in the size warning")

        monkeypatch.setattr(run_store.os.path, "getsize", refuse)
        bga_snapshot._warn_if_large(str(project))  # must not raise


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
