"""UX-408: `serialized_pairs` was described as its own opposite.

The computation (`bga/structural/batching.py:96-101`) collects pairs
that are **not** independent - same dependency chain - kept so a reader
can see *why* two elements were not batched:

```python
serialized_pairs: List[Tuple[str, str]] = [
    (a, b) ... if not _are_independent(a, b, reachable_downstream)
]
```

The terminal printed that honestly. The schema description the **page**
renders said the opposite:

```text
"Pairs that ran one after the other with nothing forcing the order."
```

So a page reader was told these pairs are unforced serialization - free
wins - when the computation selected them *because* the order is forced,
and would have gone off to "fix" pairs the tool knows cannot be batched.
The viewer and the terminal disagreed about the same rows at the caption
level, which is the page's own never-disagree property broken.

**One string, not two held equal.** The filing offers a table pinning
each (description, caption) pair. Two copies a guard holds equal can
still both be edited in one commit, and this pair drifted for as long as
it existed; the sentence is now a module constant that both import. What
is left to guard is that it still describes what the code selects for -
which no equality between two copies could ever have caught.
"""
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas                                      # noqa: E402

BATCHING = REPO / "bga/structural/batching.py"
TEXT_REPORT = REPO / "bga/report/text.py"


def _serialized_pairs_node():
    node = schemas.schema(schemas.ANALYZE)["properties"]
    return node["batch_opportunities"]["properties"]["serialized_pairs"]


class TestTheSentenceDescribesWhatTheCodeSelects:
    def test_the_page_and_the_terminal_read_one_string(self):
        """Not two that agree today.

        `bga/report/text.py` builds its caption from the same constant
        the schema publishes, so there is no second copy to drift.
        """
        source = TEXT_REPORT.read_text(encoding="utf-8")
        assert "schemas.SERIALIZED_PAIRS_MEANING" in source, (
            "the terminal caption is its own string again; the two said "
            "opposite things for as long as that was true")
        assert _serialized_pairs_node()["description"] == (
            schemas.SERIALIZED_PAIRS_MEANING)

    def test_it_says_the_order_is_forced(self):
        """The sentence's whole content, and the defect inverted.

        `not _are_independent(...)` is the filter; a description that
        says nothing forces the order describes the complement of what
        is published.
        """
        said = schemas.SERIALIZED_PAIRS_MEANING.lower()
        assert "same dependency chain" in said, said
        assert "not independently batchable" in said, said
        assert "nothing forcing" not in said, (
            "the description is the negation of what the computation "
            "selects for - the exact sentence UX-408 was filed on")

    def test_the_computation_still_selects_the_dependent_pairs(self):
        """The premise the sentence rests on.

        A sentence checked only against another sentence is two opinions.
        This reads the filter itself: if `batching.py` ever starts
        collecting the *independent* pairs, the description becomes wrong
        again and nothing about the two strings would notice.
        """
        source = BATCHING.read_text(encoding="utf-8")
        block = re.search(
            r"serialized_pairs[^\n]*=\s*\[(.*?)\n    \]", source, re.S)
        assert block, "serialized_pairs is no longer built as a list here"
        assert "if not _are_independent" in block.group(1), (
            "the filter no longer selects the pairs that are NOT "
            "independent, so the description this item corrected is "
            f"describing something else: {block.group(1)[:200]}")


class TestTheCaptionATerminalPrints:
    """The rendered line, from the committed fixture that has the rows.

    A source-text clause alone would pass on a caption that is built
    from the constant and then never reached.
    """

    def test_the_rendered_caption_carries_the_sentence(self):
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze",
             str(REPO / "tests/fixtures/macro_micro/run")],
            capture_output=True, text=True, cwd=REPO, timeout=120,
            env=dict(os.environ, PYTHONPATH=str(REPO)))
        assert done.returncode == 0, done.stderr[-2000:]
        line = next((row for row in done.stdout.splitlines()
                     if row.strip().startswith("Serialized (")), None)
        assert line, "the fixture no longer prints a serialized-pairs line"
        # The caption opens the sentence mid-line, so it lower-cases the
        # first letter and keeps everything else.
        assert schemas.SERIALIZED_PAIRS_MEANING[1:-1] in line, line
