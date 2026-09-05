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
    HEALTHY_HIT_RATIO,
    POOR_HIT_RATIO,
    compute_cache_accounting,
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
    assert round(accounting["hit_share"], 4) == 0.7222
    assert accounting["fetch"]["hit_share"] == 1.0


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
    assert accounting["hit_share"] is None


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
    def __init__(self, cache, run_mode=None):
        self.signals = {"cache": cache}
        self.confidence = {"primary": 1.0, "run_mode": run_mode}
        self.violations = []
        self.floors = {}
        self.attribution = {}
        self.total_duration_us = 1000
        self.structural = {}
        self.occupancy_stats = {}


def _cache_finding(hit_share, run_mode=None, **extra):
    cache = {"hit_share": hit_share, "built_elements": 10, "cached_elements": 90}
    cache.update(extra)
    return findings_by_id(
        compute_findings(_Result(cache, run_mode=run_mode))
    ).get("cache-hit-ratio")


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


def test_a_caches_off_run_is_not_an_alarm():
    """A nightly is *told* not to use the cache, so 0% is the intent.

    Not hypothetical, and not caught by review: this project's first
    ever cold capture - 18 of 18 elements built, 0 cached, exactly as
    asked - was reported as "barely incremental - most of the project
    rebuilt. Look for a volatile cache key near the root", hours after
    the finding shipped. `run_mode` (UX-55) was already in hand and the
    finding ignored it.
    """
    finding = _cache_finding(0.0, run_mode="full")
    assert finding["severity"] == "info"
    assert "Caches off" in finding["title"]
    assert "volatile cache key" not in finding["title"]
    assert finding["evidence"]["run_mode"] == "full"


def test_the_same_ratio_on_an_incremental_run_is_still_an_alarm():
    """The banding is not switched off - it is conditioned. An
    incremental run that reused nothing is the failure mode this finding
    exists for."""
    finding = _cache_finding(0.0, run_mode="incremental")
    assert finding["severity"] == "high"
    assert "volatile cache key" in finding["title"]


def test_no_ratio_means_no_finding():
    assert _cache_finding(None) is None


# --- churn and invalidation roots ---------------------------------------

def _churn(baseline, candidate, deps, built, durations=None, baseline_built=(),
           candidate_run_mode="incremental", baseline_run_mode="incremental"):
    """UX-93 gave this call three preconditions. The defaults here are
    the case the original tests were written against and still describe:
    two incremental runs whose baseline rebuilt nothing, i.e. every
    unchanged-key rebuild really is a rebuild of something the baseline
    had cached."""
    return compute_cache_churn(
        [_Elem(u, k) for u, k in baseline.items()],
        [_Elem(u, k) for u, k in candidate.items()],
        [_Dep(p, s) for p, s in deps],
        set(built), durations or dict.fromkeys(built, 1000000),
        baseline_built=None if baseline_built is None else set(baseline_built),
        candidate_run_mode=candidate_run_mode,
        baseline_run_mode=baseline_run_mode,
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


# --- UX-93: churn is a claim about an artifact that was there to serve --

def test_a_caches_off_candidate_gets_no_churn_verdict_at_all():
    """Round 11's first false accusation, in one line: two deliberate
    full rebuilds of the same project, caches cleared between them - the
    repository's own examples protocol - reported *"10 element(s)
    rebuilt with an unchanged cache key, costing 36.5s ... that time
    bought nothing"*. It bought the entire build.
    """
    result = _churn({"a.bst": "k1"}, {"a.bst": "k1"}, [], built=["a.bst"],
                    candidate_run_mode="full")
    assert result["applicable"] is False
    assert result["reason"] == "candidate_run_is_full"
    assert "churned_elements" not in result
    assert "invalidation_roots" not in result
    # The accounting survives - what is withdrawn is the verdict, not
    # the measurement.
    assert result["comparable_elements"] == 1
    assert result["unchanged_keys"] == 1


def test_a_caches_off_baseline_cannot_support_either_verdict():
    """The mirror case, and it needs its own answer: a cold baseline
    rebuilt everything, so every unchanged-key rebuild in the candidate
    also appears in the baseline. Reporting that as a retention failure
    would be as wrong as reporting it as waste."""
    result = _churn({"a.bst": "k1"}, {"a.bst": "k1"}, [], built=["a.bst"],
                    baseline_built=["a.bst"], baseline_run_mode="full")
    assert result["applicable"] is False
    assert result["reason"] == "baseline_run_is_full"


def test_both_runs_rebuilding_the_same_key_is_a_retention_finding():
    """Round 11's second false accusation, and the one that would have
    run forever: the fdsdk capture workflow warms the cache and then
    deliberately deletes a 25-element rebuild set - that deletion *is*
    the capture. Every band comparison of two such captures reported
    "25 element(s) rebuilt with an unchanged cache key, costing 4604.2s"
    about the mechanism producing the data.

    The rebuild is real and worth naming. What it is evidence of is the
    artifact not surviving between runs, which is a question about the
    cache, not about the project - so it gets its own bucket rather than
    a softened version of the waste wording.
    """
    result = _churn(
        {"cut.bst": "k1", "kept.bst": "k2"},
        {"cut.bst": "k1", "kept.bst": "k2"},
        [], built=["cut.bst"], baseline_built=["cut.bst"],
        durations={"cut.bst": 4_604_200_000},
    )
    assert result["rebuilt_in_both_elements"] == ["cut.bst"]
    assert result["rebuilt_in_both_us"] == 4_604_200_000
    # And it is not also billed as waste.
    assert result["churned_elements"] == []
    assert result["wasted_rebuild_us"] == 0


def test_the_baseline_had_it_cached_so_it_is_still_waste():
    """The case the original wording is true for, kept exactly: the
    baseline skipped this element, the candidate rebuilt it, and the key
    says nothing it depends on changed."""
    result = _churn({"a.bst": "k1"}, {"a.bst": "k1"}, [], built=["a.bst"],
                    baseline_built=[], durations={"a.bst": 5_000_000})
    assert result["churned_elements"] == ["a.bst"]
    assert result["wasted_rebuild_us"] == 5_000_000
    assert result["rebuilt_in_both_elements"] == []


def test_an_unmeasured_baseline_declines_rather_than_guesses():
    """Without the baseline's built set the two findings above are
    indistinguishable. `compare` already refuses to guess the candidate's
    built set for exactly this reason; this is the same rule on the other
    side of the same call."""
    result = _churn({"a.bst": "k1"}, {"a.bst": "k1"}, [], built=["a.bst"],
                    baseline_built=None)
    assert result["applicable"] is False
    assert result["reason"] == "baseline_built_set_not_measured"


def test_invalidation_roots_still_work_on_a_genuine_incremental_pair():
    """The true-positive protocol from round 11 (cold A, tweak codegen
    -> B, tweak core -> C, compare B vs C) verified this path correct
    as shipped. UX-93 conditions the churn verdict; it must not touch
    this one."""
    result = _churn(
        {"core.bst": "old", "lib.bst": "l1"},
        {"core.bst": "new", "lib.bst": "l2"},
        [("core.bst", "lib.bst")], built=["core.bst", "lib.bst"],
        baseline_built=[],
    )
    assert [r["element_uid"] for r in result["invalidation_roots"]] == ["core.bst"]
    assert result["churned_count"] == 0
