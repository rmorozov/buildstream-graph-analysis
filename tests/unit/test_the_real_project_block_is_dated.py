"""UX-492: the README's real-project block is an archive, and says so.

The block under *On a real project* introduced itself as **verbatim** —
a claim about provenance, not a hedge — and held a sentence the tool
stopped being able to print when `UX-475` split the zero-slack note in
two:

```text
README said                          the emitters can produce
Note: 77% of elements have zero      Note: N% ... , N of them off the
slack - this graph is a mesh of      critical path - this graph is a mesh
near-equal chains, so ...            Note: N% ... , all on the critical
                                     path - no second chain of equal
                                     length ...
```

The run behind it is a 3614-second `freedesktop-sdk` build (capture run
`32064333551`) that neither a clone nor CI can re-run, so the fix was
the second branch of the filing: date the block and drop the currency
claim. That leaves two things a guard can hold, and they are opposite
halves of one rule — the section carries its provenance, and it does
not present the block as this build's output.

`test_the_readme_block_is_the_real_output.py` covers the other block,
the one whose command a guard can actually run. This one cannot diff
against a fresh run; what it can do is prove the block still needs its
date.
"""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
README = REPO / "README.md"
SCENARIOS = REPO / "docs/backlog/scenarios"

#: One fixture per branch of the note `UX-475` split, so the comparison
#: below is against **both** sentences the code can emit and not just
#: the one the golden fixture happens to take.
FIXTURES = {
    "chain-graph": "tests/fixtures/golden/mixed_task_kinds",
    "mesh-graph": "tests/fixtures/one_source_many_elements/run",
}

#: The two ways the capture is named in the section, and the one value
#: that has to be the same in both.
RUN_ID = re.compile(r"actions/runs/(\d+)")
CAPTURE_REF = re.compile(r"captures/[A-Za-z0-9_./-]+")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
TASK_ID = re.compile(r"\bUX-(\d+)\b")


def _section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index("## On a real project")
    return text[start:text.index("\n## ", start + 4)]


def _block() -> list:
    fences = re.findall(r"```text\n(.*?)```", _section(), re.S)
    assert len(fences) == 1, (
        f"the section has {len(fences)} `text` fences; this guard reads "
        f"the one holding the archived report")
    return fences[0].splitlines()


def _normalise(sentence: str) -> str:
    """Whitespace and digits out: the block is wrapped to the page's
    width and the fixtures are three-element graphs, so a comparison
    that kept either would answer a question about layout rather than
    about wording."""
    return re.sub(r"\d+", "N", " ".join(sentence.split()))


def _pasted_note() -> str:
    """The block's `Note:` line, unwrapped.

    It continues onto the next lines until the report's own indentation
    starts a new finding, which is the only structure the fence has.
    """
    lines = _block()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("Note:"))
    indent = len(lines[start]) - len(lines[start].lstrip())
    parts = [lines[start].strip()]
    for line in lines[start + 1:]:
        if len(line) - len(line.lstrip()) < indent or line.strip().startswith("Note:"):
            break
        parts.append(line.strip())
    return _normalise(" ".join(parts))


@pytest.fixture(scope="module")
def emitted_notes():
    """Every zero-slack note the current code can produce, normalised."""
    notes = {}
    for expected_id, fixture in FIXTURES.items():
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", fixture, "--format", "json"],
            capture_output=True, text=True, cwd=str(REPO), timeout=180)
        assert done.returncode == 0, done.stderr
        import json

        found = {f["id"]: f["title"] for f in json.loads(done.stdout)["findings"]}
        assert expected_id in found, (
            f"{fixture} no longer publishes {expected_id!r}; this guard "
            f"reads it to learn what the code can print", sorted(found))
        notes[expected_id] = _normalise(found[expected_id])
    return notes


class TestTheSectionDoesNotPresentTheBlockAsCurrent:
    def test_it_does_not_call_the_block_verbatim(self):
        """The claim the item was filed for. `verbatim` is provenance:
        a reader who diffs it against their own run concludes the tool
        is wrong rather than the document."""
        assert "verbatim" not in _section(), (
            "the real-project section calls its archived block verbatim "
            "again; the run behind it cannot be re-run, so the block "
            "cannot carry that claim")

    def test_the_pasted_note_is_one_no_emitter_can_produce(self, emitted_notes):
        """Why the date is load-bearing rather than decorative. If this
        line becomes printable again the section's account of what
        changed is wrong, and the framing has to be re-decided rather
        than left standing."""
        pasted = _pasted_note()
        assert pasted not in emitted_notes.values(), (
            "the block's zero-slack note is one the code prints today, so "
            "the section's 'kept, not current' framing no longer "
            "describes it", pasted, emitted_notes)

    def test_the_two_emitters_still_differ_from_each_other(self, emitted_notes):
        """The clause that keeps the check above from passing vacuously:
        if both fixtures produced the same sentence, one branch would be
        unexercised and the comparison would be against half the code."""
        assert len(set(emitted_notes.values())) == 2, (
            "both fixtures print the same zero-slack note; one branch of "
            "the split is no longer covered", emitted_notes)


class TestTheSectionSaysWhereTheBlockIsFrom:
    def test_it_names_the_capture_run_and_the_day_it_ran(self):
        section = _section()
        assert RUN_ID.search(section), (
            "the section names no capture run, so the block's numbers "
            "cannot be traced to a run that produced them")
        assert ISO_DATE.search(section), (
            "the section gives no date for the capture; 'an old run' is "
            "not a date a reader can check")

    def test_the_capture_ref_and_the_linked_run_are_the_same_run(self):
        """Two names for one capture, and a half-updated section is how
        they stop agreeing."""
        section = _section()
        linked = RUN_ID.search(section)
        assert linked, "the section links no capture run to check the ref against"
        run_id = linked.group(1)
        refs = [ref for ref in CAPTURE_REF.findall(section) if "/" in ref[len("captures/"):]]
        assert refs, "the section names no `captures/…` ref for the block"
        assert any(ref.endswith(run_id) for ref in refs), (
            f"the section links run {run_id} but names capture ref(s) "
            f"{refs}, which are a different run")

    def test_every_task_it_names_is_a_task_that_exists(self):
        """The section explains what changed by naming rows. A typo'd or
        retired id is a dead end where the explanation should be."""
        named = sorted(set(TASK_ID.findall(_section())))
        missing = [f"UX-{n}" for n in named
                   if not list(SCENARIOS.glob(f"UX-{int(n):04d}-*.md"))]
        assert missing == [], (
            f"the section names task(s) with no file under "
            f"docs/backlog/scenarios: {missing}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
