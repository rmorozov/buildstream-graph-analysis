"""UX-353: a document that says "today" names the contract written today.

Review 5 read `docs/design/roles.md`'s "bga today" column and found
role R2 served by `correlate/v1`:

```text
| R2 | The recipe author | ... | **Served.** The element object
      (`correlate/v1`), blast by resource, element history, Plane 2 lanes |
```

`UX-341` moved the join to `correlate/v2` in round 51. Every other
document had followed:

```text
docs/spec/specification.md:1652  | `bga correlate --format json` | `correlate/v2` |
docs/design/architecture.md:869  | `correlate/v2` | the two planes joined ...
docs/design/architecture.md:882  | `correlate/v1` | ... Read, never written
docs/README.md:63                | `correlate/v2` | `bga correlate --format json` ...
docs/design/roles.md:40          | R2 | ... (`correlate/v1`) ...
```

`test_the_documents_keep_up_with_the_contracts.py` asks whether every
contract *has a home*; nothing asked whether a home names a contract
the tool still writes. `roles.md` is the one design document naming an
id that guard does not read, which is why the mechanical half missed
it.

**The rule, and why it is not "do not mention v1".** A superseded id
has to be nameable: `docs/README.md` and `architecture.md` both carry
a table of them, and the whole point of those rows is to tell a reader
holding an old payload that the tool still reads it. What separates
those rows from `roles.md`'s cell is that they *say so*. So an
occurrence is legitimate when the block it sits in states the
retirement, and a finding when it does not - which is exactly the
distinction a reader makes.
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

#: Where a reader looks for what the tool does *now*. `docs/audits/` and
#: `docs/backlog/` are out by construction: an audit round and a
#: scenario filing are both dated records of what was true when they
#: were written, and review 5 made the same argument for review 4's own
#: text. `docs/spec/` is ground truth and names every id by design.
ROOTS = ("docs/README.md", "docs/design", "docs/guides")

#: The vocabulary these documents already use for a retired contract.
#: Small on purpose - a marker set that grows to fit whatever a
#: document happens to say stops being a check.
MARKERS = ("never written", "only ever *read*", "superseded")

#: `directions.md` is exempt, and the exemption is *conditional*: the
#: document opens by saying it is an argument rather than a statement
#: of the present, and points at `architecture.md` for what the tool is
#: today. `test_the_exemption_still_earns_itself` holds it to that.
DATED = {"directions.md": "for what the tool is today"}


def _superseded():
    from bga import contracts

    return contracts.superseded()


def _blocks(text):
    """`(first_line, [lines])` per markdown block.

    A block is a run of non-blank lines: one table row, or one
    paragraph. Line-scoped would be wrong - `docs/README.md`'s sentence
    about the retired set names `analyze/v3` on its own line and states
    the retirement two lines above, in the same paragraph, which is
    where a reader takes it from.
    """
    out, current, start = [], [], None
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if start is None:
                start = number
            current.append(line)
        elif current:
            out.append((start, current))
            current, start = [], None
    if current:
        out.append((start, current))
    return out


def _documents():
    for root in ROOTS:
        path = REPO / root
        if path.is_file():
            yield path
        else:
            yield from sorted(path.rglob("*.md"))


def _findings():
    retired = _superseded()
    found = []
    for path in _documents():
        if path.name in DATED:
            continue
        for start, block in _blocks(path.read_text(encoding="utf-8")):
            text = " ".join(block)
            if any(marker in text for marker in MARKERS):
                continue
            for contract in retired:
                if contract not in text:
                    continue
                # The block decides whether it is a finding; the *line*
                # is what a reader has to go and change, and a table is
                # one block of forty rows.
                for offset, line in enumerate(block):
                    if contract in line:
                        found.append((path.relative_to(REPO).as_posix(),
                                      start + offset, contract,
                                      line.strip()[:120]))
                        break
    return found


class TestNoLiveDocumentServesARetiredContract:
    def test_the_population_is_not_empty(self):
        """The instrument first. A walk that reaches no document, or a
        `superseded()` that returns nothing, passes this file forever
        while asserting nothing."""
        assert len(list(_documents())) >= 5
        assert len(_superseded()) >= 5, _superseded()

    def test_every_retired_id_says_it_is_retired(self):
        bad = _findings()
        assert bad == [], (
            "a document a reader reads for what bga does today names a "
            "contract nothing writes, without saying so:\n"
            + "\n".join(f"  {name}:{line}  {contract}\n      {text}"
                        for name, line, contract, text in bad))

    def test_the_retired_tables_are_still_reachable_by_this_walk(self):
        """The other direction, and the one that makes the clause above
        mean something: both retired-contract tables *do* name these
        ids, and are passing because their rows say "never written" -
        not because the walk stopped seeing them."""
        retired = set(_superseded())
        seen = set()
        for path in _documents():
            if path.name in DATED:
                continue
            text = path.read_text(encoding="utf-8")
            seen.update(name for name in retired if name in text)
        assert len(seen) >= 5, (
            f"the walk finds only {sorted(seen)} of {sorted(retired)} - it "
            f"has stopped reading the tables it is meant to be allowing")

    def test_the_exemption_still_earns_itself(self):
        """`directions.md` is skipped because it says, in its own
        opening, that it is an argument about direction and that
        `architecture.md` is where the present tense lives. If that
        sentence goes, so does the reason to skip the file."""
        for name, sentence in DATED.items():
            found = [path for path in _documents() if path.name == name]
            assert found, f"{name} is exempted and does not exist"
            assert sentence in found[0].read_text(encoding="utf-8"), (
                f"{name} no longer says {sentence!r}, which is the whole "
                f"reason this guard skips it")


class TestTheRoleTableNamesTheLiveJoin:
    """The finding itself, pinned. The guard above would pass on a
    `roles.md` that dropped the id entirely; this says which contract
    the row is supposed to name."""

    def test_r2_is_served_by_the_current_correlate(self):
        from bga import schemas

        text = (REPO / "docs/design/roles.md").read_text(encoding="utf-8")
        row = [line for line in text.splitlines()
               if line.startswith("| R2 ")]
        assert len(row) == 1, row
        assert schemas.CORRELATE in row[0], (
            f"R2 is served by the element object, whose contract is "
            f"{schemas.CORRELATE}: {row[0]}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
