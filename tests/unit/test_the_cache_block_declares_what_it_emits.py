"""UX-438: the page guessed a unit on a real capture, and said so.

Booting the export of a real capture of `examples/06` and pressing
every one of its 468 controls produced exactly one console message:

```text
bga: transfer_share has no bga:quantity; guessed share
```

`UX-201`'s rule is *a hint is a declaration, never a guess*, and the
guess is a schema gap rather than a feature.

**Where the gap actually was.** The item's own hypothesis was that a
finding's `evidence` is a free-form object carrying no hints. That is
wrong, and reading it settled it: `findings[].evidence` declares
`properties: EVIDENCE_QUANTITIES`, and `transfer_share` has been in it
since `UX-217`. The undeclared copy was in the **population**, not the
quotation - `cache`, where `compute_cache_accounting` adds `transfer_us`
and `transfer_share` only when the run moved artifacts.

**Why no fixture could see it.** The two committed runs each have half
of what it takes to produce that block:

| fixture | Pipeline Summary | transfer span |
|---|---|---|
| `golden` | no | yes (one `DOWNLOAD`) |
| `macro_micro` | yes | no |

`compute_cache_accounting` returns `{}` without a summary, and adds
nothing without a span. So the fields were undeclared for as long as
they have existed and every guard was green - the same shape as the
rest of round 69's findings: **a real capture says things the fixtures
cannot.**

**Measured, through the page's own resolution**, on a `macro_micro`
copy carrying `TRANSFER_SPANS` (`tests/pages.py`):

```text
before   declared 863   guessed ['cache.transfer_share']
                        neither ['cache.transfer_us.DOWNLOAD',
                                 'cache.transfer_us.UPLOAD', ...]
after    declared 866   guessed []
                        neither [the two `provenance` entries `UNDECLARABLE`
                                 already names]
```

The map beside the warning was worse than the key that warned: no unit
at all, and silent, because a value with nothing to sniff produces no
complaint. Which is the item's second bullet - *check the whole map, not
the one key that warned* - and the reason `test_every_key_it_emits_is_declared`
below walks keys rather than numbers. That clause is what finds
`target_closure.targets`, a list of element names emitted since the
closure was and declared by nothing: no quantity to guess, so no console
message, so nothing ever said it was missing.
"""
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "tests/unit"))

import pages

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

SOURCE = REPO / "tests/fixtures/macro_micro/run"


@pytest.fixture(scope="module")
def emitted(tmp_path_factory):
    """The analyze document of a run that moved artifacts."""
    from tools.bga_view import payloads

    run = pages.transfer_run(SOURCE, tmp_path_factory.mktemp("transfer"))
    return payloads(str(run))["report.json"]


def test_the_fixture_produces_the_block_that_was_never_tested(emitted):
    """Otherwise every clause below passes by finding nothing.

    This is the setup the whole item turns on: a guard whose fixture
    cannot produce the shape it tests is one this repository has now
    found nine times.
    """
    cache = emitted.get("cache") or {}
    assert cache.get("transfer_us"), (
        f"the run published no transfer at all: {sorted(cache)}")
    assert isinstance(cache.get("transfer_share"), float), cache.get(
        "transfer_share")


def _undeclared(value, node, path):
    """Key paths under `value` that the schema node says nothing about.

    Keys, not numbers: the unit census below reads numeric leaves
    through the page's own resolution, and a list of names has no unit
    to resolve - which is exactly how `target_closure.targets` stayed
    invisible. Descriptions have one channel (`properties`, then
    `additionalProperties`), so walking them here re-implements nothing
    that `quantityFor` resolves through several.
    """
    if not isinstance(value, dict):
        return []
    missing = []
    for key, sub in value.items():
        inside = (node or {}).get("properties", {}).get(key)
        if inside is None:
            below = (node or {}).get("additionalProperties")
            inside = below if isinstance(below, dict) else None
        if inside is None or "description" not in inside:
            missing.append(".".join(path + [key]))
            continue
        missing += _undeclared(sub, inside, path + [key])
    return missing


def test_every_key_it_emits_is_declared(emitted):
    """The whole map, not the one key that warned."""
    from bga import schemas

    cache = emitted["cache"]
    node = schemas.schema(emitted["schema"])["properties"]["cache"]
    missing = _undeclared(cache, node, ["cache"])
    assert missing == [], (
        f"published by `compute_cache_accounting` and described by "
        f"nothing: {missing}")


@needs_node
def test_no_number_in_it_renders_from_a_guess(emitted):
    """The console message itself, read where CI can read it.

    `test_the_console_stays_clean.py` reads the real complaint on a
    real boot and needs a browser, so it is skipped wherever there is
    none - including CI. This resolves the same document through the
    same viewer module under Node, so the gap that produced the message
    cannot come back on a machine with no Chrome.
    """
    from test_every_number_says_what_it_is import UNDECLARABLE, _census_document

    census = _census_document(emitted)
    assert census["guessed"] == [], (
        f"{len(census['guessed'])} numeric leaves render from a "
        f"name-sniffed guess: {census['guessed']}")
    unexpected = sorted(set(census["neither"]) - set(UNDECLARABLE))
    assert unexpected == [], (
        f"numeric leaves with no unit at all and no entry saying why: "
        f"{unexpected}")


@needs_node
def test_the_walk_reached_the_transfer_block(emitted):
    """A census that never descended into `cache` would pass the clause
    above by having nothing to complain about. Named paths rather than a
    count: a count moves whenever anything else in the document does.
    """
    import os
    import subprocess
    import tempfile

    from test_every_number_says_what_it_is import _CENSUS

    from bga import schemas

    scratch = pathlib.Path(tempfile.mkdtemp())
    (scratch / "payload.json").write_text(json.dumps(emitted))
    (scratch / "schemas.json").write_text(
        json.dumps({name: schemas.schema(name) for name in schemas.names()}))
    reached = _CENSUS.replace(
        "declared: declared.length,", "declared: declared,")
    done = subprocess.run(
        [node, "--input-type=module", "-e", reached],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
             "BGA_VIEWER": (REPO / "tests/viewer.mjs").as_uri(),
             "BGA_PAYLOAD": str(scratch / "payload.json"),
             "BGA_SCHEMAS": str(scratch / "schemas.json")})
    assert done.returncode == 0, done.stderr
    declared = set(json.loads(done.stdout)["declared"])
    for path in ("cache.transfer_share", "cache.transfer_us.DOWNLOAD",
                 "cache.transfer_us.UPLOAD"):
        assert path in declared, (
            f"{path} is not among the leaves the walk resolved - the "
            f"census is not reaching the block this item is about")
