"""UX-713: a skill a guard forces a round to run, named by neither
document a stopped session reads.

`CLAUDE.md`'s pipeline named eight of nine skills; `review` — the only
one the cadence guard (`test_the_review_has_a_cadence.py`) sends a
session to run — was missing. `UX-471` removed a *count* of skills
because a count decays on every addition; membership does not, since
it is read off the directory rather than typed.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO / "CLAUDE.md"
SKILLS = REPO / ".claude/skills"


def test_every_skill_directory_is_named_in_claude_md():
    skills = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    text = CLAUDE_MD.read_text(encoding="utf-8")
    missing = [name for name in skills if f"`{name}`" not in text]
    assert missing == [], (
        f"CLAUDE.md does not name skill(s) {missing} — a skill under "
        f".claude/skills/ that no steering document names is a skill a "
        f"stopped session cannot find")
