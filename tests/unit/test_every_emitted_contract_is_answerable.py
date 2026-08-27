"""UX-328: `--schema` answers for everything that emits one.

The stranger walk found three contradictions in one story, and they
are all the same defect: `UX-190`'s rule - *every document `bga`
writes carries a schema id, and the tool can print that contract* -
was outgrown by three emitters nobody re-enrolled.

```text
$ bga whatif RUN --format json | head -2
{
  "schema": "whatif/v1",
$ bga whatif --schema
Error: ... whatif produces no versioned JSON output.
```

The refusal was **falsified by the tool's own output two lines up**,
and the same held for `store/v1` and `store-aggregate/v1`.

**So the guard here is structural rather than a second list.** A list
of enrolled commands is exactly what fell behind; three emitters were
added and the list was not. This derives both sides:

- what is **emitted**, by running each command over a fixture run and
  reading the `schema:` id out of its own stdout;
- what is **answerable**, from `bga <cmd> --schema` really running;
- what is **written into a run directory** instead of printed, which
  is the one legitimate reason for an id to have no command - declared
  below with the file it lives in, so "no command prints this" is a
  statement someone had to write down rather than a gap.

Their union has to be the contract inventory, which `bga.contracts`
derives from the package. A new emitter cannot outgrow this without
reddening: it either answers `--schema`, or it is declared as
file-written, or the union stops matching.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts, schemas                     # noqa: E402

RUN = REPO / "tests/fixtures/golden/mixed_task_kinds"
#: The two-plane fixture, because `correlate` is a *join* - it refuses
#: a run with no Plane 2 report, and rightly.
MACRO = REPO / "tests/fixtures/macro_micro/run"
PLANE2 = REPO / "tests/fixtures/macro_micro/plane2.json"

#: Every command that prints a JSON document, and the argv that makes
#: it. The point of running these is that the *tool* says what it
#: emits - a table of expected ids here would be the list this guard
#: exists to replace.
EMITTERS = {
    "analyze": ["analyze", str(RUN), "--format", "json"],
    "compare": ["compare", str(RUN), str(RUN), "--format", "json"],
    "blast": ["blast", "toolchain.bst", str(RUN), "--format", "json"],
    "correlate": ["correlate", str(MACRO), str(PLANE2),
                  "--format", "json"],
    "whatif": ["whatif", str(RUN), "--format", "json"],
    "sweep": ["sweep", str(RUN), "--format", "json"],
    "graph": ["graph", str(RUN), "--format", "json"],
    "floors": ["floors", str(RUN), "--format", "json"],
    "replay": ["replay", str(RUN), "--format", "json"],
    "utilisation": ["utilisation", str(RUN), "--format", "json"],
    "diagnostics": ["diagnostics", str(RUN), "--format", "json"],
}

#: Commands whose JSON carries no `schema:` id at all. "Emits nothing
#: versioned" is a claim, so the clauses below run each one and assert
#: the *absence* - an id appearing later reddens rather than sitting
#: unenrolled.
#:
#: **Empty since `UX-339`.** It held `sweep` for exactly one round:
#: `UX-328` found `bga sweep --schema` printing `analyze/v2` for a
#: document with none of that contract's four required keys, de-enrolled
#: it so the tool said what was true, and filed the contract the
#: document wanted. `sweep/v1` landed, `sweep` moved into `EMITTERS`,
#: and the equality clause covers it by existing - which is what
#: `UX-328`'s Acceptance Test said would happen.
NO_CONTRACT = {}

#: Ids written into a run directory rather than printed by a command,
#: each with the file it lives in. This is the *only* legitimate reason
#: for a contract to have no `--schema` invocation, so it is declared
#: rather than inferred - and the file name is what makes the claim
#: checkable by a reader with a run directory in front of them.
FILE_WRITTEN = {
    "host/v1": "run-context.json (bga.hostinfo)",
    "sources/v1": "sources.json (bga extract)",
    "plane2/v2": "plane2.json (bga capture)",
    # `UX-297` retired this one. Still read, never written - which is a
    # third state, and the reason `contracts.superseded()` exists.
    "plane2/v1": "plane2.json, as a capture before UX-297 wrote it",
}


def _bga(*argv, expect=0):
    done = subprocess.run([sys.executable, "-m", "bga.cli", *argv],
                          capture_output=True, text=True, cwd=str(REPO),
                          timeout=180,
                          env={**os.environ, "PYTHONPATH": str(REPO)})
    if expect is not None:
        assert done.returncode == expect, (argv, done.returncode,
                                           done.stderr[-2000:])
    return done


@pytest.fixture(scope="module")
def emitted():
    """`{command: the id it printed}`, read from the tool's own stdout."""
    found = {}
    for name, argv in EMITTERS.items():
        done = _bga(*argv)
        document = json.loads(done.stdout)
        assert "schema" in document, (
            f"`bga {name} --format json` prints a document with no `schema` "
            f"key, which UX-190 forbids before this guard even applies")
        found[name] = document["schema"]
    return found


@pytest.fixture(scope="module")
def answerable():
    """`{invocation: the id it prints}`, by really running `--schema`."""
    from bga.cli import _SCHEMA_BY_COMMAND, _SCHEMA_BY_FLAG

    found = {}
    for command in _SCHEMA_BY_COMMAND:
        done = _bga(command, "--schema")
        found[command] = json.loads(done.stdout)["title"]
    for command, pairs in _SCHEMA_BY_FLAG.items():
        for flag, _ in pairs:
            done = _bga(command, flag, "--schema")
            found[f"{command} {flag}"] = json.loads(done.stdout)["title"]
    return found


class TestTheUnversionedDocumentsAreDeclared:
    """`UX-328` was filed for three ids `--schema` would not answer.
    Enrolling them turned up a fourth defect one turn worse.

    `bga sweep --schema` printed `analyze/v2` while `bga sweep --format
    json` emitted a document with **none** of that contract's four
    required keys. A missing answer sends a reader to look; a
    confidently wrong one sends them to write a parser against a shape
    that does not exist.
    """

    def test_the_set_is_empty_and_that_is_the_point(self):
        """`UX-339` emptied it, and the emptiness is the claim.

        Every command this tool has that prints a document now answers
        `--schema` for it. `NO_CONTRACT` stays as the honest place to
        declare the next one while its contract is being written - a
        command that printed an unversioned document and was in neither
        table would be invisible to the union below.
        """
        assert NO_CONTRACT == {}, (
            "a command is declared as printing an unversioned document; "
            "the clauses below check that claim, and its contract is "
            "owed", sorted(NO_CONTRACT))

    def test_any_declared_one_really_emits_no_id(self):
        """Looped rather than parametrized: an empty parametrize is a
        *skip*, and a clause that runs nowhere is what this repository
        spends its census on. Vacuous here, live the moment an entry is
        added."""
        for command, argv in sorted(NO_CONTRACT.items()):
            document = json.loads(_bga(*argv).stdout)
            assert "schema" not in document, (
                f"`bga {command}` emits `{document.get('schema')}` now, so "
                f"it belongs in EMITTERS and in the enrolment table - being "
                f"declared unversioned is no longer true of it")

    def test_schema_refuses_for_them_rather_than_guessing(self):
        from bga.cli import _SCHEMA_BY_COMMAND

        for command in sorted(NO_CONTRACT):
            assert command not in _SCHEMA_BY_COMMAND, (
                f"`bga {command} --schema` answers with a contract its own "
                f"output does not satisfy")
            done = _bga(command, "--schema", expect=2)
            assert "no schema id yet" in done.stderr, done.stderr

    def test_the_sweep_now_answers_with_a_contract_that_fits(self):
        """`UX-339`, and the measurement that made `UX-328` de-enrol it
        kept rather than summarised.

        `bga sweep --schema` printed `analyze/v2` for a document with
        **zero of four** of that contract's required keys - not "a
        different shape" but no overlap at all. It has `sweep/v1` now,
        and this asserts both halves: the wrong contract still does not
        fit, and the right one does.
        """
        from bga import schemas

        document = json.loads(
            _bga("sweep", str(RUN), "--format", "json").stdout)
        analyze = schemas.schema(schemas.ANALYZE)["required"]
        assert [key for key in analyze if key in document] == ["schema"], (
            "sweep's document overlaps analyze/v2 by more than the id "
            "every document has - re-read why it was de-enrolled",
            sorted(document))
        assert document["schema"] == schemas.SWEEP, document["schema"]
        fits = schemas.schema(schemas.SWEEP)["required"]
        assert [key for key in fits if key not in document] == [], (
            "the document does not carry what its own contract requires",
            sorted(document))


class TestEveryEmittedIdIsAnswerable:
    def test_each_emitter_answers_with_the_id_it_emits(self, emitted):
        """Equality, per command. `bga whatif --schema` printing *some*
        contract would satisfy "it answers"; it has to print the one
        `bga whatif --format json` writes."""
        from bga.cli import _SCHEMA_BY_COMMAND, _SCHEMA_BY_FLAG

        wrong = {}
        for command, contract in emitted.items():
            enrolled = _SCHEMA_BY_COMMAND.get(command)
            if enrolled is None:
                for flag, name in _SCHEMA_BY_FLAG.get(command, ()):
                    enrolled = enrolled or name
            if enrolled != contract:
                wrong[command] = (contract, enrolled)
        assert not wrong, (
            "these commands emit an id `--schema` does not answer with; "
            "the refusal they print is falsified by their own output", wrong)

    def test_the_flagged_command_answers_per_flag(self):
        """`bga snapshot` is one command and two documents. Answering
        `--aggregate --schema` with `store/v1` would be a confident
        wrong answer, which is worse than the missing one this
        replaced."""
        listed = json.loads(_bga("snapshot", "--list", "--schema").stdout)
        aggregated = json.loads(
            _bga("snapshot", "--aggregate", "--schema").stdout)
        assert listed["title"] == "bga snapshot --list --format json", listed
        assert aggregated["title"] == \
            "bga snapshot --aggregate --format json", aggregated
        assert listed != aggregated

    def test_the_bare_flagged_command_says_which_flags_have_one(self):
        """Not a bare refusal: `bga snapshot` without a flag writes a
        run directory, and the reader needs the two flags that do print
        a document."""
        done = _bga("snapshot", "--schema", expect=2)
        assert "--aggregate" in done.stderr and "--list" in done.stderr, \
            done.stderr


class TestTheUnionIsTheInventory:
    """The structural half. Neither side is a list anybody maintains."""

    def test_answerable_plus_file_written_is_every_contract(self, answerable):
        from bga.cli import _SCHEMA_BY_COMMAND, _SCHEMA_BY_FLAG

        printed = set(_SCHEMA_BY_COMMAND.values())
        for pairs in _SCHEMA_BY_FLAG.values():
            printed |= {name for _, name in pairs}
        assert printed | set(FILE_WRITTEN) == set(contracts.ids()), (
            "a contract is neither answerable nor declared as written into "
            "a run directory - it is invisible to a reader who asks the "
            "tool what shape it is",
            sorted(set(contracts.ids()) - printed - set(FILE_WRITTEN)),
            sorted(printed & set(FILE_WRITTEN)))

    def test_nothing_is_both_printed_and_declared_file_written(self):
        from bga.cli import _SCHEMA_BY_COMMAND, _SCHEMA_BY_FLAG

        printed = set(_SCHEMA_BY_COMMAND.values())
        for pairs in _SCHEMA_BY_FLAG.values():
            printed |= {name for _, name in pairs}
        assert not (printed & set(FILE_WRITTEN)), (
            "declared as file-written and answerable at once, so the "
            "declaration is stale", sorted(printed & set(FILE_WRITTEN)))

    def test_every_answerable_id_has_a_printable_schema(self, answerable):
        """`--schema` printing something `schemas.py` cannot describe
        would be a crash, not a contract."""
        assert len(answerable) >= len(EMITTERS), answerable
        assert set(contracts.printable()) <= set(contracts.ids())

    def test_the_superseded_id_is_declared_and_not_answerable(self):
        """`plane2/v1` is read and never written. A third state, and one
        `--schema` must not offer as if a command produced it."""
        assert contracts.superseded() == ["plane2/v1"], \
            contracts.superseded()
        assert "plane2/v1" in FILE_WRITTEN


class TestAnUnknownNameAndABrokenContractAreDifferentThings:
    """The second defect `UX-339` turned up, found by its own mutation.

    `schema()` was `return _SCHEMAS[name]()` under one `except
    KeyError`, so a `KeyError` raised *inside* a document's builder -
    which is how `_check_hint` reports a view-hint for a key the
    required map does not have - came back as:

    ```text
    KeyError: "unknown schema 'sweep/v1' - this tool produces
               analyze/v2, ..., sweep/v1, ..."
    ```

    A message that names the thing it says it does not know, and sends
    the reader looking for a missing registry entry that is right
    there. The lookup and the build are separate statements now, and
    these two clauses are what keeps them apart.
    """

    def test_a_name_that_is_not_in_the_registry_says_so(self):
        with pytest.raises(KeyError) as raised:
            schemas.schema("not-a-contract/v1")
        assert "unknown schema" in str(raised.value)

    def test_a_contract_that_raises_while_building_does_not_say_unknown(
            self, monkeypatch):
        """The positive control, applied to the real registry so the
        clause cannot pass against a stub of its own making."""
        def explode():
            raise KeyError(f"{schemas.SWEEP}: view-hint for unknown key")

        monkeypatch.setitem(schemas._SCHEMAS, schemas.SWEEP, explode)
        with pytest.raises(KeyError) as raised:
            schemas.schema(schemas.SWEEP)
        assert "unknown schema" not in str(raised.value), (
            "a broken contract still reports as a missing one, which is "
            "the message that sent the last reader to the wrong file")
        assert "view-hint" in str(raised.value)


class TestTheDocumentSaysWhatTheToolDoes:
    """`docs/README.md`'s "What it emits" block, held to the inventory."""

    @staticmethod
    def _block():
        text = (REPO / "docs/README.md").read_text(encoding="utf-8")
        start = text.index("## What it emits")
        return text[start:text.index("\n## ", start + 4)]

    def test_the_count_matches_the_inventory(self):
        """It said "Nine ids" over a table of eleven."""
        block = self._block()
        rows = re.findall(r"^\| `([a-z][a-z0-9-]*/v\d+)` \|", block, re.M)
        assert sorted(rows) == contracts.ids(), (
            "the table and the derived inventory disagree",
            sorted(set(rows) ^ set(contracts.ids())))
        words = {"nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
                 "thirteen": 13}
        claimed = re.search(r"\b(" + "|".join(words) + r")\b ids", block,
                            re.I)
        assert claimed, "the block no longer states a count at all"
        assert words[claimed.group(1).lower()] == len(rows), (
            f"the block says {claimed.group(1)} ids over {len(rows)} rows")

    def test_it_does_not_promise_a_form_that_errors(self):
        """`bga --schema <id>` is not a thing this tool has. It is
        `bga <command> --schema`, and the document promised the other
        one - which is the first thing a reader tries."""
        block = self._block()
        assert "`bga --schema <id>`" not in block, (
            "the block still promises a global dispatcher; the working "
            "form is `bga <command> --schema`")

    def test_the_unknown_to_schema_sentence_counts_correctly(self):
        """It claimed "the last four" were unknown to `--schema` when
        seven were. Now that whatif/store/store-aggregate answer, four
        is the true number - and this holds it to the declaration
        rather than to the sentence staying as it is."""
        block = self._block()
        assert len(FILE_WRITTEN) == 4, FILE_WRITTEN
        assert "last four" in block, block[-800:]
        rows = re.findall(r"^\| `([a-z][a-z0-9-]*/v\d+)` \|", block, re.M)
        assert set(rows[-len(FILE_WRITTEN):]) == set(FILE_WRITTEN), (
            "the sentence says 'the last four' but the last four rows of "
            "the table are not the four file-written ids",
            rows[-len(FILE_WRITTEN):], sorted(FILE_WRITTEN))
