"""UX-288: `analyze/v2` publishes each element population once.

Measured on the 1,202-element synthetic run, in `analyze/v1`:

```text
signals.leaf_analysis.leaves                 135 uids
signals.leaf_analysis.leaves_detail          135 uids   identical: True
structural.deferrability.{deferrable,non_}   135 uids   identical: True
signals.critical_path                         14 uids
signals.critical_path_detail                  14 uids   identical, order too
signals.element_durations                  1,202 uids   both are subsets
```

The same membership three times for leaves and twice for the critical
path. A consumer meeting both copies had nothing telling it which was
authoritative if they ever disagreed - and nothing in the tool would
have noticed, because no guard said they must match.

The page rendered every copy it was given, which is how it surfaced:
19 tables over 13 distinct populations, seven pairs at 100% overlap
(Direction 14).

What is *not* duplication, and was nearly removed as if it were:
`structural.deferrability` partitioned the leaves by a duration-risk
rule that disagrees with `is_potentially_deferrable` by design - 8
against 134 on that run. The membership was the third copy; the split
was information, and it is published now as `deferral_risk` on each
leaf, which the tool had always computed and always dropped.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = REPO / "tests/fixtures/macro_micro/run"

# Populations are **discovered**, not listed.
#
# The first draft named five fields by hand, and the two mutations that
# re-added the removed duplicates reddened only the "these fields are
# gone" test - the selection check itself sailed past, because a
# re-added field was not in the list. A guard that only sees what it was
# told about cannot catch the next instance of the defect it was written
# for.
#
# So the payload is walked: any list of uid-like strings, and any map
# keyed by them, is a population, wherever it lives.
UID = re.compile(r"^[\w][\w./-]*\.bst$")


def _is_uid(value):
    return isinstance(value, str) and bool(UID.match(value))


def _is_narrative(path):
    """A `findings[...]` path restates the data; it does not publish it.

    A finding is the "so what" layer: it names the elements it is about
    and cites the numbers it read. On the macro/micro run that makes
    four pairs the sweep flags and none of them is this item's defect -
    `signals.joint_saving.elements` against the `joint-saving` finding
    that reports it, `optimization-horizon`'s `evidence.steps` against
    its own `elements`, and the two findings that share one subject
    because they are two claims about the same three elements.

    Findings travel into a CI comment as a unit (`UX-75`), so a finding
    that named no elements would be the regression. `UX-288` is about
    the **data** asserting one selection twice with nothing saying which
    copy is authoritative, so the guard checks the data the findings are
    derived from, and `_clashes` is exercised against a planted
    duplicate below so the exclusion cannot quietly become the whole
    check.

    Whether `signals.joint_saving` should exist at all once a finding
    carries every one of its four fields is a fair question and a
    separate one - filed as `UX-291` rather than decided by loosening
    this guard until it passed.
    """
    return path.startswith("findings[")


def _clashes(payload):
    """Every pair of published fields carrying one element selection.

    **Selections, not measures.** Written first over every element-keyed
    field, this immediately found `signals.blast_radius` and
    `signals.element_durations` carrying the same 11 elements - true,
    and not this item's defect. Those are two *measures* over the whole
    population ("the duration of each element", "the blast radius of
    each"), not two claims about which elements are interesting. Their
    shared membership is real repetition and it is `UX-289`'s subject.
    So the full population is excluded, deliberately and with the
    reason, rather than the guard being loosened until it passes.

    **Two elements, not one.** A one-element set matches any other
    one-element set, so the floor is where the signal starts. Measured
    on this fixture, which has a single leaf and a single serialization
    point:

    ```text
    v1 floor=1: 12 clashes      v1 floor=2: 2 clashes
    v2 floor=1:  5 clashes      v2 floor=2: 0 clashes
    ```

    Every one of the five that survive at floor 1 in `v2` is a
    coincidence - `leaf_analysis.leaves_detail` against
    `cache.target_closure.targets`, unrelated fields that both happen to
    name `all.bst`.

    The cost is stated rather than hidden: on *this* fixture the leaves
    duplication is one element and so below the floor. The sweep catches
    it on the 1,202-element run (135 elements, three ways), and
    `test_the_removed_fields_are_gone` names those fields directly so a
    re-add is caught here too.
    """
    everyone = frozenset(payload["signals"].get("element_durations") or {})
    found = {name: members
             for name, members in sorted(_populations(payload).items())
             if len(members) >= 2 and members != everyone}
    clashes = []
    for name, members in found.items():
        for other, others in found.items():
            if other >= name or members != others:
                continue
            if _is_narrative(name) or _is_narrative(other):
                continue
            clashes.append(f"`{name}` and `{other}` ({len(members)} elements)")
    return clashes


def _populations(node, path="", found=None):
    """Every `{path: element set}` the document publishes."""
    found = {} if found is None else found
    if isinstance(node, dict):
        keys = list(node)
        if keys and all(_is_uid(k) for k in keys):
            found[path] = frozenset(keys)
        for key, value in node.items():
            _populations(value, f"{path}.{key}" if path else key, found)
    elif isinstance(node, list):
        if node and all(_is_uid(v) for v in node):
            found[path] = frozenset(node)
        # a list of records that name an element each
        uids = [v.get("element_uid") for v in node
                if isinstance(v, dict) and _is_uid(v.get("element_uid"))]
        if uids and len(uids) == len(node):
            found[path] = frozenset(uids)
        for at, value in enumerate(node):
            _populations(value, f"{path}[{at}]", found)
    return found


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


class TestEachPopulationIsPublishedOnce:
    def test_no_two_selections_carry_the_same_element_set(self, payload):
        """The guard the contract did not have. Two fields naming the
        same *selection* are two answers to one question, and nothing
        says which one a reader should believe if they disagree."""
        assert _clashes(payload) == [], (
            "field(s) publishing the same selection twice - one is a copy, "
            "the other is the place it belongs:\n  "
            + "\n  ".join(_clashes(payload)))

    def test_the_check_would_see_a_planted_duplicate(self, payload):
        """The positive control. Both exclusions above - the full
        population and the narrative - subtract from what is compared,
        and a check that excludes everything passes for the wrong
        reason. So the removed field is put back and the check is asked
        about it: `signals.critical_path`, exactly the shape `UX-288`
        was filed for, in the half of the document the exclusions do not
        cover."""
        planted = json.loads(json.dumps(payload))
        planted["signals"]["critical_path"] = [
            entry["element_uid"]
            for entry in planted["signals"]["critical_path_detail"]]
        assert len(planted["signals"]["critical_path"]) >= 2, (
            "the run's path is too short for the plant to mean anything")
        assert any("signals.critical_path`" in clash
                   for clash in _clashes(planted)), _clashes(planted)

    def test_the_narrative_exclusion_is_bounded(self, payload):
        """`_is_narrative` excuses `findings[...]`, so this pins what it
        is excusing: findings that really do name elements. If the
        payload stopped publishing them the exclusion would still be
        there, silently covering nothing, and the docstring explaining
        it would be describing a document that no longer exists."""
        named = [name for name in _populations(payload)
                 if _is_narrative(name)]
        assert named, "no finding names any element - the exclusion is dead"
        assert any(name.endswith(".elements") for name in named), named

    def test_the_exclusion_is_not_a_hole(self, payload):
        """The full population is excluded in `_clashes`, so this
        asserts it is genuinely the full population and not an empty set
        that would silently excuse everything."""
        everyone = frozenset(payload["signals"].get("element_durations") or {})
        assert len(everyone) >= 4, (
            f"the run has {len(everyone)} elements, too few for the "
            f"exclusion to mean anything")

    def test_the_removed_fields_are_gone(self, payload):
        """Named, so re-adding one is a decision rather than a slip."""
        assert "critical_path" not in payload["signals"]
        assert "leaves" not in (payload["signals"].get("leaf_analysis") or {})
        deferrability = (payload.get("structural") or {}).get("deferrability") or {}
        assert "deferrable_leaves" not in deferrability
        assert "non_deferrable_leaves" not in deferrability
        bottleneck = (payload.get("structural") or {}).get("bottleneck") or {}
        assert "choke_point_impact" not in bottleneck

    def test_the_version_moved_with_them(self, payload):
        """`architecture.md`'s rule: a removal bumps the version. This is
        the first time it has been exercised."""
        assert payload["schema"] == "analyze/v2", payload["schema"]


class TestWhatReplacedThem:
    def test_the_path_is_still_reachable_in_order(self, payload):
        from bga import schemas

        path = schemas.critical_path_uids(payload["signals"])
        assert path, "the critical path is unreachable"
        assert path == [e["element_uid"]
                        for e in payload["signals"]["critical_path_detail"]]

    def test_a_v1_document_is_still_readable(self):
        """`bga` reads its own past output (`UX-249`) and `bga compare`
        reads two runs at once, so a v2 reader that could not read a v1
        path would break the loop this tool exists for."""
        from bga import schemas

        v1 = {"critical_path": ["a.bst", "b.bst"]}
        assert schemas.critical_path_uids(v1) == ["a.bst", "b.bst"]

    def test_the_choke_points_keep_their_rank_and_their_value(self, payload):
        """`choke_points` was ranked and `choke_point_impact` valued the
        same nine elements. One list of records carries both, so neither
        the order the report prints nor the number the page shows had to
        be given up to publish the membership once."""
        from bga import schemas

        points = payload["structural"]["bottleneck"]["choke_points"]
        assert points, "no choke points on this run"
        counts = [entry["downstream_count"] for entry in points]
        assert counts == sorted(counts, reverse=True), counts
        assert schemas.choke_point_uids(payload["structural"]["bottleneck"]) == [
            entry["element_uid"] for entry in points]

    def test_a_v1_bottleneck_is_still_readable(self):
        """Same reason as the critical path above: a v1 document names
        its choke points as bare uids, and a v2 reader still understands
        them."""
        from bga import schemas

        assert schemas.choke_point_uids(
            {"choke_points": ["a.bst", "b.bst"]}) == ["a.bst", "b.bst"]

    def test_each_leaf_carries_its_risk(self, payload):
        """The information the split used to carry, now on the record."""
        detail = ((payload["signals"].get("leaf_analysis") or {})
                  .get("leaves_detail") or {})
        assert detail, "no leaves on this run"
        assert all("deferral_risk" in leaf for leaf in detail.values())

    def test_the_risk_does_not_depend_on_which_sections_ran(self):
        """The defect `test_section_stage_gating` caught while this was
        being built: the risk was joined from the structural stage, so
        `--section diagnostics` published `None` where a full run
        published `medium` - a different answer for the same run. The
        rule reads only the task's kind and duration, so both stages
        apply it without either depending on the other."""
        from bga.structural.models import deferral_risk_for

        assert deferral_risk_for("BUILD", 500_000) == "medium"
        assert deferral_risk_for("BUILD", 2_000_000) == "high"
        assert deferral_risk_for("TEST", 9_000_000) == "low"
        assert deferral_risk_for("BUILD", None) is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
