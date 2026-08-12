"""
Attribution module for bga.

Implements the dependency blame chain model (M2).
"""

from .blame_chain import (
    AttributionSegment,
    BlameChainNode,
    TaskAttribution,
    BlameChainAnalyzer,
)

__all__ = [
    'AttributionSegment',
    'BlameChainNode',
    'TaskAttribution',
    'BlameChainAnalyzer',
]
