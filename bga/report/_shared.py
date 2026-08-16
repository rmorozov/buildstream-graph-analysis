"""Constants shared between bga/report/text.py and bga/report/json.py."""

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
# rises (confirmed with real timing evidence in docs/scenarios/UX-09-
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
