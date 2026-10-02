"""UX-1253: the run's verdicts are checked against each other, and a
contradiction is published as a violation naming both sides."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bga.consistency import PAIRS, VIOLATION_TYPE, disagreements

REPO = Path(__file__).resolve().parents[2]

#: Every verdict agreeing: the shape of a capacity-bound run read consistently.
AGREEING = {
    'diagnosis': 'chain_bound',
    'lb_us': 100,
    't_infinity_us': 100,
    'lb_share_of_wall': 0.99,
    'lb_cpu_binds': False,
    'binding_constraint': 'graph',
    'potential_oversubscription': False,
    'capacity_checks_ran': True,
    'capacity_oversubscribed': False,
    'capacity_undersubscribed': False,
    'builders_change': 0,
}

#: A capacity verdict that agrees with a capacity-bound diagnosis.
OVER = {'capacity_oversubscribed': True}

#: One contradiction per pair, the 2,402-element page's readings.
DISAGREEING = {
    'diagnosis_vs_floors': {'diagnosis': 'scheduler_bound', 'lb_us': 2_817_875_000, 't_infinity_us': 277_500_000},
    'oversubscription_vs_capacity_verdict': {'potential_oversubscription': True},
    'binding_constraint_vs_cpu_floor': {'binding_constraint': 'CPU'},
    'capacity_bound_vs_recommendation': {'diagnosis': 'capacity_bound', **OVER},
    'capacity_bound_vs_capacity_verdict': {'diagnosis': 'capacity_bound', 'builders_change': 2},
}

#: The same sides read consistently: each pair's silent case.
SILENT = {
    'capacity_bound_beside_lb_at_the_wall': {
        'diagnosis': 'capacity_bound',
        'lb_us': 2_817_875_000,
        't_infinity_us': 277_500_000,
        'builders_change': 2,
        **OVER,
    },
    'capacity_bound_beside_a_host_cap_keep': {
        'diagnosis': 'capacity_bound',
        'binding_constraint': 'host_cores',
        **OVER,
    },
    # UX-1268: undersubscribed is UX-1259's host-core call, not this pair's.
    'capacity_bound_beside_an_undersubscribed_verdict': {
        'diagnosis': 'capacity_bound',
        'builders_change': 2,
        'capacity_undersubscribed': True,
    },
    'capacity_bound_beside_unran_checks': {
        'diagnosis': 'capacity_bound',
        'builders_change': 2,
        'capacity_checks_ran': False,
    },
}


@pytest.mark.parametrize('case', sorted(SILENT))
def test_agreeing_sides_report_nothing(case):
    assert disagreements({**AGREEING, **SILENT[case]}) == []


def test_every_pair_has_a_disagreeing_case():
    assert {row.pair for row in PAIRS} == set(DISAGREEING)


def test_agreeing_verdicts_report_nothing():
    assert disagreements(AGREEING) == []


@pytest.mark.parametrize('pair', sorted(DISAGREEING))
def test_one_disagreement_is_one_violation_naming_both_sides(pair):
    found = disagreements({**AGREEING, **DISAGREEING[pair]})
    assert [v['pair'] for v in found] == [pair], found
    (violation,) = found
    assert violation['type'] == VIOLATION_TYPE
    row = next(r for r in PAIRS if r.pair == pair)
    assert violation['left']['verdict'] == row.left and violation['right']['verdict'] == row.right
    assert row.left in violation['detail'] and row.right in violation['detail']


@pytest.mark.parametrize(
    'args',
    [
        ['tests/fixtures/golden/mixed_task_kinds'],
        ['tests/fixtures/macro_micro/run', '--plane2', 'tests/fixtures/macro_micro/plane2.json'],
    ],
    ids=['golden', 'macro_micro'],
)
def test_the_committed_fixtures_report_none(args):
    out = subprocess.run(
        [sys.executable, '-m', 'bga.cli', 'analyze', *args, '--format', 'json'],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    published = json.loads(out.stdout)['violations']
    assert [v for v in published if v.get('type') == VIOLATION_TYPE] == []


def test_the_json_and_text_reports_publish_a_disagreement():
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.report.json import build_document
    from bga.report.text import format_text

    golden = REPO / 'tests/fixtures/golden/mixed_task_kinds'
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(golden)
    result = analyzer.analyze(golden)
    before = list(result.violations)
    result.utilisation = {**result.utilisation, 'potential_oversubscription': True}
    result.capacity_verdict = {**result.capacity_verdict, 'checks_ran': True, 'oversubscribed': False}
    published = [v['pair'] for v in build_document(result)['violations'] if v.get('type') == VIOLATION_TYPE]
    assert published == ['oversubscription_vs_capacity_verdict']
    assert result.violations == before
    assert 'verdicts disagree: utilisation.potential_oversubscription reads oversubscribed' in format_text(result)


#: `UX-1268`: the 2,402-element two-plane page, capacity-bound with a matched capacity verdict.
PAGE_SHAPE = ('--layers', '40', '--width', '60', '--workload', 'binaries')
_VIOLATIONS_TEXT = "document.getElementById('violations')?.textContent ?? ''"


def test_a_capacity_bound_page_names_the_matched_verdict(tmp_path):
    sys.path.insert(0, str(REPO))
    import tools.bga_view as view
    from tests import pages
    from tests.browser import NO_BROWSER, Browser, find_chrome

    chrome = find_chrome()
    if chrome is None:
        pytest.skip(NO_BROWSER)
    run = pages.two_plane_run(tmp_path, shape=PAGE_SHAPE, runs=2)
    page = tmp_path / 'report.html'
    view.export(str(run), str(page))
    with Browser(chrome) as opened:
        text = opened.measure(page.as_uri(), _VIOLATIONS_TEXT)
    assert 'capacity_bound_vs_capacity_verdict' in text, text
    assert 'headline.diagnosis reads capacity_bound; capacity_verdict reads capacity matched demand' in text, text
