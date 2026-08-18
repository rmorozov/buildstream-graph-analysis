"""Constants shared between bga/report/text.py and bga/report/json.py."""

from typing import Optional

from ..ingest.models import AttributionCategory

# Section names understood by format_text/format_json's `section`
# parameter, one per P1-14 hybrid subcommand alias (`graph`/`floors`/
# `replay`/`utilisation`/`diagnostics`) plus None for the full `analyze`
# report. Not exhaustive of every AnalysisResult field (e.g. attribution
# has no dedicated subcommand - `--format csv` already serves that slice).
SECTIONS = (None, 'graph', 'floors', 'replay', 'utilisation', 'diagnostics')

# signals keys populated by graph analysis (Part 5/14) vs. by advanced
# diagnostics (Part 20-29, M5) - result.signals mixes both in one flat
# dict, so section filtering needs to know which is which.
GRAPH_SIGNAL_KEYS = frozenset({
    'critical_path', 'critical_path_length', 'critical_path_detail',
    'downstream_count', 'slack', 'unweighted_depth',
})

# UX-14: a capacity sweep (Part 19) replays every task with its fixed,
# already-observed duration_us regardless of the capacity value being
# swept - real, physical CPU contention as concurrent PROCESS usage
# rises (confirmed with real timing evidence in docs/backlog/scenarios/UX-09-
# builders-max-jobs-joint-optimization.md: 8 builders x 8 max-jobs
# measured ~11% *slower* than 4x4 on the same real 4-core host) is
# structurally invisible to this model - predicted makespan can only
# ever improve or plateau with more capacity, never predict a real
# regression past a point. Spec Part 19 itself says this result is "a
# shape, not an exact runtime prediction" - this string is that same
# caveat, actually shown in the CLI output rather than living only in
# the spec document (bga/report/text.py's format_sweep_text and
# bga/cli.py's JSON sweep output both use this single copy).
SWEEP_CAPACITY_MODEL_CAVEAT = (
    "This sweep replays each task's fixed, already-observed duration - it does not "
    "model real CPU contention as concurrent PROCESS usage rises (see UX-09's real "
    "evidence this can cause an actual slowdown, not just a plateau, past some "
    "capacity). Treat this curve as a shape, not an exact runtime prediction (Part 19)."
)


def _attribution_key(category: AttributionCategory) -> str:
    """The lowercase `<category>_us` key `result.attribution` (and
    `--format json`'s `attribution`/`attribution_hints` dicts) actually
    use for a given `AttributionCategory` member - confirmed against
    `bga/analyzer.py`'s `_compute_attribution` (`execution_on_chain_us`,
    `dependency_wait_us`, etc.)."""
    return f"{category.value.lower()}_us"


# UX-04: "Biggest Opportunity" names a category (Part 11) but, before
# this fix, gave no way to know from the report itself what that
# category actually means or what to do about it - three categories
# (RESOURCE_WAIT/SCHEDULER_WAIT/IDLE) look superficially similar ("the
# critical path wasn't running") but have three completely different
# real fixes, each precisely defined in the spec but never surfaced in
# the report. Presentation-only: one static hint string per category,
# no computation change. Keyed by the enum itself (not the string key)
# so a test can enumerate AttributionCategory and assert none are
# missing - a real guard against a future new category silently
# lacking a hint.
ATTRIBUTION_CATEGORY_HINTS = {
    AttributionCategory.EXECUTION_ON_CHAIN: (
        "real work on the critical path - the only way to reduce this is to reduce "
        "the work itself"
    ),
    AttributionCategory.DEPENDENCY_WAIT: (
        "waiting on an upstream element to finish - shorten or parallelize that "
        "dependency chain"
    ),
    AttributionCategory.RESOURCE_WAIT: (
        "a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a "
        "higher N, or `bga sweep` to find the real knee point"
    ),
    AttributionCategory.SCHEDULER_WAIT: (
        "capacity was available but nothing was dispatched - try a different "
        "--heuristic in `bga replay`"
    ),
    AttributionCategory.IDLE: (
        "nothing was dependency-ready at all - likely a critical-path/graph-shape "
        "issue, not a capacity one; check Critical Path"
    ),
    AttributionCategory.RETRY_WAIT: (
        "this element needed a retry - investigate why the first attempt "
        "failed/was discarded"
    ),
    AttributionCategory.UNTRACKED_HEAD: (
        "real time before the tracked-task window started (BuildStream startup, "
        "cache query, sandbox staging) - see Pipeline Overhead, not a scheduling issue"
    ),
    AttributionCategory.UNTRACKED_TAIL: (
        "real time after the last tracked task finished - outside per-task tracking, "
        "not a scheduling issue"
    ),
}

# The same hints, keyed by the lowercase `<category>_us` string that
# result.attribution/--format json actually use - derived once from the
# enum-keyed dict above so there is exactly one source of truth.
ATTRIBUTION_CATEGORY_HINTS_BY_KEY = {
    _attribution_key(category): hint for category, hint in ATTRIBUTION_CATEGORY_HINTS.items()
}

# UX-35: `RESOURCE_WAIT`'s static hint says "try --capacity N with a
# higher N". That is right on an under-provisioned host and actively
# wrong on a saturated one - and a real run of
# examples/06-macro-micro-optimization/optimized printed it while already
# dispatching up to `builders x max-jobs` = 16 potential concurrent
# processes on 4 cores. The hints were constant strings, chosen by
# attribution category alone, consulting none of the capacity facts the
# tool has.
#
# Only RESOURCE_WAIT is conditioned: it is the one hint whose *direction*
# depends on capacity. The other seven were re-read in the same pass and
# none of them advises a direction that capacity could invert.
_RESOURCE_WAIT_KEY = _attribution_key(AttributionCategory.RESOURCE_WAIT)

_RESOURCE_WAIT_HINT_OVERSUBSCRIBED = (
    "a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - but this run is already "
    "oversubscribed (see Violations), so raising capacity will make it worse, not "
    "better: the levers here are less native parallelism per element, fewer "
    "builders, or less work"
)
_RESOURCE_WAIT_HINT_UNKNOWN_CAPACITY = (
    "a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - whether raising capacity "
    "would help depends on how loaded this host already is, and this run's capacity "
    "checks could not run (see the Certified Floors note), so this hint is "
    "unconditioned; `bga sweep` shows the shape of the curve either way"
)


def resolve_attribution_hint(key: str, capacity_verdict: Optional[dict] = None) -> Optional[str]:
    """UX-35: the next-step hint for one attribution category, given this
    run's own already-decided capacity verdict
    (`AnalysisResult.capacity_verdict`).

    Deliberately consumes that verdict rather than re-deriving one: two
    independently-derived capacity formulas comparing the same real
    inputs is precisely the divergence `UX-17` was resolved to avoid.
    `None`/empty verdict is treated as "unknown", not as "fine".
    """
    if key != _RESOURCE_WAIT_KEY:
        return ATTRIBUTION_CATEGORY_HINTS_BY_KEY.get(key)
    verdict = capacity_verdict or {}
    if verdict.get('oversubscribed'):
        return _RESOURCE_WAIT_HINT_OVERSUBSCRIBED
    if not verdict.get('checks_ran'):
        return _RESOURCE_WAIT_HINT_UNKNOWN_CAPACITY
    return ATTRIBUTION_CATEGORY_HINTS_BY_KEY.get(key)
