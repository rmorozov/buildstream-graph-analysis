"""UX-682 (join half): expected rebuild cost and the two co-change
findings, joining Plane 1's blast radius with Plane 3's kept-log
change-frequency payload.

`expected rebuild cost = frequency x weighted blast` is the quantity
that decides split-or-consolidate where blast radius alone misleads: a
narrow but frequently-rebuilt element can cost more than a wide, rarely
rebuilt one. These tests pin the ranking, the two co-change findings,
and the payload's absence rule.
"""
from bga.correlate import (
    correlate,
    expected_rebuild_cost,
    find_granularity_findings,
)
from tests.unit.test_correlate import _analysis, _native
from tests.unit.test_granularity import _Edge


def _change_frequency(elements, co_change=(), builds_lower_bound=30):
    return {
        'builds_lower_bound': builds_lower_bound,
        'window': {'first_us': 0, 'last_us': 1},
        'elements': list(elements),
        'co_change': list(co_change),
        'co_change_window_us': 0,
        'pairs_below_floor': 0,
    }


# --- expected rebuild cost ----------------------------------------------

def test_frequent_narrow_element_outranks_rare_wide_one():
    """lib-a (blast 4, weighted 40s) rebuilds 30 times; codegen (blast
    20, weighted 400s) rebuilds twice. 30 * 40s = 1200s beats 2 * 400s =
    800s despite codegen's five-times-larger blast."""
    analysis = {'elements': {'blast_radius': {
        'lib-a.bst': {'downstream_count': 4, 'weighted_duration_us': 40_000_000},
        'codegen.bst': {'downstream_count': 20, 'weighted_duration_us': 400_000_000},
    }}}
    cache_logs = {'change_frequency': _change_frequency([
        {'element': 'lib-a.bst', 'rebuilds': 30, 'unchanged_key_rebuilds': 0,
         'unchanged_key_share': 0.0},
        {'element': 'codegen.bst', 'rebuilds': 2, 'unchanged_key_rebuilds': 0,
         'unchanged_key_share': 0.0},
    ])}

    rows = expected_rebuild_cost(analysis, cache_logs)

    assert [r['element'] for r in rows] == ['lib-a.bst', 'codegen.bst']
    assert rows[0]['expected_cost_us'] == 1_200_000_000
    assert rows[1]['expected_cost_us'] == 800_000_000


def test_key_absent_without_change_frequency():
    result = correlate(_analysis(), _native(), cache_logs={'sandbox_tax': {'top_payers': []}})

    assert 'expected_rebuild_cost' not in result


def test_key_present_and_a_list_with_change_frequency():
    analysis = _analysis(blast={
        'lib-a.bst': {'downstream_count': 4, 'weighted_duration_us': 40_000_000},
    })
    cache_logs = {'change_frequency': _change_frequency([
        {'element': 'lib-a.bst', 'rebuilds': 30, 'unchanged_key_rebuilds': 0,
         'unchanged_key_share': 0.0},
    ])}

    result = correlate(analysis, _native(), cache_logs=cache_logs)

    assert result['expected_rebuild_cost'] == [{
        'element': 'lib-a.bst', 'rebuilds': 30, 'weighted_blast_us': 40_000_000,
        'expected_cost_us': 1_200_000_000, 'blast_count': 4,
    }]


# --- consolidate-by-co-change --------------------------------------------

def test_consolidate_fires_on_a_full_share_pair_with_a_shared_consumer():
    cache_logs = {'change_frequency': _change_frequency(
        elements=[
            {'element': 'pair-x.bst', 'rebuilds': 12, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'pair-y.bst', 'rebuilds': 13, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
        ],
        co_change=[
            {'a': 'pair-x.bst', 'b': 'pair-y.bst', 'co_rebuilds': 12,
             'share_of_a': 1.0, 'share_of_b': 12 / 13},
        ],
        builds_lower_bound=13,
    )}
    edges = [_Edge('pair-x.bst', 'consumer.bst'), _Edge('pair-y.bst', 'consumer.bst')]

    findings = find_granularity_findings({}, {}, cache_logs, dependencies=edges)

    consolidate = [f for f in findings if f['id'] == 'consolidate-by-co-change']
    assert len(consolidate) == 1
    assert consolidate[0]['elements'] == ['pair-x.bst', 'pair-y.bst']
    assert "pair-x.bst and pair-y.bst rebuilt together in 12 of 12 and 12 of 13" in consolidate[0]['title']
    assert "no element consumes one without the other" in consolidate[0]['title']
    assert "over at least 13 builds" in consolidate[0]['title']


def test_consolidate_does_not_fire_when_a_third_element_consumes_pair_x_alone():
    cache_logs = {'change_frequency': _change_frequency(
        elements=[
            {'element': 'pair-x.bst', 'rebuilds': 12, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'pair-y.bst', 'rebuilds': 13, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
        ],
        co_change=[
            {'a': 'pair-x.bst', 'b': 'pair-y.bst', 'co_rebuilds': 12,
             'share_of_a': 1.0, 'share_of_b': 12 / 13},
        ],
        builds_lower_bound=13,
    )}
    edges = [
        _Edge('pair-x.bst', 'consumer.bst'), _Edge('pair-y.bst', 'consumer.bst'),
        _Edge('pair-x.bst', 'only-x-consumer.bst'),
    ]

    findings = find_granularity_findings({}, {}, cache_logs, dependencies=edges)

    assert [f for f in findings if f['id'] == 'consolidate-by-co-change'] == []


# --- split-by-co-change ----------------------------------------------------

def test_split_fires_for_two_consumer_groups_that_never_co_rebuild():
    cache_logs = {'change_frequency': _change_frequency(
        elements=[
            {'element': 'a1.bst', 'rebuilds': 5, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'a2.bst', 'rebuilds': 5, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'b1.bst', 'rebuilds': 4, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
        ],
        co_change=[
            {'a': 'a1.bst', 'b': 'a2.bst', 'co_rebuilds': 5,
             'share_of_a': 1.0, 'share_of_b': 1.0},
        ],
        builds_lower_bound=5,
    )}
    edges = [
        _Edge('base.bst', 'a1.bst'), _Edge('base.bst', 'a2.bst'),
        _Edge('base.bst', 'b1.bst'),
    ]

    findings = find_granularity_findings({}, {}, cache_logs, dependencies=edges)

    split = [f for f in findings if f['id'] == 'split-by-co-change']
    assert len(split) == 1
    assert split[0]['elements'] == ['base.bst']
    assert split[0]['groups'] == [['a1.bst', 'a2.bst'], ['b1.bst']]
    assert "a1.bst" in split[0]['title'] and "b1.bst" in split[0]['title']
    assert "over at least 5 builds" in split[0]['title']


def test_split_does_not_fire_when_one_row_joins_the_groups():
    cache_logs = {'change_frequency': _change_frequency(
        elements=[
            {'element': 'a1.bst', 'rebuilds': 5, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'a2.bst', 'rebuilds': 5, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
            {'element': 'b1.bst', 'rebuilds': 4, 'unchanged_key_rebuilds': 0,
             'unchanged_key_share': 0.0},
        ],
        co_change=[
            {'a': 'a1.bst', 'b': 'a2.bst', 'co_rebuilds': 5,
             'share_of_a': 1.0, 'share_of_b': 1.0},
            {'a': 'a2.bst', 'b': 'b1.bst', 'co_rebuilds': 4,
             'share_of_a': 0.8, 'share_of_b': 1.0},
        ],
        builds_lower_bound=5,
    )}
    edges = [
        _Edge('base.bst', 'a1.bst'), _Edge('base.bst', 'a2.bst'),
        _Edge('base.bst', 'b1.bst'),
    ]

    findings = find_granularity_findings({}, {}, cache_logs, dependencies=edges)

    assert [f for f in findings if f['id'] == 'split-by-co-change'] == []
