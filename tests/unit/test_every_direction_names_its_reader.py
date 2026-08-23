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


def _role_ids():
    """The role ids the model actually defines, read from its table."""
    return set(re.findall(r"^\| (R\d+) \|", ROLES.read_text(), re.M))


def _direction_sections():
    """Each `## Direction N` heading with the text up to the next one."""
    text = DIRECTIONS.read_text()
    starts = [m.start() for m in re.finditer(r"^## Direction \d+", text, re.M)]
    starts.append(len(text))
    return [text[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]


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
        working. It is asserted so that the day someone files for R6,
        this guard tells them the map moved and `roles.md` should say
        so too.
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
        assert unserved == ["R3", "R6"], (
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
