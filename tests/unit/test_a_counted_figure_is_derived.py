"""UX-549: five counted figures a reader reads as the document's own arithmetic.

Architecture review 12, checklist item 3. Measured when this was filed:

```text
docs/README.md:88                      "eight ... only ever read"   9
docs/design/architecture.md:965        "The last four rows are      6, and not last
                                        written but not printable"
CHANGELOG.md:5                         "the twelve published        23
                                        contracts"
README.md:114                          "all thirteen canned         17
                                        questions"
docs/guides/what-the-viewer-answers.md "25 top-level sections"      53
  :19-26                               "19 keys each"               24
```

The last is the evidence block for that guide's own central rule and
had been wrong since `UX-344` lifted two namespaces; five reviews read
past it. Every figure below is recomputed from the population it
describes, so the next move in that population reddens a guard instead
of ageing a sentence.

`UX-556` closed the spec's copy (`specification.md:1671`). It sits
inside Part 32, which the rule has always permitted editing; the
deferral above read "the Part 32 registry" as the table alone. The
sentence is now derived here like the other five.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts  # noqa: E402

INDEX = REPO / "docs/README.md"
ARCHITECTURE = REPO / "docs/design/architecture.md"
CHANGELOG = REPO / "CHANGELOG.md"
README = REPO / "README.md"
GUIDE = REPO / "docs/guides/what-the-viewer-answers.md"
SPEC = REPO / "docs/spec/specification.md"
QUESTIONS_JS = REPO / "bga/viewer/questions.js"
RUN = REPO / "tests/fixtures/macro_micro/run"

#: How these documents spell a count. The map is the vocabulary, not
#: the claim - it grows ahead of the numbers rather than being chased
#: by them (`UX-341`'s lesson, in `test_every_emitted_contract_is
#: _answerable.py`).
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
         7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
         12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
         16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen",
         20: "twenty", 21: "twenty-one", 22: "twenty-two",
         23: "twenty-three", 24: "twenty-four", 25: "twenty-five",
         26: "twenty-six", 27: "twenty-seven", 28: "twenty-eight",
         29: "twenty-nine", 30: "thirty"}


def _flat(text):
    """One line, so a claim is read as a sentence rather than as a
    line-wrap. Where the wrap falls is the author's, not the claim's."""
    return " ".join(text.split())


def _emitted_block():
    """`docs/README.md`'s "What it emits" section, subject only."""
    text = INDEX.read_text(encoding="utf-8")
    start = text.index("## What it emits")
    return text[start:text.index("\n## ", start + 4)]


def _inventory_chapter():
    text = ARCHITECTURE.read_text(encoding="utf-8")
    return text.split("## The published contracts", 1)[1].split("\n## ", 1)[0]


def _inventory_rows():
    return re.findall(r"^\| `([a-z][a-z0-9-]*/v\d+)` \|",
                      _inventory_chapter(), re.M)


def _questions():
    """Every id in `questions.js`'s exported array.

    Parsed rather than imported, so the count is checkable without a
    node runtime; `test_node_agrees_on_the_count` confirms the parse
    against the real module where node exists.
    """
    text = QUESTIONS_JS.read_text(encoding="utf-8")
    body = text.split("export const QUESTIONS = [", 1)[1].split("\n];", 1)[0]
    return re.findall(r'^    id: "([a-z-]+)"', body, re.M)


class TestTheIndexCountsWhatItReadsAndNeverWrites:
    """`docs/README.md:88`. The sibling figure on the same line -
    "the last fifteen" - has been derived since `UX-341`; this one was
    restated beside it and drifted by one when `UX-535` retired
    `analyze/v4`."""

    def test_the_read_only_count_is_the_superseded_set(self):
        block = _flat(_emitted_block())
        word = WORDS[len(contracts.superseded())]
        assert f"{word} of those are only ever *read*" in block, (
            f"the block should say '{word} of those are only ever read'; "
            f"`contracts.superseded()` is {len(contracts.superseded())}",
            block[-1200:])

    def test_the_printable_count_beside_it_is_the_printable_set(self):
        """`The other eight` on the next line, held to the same rule -
        it is correct today and was restated, which is how the figure
        above got here."""
        block = _flat(_emitted_block())
        word = WORDS[len(contracts.printable())]
        assert f"The other {word} each have a command" in block, (
            f"the block should say 'The other {word}'; "
            f"`contracts.printable()` is {len(contracts.printable())}")


def _spec_contract_block():
    """Part 32's contract prose - from its registry table to the next
    Part. Bounded so a count elsewhere in the file cannot satisfy it."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("| output | schema | printed by |")
    return text[start:text.index("\n# Part 33")]


def _spec_contract_rows():
    """The ids each row of Part 32's registry table declares, in order.

    A row may declare several (`UX-341` renamed four documents in one),
    so this is a list of lists and the callers flatten it.
    """
    rows = []
    for line in _spec_contract_block().splitlines():
        # The registry table only. `UX-540`'s inputs table follows it
        # further down the Part, and reading both put `trace/v9` among
        # the retired rows - the first version of this clause failed
        # exactly that way.
        if not line.strip():
            break
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(cells) < 2 or cells[1] == "schema":
            continue
        found = re.findall(r"`([a-z0-9-]+/v\d+)`", cells[1])
        if found:
            rows.append(found)
    return rows


class TestTheArchitectureCountsItsOwnTable:
    """`docs/design/architecture.md:965`, and the two classes really are
    read off the table's rows rather than from the sentence."""

    def test_the_written_not_printable_count_is_derived(self):
        written = set(contracts.unprintable()) - set(contracts.superseded())
        word = WORDS[len(written)]
        assert f"{word.capitalize()} rows are written but not printable" \
            in _flat(_inventory_chapter()), (
                f"the chapter should say '{word.capitalize()} rows are "
                f"written but not printable'; the set is {sorted(written)}")

    def test_the_read_never_written_rows_are_the_last_ones(self):
        """The other half of the old sentence's error: it said *last*
        of a class that nine rows follow."""
        rows = _inventory_rows()
        retired = contracts.superseded()
        word = WORDS[len(retired)]
        assert f"The last {word} go one further" in _flat(
            _inventory_chapter()), (
            f"the chapter should say 'The last {word} go one further'")
        assert set(rows[-len(retired):]) == set(retired), (
            "the last rows of the inventory are not the read-never-written "
            "ones, so the sentence points at the wrong end of the table",
            rows[-len(retired):], retired)

    def test_the_rows_before_them_are_the_written_not_printable_ones(self):
        rows = _inventory_rows()
        written = set(contracts.unprintable()) - set(contracts.superseded())
        start = len(rows) - len(contracts.superseded()) - len(written)
        end = len(rows) - len(contracts.superseded())
        assert set(rows[start:end]) == written, (
            "the rows above the retired ones are not the written-but-not-"
            "printable set", rows[start:end], sorted(written))


class TestTheSpecCountsItsOwnTable:
    """`UX-556`: `specification.md:1671`, the sixth copy.

    The spec said "The last four are written but not printable" of a
    set that is six and that four rows follow. `UX-549` fixed the
    architecture's copy and filed this one, reading the rule as
    forbidding the edit; the sentence is inside Part 32, which the rule
    permits. Derived here so it cannot drift again - a count in prose
    that nothing checks is what produced both copies.
    """

    def test_the_written_not_printable_count_is_derived(self):
        written = set(contracts.unprintable()) - set(contracts.superseded())
        word = WORDS[len(written)]
        assert (f"The {word} above the retired rows are **written but not "
                f"printable**") in _flat(_spec_contract_block()), (
            f"Part 32 should say 'The {word} above the retired rows'; "
            f"the set is {sorted(written)}")

    def test_they_really_are_above_the_retired_rows(self):
        """The other half of the error: *last* of a class four rows
        follow. Read off the table, not off the sentence."""
        rows = _spec_contract_rows()
        retired, written = set(contracts.superseded()), (
            set(contracts.unprintable()) - set(contracts.superseded()))
        tail = [one for row in rows[-4:] for one in row]
        assert set(tail) == retired, (
            "the last rows of Part 32's table are not the retired ones, so "
            "the sentence points at the wrong end", tail, sorted(retired))
        above = [one for row in rows[-4 - len(written):-4] for one in row]
        assert set(above) == written, (
            "the rows above the retired ones are not the written-but-not-"
            "printable set", above, sorted(written))


class TestTheChangelogCountsThePublishedSet:
    """`CHANGELOG.md:5`. The file's own state block listed 23 while its
    opening sentence said twelve."""

    def test_the_opening_sentence_counts_the_contracts(self):
        head = _flat(
            CHANGELOG.read_text(encoding="utf-8").split("\n## ", 1)[0])
        word = WORDS[len(contracts.ids())]
        assert f"{word} published contracts" in head, (
            f"CHANGELOG.md's opening should say '{word} published "
            f"contracts'; `contracts.ids()` is {len(contracts.ids())}",
            head[:600])


class TestTheFrontDoorCountsTheCannedQuestions:
    """`README.md:114`. Three questions were added over three rounds;
    the guide's own count was corrected and the front door's was not."""

    def test_the_front_door_counts_the_library(self):
        word = WORDS[len(_questions())]
        assert f"sorts all {word} canned questions" in _flat(
            README.read_text(encoding="utf-8")), (
            f"README.md should say 'sorts all {word} canned questions'; "
            f"questions.js exports {len(_questions())}")

    def test_the_guide_counts_the_same_library(self):
        """The document the sentence points at, so the two cannot drift
        apart again in the other direction."""
        word = WORDS[len(_questions())]
        assert f"serves {word} questions" in _flat(
            GUIDE.read_text(encoding="utf-8")), (
            f"the guide should say '`bga view` serves {word} questions'")

    @pytest.mark.skipif(shutil.which("node") is None,
                        reason="node is not installed")
    def test_node_agrees_on_the_count(self):
        """The parse above is a text scan; this is the module itself."""
        out = subprocess.run(
            [shutil.which("node"), "--input-type=module", "-e",
             'const q = await import("./bga/viewer/questions.js");'
             'console.log(JSON.stringify(q.QUESTIONS.map((x) => x.id)));'],
            capture_output=True, text=True, cwd=str(REPO), timeout=60)
        assert out.returncode == 0, out.stderr
        assert json.loads(out.stdout) == _questions()


class TestTheGuidesEvidenceBlockIsTheReport:
    """`docs/guides/what-the-viewer-answers.md:19-26` - the evidence for
    that document's central rule, measured on the fixture it names."""

    @staticmethod
    def _report():
        from tools.bga_view import payloads

        return payloads(str(RUN))["report.json"]

    @staticmethod
    def _block():
        text = GUIDE.read_text(encoding="utf-8")
        start = text.index("Measured on `tests/fixtures/macro_micro/run`")
        return text[start:text.index("```", text.index("```", start) + 3)]

    def test_the_section_count_is_the_reports(self):
        report = self._report()
        assert f"report.json {len(report)} top-level sections" in _flat(
            self._block()), (
                f"the block should count {len(report)} top-level sections")

    def test_the_element_join_shape_is_the_reports(self):
        rows = self._report()["element_join"]
        widths = {len(row) for row in rows}
        assert len(widths) == 1, f"element_join rows differ in width: {widths}"
        assert f"{len(rows)} elements, {widths.pop()} keys each" \
            in _flat(self._block()), (
                "the block should count the element_join rows and their keys")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
