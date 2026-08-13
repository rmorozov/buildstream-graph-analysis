"""JSON report formatting (Part 32.4/37)."""
import json as _json
from typing import Optional

from ..ingest.models import AnalysisResult
from ._shared import GRAPH_SIGNAL_KEYS


def format_json(result: AnalysisResult, section: Optional[str] = None) -> str:
    """
    Format analysis results as JSON.

    Args:
        result: The AnalysisResult object from the analyzer
        section: Restrict output to one report section (see SECTIONS) -
            None (default) produces the full `analyze` report. The
            top-level key shape is unchanged either way (e.g. `floors`
            always lives under a `"floors"` key) - only which top-level
            keys are present differs, so existing `--format json`
            consumers of the full report see no shape change.

    Returns:
        JSON string suitable for machine processing
    """
    data = {
        'run_id': result.run_id,
        'total_duration_us': result.total_duration_us,
    }

    if section in (None, 'floors', 'replay'):
        data['floors'] = result.floors

    if section is None and hasattr(result, 'attribution') and result.attribution:
        data['attribution'] = result.attribution

    # occupancy field - check both occupancy (AnalysisResult field) and occupancy_stats (legacy name)
    if section is None:
        if hasattr(result, 'occupancy') and result.occupancy:
            data['occupancy'] = result.occupancy
        elif hasattr(result, 'occupancy_stats'):
            data['occupancy'] = result.occupancy_stats

    if section in (None, 'graph', 'diagnostics') and hasattr(result, 'signals') and result.signals:
        # Convert dataclasses to dicts for JSON serialization
        signals_data = {}
        for key, value in result.signals.items():
            if section == 'graph' and key not in GRAPH_SIGNAL_KEYS:
                continue
            if section == 'diagnostics' and key in GRAPH_SIGNAL_KEYS:
                continue
            if isinstance(value, list) and value:
                if hasattr(value[0], '__dict__'):
                    signals_data[key] = [v.__dict__ if hasattr(v, '__dict__') else v for v in value]
                else:
                    signals_data[key] = value
            elif hasattr(value, '__dict__'):
                signals_data[key] = value.__dict__
            else:
                signals_data[key] = value
        if signals_data:
            data['signals'] = signals_data

    if section in (None, 'graph') and hasattr(result, 'structural') and result.structural:
        data['structural'] = result.structural

    if section in (None, 'utilisation') and hasattr(result, 'utilisation') and result.utilisation:
        data['utilisation'] = result.utilisation

    if section is None and hasattr(result, 'confidence') and result.confidence:
        data['confidence'] = result.confidence

    if section is None and hasattr(result, 'violations'):
        # Always include, even when empty - an empty list means "checked,
        # none found", which is different from the key being absent.
        data['violations'] = result.violations

    if section is None and hasattr(result, 'model') and result.model:
        data['model'] = result.model

    return _json.dumps(data, indent=2, default=str)
