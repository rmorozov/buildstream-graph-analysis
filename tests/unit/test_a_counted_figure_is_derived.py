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

`UX-566` closed the seventh, three lines further on: "`additional
Properties` is true in all three" was a count from when three outputs
were published and `bga/schemas.py` defines eight.
"""
import functools
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task

from bga import contracts

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

    def test_the_versioning_rule_counts_the_schemas_it_describes(self):
        """`UX-566`: the seventh copy, `specification.md:1714`. "So
        `additionalProperties` is true in all three" is a count from
        when three outputs were published; `bga/schemas.py` defines
        eight. The sentence's subject is the schema documents, so the
        figure is read off them and not off any registry class."""
        from bga import schemas

        defined = sorted(schemas._SCHEMAS)
        lacking = [one for one in defined
                   if schemas.schema(one).get("additionalProperties") is not True]
        assert not lacking, (
            "the sentence claims additionalProperties for every schema and "
            "these do not set it", lacking)
        word = WORDS[len(defined)]
        assert (f"`additionalProperties` is true in all {word} schemas "
                f"`bga/schemas.py` defines") in _flat(_spec_contract_block()), (
            f"Part 32.5 should say 'true in all {word} schemas "
            f"`bga/schemas.py` defines'; it defines {len(defined)}: {defined}")


def _git_listed(root, *extra):
    """`git ls-files` from `root`, one path per line."""
    return subprocess.run(["git", "ls-files", *extra], cwd=root, check=True,
                          capture_output=True, text=True).stdout.splitlines()


def _backlog_files(directory, root=REPO):
    """What a commit from `root` would carry in one backlog directory.

    `UX-622`: the index alone is a *narrower* population than the one
    `dev_close_task.py` writes the sentence from, and the two disagree
    exactly while a row is written and not staged. Git's answer and not
    a glob's - a checkout holds `.claude/worktrees/<agent>/`, a second
    copy of the whole tree (`UX-577`), listed as one entry.
    """
    listed = _git_listed(root) + _git_listed(root, "--others",
                                             "--exclude-standard")
    return sorted(one for one in listed
                  if one.startswith(f"docs/backlog/{directory}/")
                  and not one.endswith("/"))


class TestTheArchitectureCountsTheBacklogItSendsYouTo:
    """`UX-569`: `docs/design/architecture.md:3`, the sentence that is
    the document's own reason for existing.

    `UX-88` fixed "22 scenario files (there are 76)" at another line of
    this document; the count here kept its 2026-08 value of 75 while the
    directory grew to 591. The figure beside it - the closed P0-P4
    backlog, which does not grow - is 75 and was right, so one stale
    number sat next to one true one and the pair read as arithmetic.
    """

    @staticmethod
    def _opening():
        """The sentence only, above the first chapter."""
        return _flat(ARCHITECTURE.read_text(encoding="utf-8").split(
            "\n## ", 1)[0])

    @pytest.mark.parametrize("directory", ["scenarios", "tasks"])
    def test_the_count_is_the_directory(self, directory):
        files = _backlog_files(directory)
        assert f"{len(files)} `docs/backlog/{directory}/` files" \
            in self._opening(), (
            f"architecture.md's opening should say '{len(files)} "
            f"`docs/backlog/{directory}/` files'; the index holds "
            f"{len(files)} there")

    @pytest.mark.parametrize("directory", ["scenarios", "tasks"])
    def test_the_counted_population_is_the_flat_markdown_directory(
            self, directory):
        """A figure derived from an empty population passes at nothing,
        and one derived from a directory with subdirectories counts
        something the sentence does not name."""
        files = _backlog_files(directory)
        assert len(files) > 1, f"docs/backlog/{directory}/ is empty"
        odd = [one for one in files
               if not one.endswith(".md")
               or one.rpartition("/")[0] != f"docs/backlog/{directory}"]
        assert odd == [], (
            f"docs/backlog/{directory}/ is no longer the flat markdown "
            f"directory this figure counts", odd[:5])


@pytest.fixture(scope="module")
def two_population_tree(tmp_path_factory):
    """A tree where the two populations can differ: one row committed,
    one written and not staged, one ignored, one untracked directory."""
    repo = tmp_path_factory.mktemp("counts") / "repo"
    (repo / "docs/backlog/scenarios").mkdir(parents=True)
    (repo / "docs/backlog/tasks").mkdir(parents=True)
    (repo / "docs/backlog/scenarios/UX-0001-committed.md").write_text(
        "# UX-1\n", encoding="utf-8")
    (repo / ".gitignore").write_text("*.scratch.md\n", encoding="utf-8")
    for argv in (["init", "-q"],
                 ["config", "user.email", "a@b"],
                 ["config", "user.name", "a"],
                 ["add", "docs", ".gitignore", "-f"],
                 ["commit", "-qm", "one"]):
        subprocess.run(["git", *argv], cwd=repo, check=True,
                       capture_output=True, text=True)
    (repo / "docs/backlog/scenarios/UX-0002-unstaged.md").write_text(
        "# UX-2\n", encoding="utf-8")
    (repo / "docs/backlog/scenarios/notes.scratch.md").write_text(
        "x\n", encoding="utf-8")
    return repo


class TestBothSidesReadOneBacklogPopulation:
    """`UX-622`. `dev_close_task.py` writes the sentence above from the
    index **plus** untracked (`UX-617`); this file read the index alone,
    so `--check --write` reported clean and wrote a count the guard
    rejected until the row was staged.

    They are one question, not two. `git ls-files` is the **index**, not
    `HEAD`: with one row staged and not committed, `git ls-tree HEAD`
    counted 626 here and this guard demanded 627. Both sides ask what a
    commit from this tree would carry; only the depth differed.
    """

    ONE = "scenarios"

    def test_the_two_sides_count_the_same_population(
            self, two_population_tree, monkeypatch):
        """The clause `UX-622` exists for: the writer's figure and the
        guard's, on a tree where the old pair disagreed."""
        monkeypatch.setattr(close_task, "REPO", two_population_tree)
        assert (len(_backlog_files(self.ONE, root=two_population_tree))
                == close_task._backlog_counts()[self.ONE]), (
            "dev_close_task.py derives architecture.md's count from one "
            "population and this file checks it against another, so "
            "`--check --write` writes a figure the suite rejects")

    def test_that_agreement_is_not_vacuous(self, two_population_tree):
        """An over-broad fixture would make the clause above compare two
        equal numbers on a tree where nothing could differ. The index
        alone is strictly smaller here, so the old population fails it."""
        index_only = [one for one in _git_listed(two_population_tree)
                      if one.startswith(f"docs/backlog/{self.ONE}/")]
        assert index_only, "the fixture committed no backlog row"
        assert len(index_only) < len(
            _backlog_files(self.ONE, root=two_population_tree)), (
            "the fixture has no written-but-unstaged row, so the two "
            "populations cannot differ and the agreement proves nothing")

    def test_the_population_is_what_a_commit_would_carry(
            self, two_population_tree):
        """Equality, not membership: what `.gitignore` names is what the
        widening could have spent, and a `>=` clause stays green when the
        filter stops filtering."""
        assert _backlog_files(self.ONE, root=two_population_tree) == [
            "docs/backlog/scenarios/UX-0001-committed.md",
            "docs/backlog/scenarios/UX-0002-unstaged.md"], (
            "the population is no longer the committed row plus the "
            "written one - an ignored file is being counted")

    def test_the_sentence_names_the_population_it_counts(self):
        """The two populations differ only in a dirty tree, so a reader
        cannot tell from the number which one it is. `UX-622` requires
        the sentence to say, and a phrase nothing reads is one the next
        edit drops."""
        opening = _flat(ARCHITECTURE.read_text(encoding="utf-8").split(
            "\n## ", 1)[0])
        assert "files this commit carries" in opening, (
            "architecture.md's opening counts two backlog directories "
            "without saying which population - the index, or what a "
            "commit from here would carry (they differ while a row is "
            "written and not staged)")

    def test_a_nested_worktree_is_one_entry_and_not_a_row(self, monkeypatch):
        """A checkout holds `.claude/worktrees/<agent>/`, a second copy
        of the whole tree; git does not descend into it and lists it as
        one entry with a trailing slash (`UX-577`). Counted, that copy
        is one row that does not exist."""
        monkeypatch.setattr(
            sys.modules[__name__], "_git_listed",
            lambda _root, *extra: ["docs/backlog/scenarios/UX-1-real.md"]
            if not extra else ["docs/backlog/scenarios/worktrees/agent-1/"])
        assert _backlog_files(self.ONE, root=REPO) == [
            "docs/backlog/scenarios/UX-1-real.md"], (
            "a directory entry git listed without descending into it is "
            "being counted as a backlog row")


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

# --- `UX-576`: every sentence that counts the question library --------------
#
# The count was stated three ways when this was filed - seventeen ids in
# `questions.js`, "thirteen" in `cli.md`, "fourteen" in the `measure`
# skill and in `dev_perfetto_queries.py`. The sweep below found three
# more the item had not: `bga_timeline.py`, `questions.js`'s own
# chrome-cost note, and `dev_perfetto_queries.py`'s element-taking
# subset. A phrase is legal three ways - it is one of the sentences
# `_derived_sentences()` builds from the population, it names the ids it
# counts, or it is a dated finding in `HISTORICAL`.

CLI = REPO / "docs/guides/cli.md"
SKILL = REPO / ".claude/skills/measure/SKILL.md"
HARNESS = REPO / "tools/dev_perfetto_queries.py"
TIMELINE = REPO / "tools/bga_timeline.py"
ELEMENT_TOKEN = "{element}"

#: Read as a count when spelled or written bare. `one` is left out
#: because in prose it is the pronoun - "what lets one query join them"
#: - and never a count of this library.
COUNT_WORD = re.compile(r"^(?:" + "|".join(WORDS[n] for n in range(2, 31))
                        + r"|\d{1,3})$", re.I)

#: The words a count may reach its noun through. Anything else ends the
#: phrase, which is what keeps "renaming one silently breaks a query"
#: out of the population.
MODIFIER = frozenset(
    ["of", "the", "its", "all", "canned", "shipped", "paste-ready", "perfettosql", "other", "more", "remaining", "library", "current", "existing", "only", "same", "whole", "entire", "new", "these", "those", "sql"])

NOUN = re.compile(r"\b(?:questions?|quer(?:y|ies))\b", re.I)

#: What makes a passage one about *this* library rather than about
#: questions in general. A file in `ABOUT_THE_LIBRARY` has no other
#: subject, so every count in it is one of these.
LIBRARY = ("canned", "questions.js", "question library", "query library",
           "PerfettoSQL", "perfetto.html")
ABOUT_THE_LIBRARY = ("bga/viewer/questions.js",
                     "tools/dev_perfetto_queries.py",
                     "docs/guides/what-the-viewer-answers.md")

#: Dated findings: each is true of the library as it was in the round
#: named, and rewriting one would delete a measurement. Every entry is
#: asserted to still be present, so the list cannot rot.
HISTORICAL = {
    ("docs/design/architecture.md", "All six questions"):
        "UX-312's review entry, dated 2026-08-26: the library had six",
    ("docs/design/directions.md", "four of six canned queries"):
        "round 43's review of those same six",
    ("docs/design/styleguide.md", "thirteen queries"):
        "styleguide 4d, headed '(round 58)' - and the next clause, that "
        "the page fills all three with `core.bst`, is what UX-369 fixed",
    ("bga/viewer/questions.js", "all six queries"):
        "UX-210 to UX-308, the rounds that comment is about",
    ("bga/viewer/questions.js", "four of the six queries"):
        "the same six, in the same comment",
    ("bga/viewer/questions.js", "thirteen queries"):
        "UX-348's measurement of the exported section, 216 px and four "
        "`details`, taken when it was filed",
    ("tools/dev_perfetto_queries.py", "the fourteen shipped questions"):
        "round 69 - UX-432's Outcome ran 14, 2 empty, 0 errors",
}


def _strip(token):
    return token.strip("`*_(),;:.\"'-").lower()


@functools.lru_cache(maxsize=1)
def _tracked():
    """The paths git has, as a set. Not the paths on disk."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return frozenset(out.splitlines())


def _counted_files():
    """Where a sentence counting the library can live: the documents a
    reader reads, the skills an agent reads, and the source files whose
    prose states the count. `docs/backlog/` and `docs/audits/` are the
    historical record - a task file's pasted measurement is a dated fact
    and is never rewritten."""
    paths = sorted(REPO.glob("*.md")) + [
        p for p in sorted(REPO.glob("docs/**/*.md"))
        if not p.relative_to(REPO).as_posix().startswith(
            ("docs/backlog/", "docs/audits/"))]
    paths += sorted(REPO.glob(".claude/**/*.md"))
    paths += sorted(REPO.glob("tools/*.py")) + sorted(REPO.glob("bga/**/*.js"))
    # `UX-577`: a glob walks whatever the checkout happens to hold - and a
    # main checkout holds `.claude/worktrees/<agent>/`, a whole second copy
    # of the tree at an older commit. The repository is what git tracks.
    return [one for one in paths if one.relative_to(REPO).as_posix() in _tracked()]


def _count_phrases(path):
    """Every "N ... questions" phrase in one file, with the window a
    reader meets it in. Grown backwards from the noun through `MODIFIER`
    words only, so a count is found however it is worded and a pronoun
    is not."""
    flat = _flat(path.read_text(encoding="utf-8"))
    about = path.relative_to(REPO).as_posix() in ABOUT_THE_LIBRARY
    found = []
    for match in NOUN.finditer(flat):
        window = flat[max(0, match.start() - 400):match.end() + 200]
        if not about and not any(one.lower() in window.lower()
                                 for one in LIBRARY):
            continue
        chain = []
        for token in reversed(flat[max(0, match.start() - 70):
                                   match.start()].split()):
            # A bracket ends it: "(round 58) The query library" is a
            # heading's number, not the phrase's.
            if set("()[]") & set(token):
                break
            if not (COUNT_WORD.match(_strip(token))
                    or _strip(token) in MODIFIER):
                break
            chain.append(token)
        chain.reverse()
        if not any(COUNT_WORD.match(_strip(one)) for one in chain):
            continue
        found.append((" ".join(chain + [match.group(0)]),
                      flat[max(0, match.start() - 120):match.end() + 160]))
    return found


def _question_blocks():
    """`{id: the entry's source text}`, so a subset is counted off what
    the entry declares rather than off a sentence about it."""
    text = QUESTIONS_JS.read_text(encoding="utf-8")
    body = text.split("export const QUESTIONS = [", 1)[1].split("\n];", 1)[0]
    blocks = {}
    for chunk in body.split("\n  {"):
        found = re.search(r'^    id: "([a-z-]+)"', chunk, re.M)
        if found:
            blocks[found.group(1)] = chunk
    return blocks


def _takes_element():
    return sorted(one for one, block in _question_blocks().items()
                  if ELEMENT_TOKEN in block)


def _chrome_blind():
    return sorted(one for one, block in _question_blocks().items()
                  if re.search(r"^    reads: ", block, re.M))


def _guide_question_tables():
    """The guide's two tables, as id lists - the population both its own
    "nine of the seventeen" sentence and `cli.md`'s copy count."""
    text = GUIDE.read_text(encoding="utf-8")
    body = text.split("## The canned questions", 1)[1].split("\n## ", 1)[0]
    needs, rest = body.split("**Does not need Perfetto", 1)
    return (re.findall(r"^\| `([a-z-]+)` \|", needs, re.M),
            re.findall(r"^\| `([a-z-]+)` \|", rest, re.M))


def _derived_sentences():
    """The sentences these documents must carry, written here from the
    population and nowhere from a literal. One dict, so the sweep
    accepts exactly what a clause has already checked."""
    total = len(_questions())
    needs, rest = _guide_question_tables()
    head = f"{WORDS[len(needs)].capitalize()} of the {WORDS[total]}"
    other = WORDS[len(rest)]
    return {
        "README.md": [f"sorts all {WORDS[total]} canned questions"],
        "docs/guides/cli.md": [
            f"— {WORDS[total]} paste-ready PerfettoSQL queries",
            f"{head} canned questions genuinely need the trip; "
            f"{other} are sharper"],
        "docs/guides/what-the-viewer-answers.md": [
            f"serves {WORDS[total]} questions",
            f"{head} questions genuinely require the trip. The other "
            f"{other} are"],
        ".claude/skills/measure/SKILL.md": [
            f"Runs all {WORDS[total]} questions in "
            f"`bga/viewer/questions.js`"],
        "tools/dev_perfetto_queries.py": [
            f"Two of the {WORDS[len(_takes_element())]} questions taking an "
            f"element"],
        "bga/viewer/questions.js": [
            f"{WORDS[len(_takes_element())].capitalize()} of the "
            f"{WORDS[total]} questions do"],
    }


def _derived_pairs():
    return [(rel, one) for rel, many in _derived_sentences().items()
            for one in many]


class TestEverySentenceThatCountsTheQuestionsIsDerived:
    """`UX-576`. Five sentences counted the library and a guard read one
    of them; `resource-queues` landed on 2026-09-01 and the other four
    did not move."""

    @pytest.mark.parametrize("rel,sentence", _derived_pairs())
    def test_the_sentence_is_the_population(self, rel, sentence):
        assert sentence in _flat((REPO / rel).read_text(encoding="utf-8")), (
            f"{rel} should say {sentence!r}: questions.js exports "
            f"{len(_questions())}, the guide sorts "
            f"{[len(one) for one in _guide_question_tables()]} and "
            f"{ELEMENT_TOKEN} is in {_takes_element()}")

    def test_the_two_tables_sort_the_whole_library(self):
        """The split sentences above are only derived if the tables they
        count are the library."""
        needs, rest = _guide_question_tables()
        assert sorted(needs + rest) == sorted(_questions()), (
            "the guide's two tables and questions.js disagree",
            sorted(set(needs + rest) ^ set(_questions())))

    def test_the_chrome_cost_names_the_queries_it_counts(self):
        """The other shape the fix allows: name the ids. Both copies of
        this sentence said "two of the fourteen"; they name the two now,
        and the two are read off `reads:`."""
        blind = _chrome_blind()
        assert len(blind) == 2, (
            "both chrome-cost sentences say 'two of the canned questions' "
            "and this many entries declare `reads:`", blind)
        for path in (QUESTIONS_JS, TIMELINE):
            flat = _flat(path.read_text(encoding="utf-8"))
            missing = [one for one in blind if f"`{one}`" not in flat]
            assert not missing, (
                f"{path.name} counts the chrome-blind queries without "
                f"naming these", missing)

    def test_every_historical_phrase_is_still_there(self):
        """`HISTORICAL` is an exemption list, and an exemption nothing
        uses is one nobody rechecks."""
        for (rel, phrase), why in sorted(HISTORICAL.items()):
            flat = _flat((REPO / rel).read_text(encoding="utf-8"))
            assert phrase in flat, (
                f"{rel} no longer says {phrase!r}, so its exemption ({why}) "
                f"is stale - drop the entry")

    def test_the_sweep_reads_the_sentences_it_is_for(self):
        """A sweep that finds nothing passes. This is the floor: every
        derived sentence and every historical one is in the population
        the sweep actually walks."""
        seen = {(path.relative_to(REPO).as_posix(), phrase)
                for path in _counted_files()
                for phrase, _ in _count_phrases(path)}
        for rel, sentence in _derived_pairs() + sorted(HISTORICAL):
            assert any(this == rel and (that in sentence or sentence in that)
                       for this, that in seen), (
                f"the sweep does not see {rel}'s {sentence!r}, so nothing "
                f"holds it", sorted(one for one in seen if one[0] == rel))

    def test_every_counted_sentence_is_accounted_for(self):
        """The sweep itself. Every "N ... questions" phrase in `docs/`,
        `.claude/`, `tools/` and the viewer, held against
        `questions.js`."""
        total, ids = len(_questions()), set(_questions())
        derived = _derived_sentences()
        unaccounted = []
        for path in _counted_files():
            rel = path.relative_to(REPO).as_posix()
            for phrase, window in _count_phrases(path):
                if any(phrase in one for one in derived.get(rel, ())):
                    continue
                if any(this == rel and that in phrase
                       for this, that in HISTORICAL):
                    continue
                named = {one for one in ids if f"`{one}`" in window}
                values = {int(one) if one.isdigit() else
                          next(k for k, v in WORDS.items() if v == one)
                          for one in (_strip(one) for one in phrase.split())
                          if COUNT_WORD.match(one)}
                if values and values <= {total, len(named)}:
                    continue
                unaccounted.append(
                    f"{rel}: {phrase!r} counts {sorted(values)}; the library "
                    f"serves {total} and the sentence names {sorted(named)}")
        assert not unaccounted, (
            "these sentences count the question library and nothing derives "
            "them:\n" + "\n".join(unaccounted))

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
