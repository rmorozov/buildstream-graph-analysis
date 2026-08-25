"""UX-296: `bga view` reaches a socket without parsing what it serves.

The field showstopper of round 40: a real dual-plane snapshot reached
~2 GB (`plane2.json` 1.5 GB), and `bga view` froze in parsing and then
died of memory near server start. `serve()` built every payload before
the socket existed, serially running every whole-file load path in the
codebase - the monolith parsed at a measured 2.9x bytes-to-RAM *twice*,
every snapshot's monolith re-parsed for two scalars, and the trace step
reading a decompressed log as one string right before
`ThreadingHTTPServer` was constructed.

**What this guard measures.** A store built here, never committed: one
snapshot whose Plane 2 report holds a million process records, and a
small neighbour beside it. Startup is measured in a **subprocess**, so
peak RSS is the process's own high-water mark and nothing this suite
did earlier can be mistaken for it.

Measured on the same fixture, before this item and after (247 MB of
report, 1,000,000 records):

```text
                                 before (round 39)        after
view the big run itself       17.55 s   1235.5 MB    0.23 s   39.5 MB
view its 2 MB neighbour        9.37 s   1233.3 MB    0.27 s   39.6 MB
```

The neighbour is the one that shows the shape of the defect: viewing a
2 MB run cost 1.2 GB because the aggregate walked into the *other*
snapshot's monolith for two floats.

**Why the ceilings are where they are.** `RSS_CEILING_MB` is 250: the
interpreter with this repository imported is ~39 MB here, the fixture's
report is 247 MB on disk, and 2.9x bytes-to-RAM means a single parse of
it would cost ~700 MB - so any ceiling between "what we use" and "one
parse" discriminates, and 250 leaves headroom for a slower machine's
allocator without admitting a parse. `SECONDS_CEILING` is 20: the
before-figure at this size is 17.55 s and the after-figure is 0.23 s,
and CI runners are slower than this container - the bound is a
*regression* alarm, not a benchmark.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

# How many process records the generated report holds. The item asks for
# order 10^6 events; at ~247 bytes a record that is ~247 MB, which is
# where the numbers in this file were measured.
BIG_RUN_RECORDS = 1_000_000

RSS_CEILING_MB = 250.0
SECONDS_CEILING = 20.0

BIG_STAMP = "20260825T120000Z"
SMALL_STAMP = "20260825T130000Z"


def _write_monolith(path, records):
    """A Plane 2 report with real aggregates and a million processes.

    Streamed out rather than built and dumped: this file exists to be
    too big to hold, and a fixture that had to hold it to write it would
    be making the same mistake it is here to catch.
    """
    per_element = {f"el-{i}.bst": {"cpu_us": 1000 + i, "processes": 3}
                   for i in range(200)}
    peaks = {f"el-{i}.bst": {"peak_rss_kb": 1024 * (i + 1)} for i in range(200)}
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{\n")
        handle.write(' "wall_span_s": 3600.0,\n')
        handle.write(' "cpu_time": %s,\n'
                     % json.dumps({"per_element": per_element}))
        handle.write(' "peak_memory": %s,\n'
                     % json.dumps({"available": True, "per_element": peaks}))
        handle.write(' "per_element_parallelism": [],\n')
        handle.write(' "stream_coverage": {"processes": %d},\n' % records)
        handle.write(' "processes": [\n')
        for i in range(records):
            record = {"pid": 1000 + i, "ppid": 1000,
                      "binary": "/usr/bin/cc1plus",
                      "argv": ["cc1plus", f"-o/build/obj/{i}.o",
                               f"/src/file{i}.c"],
                      "element": f"el-{i % 200}.bst", "start_ts": i * 10,
                      "end_ts": i * 10 + 9, "cpu_us": 9000,
                      "peak_rss_kb": 4096, "inv": f"inv-{i % 64}"}
            handle.write(("  " if i == 0 else " ,") + json.dumps(record) + "\n")
        handle.write(" ]\n}\n")


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    """A project whose store holds one big snapshot and one small one."""
    root = tmp_path_factory.mktemp("project")
    (root / "project.conf").write_text("name: big\n", encoding="utf-8")
    runs = root / ".bga" / "runs"
    for stamp in (BIG_STAMP, SMALL_STAMP):
        snapshot = runs / stamp
        snapshot.mkdir(parents=True)
        shutil.copytree(GOLDEN, snapshot / "run")
        (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
        # A wrapped log, so a timeline is *offered* - the point being
        # that offering one must not cost what building one costs.
        (snapshot / "build.log").write_text(
            "[--:--:--][][   main:core activity  ] START   Build\n",
            encoding="utf-8")
    _write_monolith(runs / BIG_STAMP / "plane2.json", BIG_RUN_RECORDS)
    return root


_MEASURE = textwrap.dedent("""
    import json, os, resource, sys, time
    sys.path.insert(0, %(repo)r)
    from tools.bga_view import serve
    opened = []
    real_open = open
    def watched(path, *args, **kwargs):
        opened.append(str(path))
        return real_open(path, *args, **kwargs)
    import builtins
    builtins.open = watched
    start = time.time()
    httpd, url = serve(%(run)r, port=0)
    elapsed = time.time() - start
    builtins.open = real_open
    httpd.server_close()
    print(json.dumps({
        "seconds": elapsed,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "opened": opened,
    }))
""")


def _startup(run):
    """Start a server in a subprocess and report what it cost.

    A subprocess because peak RSS is a property of a *process*: measured
    inside this one, every earlier test's allocations would be part of
    the answer, and the number would say nothing about what `bga view`
    does.
    """
    done = subprocess.run(
        [sys.executable, "-c", _MEASURE % {"repo": str(REPO), "run": str(run)}],
        capture_output=True, text=True, cwd=REPO, timeout=600)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


class TestStartupDoesNotPayForWhatItServes:

    def test_the_big_run_reaches_a_socket_inside_both_ceilings(self, store):
        """The acceptance test's first clause, on the generated run."""
        out = _startup(store / ".bga/runs" / BIG_STAMP / "run")
        assert out["peak_rss_mb"] < RSS_CEILING_MB, out
        assert out["seconds"] < SECONDS_CEILING, out

    def test_the_big_artifacts_are_not_opened_at_all(self, store):
        """The clause that says *why* it is cheap. A ceiling can be met
        by a faster machine; this cannot be met by anything but not
        reading the file."""
        out = _startup(store / ".bga/runs" / BIG_STAMP / "run")
        touched = [path for path in out["opened"]
                   if os.path.basename(path) == "plane2.json"]
        assert touched == [], (
            f"startup opened the Plane 2 monolith: {touched}")

    def test_a_neighbour_pays_nothing_for_the_big_run(self, store):
        """The acceptance test's last clause, and the measurement that
        showed the defect's shape: 1,233 MB to view a 2 MB run, because
        the store aggregate walked into the big snapshot beside it."""
        out = _startup(store / ".bga/runs" / SMALL_STAMP / "run")
        assert out["peak_rss_mb"] < RSS_CEILING_MB, out
        assert out["seconds"] < SECONDS_CEILING, out
        assert [p for p in out["opened"]
                if os.path.basename(p) == "plane2.json"] == [], out["opened"]

    def test_the_timeline_is_offered_without_being_built(self, store):
        """`UX-194`'s rule (offer only what exists) met `UX-296`'s
        (build nothing at startup): the button is offered from a file
        test, and the bytes are rendered when they are asked for."""
        out = _startup(store / ".bga/runs" / BIG_STAMP / "run")
        assert not [p for p in out["opened"]
                    if p.endswith("timeline.json") or p.endswith(".json.gz")], \
            out["opened"]
