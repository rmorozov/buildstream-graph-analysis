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

#: `UX-511`: the guide the README links carries the same archived block
#: and had the same three defects, so the clauses below read both rather
#: than one. Each entry is the heading whose section holds the block.
DOCUMENTS = {
    "README.md": "## On a real project",
    "docs/guides/real-project.md": "## Step 3 - read the headline",
}

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


def _section(document="README.md") -> str:
    path = REPO / document
    text = path.read_text(encoding="utf-8")
    # The em dash in the guide's heading is a real one in the file; the
    # table above spells it with a hyphen so the source of this guard
    # stays greppable, so the lookup is on the prefix before it.
    heading = DOCUMENTS[document].split(" - ")[0]
    start = text.index(heading)
    return text[start:text.index("\n## ", start + 4)]


def _block(document="README.md") -> list:
    fences = re.findall(r"```text\n(.*?)```", _section(document), re.S)
    assert len(fences) == 1, (
        f"{document}'s section has {len(fences)} `text` fences; this "
        f"guard reads the one holding the archived report")
    return fences[0].splitlines()


def _normalise(sentence: str) -> str:
    """Whitespace and digits out: the block is wrapped to the page's
    width and the fixtures are three-element graphs, so a comparison
    that kept either would answer a question about layout rather than
    about wording."""
    return re.sub(r"\d+", "N", " ".join(sentence.split()))


def _pasted_note(document="README.md") -> str:
    """The block's `Note:` line, unwrapped.

    It continues onto the next lines until the report's own indentation
    starts a new finding, which is the only structure the fence has.
    """
    lines = _block(document)
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


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
class TestTheSectionDoesNotPresentTheBlockAsCurrent:
    def test_it_does_not_call_the_block_verbatim(self, document):
        """The claim the item was filed for. `verbatim` is provenance:
        a reader who diffs it against their own run concludes the tool
        is wrong rather than the document."""
        assert "verbatim" not in _section(document), (
            f"{document}'s real-project section calls its archived block "
            f"verbatim again; the run behind it cannot be re-run, so the "
            f"block cannot carry that claim")

    def test_the_pasted_note_is_one_no_emitter_can_produce(
            self, document, emitted_notes):
        """Why the date is load-bearing rather than decorative. If this
        line becomes printable again the section's account of what
        changed is wrong, and the framing has to be re-decided rather
        than left standing."""
        pasted = _pasted_note(document)
        assert pasted not in emitted_notes.values(), (
            f"{document}'s zero-slack note is one the code prints today, "
            f"so the section's 'kept, not current' framing no longer "
            f"describes it", pasted, emitted_notes)

    def test_the_block_does_not_carry_the_label_ux_365_retired(self, document):
        """`UX-511`: the guide held `Biggest Opportunity` where the
        emitters print `Biggest wait category`, and taught it in prose
        underneath as the current label. A reader following the README's
        link met the retired reading twice."""
        assert "Biggest Opportunity:" not in _section(document), (
            f"{document} prints `Biggest Opportunity:` in its block; "
            f"UX-365 scoped that label to `Biggest wait category`")

    def test_the_two_emitters_still_differ_from_each_other(
            self, document, emitted_notes):
        """The clause that keeps the check above from passing vacuously:
        if both fixtures produced the same sentence, one branch would be
        unexercised and the comparison would be against half the code."""
        assert len(set(emitted_notes.values())) == 2, (
            "both fixtures print the same zero-slack note; one branch of "
            "the split is no longer covered", emitted_notes)


@pytest.mark.parametrize("document", sorted(DOCUMENTS))
class TestTheSectionSaysWhereTheBlockIsFrom:
    def test_it_names_the_capture_run_and_the_day_it_ran(self, document):
        section = _section(document)
        assert RUN_ID.search(section), (
            "the section names no capture run, so the block's numbers "
            "cannot be traced to a run that produced them")
        assert ISO_DATE.search(section), (
            "the section gives no date for the capture; 'an old run' is "
            "not a date a reader can check")

    def test_the_capture_ref_and_the_linked_run_are_the_same_run(self, document):
        """Two names for one capture, and a half-updated section is how
        they stop agreeing."""
        section = _section(document)
        linked = RUN_ID.search(section)
        assert linked, "the section links no capture run to check the ref against"
        run_id = linked.group(1)
        refs = [ref for ref in CAPTURE_REF.findall(section) if "/" in ref[len("captures/"):]]
        assert refs, "the section names no `captures/…` ref for the block"
        assert any(ref.endswith(run_id) for ref in refs), (
            f"the section links run {run_id} but names capture ref(s) "
            f"{refs}, which are a different run")

    def test_every_task_it_names_is_a_task_that_exists(self, document):
        """The section explains what changed by naming rows. A typo'd or
        retired id is a dead end where the explanation should be."""
        named = sorted(set(TASK_ID.findall(_section(document))))
        missing = [f"UX-{n}" for n in named
                   if not list(SCENARIOS.glob(f"UX-{int(n):04d}-*.md"))]
        assert missing == [], (
            f"the section names task(s) with no file under "
            f"docs/backlog/scenarios: {missing}")


class TestTheGuidesAppendixDoesNotClaimFreshness:
    """`UX-511`'s third defect, and the one it called the worst: the
    appendix asserted the Plane 1 figures were the capture's `run/`
    directory *analysed with the current code*, four sentences after
    `UX-492` had shown that four of the emitter's sentences are absent
    from the pasted block. A stale figure is a number; a false claim
    about freshness is an instruction to trust it."""

    GUIDE = REPO / "docs/guides/real-project.md"

    def _appendix(self) -> str:
        text = self.GUIDE.read_text(encoding="utf-8")
        start = text.index("## Appendix: where these numbers came from")
        end = text.find("\n## ", start + 4)
        return text[start:] if end < 0 else text[start:end]

    def test_it_does_not_say_the_figures_are_analysed_with_current_code(self):
        assert "analysed with the current code" not in self._appendix(), (
            "the appendix claims the Plane 1 figures are this capture "
            "re-analysed today; UX-492 measured four sentences the "
            "emitter prints that the block does not carry")

    def test_it_says_which_they_are_instead(self):
        """Removing the claim is half the fix - a reader still has to be
        told what they are looking at."""
        appendix = " ".join(self._appendix().split())
        assert "**not** re-run since" in appendix, (
            "the appendix drops the freshness claim without replacing it, "
            "so a reader is told nothing about what the figures are")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
