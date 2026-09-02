"""UX-514: the capture ref is pinned on purpose, and the workflow says so.

Nine published capture refs, one commit:

```text
$ git grep -n 953683fb .github/workflows/real-project-capture.yml
74:  default: 953683fb96b82cdf6d7941c4ba9859378942f22b
163:  FDSDK_REF: ${{ github.event.inputs.fdsdk_ref || '953683fb...' }}
```

A `schedule:` trigger cannot supply workflow inputs, so both crons take
the default. `UX-92`'s cache gate was deferred four times - n=3, n=5,
n=6, n=7 - each time reading the wait as temporary, and it is not: this
schedule is structurally incapable of a second commit.

So the workflow states one of two policies, and this file holds the
**policy word and the mechanism together**. `pinned` with a ref that
moves, or `advanced` with a ref that cannot, is the disagreement the
next round would otherwise re-derive from the capture list.

`UX-354` is why this reads the workflow at all: a workflow nothing reads
drifts, twice found by a red pull request rather than by the suite.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/real-project-capture.yml"

#: The two policies `UX-514` chose between, and what each one *is*: a
#: policy is not a word in a comment, it is whether anything moves the
#: ref. `pinned` - nothing does. `advanced` - something does, on a
#: stated cadence.
POLICIES = ("pinned", "advanced")

POLICY = re.compile(r"capture-ref-policy:\s*(\w+)")
BINDS = re.compile(r"(?<![$\w])FDSDK_REF\s*[:=]")
#: The env fallback: what a `schedule:` run actually captures.
FALLBACK = re.compile(
    r"FDSDK_REF:\s*\$\{\{\s*github\.event\.inputs\.fdsdk_ref\s*\|\|\s*"
    r"'([0-9a-f]{40})'\s*\}\}")


def _text():
    return WORKFLOW.read_text(encoding="utf-8")


def _input_block():
    """The `fdsdk_ref` input and its own comment, and nothing else.

    Read as a block rather than as the whole file so a policy word
    written in the file header - or in a *different* input's comment -
    is not mistaken for this one's. `UX-354`'s own lesson, one level
    down: say which part of the document is the subject."""
    lines = _text().splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.strip() == "fdsdk_ref:")
    end = next(i for i in range(start + 1, len(lines))
               if re.match(r"^      \w+:", lines[i]))
    return "\n".join(lines[start:end])


def declared_policy():
    found = POLICY.findall(_input_block())
    assert len(found) == 1, f"{len(found)} policy declarations, want 1: {found}"
    assert found[0] in POLICIES, found[0]
    return found[0]


def _env_fallback_line():
    line = next((one for one in _text().splitlines()
                 if one.strip().startswith("FDSDK_REF:")), None)
    assert line, "the workflow no longer sets FDSDK_REF"
    return line


def ref_bindings():
    """Every non-comment line that decides what `FDSDK_REF` becomes.

    Comments are stripped first, and that is the whole point. The first
    version of this guard read the mechanism as "the file says
    `ls-remote` somewhere" and passed on a policy word with nothing
    behind it: the only `ls-remote` here is in a comment explaining how
    to *list published capture refs*, which moves nothing.
    """
    bindings = []
    for line in _text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        code = re.split(r"\s#", line, maxsplit=1)[0]
        # `FDSDK_REF:` or `FDSDK_REF=` - a binding. `$FDSDK_REF` is a
        # step *reading* it, and three steps do.
        if BINDS.search(code):
            bindings.append(code.strip())
    assert bindings, "the workflow no longer binds FDSDK_REF at all"
    return bindings


class TestThePolicyIsDeclaredWhereThePinIs:
    def test_the_input_declares_exactly_one_policy(self):
        assert declared_policy() in POLICIES

    def test_the_two_copies_of_the_pin_are_the_same_commit(self):
        """A dispatch reads the input's default and a cron reads the env
        fallback. They are two hand-written copies of one ref, and a bump
        that moved one of them would give the two triggers two different
        populations without saying so anywhere."""
        block = _input_block()
        default = re.search(r"default:\s*([0-9a-f]{40})", block)
        assert default, block
        # Every commit the env line names, not the one a strict shape
        # would match - the shape is the *other* clause's subject, and a
        # guard reading both reddens twice for one change.
        fallback = re.findall(r"[0-9a-f]{40}", _env_fallback_line())
        assert fallback, _env_fallback_line()
        assert set(fallback) == {default.group(1)}, (
            f"dispatch captures {default.group(1)[:8]}, a cron captures "
            f"{[one[:8] for one in fallback]}")


class TestThePolicyAndTheMechanismAgree:
    """The claim `UX-514` closes on. The mechanism is what a scheduled
    run resolves `FDSDK_REF` to: a literal is `pinned`, and anything
    that varies by trigger, by date or by a lookup is `advanced`."""

    def test_a_pinned_ref_has_nothing_that_moves_it(self):
        if declared_policy() != "pinned":
            pytest.skip("the workflow declares `advanced`")
        moving = [one for one in ref_bindings() if not FALLBACK.fullmatch(one)]
        assert not moving, (
            "`capture-ref-policy: pinned`, but something other than the "
            "dispatch input decides the ref:\n  " + "\n  ".join(moving))

    def test_an_advanced_ref_has_something_that_moves_it(self):
        """The other direction, and the one that makes the word cost
        something: declaring `advanced` over a schedule that can only
        ever capture one commit is exactly the disagreement this file
        exists to catch."""
        if declared_policy() != "advanced":
            pytest.skip("the workflow declares `pinned`")
        moving = [one for one in ref_bindings() if not FALLBACK.fullmatch(one)]
        assert moving, (
            "`capture-ref-policy: advanced`, but the only binding of the "
            "ref is the dispatch input or one literal - a `schedule:` "
            "trigger supplies no inputs, so every cron still captures the "
            "one hardcoded commit:\n  " + "\n  ".join(ref_bindings()))

    def test_the_comment_says_what_the_choice_costs(self):
        """`UX-92` was deferred four times on a wait that cannot end. The
        pin's comment is where that is written down, so the fifth
        re-check reads it instead of re-deriving it from the ref list."""
        block = _input_block()
        assert "UX-92" in block, (
            "the pin no longer names the gate it makes impossible")


if __name__ == "__main__":                       # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
