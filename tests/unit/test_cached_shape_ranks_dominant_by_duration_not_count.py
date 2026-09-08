"""UX-684: the cached build's verdict - most changes rebuild the
cheapest subgraph, or they don't, which element the expected cost is
really in, and whether that element's own advice is to split a tall
chain or isolate a heavy one.

Example 06 carries no captured kept-log tree of its own, so this reuses
its real weighted blast (`tests/fixtures/macro_micro`) against a
synthetic Plane 3 history built the way `UX-682`'s own tests build one
- reproduced in the task file's Outcome with the exact log tree and
`bga cache-logs`/`bga correlate` commands that regenerate it.
"""
from bga.correlate import cached_shape
from tests.unit.test_correlate import _analysis
from tests.unit.test_granularity import _Edge

# Example 06's own weighted blast: `PYTHONPATH=. python3 -m bga.cli
# analyze tests/fixtures/macro_micro/run --format json`.
_BLAST = {
    'all.bst': {'downstream_count': 0, 'weighted_duration_us': 0, 'element_kind': 'stack'},
    'app.bst': {'downstream_count': 1, 'weighted_duration_us': 0, 'element_kind': 'cmake'},
    'codegen.bst': {'downstream_count': 8, 'weighted_duration_us': 24_150_000, 'element_kind': 'cmake'},
    'core.bst': {'downstream_count': 8, 'weighted_duration_us': 24_150_000, 'element_kind': 'cmake'},
    'lib-a.bst': {'downstream_count': 7, 'weighted_duration_us': 21_150_000, 'element_kind': 'cmake'},
    'lib-b.bst': {'downstream_count': 6, 'weighted_duration_us': 17_150_000, 'element_kind': 'cmake'},
    'lib-c.bst': {'downstream_count': 5, 'weighted_duration_us': 14_150_000, 'element_kind': 'cmake'},
    'lib-d.bst': {'downstream_count': 4, 'weighted_duration_us': 10_150_000, 'element_kind': 'cmake'},
    'lib-e.bst': {'downstream_count': 3, 'weighted_duration_us': 7_150_000, 'element_kind': 'cmake'},
    'lib-f.bst': {'downstream_count': 2, 'weighted_duration_us': 3_150_000, 'element_kind': 'cmake'},
    'toolchain.bst': {'downstream_count': 10, 'weighted_duration_us': 50_200_000,
                       'element_kind': 'import', 'is_foundation': True},
}

# Five elements recorded, so their own median (`lib-b.bst`, rank 3 of
# 5) differs from the graph's own median (`lib-c.bst`, rank 6 of 11) -
# `lib-b.bst` is cheap under the history's own p50 but not under the
# graph's, which the p50-population mutation below turns on. `lib-d.bst`
# rebuilds most often but `lib-a.bst` costs six times as much per
# rebuild - duration-weighted cost and change count disagree about
# which element is dominant. Counts match the log tree the task file's
# Outcome regenerates with `bga cache-logs`.
_ELEMENTS = [
    {'element': 'lib-f.bst', 'rebuilds': 3, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-d.bst', 'rebuilds': 5, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-b.bst', 'rebuilds': 2, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-a.bst', 'rebuilds': 3, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'toolchain.bst', 'rebuilds': 2, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
]

# Real macro_micro is one straight chain (toolchain/core/codegen through
# lib-a..f to app to all), so height and weight agree for every element
# in it and the advice branches never diverge (the task file's Outcome
# shows this). `cached_shape` is given this private, synthetic
# dependency graph instead, sized so height and weight disagree:
# `lib-a.bst`'s chain is the longest, tying its already-heaviest weight
# (the tie case, `UX-684`'s follow-up); `lib-d.bst` and `lib-f.bst` are
# taller than their weight rank predicts (split); `lib-b.bst` gets no
# chain at all, so its real weight lead over `lib-d.bst`/`lib-f.bst`
# is not matched by height (isolate).
_HEIGHT_EDGES = [
    ('lib-a.bst', 'h-a1.bst'), ('h-a1.bst', 'h-a2.bst'), ('h-a2.bst', 'h-a3.bst'),
    ('h-a3.bst', 'h-a4.bst'), ('h-a4.bst', 'h-a5.bst'), ('h-a5.bst', 'h-a6.bst'),
    ('lib-d.bst', 'h-d1.bst'), ('h-d1.bst', 'h-d2.bst'), ('h-d2.bst', 'h-d3.bst'),
    ('h-d3.bst', 'h-d4.bst'), ('h-d4.bst', 'h-d5.bst'),
    ('lib-f.bst', 'h-f1.bst'), ('h-f1.bst', 'h-f2.bst'), ('h-f2.bst', 'h-f3.bst'),
]


def _fixture():
    analysis = _analysis(blast=_BLAST)
    cache_logs = {'change_frequency': {
        'builds_lower_bound': max(e['rebuilds'] for e in _ELEMENTS),
        'window': {'first_us': 0, 'last_us': 1},
        'elements': list(_ELEMENTS),
        'co_change': [],
        'co_change_window_us': 0,
        'pairs_below_floor': 0,
    }}
    return analysis, cache_logs


def _independent_height(element, edges):
    """The longest downstream chain below `element`, in elements -
    walked breadth-first over plain `(predecessor, successor)` tuples
    rather than calling `bga.correlate`'s own `_height_below`, so this
    guard cannot pass by sharing a bug with the code it checks.
    """
    successors: dict = {}
    for pred, succ in edges:
        successors.setdefault(pred, []).append(succ)
    longest = 0
    frontier = [(element, 0)]
    seen = {element}
    while frontier:
        node, depth = frontier.pop()
        longest = max(longest, depth)
        for child in successors.get(node, ()):
            if child not in seen:
                seen.add(child)
                frontier.append((child, depth + 1))
    return longest


def test_cheap_share_matches_an_independent_recount():
    analysis, cache_logs = _fixture()

    shape = cached_shape(analysis, cache_logs)

    # p50 over all 11 graph elements' own weighted blast (nearest-rank,
    # `bga/store_aggregate.py:72`) - not over the five with recorded
    # changes, whose own median (`lib-b.bst`, 17,150,000) differs and
    # would classify it cheap instead of expensive.
    p50 = sorted(e['weighted_duration_us'] for e in _BLAST.values())[5]
    assert p50 == 14_150_000
    history_only_p50 = sorted(
        _BLAST[e['element']]['weighted_duration_us'] for e in _ELEMENTS
    )[2]
    assert history_only_p50 == 17_150_000 != p50, (
        "the fixture no longer discriminates the p50 population mutation")
    total_changes = sum(e['rebuilds'] for e in _ELEMENTS)
    cheap_changes = sum(e['rebuilds'] for e in _ELEMENTS
                        if _BLAST[e['element']]['weighted_duration_us'] <= p50)
    assert (shape['total_changes'], shape['cheap_changes']) == (total_changes, cheap_changes)
    assert shape['cheap_share'] == cheap_changes / total_changes
    assert shape['verdict'] == 'rebuilds_the_cheapest_subgraph'


def test_dominant_is_ranked_by_duration_weighted_cost_not_change_count():
    analysis, cache_logs = _fixture()

    shape = cached_shape(analysis, cache_logs)

    # `toolchain.bst` is the true expensive-blast leader by either
    # ranking but is a declared foundation (`UX-683`) and never leads.
    non_foundation = [e for e in _ELEMENTS if e['element'] != 'toolchain.bst']
    by_duration = max(non_foundation, key=lambda e:
                       e['rebuilds'] * _BLAST[e['element']]['weighted_duration_us'])
    by_count = max(non_foundation, key=lambda e: e['rebuilds'])
    assert by_duration['element'] != by_count['element'], (
        "the fixture no longer discriminates - duration and count agree")
    assert shape['dominant'][0]['element'] == by_duration['element']


def test_the_advice_matches_an_independent_height_and_weight_rank_comparison():
    analysis, cache_logs = _fixture()
    edges = [_Edge(pred, succ) for pred, succ in _HEIGHT_EDGES]

    shape = cached_shape(analysis, cache_logs, dependencies=edges)

    dominant_elements = [e['element'] for e in _ELEMENTS if e['element'] != 'toolchain.bst']
    heights = {e: _independent_height(e, _HEIGHT_EDGES) for e in dominant_elements}
    by_height = sorted(dominant_elements, key=lambda e: -heights[e])
    by_weight = sorted(dominant_elements,
                       key=lambda e: -_BLAST[e]['weighted_duration_us'])
    height_rank = {e: i for i, e in enumerate(by_height, start=1)}
    weight_rank = {e: i for i, e in enumerate(by_weight, start=1)}

    # The tie case (`UX-684`'s follow-up judgement): `lib-a.bst` leads
    # both rankings and reads as `isolate`, never a null advice.
    assert height_rank['lib-a.bst'] == weight_rank['lib-a.bst'] == 1
    expected = {
        e: ("split the tall chain" if height_rank[e] < weight_rank[e]
            else "isolate the heavy element")
        for e in dominant_elements
    }
    assert set(expected.values()) == {"split the tall chain", "isolate the heavy element"}, (
        "the fixture no longer exercises both advice branches")

    by_element = {d['element']: d for d in shape['dominant']}
    for element, advice in expected.items():
        assert by_element[element]['advice'] == advice, element
    top = shape['dominant'][0]
    assert top['element'] == 'lib-a.bst'
    assert ", also the tallest" in shape['sentence']
