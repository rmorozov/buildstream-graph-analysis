"""Validation and cross-run consistency checks for bga (Part 39)."""

from .determinism import run_determinism_check
from .invariants import compute_confidence

__all__ = ["run_determinism_check", "compute_confidence"]
