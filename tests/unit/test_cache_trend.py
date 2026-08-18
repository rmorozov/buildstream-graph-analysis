"""UX-103: is the cache getting worse?

`UX-92` gave one run a cache report card. These cover the series: the
band the newest run is judged against, the metrics that can leave it and
in which direction, and the two ways a series can carry no verdict at
all.

The noise model itself is `bga.compare`'s and is tested there. What is
tested here is that this uses it, including the widening rule - a band
narrower than quantization noise fires on everything, and a set of
near-identical CI runs produces exactly that.
"""
from bga.cache_trend import _band_findings, build_trend, format_trend_text


def _row(name, **overrides):
    row = {
        'run': name, 'run_mode': 'incremental', 'total_duration_us': 1_000_000,
        'hit_ratio': 0.72, 'built_elements': 25, 'cached_elements': 65,
        'transfer_us': 130_000_000, 'transfer_per_artifact_us': 2_000_000,
        'rebuild_us': 4_740_000_000, 'churn': None,
    }
    row.update(overrides)
    return row


def _series(*newest_overrides):
    """Three stable trailing runs plus one newest, whose fields differ."""
    window = [
        _row('run1', transfer_us=123_500_000, transfer_per_artifact_us=1_900_000),
        _row('run2', transfer_us=130_000_000, transfer_per_artifact_us=2_000_000),
        _row('run3', transfer_us=136_500_000, transfer_per_artifact_us=2_100_000),
    ]
    return window + [_row('newest', **(newest_overrides[0] if newest_overrides else {}))]


def test_a_degrading_remote_fires_the_transfer_finding():
    """The task's own example: pull time per artifact several times the
    trailing median, named as a cache-infrastructure problem rather than
    as a project one."""
    findings = _band_findings(_series({
        'transfer_us': 416_000_000, 'transfer_per_artifact_us': 6_400_000,
    }))
    metrics = {f['metric'] for f in findings}
    assert metrics == {'transfer_us', 'transfer_per_artifact_us'}
    per_artifact = next(f for f in findings if f['metric'] == 'transfer_per_artifact_us')
    assert '3.2x the trailing median' in per_artifact['title']
    assert 'the cache remote is degrading' in per_artifact['title']
    assert per_artifact['severity'] == 'high'


def test_a_faster_remote_is_not_a_regression():
    """Direction is per metric and it is load-bearing. Transfer time
    dropping out of the band is good news, and reporting it as a
    degradation would teach a reader to ignore the finding."""
    assert _band_findings(_series({
        'transfer_us': 10_000_000, 'transfer_per_artifact_us': 150_000,
    })) == []


def test_a_falling_hit_ratio_is_a_regression_and_a_rising_one_is_not():
    """The opposite direction, for the metric where it is opposite."""
    window = [_row(f'run{i}', hit_ratio=r) for i, r in enumerate([0.72, 0.71, 0.73])]
    falling = _band_findings(window + [_row('newest', hit_ratio=0.20)])
    assert [f['metric'] for f in falling] == ['hit_ratio']
    assert 'serving less of this build' in falling[0]['title']
    assert _band_findings(window + [_row('newest', hit_ratio=0.99)]) == []


def test_a_near_zero_band_is_widened_rather_than_believed():
    """Three CI runs of one unchanged commit differ by fractions of a
    percent, and their MAD-derived band can be tighter than quantization
    noise - at which point every reading is outside it. Measured while
    building this: rebuild seconds differing by 0.03% produced a 2.2s
    band on a 4740s median, and a 6% rise read as a regression.
    """
    window = [_row(f'run{i}', rebuild_us=base) for i, base in enumerate(
        [4_740_000_000, 4_740_500_000, 4_741_000_000]
    )]
    # Inside the widened (1%) band, far outside the measured one.
    assert _band_findings(window + [_row('newest', rebuild_us=4_760_000_000)]) == []
    # And a real move still fires, marked as judged against the widened band.
    findings = _band_findings(window + [_row('newest', rebuild_us=6_000_000_000)])
    assert [f['metric'] for f in findings] == ['rebuild_us']
    assert findings[0]['evidence']['widened_to_fixed_pct'] is True


def test_three_runs_carry_no_verdict_because_the_window_is_two():
    """A band needs `MIN_BASELINE_RUNS` *trailing* runs plus the one
    being judged. Three real captures is a trailing window of two, and
    saying so is the honest answer - the alternative is a verdict from a
    noise model that could not be built."""
    trend = build_trend([_row('a'), _row('b'), _row('c')])
    assert trend['findings'] == []
    assert trend['insufficient_window']['supplied'] == 3
    assert trend['insufficient_window']['required'] == 4
    assert 'No verdict' in format_trend_text(trend)


def test_two_runs_is_not_a_trend():
    trend = build_trend([_row('a'), _row('b')])
    assert trend['insufficient_window'] is not None


def test_a_full_window_with_nothing_wrong_says_so():
    """Silence and an all-clear must not look the same."""
    trend = build_trend(_series())
    assert trend['findings'] == []
    assert trend['insufficient_window'] is None
    assert 'sits inside the band' in format_trend_text(trend)


def test_a_metric_absent_from_the_window_is_not_trended():
    """Every published freedesktop-sdk capture is taken with remotes
    ignored, so it has no transfer at all. A trend over those must not
    invent a transfer band from Nones."""
    window = [_row(f'run{i}', transfer_us=None, transfer_per_artifact_us=None)
              for i in range(3)]
    findings = _band_findings(window + [_row('newest', transfer_us=999_000_000)])
    assert [f['metric'] for f in findings] == []


def test_the_table_renders_the_churn_labels_ux93_settled():
    """A rebuild both runs made is a retention question, not waste, and
    the trend must not relabel it on its way into a column."""
    rows = [
        _row('a'),
        _row('b', churn={'applicable': True, 'churned_count': 0,
                         'rebuilt_in_both_count': 25}),
        _row('c', churn={'applicable': False, 'reason': 'candidate_run_is_full'}),
    ]
    text = format_trend_text(build_trend(rows))
    assert '0+25r' in text
    assert 'n/a' in text
