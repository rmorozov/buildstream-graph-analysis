"""UX-252: the release body is generated, and regenerating changes nothing.

`closed.md` already holds a one-line statement of what was wrong and a
summary of what shipped, per item, written at the moment the work was
verified. Hand-writing a release body would make a third copy of those
facts after the task file's Outcome and the closed row, and two
hand-maintained copies of one fact drifting apart is this repository's
most-repeated defect.

So the body is generated and only the head is written. This file holds
both halves of that: the generator does what it claims, and the
committed body is what the generator produces.
"""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = REPO / "CHANGELOG.md"

GENERATED = re.compile(r"<!-- generated: UX-252 (\d+)→(\d+) -->\n(.*?)"
                       r"<!-- /generated -->", re.S)


def _generate(start, end):
    out = subprocess.run(
        [sys.executable, "-m", "tools.bga_release_notes",
         "--from", str(start), "--to", str(end)],
        capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr
    return out.stdout


class TestTheGeneratorDoesWhatItClaims:
    def test_it_emits_every_row_in_the_range_and_no_others(self):
        """A release note that silently drops an item reads as "nothing
        else landed", which is the one thing a changelog must not do."""
        from tools import bga_release_notes as notes

        rows = notes._rows()
        window = rows[230:238]
        body = notes.render(230, 238)
        for row in window:
            assert row["id"] in body, f"{row['id']} is in the range and not the body"
        assert body.count("\n- ") == len(window), (
            f"{body.count(chr(10) + '- ')} bullets for {len(window)} rows")
        for row in rows[:230] + rows[238:]:
            assert f"[{row['id']}]" not in body, (
                f"{row['id']} is outside the range and in the body")

    def test_it_is_deterministic(self):
        from tools import bga_release_notes as notes

        assert notes.render(200, 220) == notes.render(200, 220)

    def test_an_impossible_range_is_an_error_not_an_empty_body(self):
        """Silence would read as "nothing landed"."""
        from tools import bga_release_notes as notes

        with pytest.raises(ValueError):
            notes.render(0, 100_000)
        with pytest.raises(ValueError):
            notes.render(10, 5)

    def test_an_empty_range_says_so(self):
        from tools import bga_release_notes as notes

        assert "No scenarios closed" in notes.render(50, 50)

    def test_it_groups_by_the_topic_the_task_file_declares(self):
        from tools import bga_release_notes as notes

        assert notes._topic("UX-238") == "guards"
        assert notes._topic("UX-233") == "docs"
        assert notes._topic("UX-9999") == "uncategorised", (
            "an item with no task file is dropped rather than surfaced")

    def test_the_topic_order_puts_contracts_before_process(self):
        """A reader scanning for "what changed for me" wants the
        contract and CLI news first; alphabetical buries `contracts`."""
        from tools import bga_release_notes as notes

        assert notes.TOPIC_ORDER.index("contracts") < notes.TOPIC_ORDER.index("docs")
        assert notes.TOPIC_ORDER.index("cli") < notes.TOPIC_ORDER.index("guards")


class TestTheCommittedBodyIsGenerated:
    def test_every_generated_block_matches_the_generator(self):
        """The `test_golden.py` property, for release notes: regenerate
        and there is no diff.

        The markers carry the range, so this needs nothing but the file
        - a range kept somewhere else would be the second copy this
        item exists to avoid.
        """
        text = CHANGELOG.read_text(encoding="utf-8")
        blocks = GENERATED.findall(text)
        assert blocks, (
            "CHANGELOG.md has no `<!-- generated: UX-252 N→M -->` block; "
            "the body is supposed to be generated")
        for start, end, committed in blocks:
            expected = _generate(int(start), int(end))
            assert committed == expected, (
                f"the committed body for markers {start}→{end} is not what "
                f"`bga release-notes --from {start} --to {end}` produces - "
                f"regenerate it rather than editing it by hand")

    def test_the_head_is_outside_the_generated_block(self):
        """The judgment half stays written. A generated theme would be
        a summary of summaries and worth nothing."""
        text = CHANGELOG.read_text(encoding="utf-8")
        head = text.split("<!-- generated:", 1)[0]
        assert "Contract delta:" in head
        assert "Upgrade note:" in head
        assert "Carried findings" in head

    def test_the_release_guide_says_not_to_hand_write_it(self):
        guide = " ".join((REPO / "docs/contributing/release-guide.md")
                         .read_text(encoding="utf-8").split())
        assert "Do not hand-write it" in guide
        assert "bga release-notes" in guide


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
