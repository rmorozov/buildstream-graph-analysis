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
