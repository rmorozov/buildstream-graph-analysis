"""UX-301: the ordering authority moved, and left its old uniform on.

Round 40's verification mutated `root.prepend(decision)` to `append` -
`UX-235`'s own documented acceptance mutation - and the booted page did
not change. `UX-286`'s chapter pass had taken over: `chapters.js`
re-sorts the document after everything has rendered, placing each
section in the chapter that names it and, within a chapter, in the
order that chapter's list declares. The order is guarded, by
`test_the_report_has_chapters.py`, whose clauses redden when the
chapter table is mutated.

What was left behind was five `prepend` calls in `boot()` that decided
nothing. The next reader - or the next audit, as this one nearly did -
would mistake them for the mechanism.

**Measured before removing them**, on the booted export of the golden
fixture, with and without a comparison document spliced in:

```text
before  decision, evidence, overview, findings, headline, next_steps, ...
after   decision, evidence, overview, findings, headline, next_steps, ...
```

Identical, both cases. Which is the point: they were not doing
anything, and the five-line diff is a claim that can be checked rather
than a tidy-up that has to be believed.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
APP = REPO / "bga/viewer/app.js"
CHAPTERS = REPO / "bga/viewer/chapters.js"


def _boot_body():
    """`boot()`'s own source: from its declaration to the next
    top-level one. The focus and mark overlays live outside it and do
    prepend - deliberately, and `chapters()` steps over them because
    they are transient rather than part of the document."""
    source = APP.read_text(encoding="utf-8")
    start = source.index("async function boot() {")
    rest = source[start + 1:]
    end = re.search(r"^(export )?(async )?function ", rest, re.M)
    return rest[:end.start()] if end else rest


class TestOneMechanismDecidesTheOrder:

    def test_boot_inserts_in_source_order_and_nothing_else(self):
        """The grep guard the item asks for. A `prepend` here is an
        ordering claim, and an ordering claim that `chapters.js` will
        silently overrule is worse than none - it reads as the
        mechanism to the next person to open the file."""
        offenders = [line.strip() for line in _boot_body().splitlines()
                     if re.search(r"root\.(prepend|insertBefore)\b", line)]
        assert offenders == [], (
            "boot() is inserting by position again. `chapters.js` re-sorts "
            "the document afterwards, so this decides nothing and reads as "
            f"though it does: {offenders}")

    def test_boot_says_where_the_order_is_decided(self):
        """A comment, because the guard above can only say what must not
        be there. The next person needs to know where it *is*."""
        body = _boot_body()
        assert "chapters.js" in body, (
            "boot() names no ordering authority, so the next reader has to "
            "find it by experiment")
        assert "CHAPTERS" in body, (
            "the comment should name the table to edit, not only the file")

    def test_the_authority_still_declares_an_order(self):
        """Non-vacuity: if `chapters.js` stopped ordering anything, the
        clauses above would be guarding an absence. The declared
        sections are the order, so there have to be some."""
        declared = re.findall(r'sections:\s*\[([^\]]*)\]',
                              CHAPTERS.read_text(encoding="utf-8"), re.S)
        assert len(declared) >= 6, declared
        first = [name.strip().strip('"') for name in declared[0].split(",")
                 if name.strip()]
        assert first[:3] == ["decision", "evidence", "overview"], first
