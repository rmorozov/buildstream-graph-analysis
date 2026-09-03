"""
Exception hierarchy for bga.

Subclassing the builtin types (ValueError/FileNotFoundError) that call
sites already raise/catch means introducing these types is purely
additive: existing `except ValueError`/`except FileNotFoundError` blocks
keep working unchanged, while callers that want to distinguish failure
categories precisely (ingestion vs. analysis, say) can now catch by type
instead of string-matching the message.
"""


class BgaError(Exception):
    """Base class for all bga-specific errors."""


class IngestionError(BgaError, ValueError):
    """Input files are missing or their content is malformed (exit code 1/2)."""


class NormalizationError(BgaError, ValueError):
    """Trace normalization could not produce a valid set of tasks."""


class AnalysisError(BgaError, ValueError):
    """The analysis pipeline could not proceed (e.g. a graph cycle) - exit code 3."""


class ValidationError(BgaError, ValueError):
    """A hard-gate validation check failed."""


# UX-574: the one registry docs/guides/cli.md's Exit Codes list derives
# from, so a row cannot drift from the code again.
EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_INGESTION = 2
EXIT_ANALYSIS = 3
EXIT_REGRESSION = 4
EXIT_EFFICIENCY_REGRESSION = 5
EXIT_MISMATCHED_RUNS = 6
EXIT_SIGNAL_UNAVAILABLE = 7
EXIT_INTERRUPTED = 130

EXIT_CODES: dict[str, int] = {
    "success": EXIT_OK,
    "general error": EXIT_GENERAL,
    "ingestion failure": EXIT_INGESTION,
    "analysis failure": EXIT_ANALYSIS,
    "regression": EXIT_REGRESSION,
    "efficiency regression": EXIT_EFFICIENCY_REGRESSION,
    "mismatched runs": EXIT_MISMATCHED_RUNS,
    "signal unavailable": EXIT_SIGNAL_UNAVAILABLE,
    "interrupted": EXIT_INTERRUPTED,
}
