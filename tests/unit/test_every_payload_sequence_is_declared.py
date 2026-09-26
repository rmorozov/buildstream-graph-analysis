"""UX-1031: every list and data-keyed map in the payload is declared.

The styleguide audit (`docs/backlog/scenarios/UX-1031-...md`) walked two
`analyze/v6` payloads (`macro_micro`, 11 elements, both planes; a
4,002-element synthetic run) and found 91 containers, 41 undeclared and
19 growing with the run of which 4 had no declaration at all.
`bga:grows` (beside `bga:keyed_by` in the hint vocabulary) closes that:
every container names what it grows with, or `False` plus `maxItems`
for one that does not.

This file walks real payloads against the schema (`_ANALYZE_HINTS` via
`schemas.schema("analyze/v6")`), the same resolution grammar
`_descend`/`quantity_for_path` use, and reds on a container the schema
does not declare, or a fixed one whose payload instance exceeds its own
`maxItems` - which is what "growing with no bound" means for a
container the schema claims is fixed. The ~21 real growers the
styleguide audit found with no bounding control at all (drawn by
bespoke code the row cap and fold machinery never see) are `UX-1037`'s
own finding, not a defect in this schema's declarations; they are
carried below as a named, shrink-only list, checked against the schema
directly rather than re-derived from a payload walk.
"""
import json
import pathlib
import subprocess
import sys

import pytest

from bga import schemas

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO_MICRO = REPO / "tests/fixtures/macro_micro/run"

#: The heuristic the styleguide audit's own walker used to tell a
#: *data-keyed* map (values you'd never enumerate in `properties`) from
#: a small fixed-property object: many keys, or keys shaped like an
#: element uid, a task uid, or a path.
def _looks_data_keyed(mapping: dict) -> bool:
    if len(mapping) > 20:
        return True
    return any('/' in k or '.bst' in k or '|' in k or (k[:1].isdigit())
               for k in mapping if isinstance(k, str))


#: `UX-1037`: the growing containers the audit found with no bounding
#: control - drawn by bespoke code the row cap and fold machinery never
#: see. Shrink-only: a path leaves this list only once a real bound
#: (a page control or a `maxItems`) is added for it, never silently.
KNOWN_UNBOUNDED_GROWERS = frozenset({
    "capacity_recommendation.pinned_elements",
    "plane2_coverage.static_census.elements_at_risk",
    "plane2_coverage.static_census.static_executables",
    "findings[].evidence.steps[].entering",
    "optimization_horizon[].entering",
    "cache.target_closure.targets",
    "bottleneck.longest_serial_chain",
    "bottleneck.serial_chains[].members",
    "parallelism.levels[].elements",
    "serialization_point_risks[].pinned_elements",
    "deferrability.recommended_deferrals",
    "confidence.critical_path_cached",
    "timestamp_agreement.shorter_than_bst",
    "element_join[].worst_redundancy.elements",
    "element_join_coverage.plane1_only_with_impact",
    "element_join_coverage.undeclared_plane2_elements",
    "resource_blast.rows[].direct_elements",
    "resource_blast.rows[].blast_elements",
    "resource_blast.rows[].staged_at",
    "duration_resolution.elements",
    "duration_resolution.tasks",
    "restructuring[].elements",
    # Found walking the payload for this item, not by the audit script -
    # the same `element_join[]{}.elements` false positive (a >20-key
    # join row read as a data-keyed map) had swallowed these four
    # per-row scalar arrays into one phantom path instead of four real
    # ones.
    "element_join[].native_findings",
    "element_join[].unused_dependencies",
    "element_join[].recommendations",
    "element_join[].aggregating_dependencies",
})

#: Recorded when this item closed - `KNOWN_UNBOUNDED_GROWERS` may only
#: shrink from here, never grow, without a person deciding so.
_UNBOUNDED_GROWERS_AT_CLOSE = 26


def _analyze(run) -> dict:
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-4000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def small_plane1():
    return _analyze(GOLDEN)


@pytest.fixture(scope="module")
def small_two_plane():
    return _analyze(MACRO_MICRO)


@pytest.fixture(scope="module")
def large_plane1(tmp_path_factory):
    into = tmp_path_factory.mktemp("xl")
    run = into / "xl"
    subprocess.run(
        [sys.executable, "-m", "bga.cli", "gen-synthetic", str(run),
         "--seed", "1", "--layers", "20", "--width", "200"],
        check=True, capture_output=True, cwd=REPO)
    return _analyze(run)


class _Walker:
    """Walks a payload alongside the schema it should validate against.

    `undeclared` - a list or data-keyed map the schema has no `items` /
    `additionalProperties` for.
    `over_cap` - a container declared `bga:grows=False, maxItems=N`
    whose payload instance holds more than `N` - a fixed container that
    is not, in fact, fixed.
    """

    def __init__(self):
        self.undeclared = []
        self.over_cap = []

    def walk(self, value, node, path):
        node = node if isinstance(node, dict) else {}
        if isinstance(value, list):
            self._check_container(node, path, len(value))
            items = node.get("items")
            if not isinstance(items, dict):
                # `_descend`'s own fallback: a table that declares its
                # columns instead of `items` resolves each row against
                # the same node the columns are on (`bga/schemas.py`).
                if node.get(schemas.COLUMNS):
                    items = node
                else:
                    self.undeclared.append(path + "[]")
                    return
            for entry in value:
                self.walk(entry, items, path + "[]")
        elif isinstance(value, dict):
            props = node.get("properties")
            addl = node.get("additionalProperties")
            data_keyed = isinstance(addl, dict) and (
                _looks_data_keyed(value) or not isinstance(props, dict))
            if data_keyed:
                self._check_container(node, path, len(value))
                for sub in value.values():
                    self.walk(sub, addl, path + "{}")
                return
            for key, sub in value.items():
                child = None
                if isinstance(props, dict):
                    child = props.get(key)
                if child is None and isinstance(addl, dict):
                    child = addl
                if child is None:
                    # A row declared by `bga:columns` alone (`UX-655`)
                    # cannot also carry `items` - its own sub-container
                    # columns declare `bga:grows` on the column spec
                    # itself instead of a row `items` the table may not
                    # have (`parallelism.levels[].elements`).
                    for spec in node.get(schemas.COLUMNS) or ():
                        if isinstance(spec, dict) and spec.get("key") == key \
                                and schemas.GROWS in spec:
                            break
                    else:
                        # Only a *container* (a list, or a data-keyed
                        # map) is this guard's concern - `bga:grows`
                        # and the rest of the unit census (`UX-343`)
                        # own a bare scalar's declaration.
                        if isinstance(sub, list) or (
                                isinstance(sub, dict)
                                and _looks_data_keyed(sub)):
                            self.undeclared.append(f"{path}.{key}" if path
                                                   else key)
                    continue
                self.walk(sub, child, f"{path}.{key}" if path else key)

    def _check_container(self, node, path, size):
        if schemas.GROWS not in node:
            self.undeclared.append(path)
            return
        grows = node[schemas.GROWS]
        if grows is False:
            cap = node.get("maxItems")
            if isinstance(cap, int) and size > cap:
                self.over_cap.append((path, size, cap))


def _walk_payload(payload: dict) -> _Walker:
    root = schemas.schema(schemas.ANALYZE)
    walker = _Walker()
    for key, value in payload.items():
        if key == schemas.VERSION_KEY:
            continue
        child = (root.get("properties") or {}).get(key)
        if child is None:
            walker.undeclared.append(key)
            continue
        walker.walk(value, child, key)
    return walker


@pytest.mark.parametrize("fixture_name",
                         ["small_plane1", "small_two_plane", "large_plane1"])
class TestEveryContainerIsDeclared:
    def test_no_undeclared_container(self, fixture_name, request):
        payload = request.getfixturevalue(fixture_name)
        walker = _walk_payload(payload)
        assert walker.undeclared == [], (
            f"{fixture_name}: undeclared container(s): "
            f"{sorted(walker.undeclared)}")

    def test_no_fixed_container_exceeds_its_cap(self, fixture_name, request):
        payload = request.getfixturevalue(fixture_name)
        walker = _walk_payload(payload)
        assert walker.over_cap == [], (
            f"{fixture_name}: container(s) over their declared maxItems: "
            f"{walker.over_cap}")


class TestTheUnboundedGrowersListIsShrinkOnly:
    def test_the_list_has_not_grown(self):
        assert len(KNOWN_UNBOUNDED_GROWERS) <= _UNBOUNDED_GROWERS_AT_CLOSE, (
            "KNOWN_UNBOUNDED_GROWERS grew past its recorded size - a new "
            "unbound grower needs a person's decision (UX-1037), not a "
            "silent addition")

    def test_every_named_path_is_still_unbound(self):
        """A path leaves the list once it is bounded - it does not sit
        here claiming a gap that has already been closed."""
        root = schemas.schema(schemas.ANALYZE)

        def resolve(path):
            node = root
            for segment in schemas._path_segments(path):
                if node is None:
                    return None
                node = schemas._descend(node, segment)
            return node

        stale = []
        for path in sorted(KNOWN_UNBOUNDED_GROWERS):
            node = resolve(path)
            if node is None:
                stale.append((path, "does not resolve against the schema"))
                continue
            if node.get("maxItems") is not None:
                stale.append((path, "now carries maxItems - remove it"))
        assert stale == [], stale
