"""UX-352: a count in prose is read by nothing but a human.

Review 5, checklist item 1 - *open the module the chapter names and
check the mechanism*. `docs/design/architecture.md` said:

> `bga/viewer/chapters.js` groups them into **seven** chapters, each
> named for a question the reader has

The module has eight, and has had eight since `3c4a96b`, the commit
that introduced it *and wrote that sentence*:

```text
$ node -e 'import("./bga/viewer/chapters.js").then(
      m => console.log(m.CHAPTERS.length, m.CHAPTERS.map(c => c.id).join(",")))'
8 decide,change,compare,time,machine,elements,believe,run

$ git show 3c4a96b:bga/viewer/chapters.js | grep -c '^    id: "'
8
```

So this is not drift: the number was never true, and three reviews read
past it. That is the argument for a guard rather than a correction, and
it is `UX-322`'s argument verbatim - the CLI table went three reviews
and two filings before a guard held it, and has not moved since.

**The count is the whole claim.** When this was filed the Out of Scope
section said the bullet's chapter *table* was correct and out of scope.
There is no table: the bullet is prose, and the number in it is the
only place `architecture.md` says how many chapters the viewer has.
That is also why nothing contradicted it for three reviews - there
were no rows to count against the word.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs/design/architecture.md"
CHAPTERS_JS = REPO / "bga/viewer/chapters.js"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The prose spells small numbers as words, which is the house style and
#: not something a guard should force a document to give up. Only as far
#: as a chapter list could plausibly reach.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12}

#: "…into eight chapters, each named for…" - the claim, in the shape the
#: document makes it. Digits admitted too, so a later edit that writes
#: `8` is read rather than skipped.
_CLAIM = re.compile(r"into (\w+) chapters\b")

_COUNT = """
const chapters = await import(process.env.MOD);
console.log(JSON.stringify({
  count: chapters.CHAPTERS.length,
  ids: chapters.CHAPTERS.map((c) => c.id),
  titles: chapters.CHAPTERS.map((c) => c.title),
}));
"""


def _module():
    """What `chapters.js` actually exports.

    Through node rather than by counting `id:` lines with a regex: the
    file has an `UNCHAPTERED` fallback with an `id` of its own, and a
    regex over the source would count nine and call the document wrong
    for saying eight. The module is the authority and it can be asked.
    """
    done = subprocess.run(
        [node, "--input-type=module", "-e", _COUNT],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env={**os.environ, "MOD": CHAPTERS_JS.as_uri()})
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _claimed():
    """`(number, sentence)` for the architecture's chapter count."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    found = _CLAIM.search(text)
    assert found, (
        "architecture.md no longer says how many chapters the viewer "
        "groups the document into - if the sentence moved, this guard "
        "has to move with it rather than pass silently")
    word = found.group(1)
    number = WORDS.get(word.lower(), None)
    if number is None and word.isdigit():
        number = int(word)
    assert number is not None, (
        f"the count reads {word!r}, which is neither a digit nor one of "
        f"{sorted(WORDS)}")
    return number, found.group(0)


@needs_node
class TestTheProseCountsWhatTheModuleHolds:
    def test_the_architecture_says_how_many_chapters_there_are(self):
        claimed, sentence = _claimed()
        actual = _module()
        assert claimed == actual["count"], (
            f"architecture.md says {sentence!r}; `chapters.js` exports "
            f"{actual['count']}: {actual['ids']}")

    def test_the_sentence_is_still_there_to_read(self):
        """The instrument. `_claimed` asserts the sentence exists, and
        this is what makes that assertion a *test* rather than a
        precondition nobody would see fail: an edit that rewords the
        bullet past the pattern must redden here rather than make the
        clause above vacuous."""
        claimed, sentence = _claimed()
        assert "chapters" in sentence and claimed > 0, sentence

    def test_the_module_is_the_authority_this_reads(self):
        """And the other end of it. A `chapters.js` that stopped
        exporting `CHAPTERS` would make the comparison unreachable, and
        the failure should name that rather than a JSON decode."""
        actual = _module()
        assert actual["count"] == len(set(actual["ids"])), actual["ids"]
        assert all(actual["titles"]), actual["titles"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
