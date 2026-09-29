"""`UX-691`: which files the flake ledger says need a task.

    python3 tools/dev_flake_census.py                 # the top three

A file the drift gate reports keeps landing in `tests/flake_ledger.json`
(`dev_tier_drift.py --adopt-flake`) whether the run confirms it as
drift or only sees it once. Three appearances is the line between "one
excursion" and "a file nobody is tracking" (the task's own Motivation).
`unaccounted` names every file at or past that line with neither a
task whose header declares it in a `**Flake:**` field nor a declared
reason beside it in the ledger; `top` is what the round document's
Standing prints.

`per_run` (`UX-950`) reads a run that moved several files together, at
once, as improbable under independent files at the ledger's own rates
- such a run counts once, not once per file, toward `EXCURSION_FLOOR`.
`--record-run RUN_ID` adds a run id to the runs `per_run` divides by,
so a run that wrote no row still counts toward N.
"""

import argparse
import collections
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
LEDGER = REPO / "tests" / "flake_ledger.json"
SCENARIOS = REPO / "docs" / "backlog" / "scenarios"

#: The task's own number: two excursions could be one afternoon; a
#: third is what tells a flake apart from noise.
EXCURSION_FLOOR = 3


def load(path=LEDGER):
    if not path.is_file():
        return {"entries": [], "declared": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_counts(document):
    """`{file: row count}`, unadjusted - the rate `per_run`'s tail is
    drawn from."""
    return collections.Counter(row["file"] for row in document.get("entries") or [])


def _run_ids(document):
    """Every run id N counts: `--record-run`'s own list, union each
    entry's - the ledger only ever records a run that wrote a row."""
    entries = document.get("entries") or []
    return {str(r) for r in (document.get("runs") or [])} | {
        row.get("run_id") for row in entries if row.get("run_id") is not None
    }


#: Bonferroni across N runs - the Decision's own threshold.
FLAG_ALPHA = 0.05


def _tail_pmf(rates):
    """Poisson-binomial pmf over independent Bernoullis at `rates`, exact
    by DP - `44xN` steps, not Monte Carlo (the Decision's Route)."""
    pmf = [1.0]
    for p in rates:
        nxt = [0.0] * (len(pmf) + 1)
        for i, mass in enumerate(pmf):
            nxt[i] += mass * (1 - p)
            nxt[i + 1] += mass * p
        pmf = nxt
    return pmf


def per_run(document):
    """Runs that moved several files together, at once - a
    Poisson-binomial tail of each run's file count, against every
    file's own rate `count/N`, flagged when the tail is below
    `FLAG_ALPHA/N` (`UX-950`). `[(run_id, file_count, tail)]`, worst
    (smallest tail) first.
    """
    entries = document.get("entries") or []
    n = len(_run_ids(document))
    if not entries or not n:
        return []
    raw = _raw_counts(document)
    pmf = _tail_pmf([c / n for c in raw.values()])
    tails = [sum(pmf[k:]) for k in range(len(pmf))]
    by_run = collections.defaultdict(set)
    for row in entries:
        by_run[row.get("run_id")].add(row.get("file"))
    threshold = FLAG_ALPHA / n
    flagged = [
        (run_id, len(files), tails[len(files)]) for run_id, files in by_run.items() if tails[len(files)] < threshold
    ]
    return sorted(flagged, key=lambda row: row[2])


def counts(document):
    """`{file: excursion count}` - every ledger row counts, confirmed or
    not, except a row from a run `per_run` flags: that run counts once
    as a run event, not once per file (`UX-950`)."""
    flagged = {run_id for run_id, _k, _tail in per_run(document)}
    return collections.Counter(row["file"] for row in document.get("entries") or [] if row.get("run_id") not in flagged)


#: The header block a task's `**Flake:**` field must fall inside -
#: past this, a file name is prose, not a declaration.
HEADER_LINES = 8


def filed(name, scenarios=SCENARIOS):
    """Whether some task file's header declares this file in a
    `**Flake:**` field - a mention in prose, or of a longer path this
    name is merely a substring of, does not count. A field may name
    several files, whitespace- or comma-separated."""
    if not scenarios.is_dir():
        return False
    for task in scenarios.glob("*.md"):
        header = task.read_text(encoding="utf-8").splitlines()[:HEADER_LINES]
        for line in header:
            if not line.startswith("**Flake:**"):
                continue
            value = line[len("**Flake:**") :]
            if name in re.split(r"[\s,]+", value.strip()):
                return True
    return False


def unaccounted(document, scenarios=SCENARIOS):
    """Files at or past `EXCURSION_FLOOR` with no filed task or declared
    reason, worst first - `[(file, count)]`.

    `declared` is the ledger's own `{file: reason}` map, for an
    excursion that is not worth a task.
    """
    declared = document.get("declared") or {}
    found = [
        (name, n)
        for name, n in counts(document).items()
        if n >= EXCURSION_FLOOR and not declared.get(name) and not filed(name, scenarios)
    ]
    return sorted(found, key=lambda row: -row[1])


def top(document, n=3):
    """The ledger's `n` most-excursed files, for the round document's
    Standing."""
    return counts(document).most_common(n)


def record_run(run_id, path=LEDGER):
    """Add `run_id` to the ledger's `runs` list, deduped - a run that
    reaches the ledger step but writes no row still counts toward N."""
    document = load(path)
    run_id = str(run_id)
    runs = document.get("runs") or []
    if run_id not in {str(r) for r in runs}:
        runs.append(run_id)
        document["runs"] = runs
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"{run_id} recorded; {len(_run_ids(document))} run(s) known")
    return 0


def _report(document, top_n):
    """Standing, `per_run`'s reading beside it, then `unaccounted` -
    `main`'s default output, split out to keep `main` itself short."""
    for name, n in top(document, top_n):
        print(f"{name}  {n} excursion(s)")
    flagged = per_run(document)
    if flagged:
        print(f"\n{len(flagged)} run(s) moved several files together, at once (tail < {FLAG_ALPHA}/N):")
        for run_id, k, tail in flagged:
            print(f"  run {run_id}  {k} file(s)  tail={tail:.4g}")
    missing = unaccounted(document)
    if missing:
        print(
            f"\n{len(missing)} file(s) at or past {EXCURSION_FLOOR} excursions with no filed task or declared reason:",
            file=sys.stderr,
        )
        for name, n in missing:
            print(f"  {name}  {n} excursion(s)", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--top", type=int, default=3, help="print the ledger's N most-excursed files")
    parser.add_argument(
        "--record-run", metavar="RUN_ID", help="record this run id toward N, the runs per_run divides by (UX-950)"
    )
    args = parser.parse_args(argv)
    if args.record_run is not None:
        return record_run(args.record_run)
    return _report(load(), args.top)


if __name__ == "__main__":
    raise SystemExit(main())
