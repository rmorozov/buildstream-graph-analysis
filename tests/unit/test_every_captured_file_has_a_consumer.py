"""UX-437: the host series reaches a destination, and every captured
file has a reader that opens it.

Two halves of one item, because the second is what would have caught
the first eight rounds earlier.

**The series.** `bga snapshot` has sampled the host every two seconds
since `UX-378` and written `host-samples.jsonl` beside the run.
`read_host_samples()` was called by its own test and by nothing else -
no page, no query, no terminal line. `UX-437` sends it to the trace as
counter tracks on the Plane 1 lane, which is the destination a time
series wants: it is the one surface with the build's own time axis.

**The census.** Nothing standing asked "does this captured file have a
reader". The instrument here is a *runtime* one and deliberately not a
text scan for the file name - the repository has ~30 sightings of an
instrument that reads a proxy, and "the string `host-samples.jsonl`
appears in a module" is exactly that: it cannot tell a reader from a
writer, from a constant, from a comment. So `builtins.open` is wrapped
while the readers run over a complete capture, and the question is
answered by what was actually opened.

The census found a second file with no reader on its first run -
`run/chrome_trace.json`, which the capture layout's own row already
half-admits ("nothing on a read path requires this"). It is declared
below against `UX-452` rather than deleted here.
"""
import builtins
import contextlib
import gzip
import io
import json
import os
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_the_counter_the_constant_was_waiting_for import decode

from bga import run_store
from tools.bga_timeline import HOST_COUNTERS, HOST_SAMPLES_NAME, render

#: The committed fixture `UX-358` built so a timeline could be rendered
#: without a real capture. Its `build.log` carries the `bga-clocks`
#: line, so the monotonic start below is the run's own and the samples
#: land on the build's real axis rather than an invented one.
FIXTURE = REPO / "tests/fixtures/with_timeline"

#: `monotonic=` on the fixture's second log line. Written out rather
#: than parsed from the log, because a guard that derives its
#: expectation from the thing under test asserts only that two copies
#: of one bug agree.
MONOTONIC_AT_START = 1874.318860
INTERVAL_S = 2.0
SAMPLES = 3

#: The header `bst_native_build_tracer` writes, and three samples in the
#: shape it writes them: the two `_kb` fields move, the three `/proc/vmstat`
#: totals climb, because a series that never changes cannot tell a
#: counter that was drawn from one that was drawn as a constant.
#:
#: `UX-675`'s three move too, and `cpu_busy_cores` is fractional on
#: purpose - it is the one value in this fixture that the trace's
#: `int64` counter cannot carry unscaled, so a `MILLI` that went missing
#: would round it to 1 and the equality below would still hold.
HEADER = {"schema": "host-samples/v1", "interval_s": INTERVAL_S,
          "clock": "CLOCK_MONOTONIC", "wall_at_start": 1787331688.483485,
          "monotonic_at_start": MONOTONIC_AT_START,
          "mem_total_kb": 16461068, "swap_total_kb": 2097148,
          "available": True}


def _samples():
    return [{"mem_free_kb": 11773444 - index * 1000,
             "mem_available_kb": 15534476 - index * 20000,
             "cached_kb": 3689664,
             "swap_free_kb": 2097148 - index * 512,
             "pswpin": index, "pswpout": 2 * index,
             "pgmajfault": 39076 + 7 * index,
             "cpu_busy_cores": 1.375 + index * 0.5,
             "cores": 8, "load1": 4.25 + index,
             "t": MONOTONIC_AT_START + INTERVAL_S * index}
            for index in range(SAMPLES)]


#: Two processes under one element, enough for the Plane 2 lanes and the
#: concurrency series to exist - the census needs `plane2.log.gz` to have
#: a consumer that reads it rather than one that finds it empty.
RAW = [
    "START pid=2 ppid=1 ts=1787331691.3 element=codegen.bst inv=a src=hook "
    "cmd=cc1",
    "START pid=3 ppid=2 ts=1787331692.0 element=codegen.bst inv=a src=hook "
    "cmd=cc2",
    "END pid=3 ppid=2 ts=1787331695.0 element=codegen.bst inv=a src=hook "
    "exit=0 utime=0.5 stime=0.1 maxrss_kb=1024 cmd=cc2",
    "END pid=2 ppid=1 ts=1787331698.1 element=codegen.bst inv=a src=hook "
    "exit=0 utime=0.5 stime=0.1 maxrss_kb=2048 cmd=cc1",
]

#: Files in the capture that no reader opens, and why that is the answer
#: rather than a defect. Anything else the census finds unread fails it.
#: Keyed by path relative to the store, so a file moving is a change
#: this list has to be told about.
NO_CONSUMER_DECLARED = {
    ".gitignore":
        "written for git, not for a `bga` reader (`UX-189`). Its consumer "
        "is the clone that does not ship the capture archive.",
    "runs/<stamp>/capture-context.txt":
        "prose for a person. The capture layout's own row says `Never "
        "parsed`, which is a decision rather than a gap (`UX-146`).",
}

#: Capture-layout file rows this fixture does not carry, with the reason.
#: Without this the census could shrink to one file and stay green.
NOT_IN_THE_FIXTURE = {
    "runs/<stamp>/run/chrome_trace.json":
        "`UX-452`: the extraction stopped writing it, so a capture taken "
        "now has none. The layout still names it as `derived` because a "
        "capture taken before that item has one and still satisfies the "
        "contract - and because `bga timeline --format chrome` renders "
        "the same shape on demand. This is the entry that used to be in "
        "`NO_CONSUMER_DECLARED`: a file with no consumer became a file "
        "with no writer, which is the only way that list gets shorter "
        "without the census being weakened.",
}


def _store(into) -> pathlib.Path:
    """A project with one complete capture in it. Returns the snapshot.

    Complete on purpose: the census measures the files that are *there*,
    so a fixture missing half the layout would be a census that passes
    by having nothing to check.
    """
    project = pathlib.Path(into) / "project"
    (project / "elements").mkdir(parents=True)
    (project / "project.conf").write_text(
        "name: census\nmin-version: 2.0\nelement-path: elements\n",
        encoding="utf-8")
    run_store.write_config(str(project), {"trace_spine": "auto"})

    snapshot = pathlib.Path(run_store.store_dir(str(project))) / "runs"
    snapshot = snapshot / "20260821T170128Z"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, snapshot)
    # `UX-452`: the committed fixture was extracted before that item and
    # carries a `chrome_trace.json`; a capture taken now does not. The
    # census's population is "what a capture written by this `bga`
    # holds", so leaving it in would have this file measuring a file
    # nothing writes any more - and it is the entry that used to be in
    # `NO_CONSUMER_DECLARED` above. The layout still names the path,
    # which is why it is in `NOT_IN_THE_FIXTURE` rather than gone.
    (snapshot / "run" / "chrome_trace.json").unlink()

    with open(snapshot / HOST_SAMPLES_NAME, "w", encoding="utf-8") as out:
        for row in [HEADER] + _samples():
            out.write(json.dumps(row) + "\n")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write("\n".join(RAW) + "\n")
    report = json.loads(
        (REPO / "tests/fixtures/macro_micro/plane2.json").read_text(
            encoding="utf-8"))
    (snapshot / "plane2.json").write_text(json.dumps(report),
                                          encoding="utf-8")
    run_store.write_resource_profile(
        str(snapshot / run_store.RESOURCE_NAME), report)
    (snapshot / "element-slice.json").write_text(
        json.dumps({"elements": ["all.bst"], "elements_considered": 11,
                    "bounded_at": 400}), encoding="utf-8")
    (snapshot / "capture-context.txt").write_text(
        "captured by the consumer census\n", encoding="utf-8")
    (snapshot / run_store.SIZE_CACHE_NAME).write_text(
        json.dumps({"bytes": 0, "signature": "x"}), encoding="utf-8")
    return snapshot


def _readers(snapshot, scratch):
    """Every command that reads a capture, as callables.

    Named by their command line because that is what a reader of a
    failure needs: "nothing opens `host-samples.jsonl`" is only
    actionable beside the list of things that were asked.
    """
    import tools.bga_snapshot as snapshot_tool
    import tools.bga_view as view
    from bga import cli

    project = str(pathlib.Path(snapshot).parents[2])
    run = str(pathlib.Path(snapshot) / "run")
    return {
        "bga timeline": lambda: render(str(snapshot),
                                       str(scratch / "t.pftrace"), quiet=True),
        "bga view --export": lambda: view.export(run,
                                                 str(scratch / "r.html")),
        "bga view (payloads)": lambda: view.payloads(run),
        "bga analyze": lambda: cli.main(["analyze", run, "--format", "json"]),
        "bga blast": lambda: cli.main(["blast", "all.bst", run,
                                       "--project", str(FIXTURE),
                                       "-f", "json"]),
        "bga correlate": lambda: cli.main(["correlate", run, "-f", "json"]),
        "the store listing": lambda: snapshot_tool.store_listing(project),
        "the store's settings": lambda: run_store.read_config(project),
    }


@pytest.fixture(scope="module")
def census(tmp_path_factory):
    """What every reader opened inside the store, and what failed.

    `builtins.open` rather than a text scan: `gzip.open`, `json.load`
    off a path and `pathlib.read_text` all bottom out here, so this
    observes the read instead of inferring it from source.
    """
    scratch = tmp_path_factory.mktemp("census")
    snapshot = _store(scratch)
    store = pathlib.Path(run_store.store_dir(str(snapshot.parents[2])))
    opened, failed = set(), {}
    real_open = builtins.open

    def spy(file, *args, **kwargs):
        handle = real_open(file, *args, **kwargs)
        # Recorded **after** the open returns, so an attempted read of a
        # file that is not there does not count as a consumer. It would
        # otherwise: `read_host_samples` opens the path either way, so a
        # census over attempts would have passed on the very absence
        # `UX-437` was filed on.
        with contextlib.suppress(TypeError, ValueError):
            opened.add(os.path.realpath(file))
        return handle

    for name, reader in _readers(snapshot, scratch).items():
        builtins.open = spy
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = reader()
            if isinstance(code, int) and code != 0:
                # A command that exits non-zero stopped early, so the
                # files it would have opened are unread for a reason
                # that is not "nothing consumes them".
                failed[name] = f"exit {code}"
        except BaseException as exc:
            failed[name] = f"{type(exc).__name__}: {exc}"
        finally:
            builtins.open = real_open

    root = os.path.realpath(store)
    present = sorted(
        os.path.relpath(os.path.join(where, name), root)
        for where, _dirs, names in os.walk(root) for name in names)
    read = {os.path.relpath(path, root) for path in opened
            if path.startswith(root + os.sep)}
    return {"snapshot": snapshot, "store": store, "scratch": scratch,
            "present": present, "read": read, "failed": failed,
            "readers": sorted(_readers(snapshot, scratch))}


def _generic(path):
    """A store-relative path with the run's stamp replaced, so the
    declarations above name a layout row rather than one fixture."""
    parts = pathlib.PurePosixPath(path).parts
    if len(parts) > 1 and parts[0] == "runs":
        return "/".join(("runs", "<stamp>") + parts[2:])
    return path


class TestTheCensusCanSeeAnything:
    """What makes the two clauses after it mean something."""

    def test_every_reader_ran_clean(self, census):
        assert census["failed"] == {}, (
            f"a reader that raised opens nothing after the raise, so the "
            f"census would report its files unread: {census['failed']}")

    def test_the_fixture_carries_every_file_the_layout_names(self, census):
        rows = {_generic(path.split("/", 1)[1])
                for path in run_store.layout_paths() if not path.endswith("/")}
        have = {_generic(path) for path in census["present"]}
        missing = sorted(rows - have - set(NOT_IN_THE_FIXTURE))
        assert missing == [], (
            f"the capture layout names {len(rows)} files and this fixture "
            f"has {len(have)}; a census over a fixture missing rows passes "
            f"by having nothing to check: {missing}")


class TestEveryCapturedFileHasAConsumer:

    def test_nothing_in_the_capture_is_written_and_never_read(self, census):
        unread = sorted(path for path in census["present"]
                        if path not in census["read"]
                        and _generic(path) not in NO_CONSUMER_DECLARED)
        assert unread == [], (
            f"{len(unread)} file(s) in the capture that no reader opens. "
            f"Readers asked: {', '.join(census['readers'])}. This is the "
            f"gap `UX-437` was filed on, one level earlier than `UX-401`'s "
            f"published-key census: {unread}")

    def test_the_host_samples_are_among_the_files_that_are_read(self, census):
        read = {_generic(path) for path in census["read"]}
        assert f"runs/<stamp>/{HOST_SAMPLES_NAME}" in read, (
            f"{HOST_SAMPLES_NAME} is written by every capture and opened by "
            f"no reader - the state `UX-437` found after eight rounds")

    def test_every_declared_exemption_is_still_unread(self, census):
        """A declaration that has quietly become true again is a comment
        claiming a defect that no longer exists."""
        stale = sorted(path for path in census["present"]
                       if _generic(path) in NO_CONSUMER_DECLARED
                       and path in census["read"])
        assert stale == [], (
            f"declared as having no consumer, and now read: {stale}. Delete "
            f"the entry in NO_CONSUMER_DECLARED rather than leaving it.")


@pytest.fixture(scope="module")
def drawn(census):
    """The fixture's capture, rendered, decoded off the wire."""
    out = census["scratch"] / "host.pftrace"
    result = render(str(census["snapshot"]), str(out), quiet=True)
    return {"result": result, "trace": decode(out)}


class TestTheHostSeriesReachesTheTrace:

    def _tracks(self, drawn):
        return {entry["name"]: uuid
                for uuid, entry in drawn["trace"]["counters"].items()}

    def test_each_sampled_field_is_a_counter_track_with_its_unit(self, drawn):
        counters = {entry["name"]: entry
                    for entry in drawn["trace"]["counters"].values()}
        for _key, label, unit, _scale in HOST_COUNTERS:
            assert label in counters, (
                f"{label} is sampled and not drawn: {sorted(counters)}")
            assert counters[label]["unit_name"] == unit, counters[label]

    def test_the_kilobyte_fields_are_published_in_bytes(self, drawn):
        """`UX-437`'s second bullet: `mem_available_kb` is bytes on the
        wire and must say so. A track labelled `bytes` carrying kilobytes
        would be `UX-351`'s defect with a unit attached."""
        tracks = self._tracks(drawn)
        values = {}
        for sample in drawn["trace"]["samples"]:
            values.setdefault(sample["track"], []).append(sample["value"])
        drawn_mem = values[tracks["host memory available"]]
        assert drawn_mem == [row["mem_available_kb"] * 1024
                             for row in _samples()], drawn_mem

    def test_the_samples_sit_inside_the_build_they_were_taken_during(
            self, census, drawn):
        """Not on `CLOCK_MONOTONIC`, which is a number of seconds since
        this machine booted and means nothing beside a slice.

        Spacing alone would not say this: an interval is the same
        whatever epoch it is on, so a series drawn 55 years early keeps
        it exactly. What pins the axis is the *window* - the build's own
        `wall_clock` out of `run-context.json`, which is the range every
        Plane 1 slice sits in.
        """
        window = json.loads(
            (pathlib.Path(census["snapshot"]) / "run"
             / "run-context.json").read_text(encoding="utf-8"))["wall_clock"]
        tracks = self._tracks(drawn)
        stamps = sorted(sample["ts"] for sample in drawn["trace"]["samples"]
                        if sample["track"] == tracks["host swap free"])
        assert len(stamps) == SAMPLES, stamps
        outside = [at for at in stamps
                   if not (window["start_us"] * 1000 <= at
                           <= window["end_us"] * 1000)]
        assert outside == [], (
            f"host samples outside the build's own wall clock "
            f"{window}: {outside}")
        assert stamps[0] == int(round(HEADER["wall_at_start"] * 1e9)), stamps
        spacing = [(later - earlier) / 1e9
                   for earlier, later in zip(stamps, stamps[1:])]
        assert spacing == [INTERVAL_S] * (SAMPLES - 1), spacing

    def test_the_cumulative_totals_are_drawn_as_they_were_sampled(self, drawn):
        """`pgmajfault` is a total since boot, not a rate. Publishing it
        as anything else would be inventing a number the capture never
        took - the trace dictionary says which three are cumulative."""
        tracks = self._tracks(drawn)
        faults = [sample["value"] for sample in drawn["trace"]["samples"]
                  if sample["track"] == tracks["host major faults"]]
        assert sorted(faults) == [row["pgmajfault"] for row in _samples()], (
            faults)

    def test_the_fractional_cpu_series_survives_an_int64_counter(self, drawn):
        """`UX-675`: `counter_value` is an `int64` and cores busy is a
        ratio, so `HOST_COUNTERS` carries a `MILLI` for it exactly as it
        carries `KB` for memory. Drawn unscaled the fixture's first
        sample lands as 1 instead of 1.375 - 37 % of a core, on the one
        series the item exists to make readable."""
        tracks = self._tracks(drawn)
        busy = sorted(sample["value"] for sample in drawn["trace"]["samples"]
                      if sample["track"] == tracks["host cores busy"])
        assert busy == sorted(int(round(row["cpu_busy_cores"] * 1000))
                              for row in _samples()), busy

    def test_the_result_counts_the_two_populations_apart(self, drawn):
        """`counters` is `UX-310`'s concurrency series and `UX-430`'s
        narrowing guard reads it as such. Folding the host samples into
        it would leave that guard comparing something else."""
        result = drawn["result"]
        assert result["host_counters"] == SAMPLES * len(HOST_COUNTERS), result
        assert result["counters"] == len(
            list(drawn["trace"]["samples"])) - \
            result["host_counters"], result

    def test_a_capture_with_no_host_samples_draws_no_host_track(
            self, census, tmp_path):
        """The item's own acceptance mutation, as a clause: delete the
        file and the series is gone rather than fabricated."""
        bare = tmp_path / "bare"
        shutil.copytree(census["snapshot"], bare)
        (bare / HOST_SAMPLES_NAME).unlink()
        out = tmp_path / "bare.pftrace"
        result = render(str(bare), str(out), quiet=True)
        assert result["host_counters"] == 0 and result["host_series"] == []
        names = {entry["name"] for entry in decode(out)["counters"].values()}
        assert not any(name.startswith("host ") for name in names), names


class TestTheSummarySaysWhichItHas:
    """`UX-395`'s rule: a row a summary leaves out is a row a reader
    assumes was fine. Both branches, because only one of them can be
    wrong at a time."""

    def _lines(self, snapshot, out):
        from tools.bga_timeline import describe

        return describe(render(str(snapshot), str(out), quiet=True),
                        str(out)).splitlines()

    def test_it_names_the_series_when_there_are_some(self, census):
        text = "\n".join(self._lines(census["snapshot"],
                                     census["scratch"] / "say.pftrace"))
        assert "host counters" in text, text
        for _key, label, _unit, _scale in HOST_COUNTERS:
            assert label in text, text

    def test_it_says_so_when_there_are_none(self, census, tmp_path):
        bare = tmp_path / "bare"
        shutil.copytree(census["snapshot"], bare)
        (bare / HOST_SAMPLES_NAME).unlink()
        text = "\n".join(self._lines(bare, tmp_path / "bare.pftrace"))
        assert "No host series" in text and HOST_SAMPLES_NAME in text, text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
