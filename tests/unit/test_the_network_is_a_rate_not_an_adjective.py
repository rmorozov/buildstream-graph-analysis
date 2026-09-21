"""UX-897: "40% of this build was transfer" names no cause.

A slow link, a slow remote and an object count that would be slow on any
link produce the same share of wall clock and have three different
fixes, one of which is hardware somebody would be asked to buy. The
share could not tell them apart because no byte count was captured
anywhere - `cache_trend`'s own docstring opens on "a remote that slows
from 40MB/s to 5MB/s", a throughput the tool could not compute.

**Where the bytes are not.** BuildStream 2.8.0 reports none.
`_artifactcache.py:135,201` log `Pushed artifact <key> -> <remote>` and
`Pulled artifact <key> <- <remote>`, with no size, per element or per
session; `_sourcecache.py` is the same; and `buildbox-casd`'s exact
`GetLocalDiskUsage` reaches only the TTY status bar. So the row's own
premise - "the same extraction pass that reads the pipeline summary can
read them" - is false, and the counters come from the host instead.

**What that costs in honesty.** They are the *host's* bytes, not
BuildStream's. The clauses below hold that caveat in the schema, in the
finding's own sentence, and in the `source` the block carries, because a
number whose scope is wrong by an unknown factor is worse unlabelled
than absent.
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

from bga.cache_effectiveness import _transfer_window_us, compute_cache_accounting
from bga.findings import compute_findings, findings_by_id
from bga.ingest.models import AnalysisResult
from tools.bst_native_build_tracer import network_bytes, read_net_sample, sum_net_dev

MIB = 1024 * 1024


class _Ctx:
    def __init__(self, queue_summary=None):
        self.queue_summary = queue_summary
        self.cache_capacity = None


class _Resource:
    def __init__(self, value):
        self.value = value


class _Task:
    def __init__(self, resource, start_us, finish_us):
        self.primary_resource = _Resource(resource)
        self.start_us = start_us
        self.finish_us = finish_us
        self.task_key = None


SUMMARY = {'build': {'processed': 1, 'skipped': 3, 'failed': 0}}

#: Two pulls overlapping by a second: summed they are 20s, and the
#: window they occupy is 15s. The whole point of the second number.
OVERLAPPING = [
    _Task('DOWNLOAD', 0, 10_000_000),
    _Task('DOWNLOAD', 5_000_000, 15_000_000),
]


def _accounting(tasks=OVERLAPPING, bytes_read=None, duration_us=60_000_000):
    return compute_cache_accounting(
        _Ctx(SUMMARY), graph=None, tasks=tasks,
        total_duration_us=duration_us, network_bytes=bytes_read)


def _finding(accounting):
    result = AnalysisResult()
    result.signals['cache'] = accounting
    return findings_by_id(compute_findings(result)).get('cache-transfer-cost')


class TestTheWindowIsAUnionNotASum:
    def test_concurrent_pulls_are_counted_once(self):
        """`transfer_us` sums to 20s because it answers how much pulling
        happened. A throughput divided by that would report half the
        rate the link achieved."""
        accounting = _accounting()
        assert sum(accounting['transfer_us'].values()) == 20_000_000
        assert accounting['transfer_window_us'] == 15_000_000

    def test_disjoint_spans_add(self):
        spans = [_Task('DOWNLOAD', 0, 2_000_000),
                 _Task('UPLOAD', 10_000_000, 13_000_000)]
        assert _transfer_window_us(spans) == 5_000_000

    def test_a_run_with_no_transfer_has_no_window(self):
        assert _transfer_window_us([]) is None
        assert _transfer_window_us([_Task('PROCESS', 0, 9)]) is None


class TestTheRateIsPublishedWhenBytesAre:
    def test_bytes_over_the_window(self):
        """150 MiB over 15s is 10 MiB/s, and the arithmetic is the whole
        claim - no modelling between the counter and the number."""
        accounting = _accounting(bytes_read={'rx_bytes': 100 * MIB,
                                             'tx_bytes': 50 * MIB})
        assert accounting['transfer_bytes'] == {
            'rx': 100 * MIB, 'tx': 50 * MIB, 'total': 150 * MIB,
            'source': 'host_counters'}
        assert accounting['transfer_rate_bytes_per_s'] == pytest.approx(
            10 * MIB, rel=1e-9)

    def test_halving_the_bytes_halves_the_rate_and_moves_no_share(self):
        """The mutation the row names. The two numbers answer different
        questions and must not move together."""
        full = _accounting(bytes_read={'rx_bytes': 100 * MIB, 'tx_bytes': 50 * MIB})
        half = _accounting(bytes_read={'rx_bytes': 50 * MIB, 'tx_bytes': 25 * MIB})
        assert half['transfer_rate_bytes_per_s'] == pytest.approx(
            full['transfer_rate_bytes_per_s'] / 2)
        assert half['transfer_share'] == full['transfer_share']

    def test_the_finding_names_the_rate_and_its_scope(self):
        finding = _finding(_accounting(bytes_read={'rx_bytes': 100 * MIB,
                                                   'tx_bytes': 50 * MIB}))
        assert '10.0M/s' in finding['title']
        assert 'upper bound' in finding['title']
        assert finding['evidence']['transfer_bytes'] == 150 * MIB


class TestNoBytesIsNoRate:
    def test_a_capture_with_no_counters_prints_what_it_printed_before(self):
        """The row's own acceptance test: on a capture with no bytes,
        the transfer line is exactly today's."""
        accounting = _accounting()
        assert 'transfer_bytes' not in accounting
        assert 'transfer_rate_bytes_per_s' not in accounting
        title = _finding(accounting)['title']
        assert title.endswith('rather than making them')

    def test_removing_the_byte_key_removes_the_clause(self):
        """Not a zero and not a `0.0B/s` - the sentence loses its
        second half rather than gaining a false one."""
        with_bytes = _finding(_accounting(bytes_read={'rx_bytes': MIB,
                                                      'tx_bytes': 0}))
        without = _finding(_accounting())
        assert '/s' in with_bytes['title']
        assert '/s' not in without['title']

    def test_a_partial_counter_pair_is_no_reading(self):
        """One direction is not a session's traffic, and half a sum is
        not an upper bound on anything."""
        accounting = _accounting(bytes_read={'rx_bytes': MIB})
        assert 'transfer_bytes' not in accounting

    def test_no_transfer_span_means_no_division(self):
        """The row's second mutation: zero the transfer seconds and
        there is no rate, rather than a division by zero."""
        accounting = _accounting(tasks=[_Task('PROCESS', 0, 5)],
                                 bytes_read={'rx_bytes': MIB, 'tx_bytes': MIB})
        assert 'transfer_window_us' not in accounting
        assert 'transfer_rate_bytes_per_s' not in accounting


class TestTheCommittedCaptureCarriesIt:
    """`UX-460`'s rule: the clause is reached by a capture in the tree,
    not only by a dict built here."""

    def test_the_pull_fixture_prints_a_rate(self):
        out = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze",
             "tests/fixtures/a_build_that_pulls/run"],
            capture_output=True, text=True, check=True).stdout
        line = [ln for ln in out.splitlines() if "artifact transfer" in ln]
        assert line and "/s" in line[0], out
        assert "upper bound" in line[0]

    def test_the_same_capture_without_counters_prints_what_it_did_before(
            self, tmp_path):
        """The row's own acceptance test, on the capture that can
        actually show it: the *same* run with its host-samples series
        removed prints the transfer line exactly as it printed before
        this landed - not a zero rate, not an empty clause."""
        source = pathlib.Path("tests/fixtures/a_build_that_pulls")
        copied = tmp_path / "no-counters"
        shutil.copytree(source, copied)
        (copied / "host-samples.jsonl").unlink()
        out = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(copied / "run")],
            capture_output=True, text=True, check=True).stdout
        line = [ln for ln in out.splitlines() if "artifact transfer" in ln]
        assert line, out
        assert line[0].endswith("rather than making them")


class TestTheTrendGainsTheSeries:
    """`cache_trend`'s own docstring opens on "a remote that slows from
    40MB/s to 5MB/s" and the table had no column for it."""

    def test_the_table_carries_a_rate_column(self):
        from bga.cache_trend import build_trend, format_trend_text

        rows = [
            {'run': 'a/run', 'hit_share': 0.8, 'built_elements': 2,
             'cached_elements': 8, 'transfer_us': 3_000_000,
             'transfer_per_artifact_us': 375_000,
             'transfer_rate_bytes_per_s': 40 * MIB, 'churn': None},
            {'run': 'b/run', 'hit_share': 0.8, 'built_elements': 2,
             'cached_elements': 8, 'transfer_us': 24_000_000,
             'transfer_per_artifact_us': 3_000_000,
             'transfer_rate_bytes_per_s': 5 * MIB, 'churn': None},
        ]
        out = format_trend_text(build_trend(rows))
        assert 'rate' in out
        assert '40.0M/s' in out and '5.0M/s' in out

    def test_a_run_with_no_counters_leaves_the_cell_empty(self):
        """A trend that plotted a zero for a reading nobody took would
        draw a cliff where a capture simply predates the field."""
        from bga.cache_trend import build_trend, format_trend_text

        rows = [{'run': 'a/run', 'hit_share': 0.8, 'built_elements': 2,
                 'cached_elements': 8, 'transfer_us': 3_000_000,
                 'transfer_per_artifact_us': 375_000,
                 'transfer_rate_bytes_per_s': None, 'churn': None}]
        row_line = [ln for ln in format_trend_text(build_trend(rows)).splitlines()
                    if ln.startswith('a/run')]
        assert row_line, 'the run did not render'
        assert '/s' not in row_line[0], row_line[0]


class TestTheCountersComeOffTheHost:
    #: A constructed `/proc/net/dev`, because whether dropping `lo`
    #: changes this host's total depends on what this host is doing -
    #: sampling the live file would pass whatever the exclusion did.
    NET_DEV = [
        "Inter-|   Receive                    |  Transmit\n",
        " face |bytes packets errs drop fifo frame compressed multicast|"
        "bytes packets errs drop fifo colls carrier compressed\n",
        "    lo: 900 5 0 0 0 0 0 0 800 5 0 0 0 0 0 0\n",
        "  eth0: 100 2 0 0 0 0 0 0  70 2 0 0 0 0 0 0\n",
        "  eth1:  30 1 0 0 0 0 0 0  20 1 0 0 0 0 0 0\n",
    ]

    def test_loopback_is_not_the_link(self):
        """A local `buildbox-casd` is on the other end of most loopback
        traffic; counting its 900 bytes here would report ten times the
        130 that actually crossed a wire."""
        assert sum_net_dev(self.NET_DEV) == {
            'net_rx_bytes': 130, 'net_tx_bytes': 90}

    def test_the_live_host_parses(self):
        """The constructed file above is only worth something if the
        real one has the same shape."""
        assert set(read_net_sample()) == {'net_rx_bytes', 'net_tx_bytes'}

    def test_a_series_is_its_last_reading_less_its_first(self):
        read = {'samples': [
            {'t': 1.0, 'net_rx_bytes': 1000, 'net_tx_bytes': 10},
            {'t': 3.0, 'net_rx_bytes': 1500, 'net_tx_bytes': 40},
            {'t': 5.0, 'net_rx_bytes': 4000, 'net_tx_bytes': 110},
        ]}
        assert network_bytes(read) == {
            'rx_bytes': 3000, 'tx_bytes': 100, 'span_s': 4.0}

    def test_one_sample_is_nothing_to_subtract(self):
        """A build too short to be sampled twice moved an unknown
        amount, not zero."""
        assert network_bytes(
            {'samples': [{'t': 1.0, 'net_rx_bytes': 1, 'net_tx_bytes': 2}]}) == {}

    def test_a_series_older_than_the_counters_is_empty(self):
        assert network_bytes({'samples': [{'t': 1.0}, {'t': 3.0}]}) == {}

    def test_a_counter_that_went_backwards_is_not_negative_traffic(self):
        """An interface reset or removed mid-build, which is a gap in
        the reading rather than bytes flowing the other way."""
        read = {'samples': [
            {'t': 1.0, 'net_rx_bytes': 9000, 'net_tx_bytes': 9000},
            {'t': 3.0, 'net_rx_bytes': 10, 'net_tx_bytes': 20},
        ]}
        assert network_bytes(read) == {
            'rx_bytes': 0, 'tx_bytes': 0, 'span_s': 2.0}
