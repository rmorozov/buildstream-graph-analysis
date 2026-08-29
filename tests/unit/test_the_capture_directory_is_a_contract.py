"""UX-381: the capture directory is a contract, and now it says so.

Every published `bga` command line names a path inside `.bga/`, and the
tool prints them itself at the end of every capture:

```text
bga blast storm.bst .../.bga/runs/20260829T083056Z/run
bga correlate .../.bga/runs/20260829T083056Z/run
bga compare @prev @last
```

`@last` and `@prev` resolve by listing `runs/`; `bga view` reads
`run/`; `bga correlate` finds `plane2.json` as a sibling; `bga
timeline` reads `plane2.log.gz` and `build.log`; the store aggregator
walks the lot. Measured when this was filed, the layout was
load-bearing in a dozen places and written down in one:

```text
paths a capture writes                            21
named in Part 32's contract registry               1   (plane2.json)
in `docs/design/capture-workflow.md`'s table       9   - of a DIFFERENT
                                                       directory, with
                                                       different names
                                                       for two of them
in no table anywhere                               7
```

That table describes the CI field-capture bundle, where the Plane 2
report is `native-report.json` and the raw log is `native-trace.log`. A
reader who found it and went looking for `native-report.json` in a
snapshot would not find one. It now says so in the sentence above it.

**Presence has three values, not two.** "Not there" means three
different things in this directory, and a consumer that cannot tell
them apart cannot tell a broken capture from a cheap one: `required`
means the capture is unusable, `conditional` means an option was off,
`derived` means nothing at all. A reader used to learn the difference
by getting an error.

This is `UX-328`'s rule one level up: every *document* answers for its
own schema, and the *directory* they live in answered for nothing.
"""
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts, run_store  # noqa: E402

SPEC = REPO / "docs/spec/specification.md"
WORKFLOW = REPO / "docs/design/capture-workflow.md"
REAL = REPO / "examples/06-macro-micro-optimization/.bga"
needs_real_capture = pytest.mark.skipif(
    not REAL.is_dir(), reason="no real capture in this tree")


def _spec_table():
    """`{path: (presence, contract)}` from 32.6's own table."""
    text = SPEC.read_text(encoding="utf-8")
    assert "## 32.6 The capture directory" in text, "the spec has no 32.6"
    body = text.split("## 32.6 The capture directory", 1)[1]
    body = body.split("\n## ", 1)[0]
    rows = {}
    for line in body.splitlines():
        match = re.match(r"^\| `([^`]+)` \| (\w+) \| (`[^`]+`|—) \|", line)
        if match:
            contract = match.group(3)
            rows[match.group(1)] = (
                match.group(2),
                contract.strip("`") if contract != "—" else None)
    return rows


def _walked(store):
    """Every path a real capture holds, keyed the way the table is.

    A stamped run directory is one row in the contract, not one row per
    capture, so the stamp is normalised - which is the only way a fixed
    number of rows can describe a store with a hundred runs in it.
    """
    seen = set()
    for path in sorted(store.rglob("*")):
        rel = path.relative_to(store.parent).as_posix()
        rel = re.sub(r"/runs/[^/]+(/|$)", r"/runs/<stamp>\1", rel)
        if path.is_dir():
            rel += "/"
        seen.add(rel)
    seen.add(f"{run_store.STORE_DIRNAME}/")
    return seen


class TestTheContractExists:
    def test_the_directory_declares_one(self):
        assert run_store.SCHEMA == "capture-layout/v1"
        assert run_store.SCHEMA in contracts.ids(), (
            "the capture layout is declared and not inventoried - which "
            "is `UX-248`'s defect, which this item is a case of")

    def test_the_module_that_writes_the_names_states_the_contract(self):
        """The constants were always here; the *statement* was not.
        `run_store.CAPTURE_LAYOUT` is built from those same constants,
        so a rename moves both or neither."""
        paths = run_store.layout_paths()
        for name in (run_store.PLANE2_NAME, run_store.RAW_LOG_NAME,
                     run_store.RESOURCE_NAME, run_store.ANALYSIS_NAME,
                     run_store.HOST_SAMPLES_NAME,
                     run_store.SIZE_CACHE_NAME, run_store.CONFIG_NAME):
            assert any(path.endswith("/" + name) or path.endswith(name)
                       for path in paths), (
                f"`{name}` is a constant this module exports and a path "
                f"the contract does not name")

    def test_every_row_says_which_of_the_three_it_is(self):
        allowed = {run_store.REQUIRED, run_store.CONDITIONAL,
                   run_store.DERIVED}
        for path, presence, _contract, what in run_store.CAPTURE_LAYOUT:
            assert presence in allowed, (path, presence)
            assert len(what) > 40, (
                f"`{path}`'s sentence is too short to say what an absence "
                f"means, which is the column a reader came for")

    def test_no_path_is_named_twice(self):
        paths = run_store.layout_paths()
        assert len(set(paths)) == len(paths)

    def test_a_path_the_contract_does_not_name_answers_none(self):
        assert run_store.layout_presence("runs/<stamp>/nothing.json") is None


class TestTheSpecificationAndTheModuleAgree:
    """One statement in two places is two statements. The table is
    rendered from the module, and this holds them equal in both
    directions - the same shape Part 32.5's own registry guard has."""

    def test_every_declared_path_is_in_the_table(self):
        table = _spec_table()
        missing = [p for p in run_store.layout_paths() if p not in table]
        assert missing == [], (
            f"path(s) the module declares and 32.6 does not list: {missing}")

    def test_the_table_names_nothing_the_module_does_not(self):
        declared = set(run_store.layout_paths())
        extra = sorted(set(_spec_table()) - declared)
        assert extra == [], (
            f"32.6 lists path(s) no capture writes: {extra}")

    def test_the_presence_and_the_contract_match_row_for_row(self):
        table = _spec_table()
        for path, presence, contract, _what in run_store.CAPTURE_LAYOUT:
            assert table[path] == (presence, contract), (
                f"`{path}`: the module says {(presence, contract)} and "
                f"32.6 says {table[path]}")

    def test_every_contract_a_row_cites_is_a_real_one(self):
        """A row citing an id nothing owns would send a reader to
        `bga --schema` for a shape that does not exist."""
        known = set(contracts.ids()) | {"graph/v9", "trace/v9",
                                        "run-context/v9"}
        cited = [c for _p, _pr, c, _w in run_store.CAPTURE_LAYOUT if c]
        unknown = sorted(set(cited) - known)
        assert unknown == [], unknown


FIXTURE = REPO / "tests/fixtures/macro_micro"


def _committed_store(tmp_path):
    """A `.bga`-shaped tree around the committed run fixture.

    `UX-213`'s census caught the first draft of this file putting all
    three of its directional clauses behind `needs_real_capture`, so
    the Falsification - the half that checks the contract against a
    *directory* rather than against the specification - ran on one
    machine and skipped in CI. The clone has no `.bga` store, but it
    does have a real run directory: `tests/fixtures/macro_micro`, whose
    filenames are what the extraction actually wrote, not what this
    contract says it should have.

    So the store shape is assembled here and the *names inside it* come
    from the fixture. What that leaves to the real-capture arm below is
    exactly what only a live capture produces - `build.log`, `.size`,
    `capture-context.txt` - which is one clause rather than three.
    """
    store = tmp_path / run_store.STORE_DIRNAME
    snapshot = store / run_store.RUNS_DIRNAME / "20260821T120000Z"
    snapshot.mkdir(parents=True)
    shutil.copytree(FIXTURE / "run", snapshot / run_store.RUN_SUBDIR)
    shutil.copy(FIXTURE / run_store.PLANE2_NAME,
                snapshot / run_store.PLANE2_NAME)
    (store / ".gitignore").write_text("*\n", encoding="utf-8")
    (store / run_store.SCRATCH_DIRNAME).mkdir()
    return store


class TestACommittedCaptureSatisfiesIt:
    """The Falsification, on a tree every clone has."""

    def test_every_path_on_disk_is_named(self, tmp_path):
        """The first direction. The `run/` subtree's filenames are the
        extraction's own, carried by a committed fixture - so this is
        the contract checked against something that did not come from
        it."""
        declared = set(run_store.layout_paths())
        unnamed = sorted(_walked(_committed_store(tmp_path)) - declared)
        assert unnamed == [], (
            f"path(s) a capture holds that the contract does not name: "
            f"{unnamed}")

    def test_every_required_path_is_present(self, tmp_path):
        on_disk = _walked(_committed_store(tmp_path))
        absent = [path for path, presence, _c, _w in run_store.CAPTURE_LAYOUT
                  if presence == run_store.REQUIRED and path not in on_disk]
        assert absent == [], (
            f"required path(s) this capture does not have: {absent}")

    def test_a_capture_without_plane_two_still_satisfies_it(self, tmp_path):
        """The other direction, so the fix is not "mark everything
        required": this store carries no `plane2.log.gz`, no
        `plane2-resource.json` and no `host-samples.jsonl` at all, and
        the contract calls each of them conditional."""
        store = _committed_store(tmp_path)
        (store / run_store.RUNS_DIRNAME / "20260821T120000Z"
         / run_store.PLANE2_NAME).unlink()
        on_disk = _walked(store)
        absent = [path for path, presence, _c, _w in run_store.CAPTURE_LAYOUT
                  if presence == run_store.REQUIRED and path not in on_disk]
        assert absent == [], (
            "a Plane-2-less capture fails the required set, so a path "
            f"that is conditional in practice is marked required: {absent}")


@needs_real_capture
class TestARealCaptureSatisfiesIt:
    def test_every_path_a_live_capture_adds_is_named(self):
        """What the committed fixture cannot carry: `build.log`,
        `.size` and `capture-context.txt` are written by a capture that
        actually ran, and `UX-189` keeps the archive out of a clone.
        Before this landed the contract named one of twenty-one."""
        declared = set(run_store.layout_paths())
        unnamed = sorted(_walked(REAL) - declared)
        assert unnamed == [], (
            f"path(s) a real capture holds that the contract does not "
            f"name: {unnamed}")



class TestTheOtherTableSaysWhichDirectoryItIs:
    """`capture-workflow.md`'s table describes the CI field-capture
    bundle and names two files differently. It reads as a description
    of a snapshot until it says otherwise."""

    def test_it_scopes_itself(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        assert "native-report.json" in text, "the bundle table has moved"
        head = text.split("| `native-report.json` |", 1)[0]
        scope = head[-1200:]
        assert "not a snapshot" in scope, (
            "the field-capture table still reads as a description of a "
            "capture directory")
        assert "plane2.json" in scope, (
            "the scope note does not say what a snapshot calls the same "
            "file, which is the thing a reader went looking for")

    def test_the_snapshot_layout_is_pointed_at(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        assert "32.6" in text or "capture-layout/v1" in text, (
            "nothing sends the reader to the layout that does describe a "
            "snapshot")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
