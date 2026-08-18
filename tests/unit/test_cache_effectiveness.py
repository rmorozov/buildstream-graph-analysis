"""UX-92 stages 1 and 2: what the cache did, and what invalidated it.

Round 6 established that every real CI build is incremental, which makes
the cache the dominant efficiency mechanism - and every other signal in
this tool describes *the work the build did*. A build whose cache
behaviour is terrible does more work, does it efficiently, and scores
well: occupancy, the efficiency score and the certified floors are all
blind to it by construction. That is not a gap in one report section, it
is a whole axis the tool could not see.

Two things are computed here, from data already captured:

1. **Accounting** - BuildStream's own closing Pipeline Summary says how
   many elements it built and how many it skipped. Nothing is modelled.
2. **Churn and invalidation roots** - a cache key is a hash over an
   element's definition *and* its dependencies' keys, so comparing two
   runs' keys answers "did anything that affects this element change"
   exactly, without a source-ref diff.

The end-to-end numbers quoted below are from real `examples/06` builds
run for this task with a real bst 2.7.0, not from fixtures.
"""
from bga.cache_effectiveness import (
    HEALTHY_HIT_RATIO, POOR_HIT_RATIO, compute_cache_accounting,
    compute_cache_churn,
)
from bga.findings import compute_findings, findings_by_id


class _Ctx:
    def __init__(self, queue_summary):
        self.queue_summary = queue_summary


class _Elem:
    def __init__(self, uid, cache_key, requested_target=False):
        self.uid = uid
        self.cache_key = cache_key
        self.requested_target = requested_target


class _Dep:
    def __init__(self, predecessor, successor):
        self.predecessor = predecessor
        self.successor = successor


class _Graph:
    def __init__(self, elements, dependencies):
        self.elements = elements
        self.dependencies = dependencies


# --- accounting ---------------------------------------------------------

def test_the_real_capture_numbers():
    """The acceptance test's own figures, from the published fdsdk
    capture: 65 cached, 25 built."""
    accounting = compute_cache_accounting(
        _Ctx({"build": {"processed": 25, "skipped": 65, "failed": 0},
              "fetch": {"processed": 0, "skipped": 90, "failed": 0}}),
    )
    assert accounting["built_elements"] == 25
    assert accounting["cached_elements"] == 65
    assert round(accounting["hit_ratio"], 4) == 0.7222
    assert accounting["fetch"]["hit_ratio"] == 1.0


def test_a_capture_with_no_pipeline_summary_gets_no_block():
    """Absent, not zero-filled. A block of Nones invites a consumer to
    render zeros, and "the cache did nothing" is a very different claim
    from "nobody wrote down what the cache did"."""
    assert compute_cache_accounting(_Ctx(None)) == {}
    assert compute_cache_accounting(_Ctx({})) == {}


def test_an_empty_queue_has_no_hit_ratio_rather_than_a_perfect_one():
    """A queue that processed nothing did not achieve 100%."""
    accounting = compute_cache_accounting(
        _Ctx({"build": {"processed": 0, "skipped": 0}}),
    )
    assert accounting["hit_ratio"] is None


def test_the_target_closure_is_accounted_separately():
    """A project-wide ratio says little when the thing being shipped
    rebuilt entirely. The closure walk includes runtime edges - unlike
    the critical-path walk, which excludes them correctly for a
    different question - because shipping a target requires them."""
    graph = _Graph(
        [_Elem("app.bst", "k1", requested_target=True),
         _Elem("lib.bst", "k2"), _Elem("unrelated.bst", "k3")],
        [_Dep("lib.bst", "app.bst")],
    )

    class _Key:
        def __init__(self, uid):
            self.element_uid = uid
            self.task_kind = type("K", (), {"value": "BUILD"})()

    class _Task:
        def __init__(self, uid):
            self.task_key = _Key(uid)

    accounting = compute_cache_accounting(
        _Ctx({"build": {"processed": 1, "skipped": 2}}), graph, [_Task("app.bst")],
    )
    closure = accounting["target_closure"]
    assert closure["elements"] == 2          # app + lib, not the unrelated one
    assert closure["built"] == 1
    assert closure["cached"] == 1


# --- the finding --------------------------------------------------------

class _Result:
    def __init__(self, cache):
        self.signals = {"cache": cache}
        self.confidence = {"primary": 1.0}
        self.violations = []
        self.floors = {}
        self.attribution = {}
        self.total_duration_us = 1000
        self.structural = {}
        self.occupancy_stats = {}


def _cache_finding(hit_ratio, **extra):
    cache = {"hit_ratio": hit_ratio, "built_elements": 10, "cached_elements": 90}
    cache.update(extra)
    return findings_by_id(compute_findings(_Result(cache))).get("cache-hit-ratio")


def test_a_healthy_cache_is_still_reported():
    """Not gated on being bad. On an incremental build the cache decides
    how much work there was, so it is context for reading everything
    else - what a good ratio changes is the sentence, not whether the
    line appears."""
    finding = _cache_finding(0.9)
    assert finding is not None
    assert finding["severity"] == "info"
    assert "90%" in finding["title"]


def test_a_barely_incremental_build_says_so_loudly():
    finding = _cache_finding(POOR_HIT_RATIO - 0.01)
    assert finding["severity"] == "high"
    assert "volatile cache key" in finding["title"]


def test_the_middle_band_is_a_question_not_an_alarm():
    finding = _cache_finding((POOR_HIT_RATIO + HEALTHY_HIT_RATIO) / 2)
    assert finding["severity"] == "medium"


def test_no_ratio_means_no_finding():
    assert _cache_finding(None) is None


# --- churn and invalidation roots ---------------------------------------

def _churn(baseline, candidate, deps, built, durations=None):
    return compute_cache_churn(
        [_Elem(u, k) for u, k in baseline.items()],
        [_Elem(u, k) for u, k in candidate.items()],
        [_Dep(p, s) for p, s in deps],
        set(built), durations or {u: 1_000_000 for u in built},
    )


def test_nothing_changed_means_no_churn_and_no_roots():
    """Measured for real: `examples/06` built twice with caches on
    reported 0 churn, 0 changed keys, across 11 comparable elements."""
    result = _churn({"a.bst": "k1", "b.bst": "k2"},
                    {"a.bst": "k1", "b.bst": "k2"}, [("a.bst", "b.bst")], built=[])
    assert result["churned_count"] == 0
    assert result["changed_keys"] == 0
    assert result["invalidation_roots"] == []


def test_a_rebuild_with_an_unchanged_key_is_churn():
    """The definition is not a judgement call: the key covers the
    element and everything it depends on, so an identical key means the
    artifact it produced already existed."""
    result = _churn({"a.bst": "k1"}, {"a.bst": "k1"}, [], built=["a.bst"],
                    durations={"a.bst": 5_000_000})
    assert result["churned_elements"] == ["a.bst"]
    assert result["wasted_rebuild_us"] == 5_000_000


def test_the_root_of_an_invalidation_is_named_and_the_rest_explained():
    """The real measurement this exists for: one comment added to one
    source file of `examples/06`'s `core.bst` rebuilt **9 of 11**
    elements. The useful output is not the nine - it is that they all
    trace to one root."""
    baseline = {"core.bst": "old", "lib.bst": "l1", "app.bst": "a1"}
    candidate = {"core.bst": "new", "lib.bst": "l2", "app.bst": "a2"}
    deps = [("core.bst", "lib.bst"), ("lib.bst", "app.bst")]
    result = _churn(baseline, candidate, deps, built=["core.bst", "lib.bst", "app.bst"])

    assert result["changed_keys"] == 3
    assert [r["element_uid"] for r in result["invalidation_roots"]] == ["core.bst"]
    root = result["invalidation_roots"][0]
    assert root["downstream_rebuilt"] == 2
    assert root["downstream_us"] == 2_000_000


def test_two_independent_changes_are_two_roots():
    """A single root and twenty roots are different problems, and the
    report must be able to tell them apart."""
    result = _churn(
        {"a.bst": "1", "b.bst": "1", "c.bst": "1"},
        {"a.bst": "2", "b.bst": "2", "c.bst": "1"},
        [], built=["a.bst", "b.bst"],
    )
    assert [r["element_uid"] for r in result["invalidation_roots"]] == ["a.bst", "b.bst"]


def test_an_element_only_one_side_has_is_skipped_rather_than_guessed():
    """An element the baseline never had cannot have churned."""
    result = _churn({"a.bst": "1"}, {"a.bst": "1", "new.bst": "9"}, [],
                    built=["new.bst"])
    assert result["comparable_elements"] == 1
    assert result["churned_count"] == 0
    assert result["invalidation_roots"] == []


def test_no_comparable_keys_produces_no_block():
    assert _churn({}, {}, [], built=[]) == {}
