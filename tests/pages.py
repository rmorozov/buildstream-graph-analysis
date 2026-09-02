"""UX-359: the page a guard measures is the page a user gets.

Every browser guard in this repository built its page the same way, by
copy-paste from the one before it:

```python
run = tmp_path_factory.mktemp(f"shape-{name}") / "run"
shutil.copytree(fixture, run)
(run / "expected_output.json").unlink(missing_ok=True)
view.export(str(run), str(page))
```

`macro_micro`'s Plane 2 report is not inside `run/`. It is
`tests/fixtures/macro_micro/plane2.json`, a **sibling**, found by
`run_store.sibling_plane2` looking at `../plane2.json` from a directory
named `run`. `copytree` copies the run and leaves the sibling behind, so
every one of those guards exported a page with Plane 2 missing:

```text
                                 height  sections  words  buttons  strips
the page a user gets            24,689px       58  8,174      381     19
the page every guard measured   21,346px       55  6,845      341     18
```

Three sections, 1,329 words, 40 buttons and 3,343 px that no guard had
ever seen - and the missing part is the Plane 2 half, which is the half
the tool's second plane exists to produce.

The copy is not the defect; copying only the *run* is. A capture is a
snapshot directory with a run inside it and its siblings beside it, so
this module copies the snapshot. `expected_output.json` - the one thing
the old idiom needed a copy for at all - is removed from the copy, which
is why the copy is still made rather than exporting in place.

`test_the_guards_measure_the_page.py` holds the two to the same
rendering.
"""
import json
import os
import pathlib
import shutil

REPO = pathlib.Path(__file__).resolve().parents[1]

#: UX-399: one statement that turns the layout optimisation off.
#:
#: `content-visibility: auto` lets the browser skip laying out a section
#: that is not near the viewport, which is what makes the fully expanded
#: page cost ~2 ms a reflow instead of ~26 ms. The price is that
#: `scrollHeight` is an *estimate* until a section has been rendered
#: once, and the estimate depends on which sections the reader (or the
#: guard) has scrolled past - so two routes to the same expanded page
#: report heights 264 px apart.
#:
#: A guard whose claim is about the **document** - how much there is to
#: read, whether two controls reach the same state - prepends this and
#: measures the fully laid-out page. A guard whose claim is about what a
#: reader *sees* must not: that reader has the optimisation on.
#:
#: `insertAdjacentHTML` rather than the node-building DOM call, because
#: the shim census (`UX-264`) reads that call as a node harness which
#: should be importing the shared shim, and this runs in a browser where
#: there is no shim.
FULL_LAYOUT_JS = (
    'document.head.insertAdjacentHTML("beforeend",'
    ' "<style>section.chapter > section[data-section]'
    '{ content-visibility: visible !important; }</style>");'
)

#: The committed fixtures every browser guard walks, by the label they
#: all already used. One definition, so a fixture added tomorrow reaches
#: every guard that parametrises over this rather than none of them.
FIXTURES = {
    "golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
    "macro_micro": REPO / "tests/fixtures/macro_micro/run",
}

#: UX-358: the one committed capture that can render a **timeline**.
#:
#: Not in `FIXTURES`, deliberately. Every guard that parametrises over
#: those two would add a third browser boot for a page that differs
#: from them in exactly one respect, and this exists for that one
#: respect: it is the snapshot with a `build.log`, so `bga timeline`
#: renders, `trace_bytes` is not `None`, and `#perfetto` gets a box.
#:
#: **A Plane 1 capture, and committed.** The first attempt at this
#: pointed at `examples/06`'s real two-plane capture - which is real,
#: and **gitignored** (`UX-189`: a clone does not ship the capture
#: archive). It exists on a machine that ran the example and in no
#: clone, so the guard passed here and failed in CI, which is the
#: defect `UX-358` was filed about happening to its own fix. This is
#: the wrapped log and the run, 64 KB, in the tree.
WITH_TIMELINE = REPO / "tests/fixtures/with_timeline/run"

#: `bga snapshot` writes it and `bga view` refuses to export beside it;
#: removing it is the whole reason a copy is made.
_DROPPED = "expected_output.json"

_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")


#: UX-364: the **two-plane** state, constructed rather than committed.
#:
#: `WITH_TIMELINE` is Plane 1 only and the two in `FIXTURES` have no
#: timeline at all, so until this existed no guard could reach a page
#: whose trace carries Plane 2 lanes - which is the state the handoff's
#: lead sentence was written for and claimed unconditionally.
#:
#: Built rather than committed because it needs no real capture: a
#: four-line wrapped Plane 1 log and two raw Plane 2 records merge into
#: a real two-plane trace, over the golden run. `bga snapshot` writes a
#: much larger version of the same shape; `UX-189` is why this is not
#: another 700 KB in the tree.
#:
#: `test_one_timeline_both_planes.py` builds the same shape for the CLI
#: route with `--no-keep-raw` and uncompressed variants. This one exists
#: to be *exported as a page*, which that one never does.
_WRAPPED_LOG = """\
[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""

_RAW_PLANE2 = """\
START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


def two_plane_snapshot(into) -> pathlib.Path:
    """A snapshot whose trace carries **both** planes. The run inside it.

    Shaped like one `bga snapshot` writes: a wrapped BuildStream log
    beside a `run/`, and the raw Plane 2 log the merge reads.
    """
    import gzip

    snapshot = pathlib.Path(into) / "20260821T120000Z"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "build.log").write_text(_WRAPPED_LOG, encoding="utf-8")
    shutil.copytree(FIXTURES["golden"], snapshot / "run",
                    ignore=_IGNORED, dirs_exist_ok=True)
    (snapshot / "run" / _DROPPED).unlink(missing_ok=True)
    with gzip.open(snapshot / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW_PLANE2)
    return snapshot / "run"


#: `UX-369`: the seeded scale run, as a run directory.
#:
#: Not a fixture and not committed - `bga gen-synthetic --seed 1` is
#: deterministic, so 1,202 elements cost a subprocess rather than a
#: megabyte in the tree (`UX-189`). Measured at 3.5 s for the generate
#: and the export together, which is why a file that calls this is
#: tiered rather than left in `small`.
#:
#: The two committed fixtures are 11-element runs, and round 2 found
#: four defects at this size that were invisible at eleven. `UX-367`
#: is the item about the budgets never being measured here.
def scale_run(into, name="scale", shape=()) -> pathlib.Path:
    """`gen-synthetic --seed 1` into `into`. The run directory."""
    import subprocess
    import sys

    run = pathlib.Path(into) / name
    subprocess.run([sys.executable, "-m", "bga.cli", "gen-synthetic",
                    str(run), "--seed", "1", *shape],
                   check=True, capture_output=True, cwd=str(REPO))
    return run


#: `UX-526`: the **top** of the large size class, as `scale_run` is its
#: bottom. `--layers 20 --width 200` is 4,002 elements from the same
#: seed, 0.6 s to generate - a budget measured only at 1,202 governs a
#: class it never meets, which is `UX-367`'s own defect one size up.
def xl_run(into) -> pathlib.Path:
    """`gen-synthetic --seed 1 --layers 20 --width 200`. 4,002 elements."""
    return scale_run(into, "xl", ("--layers", "20", "--width", "200"))


def scale_two_plane_snapshot(into, per_element=12,
                             programs=("cc",)) -> pathlib.Path:
    """`UX-430`: the scale run, wrapped as a two-plane **snapshot**.

    `scale_run` gives 1,202 elements as a run directory; a timeline needs
    the snapshot around it - the wrapped BuildStream log Plane 1 is read
    from, and the raw Plane 2 log the merge reads. Both are generated
    from the run's own `graph.json`, so the populations agree with the
    analysis rather than being invented beside it.

    `per_element` processes per element, because the track count is what
    `UX-430` is about and it rises with the process population: one
    process track per element and one thread track per traced pid
    (`_write_trackevent`). Twelve is a plausible compile job - a shell
    and eleven children - and the caller can ask for another number,
    which is what makes the bound measurable rather than asserted.

    `programs` are the executables the processes run, cycled through.
    The default is one, which keeps the track measurement above about
    tracks; `UX-433` passes a real toolchain's worth, because the cost of
    a per-slice executable annotation depends on how many distinct ones
    there are and a fixture with one program measures the best case.

    Returns the **snapshot**, not the run: `bga timeline` takes it.
    """
    import gzip
    import json

    run = scale_run(into)
    snapshot = pathlib.Path(into) / "20260821T120000Z"
    snapshot.mkdir(parents=True, exist_ok=True)
    shutil.copytree(run, snapshot / "run", dirs_exist_ok=True)
    with open(snapshot / "run" / "graph.json", encoding="utf-8") as handle:
        elements = [row["uid"] for row in json.load(handle)["elements"]]

    def stamp(seconds):
        whole = int(seconds)
        return (f"2026-08-21 12:{whole // 60:02d}:{whole % 60:02d},"
                f"{int((seconds - whole) * 1000):03d}")

    lines = [f"[wrapper][{stamp(0)}] INFO: Executing command: bst build "
             f"all.bst"]
    raw, pid = [], 100
    for index, uid in enumerate(elements):
        # One second each, laid end to end. The *shape* of the timeline
        # is not what this fixture is for - the population is.
        start, end = 1.0 + index, 1.9 + index
        digest = f"{index:08x}"
        lines.append(f"[wrapper][{stamp(start)}] INFO: [00:00:00][{digest}]"
                     f"[   build:{uid}] START Building")
        lines.append(f"[wrapper][{stamp(end)}] INFO: [00:00:00][{digest}]"
                     f"[   build:{uid}] SUCCESS Building")
        for child in range(per_element):
            pid += 1
            began = 1000.0 + index + child / 100.0
            program = programs[(index + child) % len(programs)]
            command = f"{program} -c f{child}.c"
            raw.append(f"START pid={pid} ppid=1 ts={began:.6f} element={uid} "
                       f"inv=inv-{index} src=spine cmd={command}\n")
            raw.append(f"END pid={pid} ppid=1 ts={began + 0.05:.6f} "
                       f"element={uid} inv=inv-{index} src=spine exit=0 "
                       f"utime=0.01 stime=0.01 maxrss_kb=1024 "
                       f"cmd={command}\n")
    lines.append(f"[wrapper][{stamp(2.0 + len(elements))}] INFO: Return "
                 f"code: 0")
    (snapshot / "build.log").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write("".join(raw))
    return snapshot


#: `UX-438`: what a run with artifact transfer in it looks like.
#:
#: `compute_cache_accounting` publishes `transfer_us` and
#: `transfer_share` only when the run has spans whose primary resource
#: is `DOWNLOAD` or `UPLOAD`, and **no committed fixture has one** with
#: a Pipeline Summary beside it - `golden` has a DOWNLOAD span and no
#: summary, `macro_micro` has the summary and no DOWNLOAD span. So two
#: published fields were undeclared for as long as they have existed
#: and every guard passed, because the shape that produces them was the
#: shape nothing tested.
#:
#: Injected into a copy rather than added to the fixture: the committed
#: runs are the population a dozen other guards state numbers about,
#: and moving one to close a schema gap would move those too.
TRANSFER_SPANS = (("PULL", "DOWNLOAD", 4_000_000),
                  ("PUSH", "UPLOAD", 1_500_000))


def transfer_run(fixture, into) -> pathlib.Path:
    """`snapshot_copy`, plus a transfer span per entry above.

    The run it returns publishes a `cache` block carrying `transfer_us`
    and `transfer_share`, which is what makes those two fields
    reachable by a guard at all.
    """
    run = snapshot_copy(fixture, into)
    trace = run / "trace.json"
    doc = json.loads(trace.read_text(encoding="utf-8"))
    spans = doc["spans"]
    # Anchored on a span the run already has, so the injected work sits
    # inside the run's own window and `transfer_share` is a share of
    # this run rather than of a wall-clock nobody measured.
    first = min(span["ts_us"] for span in spans)
    element = spans[0]["task_key"].split("|", 1)[0]
    for index, (kind, resource, duration) in enumerate(TRANSFER_SPANS):
        spans.append({"task_key": f"{element}|{kind}|{kind}|{index}",
                      "ts_us": first, "dur_us": duration,
                      "resources": [resource], "primary_resource": resource,
                      "status": "SUCCESS"})
    trace.write_text(json.dumps(doc), encoding="utf-8")
    return run


def snapshot_copy(fixture, into) -> pathlib.Path:
    """Copy the fixture's whole **snapshot** and return the run inside it.

    `into` is a directory the caller owns - a `tmp_path` or a
    `tmp_path_factory.mktemp(...)`. The snapshot lands at
    `into/snapshot`, so the run keeps both its own name and its
    siblings, and `sibling_plane2` finds what it finds in the tree.
    """
    fixture = pathlib.Path(fixture)
    snapshot = pathlib.Path(into) / "snapshot"
    shutil.copytree(fixture.parent, snapshot, ignore=_IGNORED,
                    dirs_exist_ok=True)
    run = snapshot / fixture.name
    (run / _DROPPED).unlink(missing_ok=True)
    return run


def export_page(fixture, into, name="report.html", **kwargs) -> pathlib.Path:
    """`snapshot_copy`, then `bga view --export`. The page's path.

    Imported inside the call rather than at module scope: `tests/` is on
    the path for guards that never touch the viewer, and importing
    `tools.bga_view` at collection time would make every one of them pay
    for it.
    """
    import tools.bga_view as view

    run = snapshot_copy(fixture, into)
    page = pathlib.Path(into) / name
    page.parent.mkdir(parents=True, exist_ok=True)
    view.export(str(run), str(page), **kwargs)
    return page


def export_uri(fixture, into, name="report.html", **kwargs) -> str:
    """The `file://` URI `Browser.measure` wants."""
    return export_page(fixture, into, name, **kwargs).as_uri()


def pages(tmp_path_factory, prefix="page", labels=None) -> dict:
    """`{label: file:// uri}` for the committed fixtures.

    The whole of what most guards' `pages` fixture did, so the next one
    inherits the fix rather than the idiom that needed it.
    """
    chosen = FIXTURES if labels is None else {
        label: FIXTURES[label] for label in labels}
    return {label: export_uri(fixture,
                              tmp_path_factory.mktemp(f"{prefix}-{label}"))
            for label, fixture in chosen.items()}


def in_place_uri(fixture, into, name="report.html") -> str:
    """The page exported from the fixture **where it lies**.

    Only `test_the_guards_measure_the_page.py` wants this: it is the
    reference the copy is held against, and it is not a way to write a
    guard - an export writes nothing into the run, but a fixture is not
    a scratch directory and a guard that treats it as one is one bug
    away from editing the tree.
    """
    import tools.bga_view as view

    page = pathlib.Path(into) / name
    page.parent.mkdir(parents=True, exist_ok=True)
    view.export(str(pathlib.Path(fixture)), str(page))
    return page.as_uri()


def has_expected_output(fixture) -> bool:
    """Whether the fixture carries the file the copy exists to drop.

    Read by the guard on the guards, so "the copy is unnecessary now"
    fails loudly instead of quietly making `snapshot_copy` a synonym for
    `in_place`.
    """
    return os.path.isfile(os.path.join(str(fixture), _DROPPED))
