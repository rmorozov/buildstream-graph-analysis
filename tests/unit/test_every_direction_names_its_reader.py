"""UX-231: every direction, and every new filing, names whose problem it solves.

Round 27 wrote the role model: eight roles, and the finding that
twenty-six rounds of audits served four of them thoroughly and four
almost not at all — *invisibly*, because nothing ever required a
direction or a filing to say whose problem it solves.

That gap analysis only stays true if the tracing is routine, which is
what these guards make it. Directions 8 and 9 were born with a
`Serves:` line; 1–7 gained one retroactively, assigned from what each
direction argues rather than from its title.

Deliberately **not** retro-tagged: UX-1..226. The archaeology would be
guesswork, and a guessed role id is worse than an absent one — the
round history already tells that story. The guard starts at UX-227,
which is where the convention starts.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIRECTIONS = REPO / "docs" / "design" / "directions.md"
ROLES = REPO / "docs" / "design" / "roles.md"
SCENARIOS = REPO / "docs" / "backlog" / "scenarios"

# The convention starts here. Everything below is history.
FIRST_TAGGED = 227

#: An item id wherever a status line cites one - `UX-581`.
_ITEM = re.compile(r"\bUX-0*(\d+)\b")


def _role_ids():
    """The role ids the model actually defines, read from its table."""
    return set(re.findall(r"^\| (R\d+) \|", ROLES.read_text(), re.M))


def _direction_sections():
    """Each `## Direction N` heading with the text up to the next `## `.

    `UX-581`: bounded by *any* level-2 heading, not the next Direction.
    The document interleaves `## Round history` and `## Verification
    Log` between directions, and the old bound swallowed them - so
    Direction 16's section carried the 60-row round table and every id
    in it.
    """
    text = DIRECTIONS.read_text()
    heads = list(re.finditer(r"^## .*$", text, re.M))
    out = []
    for i, head in enumerate(heads):
        if not head.group(0).startswith("## Direction "):
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append(text[head.start():end])
    return out


def _statuses():
    """`(heading, the Status line)` per direction - `UX-581`."""
    out = []
    for section in _direction_sections():
        for line in section.splitlines():
            if line.startswith("**Status:**"):
                out.append((section.splitlines()[0], line))
                break
    return out


def _filing_numbers():
    """Every filed item number, from the files `git` tracks."""
    return {int(re.match(r"UX-0*(\d+)-", path.name).group(1))
            for path in _task_files()}


def _closed_filings():
    """The subset whose own header line carries the closed marker."""
    return {int(re.match(r"UX-0*(\d+)-", path.name).group(1))
            for path in _task_files()
            if "**Status:** 🟢" in path.read_text().split("\n## ", 1)[0]}


def _task_files():
    return sorted(SCENARIOS.glob("UX-*.md"))


def _tagged_task_files():
    for path in sorted(SCENARIOS.glob("UX-*.md")):
        match = re.match(r"UX-0*(\d+)-", path.name)
        if match and int(match.group(1)) >= FIRST_TAGGED:
            yield path


class TestTheRoleModelIsReadable:

    def test_it_defines_the_roles_the_lines_reference(self):
        assert _role_ids() == {f"R{n}" for n in range(1, 9)}, _role_ids()

    def test_there_are_directions_to_check(self):
        """A guard over an empty set passes vacuously."""
        assert len(_direction_sections()) >= 9

    def test_there_are_tagged_filings_to_check(self):
        assert len(list(_tagged_task_files())) >= 9


class TestEveryDirectionNamesItsReader:

    def test_each_one_carries_a_serves_line(self):
        missing = [section.splitlines()[0] for section in _direction_sections()
                   if "**Serves:**" not in section]
        assert missing == [], (
            f"a direction that does not say whose problem it solves is how "
            f"four roles went unserved for twenty-six rounds: {missing}")

    def test_each_serves_line_names_a_role_the_model_defines(self):
        known = _role_ids()
        for section in _direction_sections():
            heading = section.splitlines()[0]
            # The line may run on, so take the whole paragraph.
            paragraph = section.split("**Serves:**", 1)[1].split("\n\n", 1)[0]
            named = set(re.findall(r"\bR\d+\b", paragraph))
            assert named, f"{heading}: Serves names no role id"
            assert named <= known, f"{heading}: unknown role(s) {named - known}"

    def test_the_serves_line_is_near_the_top(self):
        """Below the fold it is documentation; at the top it is a
        header a reader cannot miss."""
        for section in _direction_sections():
            head = "\n".join(section.splitlines()[:6])
            assert "**Serves:**" in head, section.splitlines()[0]


class TestEveryDirectionSaysWhereItStands:
    """`UX-581`: the same walk, asking where the direction got to.

    A direction with a `Serves:` line and no status reads as landed
    whatever it is: round 83 found five tails - D8's explain-path, D9's
    three unfiled steps, D10's uncut tag, D11's two unpublished `yes`
    rows, D1's stale "none of it is currently printed" - none of them
    landed, none declined, none visible.
    """

    def test_each_one_carries_a_status_line(self):
        walked = {heading for heading, _ in _statuses()}
        missing = [section.splitlines()[0] for section in _direction_sections()
                   if section.splitlines()[0] not in walked]
        assert missing == [], (
            f"a direction with no status reads as landed whichever it is: "
            f"{missing}")

    def test_the_status_line_is_near_the_top(self):
        """Beside `Serves:`, where a reader meets it before the argument."""
        for section in _direction_sections():
            head = "\n".join(section.splitlines()[:10])
            assert "**Status:**" in head, section.splitlines()[0]

    def test_each_status_uses_the_vocabulary(self):
        """Three words, so the set is countable rather than read."""
        for heading, status in _statuses():
            word = status.split("**Status:**", 1)[1].strip().split()[0]
            assert word in ("landed", "partial", "declined"), (heading, word)

    def test_a_partial_names_a_filed_id_or_states_a_decline(self):
        """The claim. "partial" with no remainder is the silence this
        item is about, written in the new vocabulary."""
        bare = []
        for heading, status in _statuses():
            rest = status.split("**Status:**", 1)[1].strip()
            if not rest.startswith("partial"):
                continue
            remainder = rest[len("partial"):]
            if not (_ITEM.search(remainder) or "declin" in remainder):
                bare.append(f"{heading}: {rest[:80]}")
        assert bare == [], (
            "a `partial` states what remains as a filed id or a decline, "
            f"or the tail is silent again: {bare}")

    def test_a_declined_status_says_why(self):
        for heading, status in _statuses():
            rest = status.split("**Status:**", 1)[1].strip()
            if rest.startswith("declined"):
                assert len(rest[len("declined"):].strip(" —-")) >= 20, heading

    def test_a_partial_is_not_wholly_made_of_closed_filings(self):
        """Derived, so the status cannot go stale the way the sentences
        it replaces did: the day every id a `partial` names is 🟢, the
        remainder has landed and the word is wrong."""
        closed = _closed_filings()
        stale = []
        for heading, status in _statuses():
            rest = status.split("**Status:**", 1)[1].strip()
            if not rest.startswith("partial"):
                continue
            named = {int(n) for n in _ITEM.findall(rest[len("partial"):])}
            if named and named <= closed:
                stale.append(f"{heading}: {sorted(named)} are all closed")
        assert stale == [], (
            f"a `partial` whose whole remainder has landed: {stale}")

    def test_a_landed_status_names_only_closed_filings(self):
        """The other direction, and the one that keeps `landed` cheap to
        write and expensive to write *wrongly*."""
        closed = _closed_filings()
        known = _filing_numbers()
        wrong = []
        for heading, status in _statuses():
            rest = status.split("**Status:**", 1)[1].strip()
            if not rest.startswith("landed"):
                continue
            for number in sorted({int(n) for n in _ITEM.findall(rest)}):
                if number not in known:
                    wrong.append(f"{heading}: UX-{number} is no filing")
                elif number not in closed:
                    wrong.append(f"{heading}: UX-{number} is not closed")
        assert wrong == [], f"a `landed` status citing open work: {wrong}"

    def test_the_statuses_are_not_all_one_word(self):
        """A blanket `landed` would satisfy every claim above. The
        document's own tails are what makes this true today."""
        words = {status.split("**Status:**", 1)[1].strip().split()[0]
                 for _, status in _statuses()}
        assert len(words) >= 2, words

    def test_the_walk_finds_every_direction_the_document_argues(self):
        """A guard over an empty population passes vacuously, and the
        `## Direction N` numbering runs 1-17 out of order."""
        numbered = {int(re.match(r"## Direction (\d+)", section).group(1))
                    for section in _direction_sections()}
        assert numbered == set(range(1, 18)), sorted(numbered)


class TestEveryNewFilingNamesItsReader:

    def test_each_carries_a_serves_field(self):
        missing = [p.name for p in _tagged_task_files()
                   if "Serves:" not in p.read_text().split("\n\n", 2)[0]
                   + p.read_text().split("\n\n", 2)[1]]
        assert missing == [], (
            f"filings from UX-{FIRST_TAGGED} carry `Serves:` in their header "
            f"line: {missing}")

    def test_each_names_a_role_the_model_defines(self):
        for path in _tagged_task_files():
            header = path.read_text().split("## ", 1)[0]
            named = set(re.findall(r"\bR\d+\b", header))
            assert named <= _role_ids(), (path.name, named - _role_ids())

    def test_the_query_the_role_model_promised_works(self):
        """"Which filings serve role R?" answered by reading the header
        line, which is the whole point of the convention.

        The first draft of this guard asked for R6 and passed - on
        `UX-231`'s own acceptance prose, which contains the string
        `Serves:.*R6` inside a worked example of the query. A guard
        that matches the sentence describing it is not a guard. It
        asks about a role that is genuinely served now, and reads only
        the `Serves:` field rather than the whole file.
        """
        served = {}
        for path in _tagged_task_files():
            for line in path.read_text().splitlines():
                if "**Serves:**" not in line:
                    continue
                for role in re.findall(r"\bR\d+\b", line.split("**Serves:**")[1]):
                    served.setdefault(role, []).append(path.name)
                break
        assert served.get("R5"), "UX-234 is filed as R5's first instrumentation"
        assert any("UX-0234" in name for name in served["R5"]), served["R5"]

    def test_a_role_with_no_filing_is_visible_as_such(self):
        """The role model's actual job. R6 - the contributor waiting on
        a queue - has **no** filing: round 27 opened Direction 9 for
        R5-R8 and filed only UX-234, which serves R5 and R7.

        That is not a defect to fix here; it is the gap analysis
        working. It is asserted so that the day someone files for a
        role, this guard tells them the map moved and `roles.md` should
        say so too.

        **It has earned its keep twice.** R3 - the graph owner - was in
        this list until round 32, when `UX-258`/`UX-259` filed against
        the blast ranking; this guard caught that `roles.md` still
        claimed R3 was served by round-19 work alone. In round 83 it
        emptied: `UX-594` files the requested-at instant R6's waiting
        would be measured from, so every role now has *a* filing.

        Filed is not served, and the two are now guarded separately.
        `test_the_roles_table_names_who_serves_it.py` reads **closed**
        filings and still holds that R6's cell names nobody; this one
        reads every filing, so it reddens the day a role loses its
        last one - or the day a ninth role arrives unfiled.
        """
        served = set()
        for path in _tagged_task_files():
            for line in path.read_text().splitlines():
                if "**Serves:**" in line:
                    served.update(
                        re.findall(r"\bR\d+\b", line.split("**Serves:**")[1]))
                    break
        unserved = sorted(_role_ids() - served,
                          key=lambda r: int(r[1:]))
        assert unserved == [], (
            f"the set of roles with no filing since UX-{FIRST_TAGGED} changed "
            f"to {unserved}. That is the role model earning its file - update "
            f"roles.md's table in the same commit (fixing guide, item 7).")


class TestTheConventionIsWrittenDown:

    def test_the_fixing_guide_asks_the_question(self):
        guide = (REPO / "docs/contributing/fixing-guide.md").read_text()
        assert "roles.md" in guide
        assert "which roles are served" in guide

    def test_both_guides_name_their_role(self):
        real = (REPO / "docs/guides/real-project.md").read_text()
        ci = (REPO / "docs/guides/ci-comment.md").read_text()
        assert "R1" in real.split("\n\n", 3)[1], "real-project.md is R1's journey"
        assert "R4" in ci.split("\n\n", 3)[1], "ci-comment.md is R4's page"

    def test_the_style_guide_documents_the_field(self):
        style = (REPO / "docs/contributing/style-guide.md").read_text()
        assert "Serves:" in style
