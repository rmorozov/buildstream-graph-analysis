"""UX-767: the gate covers one channel, and the row it names says so.

`gate_covers_push.py` fires only on a Bash tool call in this session.
The channel mix behind rounds 103-105's 41 pushes is not recoverable
from committed material - only that at least one used this covered
channel, so the hook is non-total. Read here, not enforced by a second
check: this is a text guard, so it can confirm the sentence's
substantive terms are present, never that the sentence is *true*.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
HOOK_MODULE = REPO / ".claude/hooks/gate_covers_push.py"
FIXING_GUIDE = REPO / "docs" / "contributing" / "fixing-guide.md"

#: The claim's substantive terms, not just the citation - a citation
#: survives a rewrite that reverses the meaning it names (the
#: verifier's finding: both prior guards passed a boundary sentence
#: replaced by "this hook catches every push on every channel" with
#: `UX-767` left in place). Collapsed to single spaces before matching:
#: the hook's docstring wraps the same phrase across two source lines.
SUBSTANTIVE_TERMS = ("not recoverable from committed material",
                      "at least one used this covered channel")
REVERSAL = "this hook catches every push on every channel"


def _collapsed(text):
    return " ".join(text.split())


def _reversed(text, anchor, end_marker):
    """`text` with the whole boundary paragraph naming `anchor` (up to
    `end_marker`, exclusive) swapped for one that claims total coverage
    - the verifier's own mutation. A single `"."` will not do: the
    substantive terms sit in the sentence *after* the first period."""
    start = text.index(anchor)
    end = text.index(end_marker, start)
    return text[:start] + REVERSAL + " (UX-767).\n" + text[end:]


class TestTheHookNamesItsOwnChannel:
    def test_the_hook_docstring_states_the_boundary(self):
        text = _collapsed(HOOK_MODULE.read_text(encoding="utf-8"))
        assert "PreToolUse" in text
        for term in SUBSTANTIVE_TERMS:
            assert term in text, f"missing substantive term: {term!r}"

    def test_the_fixing_guide_states_the_boundary(self):
        text = _collapsed(FIXING_GUIDE.read_text(encoding="utf-8"))
        assert "Bash tool call" in text
        for term in SUBSTANTIVE_TERMS:
            assert term in text, f"missing substantive term: {term!r}"

    def test_a_reversal_that_keeps_the_citation_fails_the_hook_guard(self):
        text = HOOK_MODULE.read_text(encoding="utf-8")
        reversed_text = _collapsed(_reversed(text, "Channel, not command", '"""'))
        assert "UX-767" in reversed_text
        assert not all(term in reversed_text for term in SUBSTANTIVE_TERMS)

    def test_a_reversal_that_keeps_the_citation_fails_the_guide_guard(self):
        text = FIXING_GUIDE.read_text(encoding="utf-8")
        reversed_text = _collapsed(_reversed(text, "It also only ever fires", "\n\n"))
        assert "UX-767" in reversed_text
        assert not all(term in reversed_text for term in SUBSTANTIVE_TERMS)
