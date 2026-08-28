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
import os
import pathlib
import shutil

REPO = pathlib.Path(__file__).resolve().parents[1]

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
