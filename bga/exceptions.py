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
