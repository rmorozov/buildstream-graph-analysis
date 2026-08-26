"""UX-315: the prose in the question library reads the way it was typed.

Every `why` in `bga/viewer/questions.js` is assembled by concatenating
string literals across source lines, and the file's convention was to
begin each continuation with a space while the previous literal already
ended with one:

```js
why:
  "Plane 1's element spans, aggregated - scoped to the element " +
  " plane, so Plane 2 command names cannot crowd the answer.",
```

The reader gets `the element  plane`. Measured before the fix: **13 of
13** questions affected, 49 continuation lines in all - the file's
convention rather than one slip, and every one of them prose the page
renders.

This holds two things, because the defect has two shapes.

**The rendered text.** No prose field of a question carries a doubled
space. `sql` is deliberately not in that set: 12 of its 13 values
contain runs of spaces, and those are the query's own indentation
inside a template literal - its layout, not a typo.

**The shape that produced it.** A string literal ending in a space,
concatenated with one beginning in a space, anywhere in the shipped
tree. That clause exists because `UX-315`'s own Out of Scope asked
whether the pattern lived anywhere else and said the answer was a
search rather than an assumption. The search was run: 49 sites, all of
them in `questions.js`, none in the other 104 files. So this is not
widening a guard to cover a defect nobody found - it is holding a
convention at the shape a copied-from-the-one-above question would
bring back, in the file where it happened and in whatever file is
next.
"""
import json
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The fields a reader reads as sentences. `sql` is the query and
# `id`/`category`/`plane`/`example` are identifiers, not prose.
PROSE_FIELDS = ("title", "why")

# Where shipped code lives. `tests/` is excluded on purpose: a fixture
# may build a string with doubled spaces precisely to assert something
# about one.
SOURCE_ROOTS = ("bga", "tools")
SOURCE_SUFFIXES = {".js", ".py", ".html"}

# A literal that ends in a space, concatenated with one that begins in
# a space - in either quote style. `"a\n" + " b"` does not match: the
# first literal ends in an escape, not a space.
GLUED = (re.compile(r"""" \s*\+$"""), re.compile(r'''^"[ ]'''))
GLUED_SINGLE = (re.compile(r"""' \s*\+$"""), re.compile(r"""^'[ ]"""))


def _questions():
    """The library, as data, read by running the module it lives in."""
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _glued_sites(text):
    """Line numbers where a space-ending literal meets a space-starting one."""
    lines = text.splitlines()
    found = []
    for n in range(len(lines) - 1):
        above, below = lines[n].rstrip(), lines[n + 1].strip()
        for ends, starts in (GLUED, GLUED_SINGLE):
            if ends.search(above) and starts.match(below):
                found.append(n + 1)
    return found


def _sources():
    for root in SOURCE_ROOTS:
        for path in sorted((REPO / root).rglob("*")):
            if path.is_file() and path.suffix in SOURCE_SUFFIXES:
                yield path


@needs_node
class TestNoQuestionSaysAnythingTwice:

    def test_no_prose_field_carries_a_doubled_space(self):
        doubled = {}
        for question in _questions():
            for field in PROSE_FIELDS:
                value = question.get(field)
                if isinstance(value, str) and re.search(r"  ", value):
                    doubled.setdefault(question["id"], []).append(field)
        assert not doubled, (
            "a canned question renders a doubled space, which is what "
            f"UX-315 fixed in 13 of 13 of them: {doubled}")

    def test_the_sql_is_not_held_to_that_rule(self):
        """The exclusion is deliberate, so it is stated rather than implied."""
        indented = [q["id"] for q in _questions() if re.search(r"  ", q["sql"])]
        assert indented, (
            "no query indents its own text any more. If the SQL was "
            "reformatted, PROSE_FIELDS may now be able to include it - "
            "check, rather than deleting this clause.")


class TestTheShapeThatCausedItIsGone:

    def test_no_shipped_module_glues_two_spaces_together(self):
        sites = {}
        for path in _sources():
            found = _glued_sites(path.read_text())
            if found:
                sites[str(path.relative_to(REPO))] = found
        assert not sites, (
            "a string literal ending in a space is concatenated with one "
            "beginning in a space - the shape UX-315 removed from 49 sites "
            f"in questions.js: {sites}")

    def test_the_search_covers_the_tree_it_claims_to(self):
        """A scan of nothing passes. This says what it actually read."""
        scanned = list(_sources())
        assert len(scanned) > 80, (
            f"the shape scan read only {len(scanned)} files; it was written "
            "against 105 and a pass over a near-empty list means nothing")
        assert any(p.name == "questions.js" for p in scanned), (
            "the file the defect was found in is not in the scanned set")
