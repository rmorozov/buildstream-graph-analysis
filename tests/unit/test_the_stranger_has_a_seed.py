"""UX-330: a no-BuildStream newcomer has one command into the whole tool.

Three walk frictions with one root. The example `.bga` stores are empty
scaffolds - a `.gitignore` and a `tmp/` - so every store command
dead-ended in *"take a snapshot"*, with the one command that cannot run
without `bst`. The only real run data sat in a fixtures directory named
by `real-project.md`'s **appendix**. And nothing committed anywhere
could feed `bga timeline`, so *"one trace, both planes"* was a claim a
stranger had no way to check.

So `bga gen-synthetic --store` plants a whole store, and this walks it
the way the README says to. Every clause below is a command a reader
types; the point is not that the code paths work - other files guard
those - but that they work **on what the seed produced**, which is a
different question and the one that was failing.

**Two defects the walk found on the way**, both fixed here and both
recorded because a seed that quietly needed a patched tool would be no
seed at all:

- the first draft wrote Plane 2 records with `element=` before `ts=`.
  The parser reads `pid`/`ppid`/`ts` positionally and drops any line
  that does not open with them, so the log read correctly and parsed to
  **nothing** - a timeline with one plane in it and no error.
- the first draft wrote one cache key (`aaaaaaaa`) for every element.
  The wrapped-log parser keys a task's span on that bracket, so
  fourteen elements collapsed into **three** spans.

Neither is a defect in `bga`; both are the seed being wrong in a way
only a walk could see.
"""
import gzip
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def _bga(*argv, cwd=None, expect=0):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", *argv],
        capture_output=True, text=True, cwd=str(cwd or REPO), timeout=300,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    if expect is not None:
        assert done.returncode == expect, (argv, done.returncode,
                                           done.stdout[-1500:],
                                           done.stderr[-1500:])
    return done


@pytest.fixture(scope="module")
def seed(tmp_path_factory):
    """The seed, planted by the command the README prints."""
    root = tmp_path_factory.mktemp("seed") / "demo"
    _bga("gen-synthetic", "--store", str(root))
    return root


class TestTheSeedIsAStore:
    def test_it_plants_a_project_root_so_the_aliases_resolve(self, seed):
        """Store resolution walks up for `project.conf` (`UX-127`). No
        marker, no `@last`, and the seed would be a directory of files
        rather than a store."""
        assert (seed / "project.conf").is_file()
        assert (seed / ".bga" / "runs").is_dir()

    def test_it_plants_more_than_one_run(self, seed):
        """One snapshot makes `@prev`, `compare` and the trend all
        refuse - which is the dead end this item is about, one step
        further along."""
        runs = sorted(p.name for p in (seed / ".bga" / "runs").iterdir())
        assert len(runs) >= 2, runs
        assert runs == sorted(runs), "stamps do not sort in time order"

    def test_every_snapshot_carries_both_planes_and_the_wrapped_log(self, seed):
        for snapshot in (seed / ".bga" / "runs").iterdir():
            assert (snapshot / "build.log").is_file(), snapshot
            assert (snapshot / "plane2.log.gz").is_file(), snapshot
            for name in ("graph.json", "trace.json", "run-context.json",
                         "sources.json"):
                assert (snapshot / "run" / name).is_file(), (snapshot, name)

    def test_the_plane_2_log_parses_to_records(self, seed):
        """The defect the first draft had. A log that *reads* right and
        parses to zero records is the failure mode a shape check misses,
        so this asks the real parser."""
        sys.path.insert(0, str(REPO))
        from tools.bst_native_build_tracer import (parse_trace_lines,
                                                   stream_records)

        newest = sorted((seed / ".bga" / "runs").iterdir())[-1]
        with gzip.open(newest / "plane2.log.gz", "rt") as handle:
            records = list(stream_records(iter(parse_trace_lines(handle))))
        assert len(records) >= 10, (
            "the seed's Plane 2 log parses to almost nothing - check the "
            "`pid`/`ppid`/`ts` field order", len(records))
        assert all(r.get("element") for r in records), (
            "a record carries no element, so the two planes cannot align")

    def test_the_wrapped_log_gives_every_element_its_own_span(self, seed):
        """The second defect the first draft had: one cache key for all
        of them, and fourteen elements became three spans."""
        newest = sorted((seed / ".bga" / "runs").iterdir())[-1]
        graph = json.loads(
            (newest / "run" / "graph.json").read_text(encoding="utf-8"))
        log = (newest / "build.log").read_text(encoding="utf-8")
        keys = set(re.findall(r"\]\[([0-9a-f]{8})\]\[\s*build:", log))
        assert len(keys) == len(graph["elements"]), (
            "the wrapped log does not give each element its own cache "
            "key, so their spans collapse into one another",
            len(keys), len(graph["elements"]))


class TestTheWalkTheReadmePromises:
    """Each command the seed's own closing message tells a reader to
    run, run against what it planted."""

    def test_the_store_lists_its_runs(self, seed):
        done = _bga("snapshot", "--list", cwd=seed)
        assert "@last" in done.stdout and "@prev" in done.stdout, done.stdout

    def test_analyze_answers_on_the_alias(self, seed):
        done = _bga("analyze", "@last", cwd=seed)
        assert "Build Efficiency Report" in done.stdout
        assert "Critical Path Length" in done.stdout

    def test_compare_has_two_runs_to_compare(self, seed):
        """And something to say about them: the seed makes the second
        run's slowest element slower on purpose, because a store whose
        two runs are identical makes `compare` correct and useless."""
        done = _bga("compare", "@prev", "@last", cwd=seed)
        assert "Run Comparison" in done.stdout, done.stdout

    def test_blast_resolves_the_shared_source(self, seed):
        """`UX-171`'s inventory, seeded - without it `blast` says "this
        run carries no source inventory" and the reader is back at a
        dead end."""
        done = _bga("blast", "https://example.invalid/shared-toolchain.git",
                    "@last", cwd=seed)
        assert "Sourced directly by" in done.stdout, done.stdout
        assert "Nothing matched" not in done.stdout, done.stdout

    def test_the_timeline_renders_both_planes(self, seed, tmp_path):
        """`UX-188`'s "one trace, both planes", which no committed
        artifact could exercise before this item."""
        out = tmp_path / "timeline.pftrace.gz"
        done = _bga("timeline", "@last", "-o", str(out), cwd=seed)
        report = json.loads(done.stdout.strip().splitlines()[-1])
        assert report["planes"] == ["1", "2"], (
            "the seed's timeline is not both planes", report)
        assert report["anchor"], "the two planes did not align on an element"
        assert report["slices"] > 10, report

    def test_the_export_is_a_page(self, seed, tmp_path):
        out = tmp_path / "report.html"
        done = _bga("view", "@last", "--export", str(out), cwd=seed)
        report = json.loads(done.stdout.strip().splitlines()[-1])
        assert report["has_timeline"] is True, report
        assert out.stat().st_size > 100_000

    def test_capture_report_reads_the_seed_s_own_plane_2_log(self, seed):
        """The third friction, and the one that reproduced on the
        *committed* capture too - see the class below."""
        newest = sorted((seed / ".bga" / "runs").iterdir())[-1]
        done = _bga("capture", "report", str(newest / "plane2.log.gz"),
                    cwd=seed)
        assert "Native Build Trace" in done.stdout, done.stdout


class TestTheMissingLogNamesItsOwnCause:
    """`bga timeline` had one explanation for three situations.

    ```text
    <path>: no build.log here. `bga timeline` renders a snapshot
    directory (the one `bga snapshot` created), not a run directory -
    try its parent.
    ```

    That is right for exactly one of them. Pointed at a snapshot that
    kept no wrapped log - a generated store, an import, a capture taken
    without the wrapper - it sent the reader **up a directory**, to a
    place with no snapshot in it, and the real cause was never named.
    Which is how `UX-330`'s own seed work hit it: the first `--store`
    draft had no `build.log`, and the tool advised the one thing that
    could not help.
    """

    def test_a_run_directory_is_told_to_try_its_parent(self):
        """The case the old message was written for, kept."""
        done = _bga("timeline", "tests/fixtures/golden/mixed_task_kinds",
                    "-o", os.devnull, expect=None)
        assert done.returncode != 0
        assert "run* directory" in done.stderr, done.stderr
        assert "try " in done.stderr

    def test_a_snapshot_with_no_log_is_told_that_instead(self, tmp_path):
        """The case it got wrong. A directory with a `run/` in it is a
        snapshot; telling its reader to look at the parent is advice
        that cannot work."""
        snapshot = tmp_path / "20260101T000000Z"
        (snapshot / "run").mkdir(parents=True)
        done = _bga("timeline", str(snapshot), "-o", os.devnull, expect=None)
        assert done.returncode != 0
        assert "this capture kept none" in done.stderr, done.stderr
        assert "try its parent" not in done.stderr, (
            "still sending the reader up a directory from a snapshot",
            done.stderr)

    def test_neither_shape_says_so(self, tmp_path):
        empty = tmp_path / "not-a-capture"
        empty.mkdir()
        done = _bga("timeline", str(empty), "-o", os.devnull, expect=None)
        assert done.returncode != 0
        assert "neither a snapshot directory nor a run directory" in \
            done.stderr, done.stderr

    def test_the_three_messages_are_actually_different(self, tmp_path):
        """The positive control. Three branches that produced one
        sentence would pass every clause above that only looks for a
        substring in its own case."""
        snapshot = tmp_path / "20260101T000000Z"
        (snapshot / "run").mkdir(parents=True)
        empty = tmp_path / "nothing"
        empty.mkdir()
        said = {
            _bga("timeline", target, "-o", os.devnull,
                 expect=None).stderr.strip()
            for target in ("tests/fixtures/golden/mixed_task_kinds",
                           str(snapshot), str(empty))}
        assert len(said) == 3, ("two of the three cases print the same "
                                "sentence", said)


class TestAGzippedRawLogIsARawLog:
    """`bga capture report` said a compressed trace was **neither** a
    trace nor a report.

    **A correction, and the reason CI caught it and this container did
    not.** The first draft of this class called `examples/06`'s capture
    "the committed capture". It is not committed - `UX-189` keeps the
    capture archive out of a clone deliberately, and this container has
    it only because earlier work fetched it. The skip census
    (`UX-235`) is what said so, by refusing a skip reason nobody had
    declared. The claim is corrected here, in the task file and in the
    architecture's own words: what a clone has is the seed.

    Every snapshot stores its Plane 2 log as `plane2.log.gz` - the
    capture writes it compressed, and `timeline` and `correlate` both
    read it that way. `report` opened it as text, found nothing
    parseable in the deflate stream, and printed:

    ```text
    ...no trace events could be parsed from this file. `report` expects
    a raw trace log... this error means the file is neither.
    ```

    It is a raw trace. It is gzipped. The one thing the message named is
    the one thing that was not wrong with it.
    """

    #: `examples/06`'s real capture. **Not in a clone** - `UX-189`
    #: keeps the capture archive out of one on purpose, and CI runs
    #: without it, so these two clauses declare their absence through
    #: the reason `tests/conftest.py` already knows rather than
    #: inventing one. The seed's own log is guarded above and is
    #: present everywhere, so the fix is never unguarded; what these
    #: add is the same answer on a capture nobody wrote for this test.
    REAL = REPO / ("examples/06-macro-micro-optimization/.bga/runs/"
                   "20260821T170127Z/plane2.log.gz")
    ABSENT = "the example capture is not in this clone (UX-189)"

    @pytest.mark.skipif(not REAL.exists(), reason=ABSENT)
    def test_the_real_gzipped_log_renders(self):
        done = _bga("capture", "report", str(self.REAL))
        assert "Native Build Trace" in done.stdout
        assert "813" in done.stdout, "the process count moved"

    def test_the_same_log_uncompressed_gives_the_same_answer(self, tmp_path):
        """Detected by magic number rather than extension: a reader who
        renamed the file should not get a different answer."""
        if not self.REAL.exists():
            pytest.skip(self.ABSENT)
        plain = tmp_path / "plane2.log"
        plain.write_bytes(gzip.open(self.REAL, "rb").read())
        renamed = tmp_path / "still-gzipped.log"
        renamed.write_bytes(self.REAL.read_bytes())
        first = _bga("capture", "report", str(plain)).stdout
        second = _bga("capture", "report", str(renamed)).stdout
        assert first.splitlines()[3] == second.splitlines()[3], (
            first.splitlines()[3], second.splitlines()[3])

    def test_the_seed_covers_this_where_the_capture_does_not(self, seed):
        """The clause that runs everywhere, so the two above skipping in
        a clone leaves nothing unguarded. `UX-330`'s seed writes its
        Plane 2 log gzipped exactly as a capture does."""
        newest = sorted((seed / ".bga" / "runs").iterdir())[-1]
        log = newest / "plane2.log.gz"
        assert log.read_bytes()[:2] == b"\x1f\x8b", "the seed's log is not gzipped"
        done = _bga("capture", "report", str(log))
        assert "Native Build Trace" in done.stdout, done.stdout


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
