"""Constants shared between bga/report/text.py and bga/report/json.py."""

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
    'critical_path', 'critical_path_length', 'downstream_count', 'slack', 'unweighted_depth',
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
