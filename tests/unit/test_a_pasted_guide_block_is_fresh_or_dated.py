"""UX-578: a guide's pasted `bga` output is re-run here, or it is dated.

`test_the_readme_block_is_the_real_output.py` diffs the README's one
block against a fresh run. Nothing did that for `docs/guides/`, and five
pasted outputs there had drifted from the tool with no label saying so -
a missing `load it with:` line, a `correlate` block starting four
sections in with no cut marker, two byte figures for one trace, and two
published keys that no longer exist.

So every `$ bga …` block in `docs/guides/` takes one of two branches,
and this reads which:

* it names a path under `tests/fixtures/`, and every line it pastes is
  diffed against a fresh run - verbatim, in order, and contiguous unless
  an `[... elided: … ...]` marker declares the cut; or
* it carries the `UX-511` label - *kept, not current*, an ISO date, and
  a `Cuts:` sentence - because the run behind it cannot be repeated in a
  clone.

The second branch is `UX-511`'s and is not a hiding place: a labelled
block must say what a fresh run would add, and the last clause here
asserts both branches are non-empty, so a change that quietly labelled
everything reddens.
"""
import pathlib
import re
import shlex
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDES = REPO / "docs/guides"

#: The README guard's marker, so a cut is declared the same way on both
#: sides of the documentation.
ELISION = re.compile(r"^\[\.\.\. elided: .+ \.\.\.\]$")

#: A block is re-runnable here when its command names a committed
#: fixture. `@last`, `/tmp/run` and a project path are the three ways
#: the guides name a capture nobody else has.
FIXTURE_ROOT = "tests/fixtures/"

#: The `UX-511` label: the framing, a day, and what was left out.
KEPT = re.compile(r"kept, not current", re.I)
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
CUTS = re.compile(r"Cuts:\s*(\S.*)", re.S)


class Block:
    """One pasted block, its command lines, and the prose under it."""

    def __init__(self, document, line, body, trailer):
        self.document = document
        self.line = line
        self.body = body
        self.trailer = trailer

    @property
    def id(self):
        return f"{self.document}:{self.line}"

    @property
    def commands(self):
        return [b[2:] for b in self.body if b.startswith("$ ")]

    @property
    def diffable(self):
        return any(FIXTURE_ROOT in command for command in self.commands)

    def segments(self):
        """`(command, pasted lines)` per `$ ` line in the block."""
        out = []
        for raw in self.body:
            if raw.startswith("$ "):
                out.append((raw[2:], []))
            elif out:
                out[-1][1].append(raw)
        return out


def _blocks():
    """Every `console`/`text` fence in the guides opening with `$ bga`."""
    found = []
    for path in sorted(GUIDES.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            opened = re.match(r"^```(console|text)\s*$", lines[index])
            if not opened:
                index += 1
                continue
            close = index + 1
            while close < len(lines) and not lines[close].startswith("```"):
                close += 1
            body = lines[index + 1:close]
            if body and body[0].startswith("$ bga "):
                # The prose between this fence and the next one is where
                # a label lives; stopping at the next fence keeps a
                # neighbouring block's label from covering this one.
                after = close + 1
                while after < len(lines) and not lines[after].startswith("```"):
                    after += 1
                found.append(Block(
                    path.relative_to(REPO).as_posix(), index + 2, body,
                    "\n".join(lines[close + 1:after])))
            index = close + 1
    return found


BLOCKS = _blocks()


def _fresh(command):
    """The command, run from the repository root, as a list of lines."""
    argv = shlex.split(command)
    assert argv[0] == "bga", command
    done = subprocess.run([sys.executable, "-m", "bga.cli"] + argv[1:],
                          capture_output=True, text=True, cwd=str(REPO),
                          timeout=180)
    assert done.returncode == 0, (command, done.returncode, done.stderr)
    return done.stdout.splitlines()


def _json(subcommand, *args):
    """One `bga … --format json` run, parsed."""
    import json

    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", subcommand, *args,
         "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO), timeout=180)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _ids(blocks):
    return [block.id for block in blocks]


class TestThePopulationIsTheOneTheItemNamed:
    def test_there_are_blocks_to_read(self):
        """A population rule that selects nothing passes everything."""
        assert len(BLOCKS) >= 5, (
            "no `$ bga` blocks found under docs/guides; the guard below "
            "would be reading an empty set", _ids(BLOCKS))

    def test_both_branches_are_exercised(self):
        """Non-vacuity, both ways. If nothing is diffable this guard is
        a spell-check on labels; if nothing is labelled the second
        branch has never run."""
        diffed = [block for block in BLOCKS if block.diffable]
        kept = [block for block in BLOCKS if not block.diffable]
        assert diffed and kept, (
            "one branch of the rule has no block in it",
            _ids(diffed), _ids(kept))

    def test_a_block_that_can_be_re_run_is_not_labelled_instead(self):
        """The two branches are exclusive. A `kept, not current` label
        on a block whose fixture is committed would stand where the diff
        should be, and the diff is the stronger claim."""
        mislabelled = [block.id for block in BLOCKS
                       if block.diffable and KEPT.search(block.trailer)]
        assert mislabelled == [], (
            "block(s) name a committed fixture and are dated as archives "
            "anyway; they are diffed, so the label is not the answer",
            mislabelled)


@pytest.mark.parametrize(
    "block", [b for b in BLOCKS if b.diffable], ids=_ids(
        [b for b in BLOCKS if b.diffable]))
class TestADiffedBlockIsAFreshRun:
    def test_every_pasted_line_is_a_real_line(self, block):
        for command, pasted in block.segments():
            fresh = _fresh(command)
            missing = [line for line in pasted
                       if line.strip() and not ELISION.match(line)
                       and line not in fresh]
            assert missing == [], (
                f"{block.id} pastes lines `{command}` does not print",
                missing)

    def test_the_lines_are_in_the_order_and_contiguity_pasted(self, block):
        """Membership alone cannot see a reshuffle, and adjacency is
        what the elision marker is for: two pasted lines that are not
        adjacent in the real output are an undeclared cut."""
        for command, pasted in block.segments():
            fresh = _fresh(command)
            previous = None
            undeclared = []
            for line in pasted:
                if not line.strip():
                    continue
                if ELISION.match(line):
                    previous = None
                    continue
                assert line in fresh, (
                    f"{block.id} pastes a line `{command}` does not "
                    f"print:\n  {line!r}")
                here = fresh.index(line)
                if previous is not None and here != previous + 1:
                    undeclared.append((line, fresh[previous + 1:here]))
                previous = here
            assert undeclared == [], (
                f"{block.id} jumps over lines `{command}` prints with no "
                f"`[... elided: … ...]` marker", undeclared)

    def test_the_ends_of_each_paste_are_declared_too(self, block):
        """The clause the first mutation of this guard walked through:
        adjacency between pasted lines cannot see a cut *before the
        first* or *after the last*, which is where an over-long report
        gets trimmed."""
        for command, pasted in block.segments():
            fresh = _fresh(command)
            lines = [line for line in pasted if line.strip()]
            assert lines, (block.id, command)
            for end, edge in ((0, fresh[0]), (-1, fresh[-1])):
                if ELISION.match(lines[end]):
                    continue
                assert lines[end] == edge, (
                    f"{block.id} starts or stops partway through what "
                    f"`{command}` prints with no `[... elided: … ...]` "
                    f"marker at that end", lines[end], edge)


@pytest.mark.parametrize(
    "block", [b for b in BLOCKS if not b.diffable], ids=_ids(
        [b for b in BLOCKS if not b.diffable]))
class TestAKeptBlockCarriesItsDateAndItsCuts:
    def test_it_is_framed_as_kept_not_current(self, block):
        assert KEPT.search(block.trailer), (
            f"{block.id} cannot be re-run here and does not say so; a "
            f"reader diffing it against their own run concludes the tool "
            f"is wrong rather than the page")

    def test_it_names_the_day(self, block):
        assert ISO_DATE.search(block.trailer), (
            f"{block.id} is kept without a date; 'an old run' is not "
            f"something a reader can check")

    def test_it_lists_its_cuts(self, block):
        found = CUTS.search(block.trailer)
        assert found and found.group(1).strip(), (
            f"{block.id} carries no `Cuts:` sentence, so a reader cannot "
            f"tell what a fresh run would add to it")


class TestTheGuidesNameKeysTheReportPublishes:
    """The other half of the drift: two of the five were not blocks but
    table cells naming `element_join[].peak_rss_kb` and a `structural`
    namespace, neither of which `analyze/v5` has. A key quoted in
    backticks is a promise about the JSON, and these three clauses read
    only cells that make it - never the Perfetto column beside them,
    whose keys are the trace's and are not in any report."""

    #: The two-column table under this heading answers each canned
    #: question with *the page's* key; its right column is the subject.
    PAGE_ANSWERS = "**Does not need Perfetto"

    #: `cli.md`'s correlate table names the row's keys bare, one line
    #: per plane.
    CORRELATE_ROW = "| Plane 2 | "

    @pytest.fixture(scope="module")
    def report(self):
        return _json("analyze", "tests/fixtures/macro_micro/run",
                     "--plane2", "tests/fixtures/macro_micro/plane2.json")

    @pytest.fixture(scope="module")
    def joined(self):
        return _json("correlate", "tests/fixtures/macro_micro/run",
                     "tests/fixtures/macro_micro/plane2.json")

    def _cells(self, document, anchor, column):
        text = (REPO / document).read_text(encoding="utf-8")
        start = text.index(anchor)
        end = text.index("\n## ", start + 4)
        rows = [line for line in text[start:end].splitlines()
                if line.startswith("|") and "---" not in line]
        assert rows, (document, anchor)
        return [row.split("|")[column].strip() for row in rows]

    def test_every_element_join_key_the_guides_name_is_on_the_row(self, report):
        """`UX-578`'s fifth drift: `element_join[].peak_rss_kb`, which
        `UX-341` renamed to bytes and nothing here noticed."""
        row = report["element_join"][0]
        named = set()
        for path in sorted(GUIDES.glob("*.md")):
            named |= set(re.findall(r"`element_join\[\]\.([a-z_0-9]+)`",
                                    path.read_text(encoding="utf-8")))
        assert named, "no `element_join[].…` key named in the guides"
        assert sorted(k for k in named if k not in row) == [], (
            "the guides name element_join key(s) the report does not "
            "publish", sorted(named), sorted(row))

    def test_every_namespace_the_page_answers_with_exists(self, report):
        """`UX-578`'s fourth: `waited-on-flow` was answered with "the
        declared graph, in `structural`" and there is no such key."""
        named = set()
        for cell in self._cells("docs/guides/what-the-viewer-answers.md",
                                self.PAGE_ANSWERS, 2):
            named |= set(re.findall(r"`([a-z_0-9]+)(?:\.[a-z_0-9]+)?`", cell))
        assert len(named) >= 4, ("the page-answers table named almost "
                                 "nothing; the anchor has moved", named)
        assert sorted(k for k in named if k not in report) == [], (
            "the page-answers table names namespace(s) analyze does not "
            "publish", sorted(named), sorted(report))

    def test_the_correlate_row_table_names_the_rows_own_keys(self, joined):
        """The same rename, on `cli.md`'s side of it."""
        row = joined["elements"][0]
        named = set()
        for cell in self._cells("docs/guides/cli.md", self.CORRELATE_ROW, 2):
            named |= set(re.findall(r"`([a-z_0-9]+)`", cell))
        assert len(named) >= 4, ("the correlate row table named almost "
                                 "nothing; the anchor has moved", named)
        assert sorted(k for k in named if k not in row) == [], (
            "cli.md's correlate table names key(s) the row does not "
            "carry", sorted(named), sorted(row))


class TestOneMeasurementForTheScaleTrace:
    """`UX-430` published 486,167 B and `UX-445` 491,397 B for the same
    16,832-track trace, and the guides quoted both, in three places
    across two documents. Two numbers for one measurement means at least
    one is wrong and the reader cannot tell which."""

    #: The subject is the figure quoted *for this trace*, so the window
    #: is anchored on the two markers that always accompany it rather
    #: than on the unit - a 400-600 KB figure elsewhere in the guides is
    #: a different thing (the HTML export weighs 520,048 B).
    ANCHORS = ("16,832", "4 MiB")
    WINDOW = 250
    FIGURE = re.compile(r"\b(\d{3}),(\d{3})\b|\b(\d{3}) KB\b")
    BAND = (400_000, 600_000)

    def _figures(self):
        found = {}
        for path in sorted(GUIDES.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for anchor in [found for marker in self.ANCHORS
                           for found in re.finditer(re.escape(marker), text)]:
                window = text[max(0, anchor.start() - self.WINDOW):
                              anchor.end() + self.WINDOW]
                for match in self.FIGURE.finditer(window):
                    raw = match.group(0)
                    value = (int(raw.replace(",", "")) if "," in raw
                             else int(match.group(3)) * 1000)
                    if self.BAND[0] <= value <= self.BAND[1]:
                        found.setdefault(round(value / 1000), set()).add(
                            f"{path.name}: {raw}")
        return found

    def test_the_guides_quote_one_figure_for_it(self):
        found = self._figures()
        assert len(found) == 1, (
            "the guides quote more than one byte figure for the "
            "16,832-track seeded scale trace",
            {kb: sorted(where) for kb, where in found.items()})

    def test_it_is_quoted_in_more_than_one_place(self):
        """The clause above passes on an empty set and on a single
        mention; neither is the state this item was filed about."""
        found = self._figures()
        assert found, "no byte figure for the scale trace found"
        assert len(next(iter(found.values()))) >= 2, (
            "only one place quotes it, so the agreement clause above is "
            "not reading the drift this item found", found)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
