"""Report formatting (text/JSON/CSV) - Part 32.4/37."""

from ._shared import GRAPH_SIGNAL_KEYS, SECTIONS, SWEEP_CAPACITY_MODEL_CAVEAT
from .json import format_json
from .text import format_compare_text, format_csv, format_sweep_text, format_text

__all__ = [
    "SECTIONS",
    "GRAPH_SIGNAL_KEYS",
    "SWEEP_CAPACITY_MODEL_CAVEAT",
    "format_text",
    "format_json",
    "format_csv",
    "format_sweep_text",
    "format_compare_text",
]
