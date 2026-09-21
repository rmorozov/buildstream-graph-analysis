"""UX-896: a cache too small to hold the project is not a cache-key problem.

`cache_effectiveness` reads the cache's behaviour and nothing read its
capacity, so the field case - an agent holding most of a project's
artifacts and evicting the rest - rebuilt, and the rebuild read as a
volatile key. The two have different fixes and one of them is a disk.

What is guarded here is the whole absence rule as much as the arithmetic.
A cache with no recorded quota must produce *no* capacity claim, because
"this cache has no ceiling" and "nobody looked" are the same silence to a
reader and a different decision to an operator sizing an agent.

The per-element half of the row is deliberately not here. BuildStream
2.8.0 exposes no cheap exact artifact weight - `%{artifact-cas-digest}`
renders the serialized root `Directory` proto's own size, not the
artifact's, and `bst artifact list-contents --long` enumerates every
file and deduplicates nothing. `UX-907` carries that question, and
`test_the_capacity_block_claims_no_artifact_weight` holds this module to
not quietly growing one.
"""
import json
import os

import pytest

from bga import cache_capacity
from bga.cache_effectiveness import compute_cache_accounting, compute_cache_capacity
from bga.findings import compute_findings, findings_by_id
from bga.ingest.models import AnalysisResult

#: A cache at 96.9% of a 64G quota whose watermark is 80%: BuildStream
#: is already evicting. Bytes, not adjectives - every derived number
#: below is this dict's arithmetic and can be checked by hand.
FULL = {
    "cachedir": "/home/ci/.cache/buildstream",
    "quota_declared": "64G",
    "reserved_declared": "5%",
    "low_watermark_declared": "80%",
    "volume_total_bytes": 536870912000,
    "volume_free_bytes": 42949672960,
    "quota_bytes": 68719476736,
    "reserved_bytes": 26843545600,
    "cache_used_bytes": 66571993088,
    "cache_used_source": "cas_walk",
}


class _Ctx:
    def __init__(self, capacity=None, queue_summary=None):
        self.cache_capacity = capacity
        self.queue_summary = queue_summary


def _capacity(**overrides):
    recorded = dict(FULL)
    for key, value in overrides.items():
        if value is _ABSENT:
            recorded[key] = None
        else:
            recorded[key] = value
    return compute_cache_capacity(_Ctx(recorded))


class _Absent:
    def __repr__(self):
        return "<absent>"


_ABSENT = _Absent()


def _findings(capacity):
    result = AnalysisResult()
    result.signals['cache'] = {'capacity': capacity}
    return findings_by_id(compute_findings(result))


class TestTheCeilingIsRead:
    def test_a_full_cache_is_past_its_watermark(self):
        """66571993088 / 68719476736 = 0.9688, over 0.80."""
        capacity = _capacity()
        assert capacity['used_share'] == pytest.approx(0.96875, abs=1e-5)
        assert capacity['at_low_watermark'] is True
        assert capacity['headroom_bytes'] == 2147483648

    def test_the_shortfall_is_the_same_signed_field(self):
        """A cache over its quota reports negative headroom rather than
        a second field - one subtraction, one name."""
        capacity = _capacity(cache_used_bytes=68719476736 + 3221225472)
        assert capacity['headroom_bytes'] == -3221225472
        assert capacity['used_share'] > 1

    def test_a_quota_larger_than_its_volume_is_named(self):
        """The acceptance test's second sizing answer, and the one that
        needs no walk: a 600G quota on a 500G volume with 25G reserved
        is a ceiling the disk will never let the cache reach."""
        capacity = _capacity(quota_bytes=644245094400)
        assert capacity['quota_over_volume_bytes'] == (
            644245094400 - (536870912000 - 26843545600))

    def test_a_quota_inside_its_volume_says_nothing(self):
        assert _capacity()['quota_over_volume_bytes'] is None


class TestAbsenceIsNotZero:
    def test_no_capacity_recorded_is_an_empty_block(self):
        """A capture older than this field, which must not read as a
        cache of size zero."""
        assert compute_cache_capacity(_Ctx(None)) == {}

    def test_an_infinite_quota_derives_nothing(self):
        """`infinity` is BuildStream's default. `quota_bytes` is None
        there, and every number that divides by it stays None rather
        than dividing by zero or reading the cache as full."""
        capacity = _capacity(quota_declared="infinity", quota_bytes=_ABSENT)
        assert capacity['used_share'] is None
        assert capacity['headroom_bytes'] is None
        assert capacity['at_low_watermark'] is None
        assert capacity['quota_over_volume_bytes'] is None

    def test_an_unwalked_cache_derives_nothing(self):
        """The default capture: quota and volume read, no walk. The
        sizing facts survive; nothing claims what the cache holds."""
        capacity = _capacity(cache_used_bytes=_ABSENT,
                             cache_used_source="not_walked")
        assert capacity['quota_bytes'] == 68719476736
        assert capacity['used_share'] is None
        assert capacity['at_low_watermark'] is None

    def test_no_watermark_declared_withholds_the_verdict(self):
        """The share is still arithmetic; whether it is *past* anything
        is not, without the watermark to be past."""
        capacity = _capacity(low_watermark_declared=_ABSENT)
        assert capacity['used_share'] == pytest.approx(0.96875, abs=1e-5)
        assert capacity['at_low_watermark'] is None


class TestTheFindingFiresOnFactsOnly:
    def test_a_full_cache_names_eviction(self):
        finding = _findings(_capacity())['cache-capacity']
        assert 'evicting' in finding['title']
        assert finding['severity'] == 'high'
        assert finding['evidence']['headroom_bytes'] == 2147483648

    def test_a_cache_inside_its_watermark_says_nothing(self):
        """Half the acceptance test: on a quota larger than what the
        cache holds, the report is silent."""
        capacity = _capacity(cache_used_bytes=34359738368)  # 32G of 64G
        assert capacity['at_low_watermark'] is False
        assert 'cache-capacity' not in _findings(capacity)

    def test_an_absent_quota_fires_nothing(self):
        """The mutation the task names: set the quota absent and the
        finding disappears rather than reading zero."""
        capacity = _capacity(quota_declared="infinity", quota_bytes=_ABSENT)
        assert 'cache-capacity' not in _findings(capacity)

    def test_halving_the_quota_makes_a_fitting_cache_full(self):
        """The mutation from the other direction: 32G held is 50% of a
        64G quota and 100% of a 32G one."""
        held = {'cache_used_bytes': 34359738368}
        assert 'cache-capacity' not in _findings(_capacity(**held))
        tighter = _capacity(quota_bytes=34359738368, quota_declared="32G", **held)
        assert 'cache-capacity' in _findings(tighter)

    def test_an_over_large_quota_fires_on_its_own(self):
        """It needs no walk, so it is the one claim a default capture
        can still make."""
        capacity = _capacity(quota_bytes=644245094400, quota_declared="600G",
                             cache_used_bytes=_ABSENT,
                             cache_used_source="not_walked")
        finding = _findings(capacity)['cache-capacity']
        assert 'larger than the volume' in finding['title']


class TestTheBlockRidesWithTheAccounting:
    def test_capacity_survives_a_capture_with_no_pipeline_summary(self):
        """Capacity is a fact about the machine, not about the queues,
        so the summary's absence must not take it with it."""
        accounting = compute_cache_accounting(_Ctx(dict(FULL)))
        assert accounting['capacity']['at_low_watermark'] is True

    def test_no_summary_and_no_capacity_is_still_an_empty_block(self):
        assert compute_cache_accounting(_Ctx(None)) == {}

    def test_the_committed_capture_carries_it(self):
        """`UX-460`'s rule, at the source: the fixture that reaches this
        finding is a real run directory in the tree, not a dict built
        here."""
        path = os.path.join("tests", "fixtures", "a_build_that_pulls",
                            "run", "run-context.json")
        with open(path, encoding="utf-8") as handle:
            recorded = json.load(handle)["cache_capacity"]
        assert recorded["quota_declared"] == "64G"
        assert recorded["cache_used_source"] == "cas_walk"


class TestWhatTheConfigurationSays:
    def test_buildstreams_own_suffixes(self):
        """1024-based, as `utils._parse_size` reads them."""
        assert cache_capacity.parse_size("64G") == 68719476736
        assert cache_capacity.parse_size("500M") == 524288000
        assert cache_capacity.parse_size("1T") == 1099511627776

    def test_infinity_is_not_a_size(self):
        assert cache_capacity.parse_size("infinity") is None

    def test_a_percentage_needs_a_volume(self):
        assert cache_capacity.parse_size("10%") is None
        assert cache_capacity.parse_size("10%", 1000) == 100

    def test_a_watermark_is_a_ratio_not_a_size(self):
        assert cache_capacity.parse_percentage("80%") == pytest.approx(0.8)
        assert cache_capacity.parse_percentage("nonsense") is None

    def test_the_cache_block_is_read_verbatim(self, tmp_path):
        config = tmp_path / "buildstream.conf"
        config.write_text(
            "cachedir: ${XDG_CACHE_HOME}/buildstream\n"
            "cache:\n  quota: 64G\n  low-watermark: 80%\n",
            encoding="utf-8")
        env = {"XDG_CACHE_HOME": "/var/cache"}
        read = cache_capacity.read_config(str(config), env=env)
        assert read["cachedir"] == "/var/cache/buildstream"
        assert read["quota_declared"] == "64G"
        assert read["low_watermark_declared"] == "80%"
        assert read["reserved_declared"] is None

    def test_a_bare_number_survives_yaml(self, tmp_path):
        """YAML reads `quota: 64` as an int; BuildStream parses a
        string. A block that handed an int to the parser would report no
        quota on a configuration that declares one."""
        config = tmp_path / "buildstream.conf"
        config.write_text("cache:\n  quota: 64\n", encoding="utf-8")
        read = cache_capacity.read_config(str(config), env={})
        assert read["quota_declared"] == "64"
        assert cache_capacity.parse_size(read["quota_declared"]) == 64

    def test_no_configuration_is_an_empty_read(self, tmp_path):
        assert cache_capacity.read_config(str(tmp_path / "absent"), env={}) == {}


class TestTheWalkCountsTheVolumeNotTheNames:
    def test_a_hardlinked_blob_is_counted_once(self, tmp_path):
        """CAS hardlinks one object into several trees. Counting the
        links would report a cache larger than the disk it is on."""
        cas = tmp_path / "cas" / "objects"
        cas.mkdir(parents=True)
        blob = cas / "aa"
        blob.write_bytes(b"x" * 8192)
        os.link(blob, cas / "bb")
        once, source = cache_capacity.cas_size_bytes(str(tmp_path))
        assert source == "cas_walk"
        assert once == os.stat(blob).st_blocks * 512

    def test_no_cas_is_absent_rather_than_zero(self, tmp_path):
        assert cache_capacity.cas_size_bytes(str(tmp_path)) == (None, "absent")

    def test_a_walk_out_of_time_reports_no_number(self, tmp_path):
        """A truncated sum is not a cache size, so the budget returns
        None with its own reason rather than what it had reached."""
        cas = tmp_path / "cas"
        cas.mkdir()
        (cas / "blob").write_bytes(b"x" * 4096)
        assert cache_capacity.cas_size_bytes(str(tmp_path), budget_s=-1) == (
            None, "budget_exceeded")

    def test_the_default_capture_does_not_walk(self, tmp_path):
        """`with_usage` off is the default, and off must say `not_walked`
        rather than leave the source absent beside an absent number."""
        block = cache_capacity.collect(
            env={"XDG_CACHE_HOME": str(tmp_path)},
            config={"cachedir": str(tmp_path)})
        assert block["cache_used_bytes"] is None
        assert block["cache_used_source"] == "not_walked"


class TestTheRowKnowsWhatItDoesNotCarry:
    def test_the_capacity_block_claims_no_artifact_weight(self):
        """The gap this row measured and did not close. A later round
        that adds a per-element weight has to move this guard, which is
        the point: the proxy that looks like one (`artifact-cas-digest`)
        must not arrive under a name that reads as the real thing."""
        assert not [key for key in _capacity()
                    if "artifact" in key or "element" in key]
