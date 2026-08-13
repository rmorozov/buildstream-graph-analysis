"""
Determinism harness (Part 35 - Determinism Contract, invariant I11).

"No Python hash iteration order, dictionary order, filesystem order, or
concurrency-dependent ordering may influence results." This module runs
the same analysis repeatedly against the same input and asserts every
run produces byte-identical canonical output.

This is a test/validation tool, not user-facing analysis output - it is
expected (and fine) to be slow, since it runs the full pipeline N times.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _diff_paths(a: Any, b: Any, path: str = "") -> List[str]:
    """Recursively find differing key paths between two JSON-decoded
    values, so a mismatch is diagnosable ("which field differs and how"),
    not just "mismatch found"."""
    if isinstance(a, dict) and isinstance(b, dict):
        diffs = []
        for key in sorted(set(a.keys()) | set(b.keys())):
            sub_path = f"{path}.{key}" if path else key
            if key not in a:
                diffs.append(f"{sub_path}: missing in run 1, present in later run")
            elif key not in b:
                diffs.append(f"{sub_path}: present in run 1, missing in later run")
            else:
                diffs.extend(_diff_paths(a[key], b[key], sub_path))
        return diffs
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        diffs = []
        for i, (av, bv) in enumerate(zip(a, b)):
            diffs.extend(_diff_paths(av, bv, f"{path}[{i}]"))
        return diffs
    if a != b:
        return [f"{path}: {a!r} != {b!r}"]
    return []


def run_determinism_check(run_dir: Path, n: int = 100) -> Dict[str, Any]:
    """
    Run the full analysis pipeline n times against the same run_dir and
    assert every run produces byte-identical canonical output.

    Canonical serialization reuses bga.cli.format_json (the same
    serializer the CLI's --format json path already uses - not a second,
    divergent serializer), with keys sorted so a mismatch reflects a
    genuine value difference, not an incidental dict-insertion-order
    artifact of the serializer itself.

    Returns:
        {
            'deterministic': bool,
            'n': int,
            'mismatches': [{'run_index': int, 'diffs': [str, ...]}, ...],
        }
        A non-empty 'mismatches' list is the harness doing its job -
        finding a real nondeterminism bug is success for this tool, not
        failure of it.
    """
    # Imported here, not at module load time, to avoid import-order
    # issues between bga.cli and bga.validation (cli imports analyzer;
    # this module only needs cli's formatter, one-directional).
    from ..analyzer import BuildEfficiencyAnalyzer
    from ..cli import format_json

    canonical_runs: List[Any] = []
    for i in range(n):
        analyzer = BuildEfficiencyAnalyzer(run_dir)
        analyzer.load()
        result = analyzer.analyze()
        serialized = format_json(result)
        canonical_runs.append(json.loads(serialized))

    baseline = canonical_runs[0]
    baseline_canonical = json.dumps(baseline, sort_keys=True)

    mismatches = []
    for i, run_data in enumerate(canonical_runs[1:], start=1):
        if json.dumps(run_data, sort_keys=True) != baseline_canonical:
            diffs = _diff_paths(baseline, run_data)
            mismatches.append({"run_index": i, "diffs": diffs})
            logger.warning("Determinism check: run %d differs from run 0: %s", i, diffs)

    deterministic = len(mismatches) == 0
    if deterministic:
        logger.info("Determinism check passed: %d runs, all identical", n)
    else:
        logger.warning(
            "Determinism check FAILED: %d of %d runs differ from run 0",
            len(mismatches), n,
        )

    return {
        "deterministic": deterministic,
        "n": n,
        "mismatches": mismatches,
    }
