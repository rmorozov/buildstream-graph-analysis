"""UX-563: Part 8.2's `UNKNOWN` holder is a state the code cannot reach.

Measured when this was filed:

```text
specification.md:625-632          blocking_tasks = UNKNOWN, ambiguous = true
specification.md:2821 (Part 42)   Holder set + `UNKNOWN`; never invent a blocker
blame_chain.py:556-563, :780      'ambiguous': False - "structurally always False"
invariants.py:323-327             sums it -> Part 33.4's term is a constant 0
```

Part 32.7.1 records the decision: the occupancy holder model retired the
state, `UNKNOWN` stays reserved, and the hard rule is enforced by the
model rather than by the flag. The three claims below are the ones that
note makes, each read off the thing it names.

The first is an AST walk, not a grep: `'ambiguous'` occurs in this
repository as a docstring word, as a Plane 2 correlation key and as a
dict key, and only the last is the subject (§5's first proxy shape).

holds: rules.md#never-invent-data-the-spec-says-must-be-unknown-or-absent
"""
import ast
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SPEC = REPO / "docs/spec/specification.md"
ATTRIBUTION = REPO / "bga/attribution"


def _note():
    """32.7.1's own text, subject only - bounded so a sentence in
    another Part cannot satisfy a claim about this one."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("### 32.7.1 ")
    return text[start:text.index("\n### ", start + 5)] \
        if "\n### " in text[start:] else text[start:text.index("\n---", start)]


def _ambiguous_values():
    """Every value any module under `bga/attribution/` assigns to an
    `'ambiguous'` dict key, as (module, literal-or-None)."""
    found = []
    for path in sorted(ATTRIBUTION.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "ambiguous":
                        literal = (value.value
                                   if isinstance(value, ast.Constant) else None)
                        found.append((path.name, literal, node.lineno))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.slice, ast.Constant)
                            and target.slice.value == "ambiguous"):
                        literal = (node.value.value
                                   if isinstance(node.value, ast.Constant)
                                   else None)
                        found.append((path.name, literal, node.lineno))
    return found


class TestNoCodePathWritesTheState:
    """The structural half: `True` is not written anywhere, so the flag
    is a declaration and not a placeholder waiting for a case."""

    def test_the_holder_flag_is_written_and_only_ever_false(self):
        values = _ambiguous_values()
        assert values, (
            "no module under bga/attribution/ writes an 'ambiguous' key - "
            "either the holder record lost the key or this guard stopped "
            "finding it")
        offenders = [v for v in values if v[1] is not False]
        assert not offenders, (
            "Part 32.7.1 says `'ambiguous': False` is the only value any "
            "code path writes; these write something else, so the state is "
            "reachable and the note is wrong", offenders)


def _saturated_resource_wait():
    """A genuinely saturated wait, and the holder record the classifier
    returns for it.

    The golden run has no RESOURCE_WAIT segment at all - measured, 10
    segments, all EXECUTION_ON_CHAIN - so a guard reading it would pass
    on an empty population rather than on the flag. This is the smallest
    input that reaches the code under test.
    """
    from bga.attribution.blame_chain import BlameChainAnalyzer
    from bga.ingest.models import NormalizedTask, Resource, TaskKey, TaskKind

    def task(uid, ready_us, start_us, finish_us):
        return NormalizedTask(
            task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
            ready_us=ready_us, start_us=start_us, finish_us=finish_us,
            resources=[Resource.PROCESS])

    waiting = task("waiting.bst", 0, 10000, 20000)
    holder = task("holder.bst", 0, 0, 10000)
    analyzer = BlameChainAnalyzer(normalized_tasks=[waiting, holder])
    is_wait, info = analyzer.classify_resource_wait(
        waiting, {}, {Resource.PROCESS: 1})
    assert is_wait is True, "the scenario stopped being a resource wait"
    return waiting, info


class TestTheConfidenceTermIsConstantZero:
    """The consequence half: Part 33.4's `ambiguous_wait_time` input.
    `UX-563`'s finding was that the gate reads a zero that can never be
    anything else, and 32.7.1's second row says so."""

    def test_a_real_saturated_wait_names_a_holder_and_is_not_ambiguous(self):
        """32.7.1's argument, on the code: every microsecond reported is
        backed by an identified holder, so there is nothing to flag."""
        _, info = _saturated_resource_wait()
        assert info["blocking_tasks"], (
            "a saturated wait reported no holder at all - that is exactly "
            "the state 8.2 calls UNKNOWN, and 32.7.1 says it cannot arise")
        assert info["ambiguous"] is False, (
            "the classifier flagged a wait ambiguous; 32.7.1's first row "
            "says False is the only value written", info)

    def test_the_term_is_live_and_the_real_record_contributes_nothing(self):
        """Differential, so a dead term cannot pass as a zero one: the
        same segment scored twice, once with the record the classifier
        actually returns and once with its flag forced true. The second
        must move the score - otherwise this guard is reading a term
        nothing consumes."""
        from bga.attribution.blame_chain import (AttributionCategory,
                                                 AttributionSegment)
        from bga.validation.invariants import compute_confidence

        waiting, info = _saturated_resource_wait()

        def score(holder_info):
            segment = AttributionSegment(
                start_us=0, end_us=10000,
                category=AttributionCategory.RESOURCE_WAIT,
                task_key=waiting.task_key,
                metadata={"holder_info": holder_info})
            confidence, _ = compute_confidence(
                normalized_tasks=[waiting], run_context=None, trace=None,
                graph=None, violations=[], attribution_segments=[segment],
                graph_analysis=None,
                attribution={"untracked_head_us": 0, "untracked_tail_us": 0},
                floors={})
            return confidence["attribution_score"]

        forced = dict(info, ambiguous=True)
        assert score(forced) < 1.0, (
            "forcing the flag true did not penalise the attribution score, "
            "so this guard reads a term the gate no longer consumes")
        assert score(info) == 1.0, (
            "the record the classifier really returns penalised the score, "
            "so Part 33.4's ambiguous_wait_time term is not the constant 0 "
            "that 32.7.1's second row declares")


class TestTheRegistrySaysSo:
    """A retired state that is retired only in the code is the defect
    `UX-563` filed. The note is the other half of the fix."""

    def test_the_note_names_the_part_and_both_consumers(self):
        note = " ".join(_note().split())
        assert "Part 8.2" in note and "Part 42" in note, (
            "32.7.1 should name both places the spec states the rule", note)
        assert "bga/attribution/blame_chain.py" in note, (
            "32.7.1 should name the module that writes the flag", note)
        assert "bga/validation/invariants.py" in note, (
            "32.7.1 should name Part 33.4's consumer", note)

    def test_the_note_keeps_unknown_reserved(self):
        """The hard rule did not change; only its enforcement did. A
        note that read as licence to invent a holder would be worse
        than the drift it settles."""
        note = " ".join(_note().split())
        assert "`UNKNOWN` remains reserved; nothing writes it." in note, (
            "32.7.1 should say UNKNOWN stays reserved", note)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
