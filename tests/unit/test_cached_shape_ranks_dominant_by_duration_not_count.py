"""UX-684: the cached build's verdict - most changes rebuild the
cheapest subgraph, or they don't, and which element the expected cost
is really in.

Example 06 carries no captured kept-log tree of its own, so this reuses
its real weighted blast (`tests/fixtures/macro_micro`) against a
synthetic Plane 3 history built the way `UX-682`'s own tests build one.
"""
from bga.correlate import cached_shape
from tests.unit.test_correlate import _analysis

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
# graph's, which the second mutation below turns on. `lib-d.bst`
# rebuilds most often but `lib-a.bst` costs three times as much per
# rebuild - duration-weighted cost and change count disagree about
# which element is dominant.
_ELEMENTS = [
    {'element': 'lib-f.bst', 'rebuilds': 30, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-d.bst', 'rebuilds': 40, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-b.bst', 'rebuilds': 15, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'lib-a.bst', 'rebuilds': 30, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
    {'element': 'toolchain.bst', 'rebuilds': 20, 'unchanged_key_rebuilds': 0, 'unchanged_key_share': 0.0},
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
