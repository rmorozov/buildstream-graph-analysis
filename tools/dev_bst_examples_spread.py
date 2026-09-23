#!/usr/bin/env python3
"""UX-941: `bst-examples`' wall clock as a spread, and its exact figures as notices.

The job writes no record of its own clock, so the one reading is the
jobs API's `completed_at - started_at` - one run of each sha, never N
runs of one. `--fetch` stores those readings in `DATA`; the default
prints the spread; `--write` puts it in the paragraph beside the job,
which `test_the_examples_clock_is_a_spread.py` holds to `DATA`.

Below `MIN_RUNS` readings no median is printed: a population of one is
the condition this row names (`UX-895`'s three repeats per arm).

`--notices` is the other half: figures exact at n=1, one `::notice::`
line each, which a session reads back from the check run's annotations.
"""
import argparse
import ast
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
DATA = REPO / "tests" / "bst_examples_clock.json"
CI = REPO / ".github" / "workflows" / "ci.yml"
JOB = "bst-examples"
WORKFLOW = "ci.yml"
API = "https://api.github.com/repos/"
MIN_RUNS = 3

#: The paragraph's one derived line in `ci.yml`; `--write` rewrites it.
FIGURE_LINE = re.compile(r"^(\s*#\s+clock: ).*$", re.MULTILINE)

#: The staged toolchain `examples/stage_cpp_toolchain.sh` builds 05 on.
TOOLCHAIN = "examples/05-cmake-cpp-toolchain/files/toolchain"

#: Every analyze report the job writes as JSON, under `artifacts/`.
#: Fixed rather than globbed, so a report the job failed to write is a
#: notice saying so rather than a missing line.
REPORTS = (
    "01-resource-contention/report.json",
    "02-deep-chain-mixed-kinds/report.json",
    "03-project-refs-identity/report-v1.json",
    "03-project-refs-identity/report-v2.json",
    "06-macro-micro-optimization/report-baseline.json",
    "06-macro-micro-optimization/report-optimized.json",
)

NOTICE_TITLE = "UX-941 structural"


class TooFewRuns(ValueError):
    pass


def load(path=None) -> dict:
    with open(path or DATA, encoding="utf-8") as handle:
        return json.load(handle)


def spread(seconds) -> dict:
    """Median, range and max/min over the readings; refuses a population
    smaller than `MIN_RUNS` rather than calling one reading a median."""
    values = sorted(int(s) for s in seconds)
    if len(values) < MIN_RUNS:
        raise TooFewRuns(
            f"{len(values)} run(s) of {JOB}: fewer than {MIN_RUNS}, so no "
            f"median - one run of each sha is not a population")
    mid = len(values) // 2
    twice_median = (values[mid] * 2 if len(values) % 2
                    else values[mid - 1] + values[mid])
    return {"runs": len(values), "twice_median": twice_median,
            "min": values[0], "max": values[-1]}


def figure(got: dict, measured: str) -> str:
    half = got["twice_median"] // 2
    median = f"{half}.5" if got["twice_median"] % 2 else f"{half}"
    ratio = f"{got['max'] / got['min']:.2f}"
    return (f"{got['runs']} runs of main, median {median}s, "
            f"{got['min']}-{got['max']}s, max/min {ratio}, read {measured}")


def range_token(got: dict) -> str:
    """What a sentence pricing the job in seconds must carry."""
    return f"{got['min']}-{got['max']}s"


def current(path=None) -> tuple[dict, str]:
    data = load(path)
    return spread(r["seconds"] for r in data["runs"]), data["measured"]


def drift_factor() -> float:
    """`dev_tier_drift.CI_DRIFT_FACTOR`, read without importing it: that
    module needs `defusedxml`, which the job running `--notices` lacks."""
    tree = ast.parse((REPO / "tools" / "dev_tier_drift.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and getattr(node.targets[0], "id", None) == "CI_DRIFT_FACTOR"):
            return ast.literal_eval(node.value)
    raise LookupError("CI_DRIFT_FACTOR is not assigned in dev_tier_drift.py")


def write_figure(text: str, line: str) -> str:
    return FIGURE_LINE.sub(lambda m: m.group(1) + line, text, count=1)


def _get(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _seconds(started: str, completed: str) -> int:
    parse = datetime.datetime.fromisoformat
    return int((parse(completed.replace("Z", "+00:00"))
                - parse(started.replace("Z", "+00:00"))).total_seconds())


def fetch(repo: str, token: str, since: str, limit: int) -> list[dict]:
    """The job's successful runs on main pushes created on or after
    `since`, newest first, at most `limit`."""
    rows, page = [], 1
    while len(rows) < limit:
        runs = _get(f"{API}{repo}/actions/workflows/{WORKFLOW}/runs?branch=main"
                    f"&event=push&status=completed&per_page=100&page={page}",
                    token)["workflow_runs"]
        if not runs:
            break
        for run in runs:
            if run["created_at"][:10] < since or len(rows) >= limit:
                return rows
            jobs = _get(f"{API}{repo}/actions/runs/{run['id']}/jobs?per_page=100",
                        token)["jobs"]
            for job in jobs:
                if job["name"] == JOB and job["conclusion"] == "success":
                    rows.append({
                        "run_id": run["id"], "head_sha": run["head_sha"][:8],
                        "started_at": job["started_at"],
                        "completed_at": job["completed_at"],
                        "seconds": _seconds(job["started_at"], job["completed_at"])})
        page += 1
    return rows


def notices(artifacts: str, toolchain: str) -> list[str]:
    """One `::notice::` line per exact figure the job already computed.
    A figure whose input is missing says `absent`, never nothing."""
    sys.path.insert(0, str(REPO))
    from tools import nix_closure
    lines = []
    if os.path.isdir(toolchain + nix_closure.STORE):
        staged = str(len(nix_closure.staged_hashes(toolchain)))
    else:
        staged = "absent"
    lines.append(f"examples/05 toolchain: {staged} store paths staged "
                 f"(nix_closure.staged_hashes)")
    for name in REPORTS:
        path = os.path.join(artifacts, name)
        try:
            with open(path, encoding="utf-8") as handle:
                count = str(int(json.load(handle)["graph_metrics"]["num_elements"]))
        except (OSError, ValueError, KeyError, TypeError):
            count = "absent"
        lines.append(f"examples/{name}: {count} elements "
                     f"(graph_metrics.num_elements)")
    return [f"::notice title={NOTICE_TITLE}::{line}" for line in lines]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--fetch", action="store_true",
                        help="read the jobs API into DATA (needs GITHUB_TOKEN)")
    parser.add_argument("--repo", default="rmorozov/buildstream-graph-analysis")
    parser.add_argument("--since", default=None,
                        help="first day of the population, YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--write", action="store_true",
                        help="rewrite the figure line in ci.yml")
    parser.add_argument("--notices", nargs=2, metavar=("ARTIFACTS", "TOOLCHAIN"),
                        help="print the structural figures as ::notice:: lines")
    args = parser.parse_args(argv)

    if args.notices:
        print("\n".join(notices(*args.notices)))
        return 0
    if args.fetch:
        since = args.since or load()["since"]
        rows = fetch(args.repo, os.environ["GITHUB_TOKEN"], since, args.limit)
        today = datetime.date.today().isoformat()
        DATA.write_text(json.dumps({
            "measured": today, "since": since, "repo": args.repo,
            "command": "python3 tools/dev_bst_examples_spread.py --fetch "
                       f"--since {since} --limit {args.limit}",
            "runs": rows}, indent=1) + "\n", encoding="utf-8")
    try:
        got, measured = current()
    except TooFewRuns as refused:
        print(f"dev_bst_examples_spread: {refused}", file=sys.stderr)
        return 1
    if args.write:
        CI.write_text(write_figure(CI.read_text(encoding="utf-8"),
                                   figure(got, measured)), encoding="utf-8")
    print(f"{figure(got, measured)}  (CI_DRIFT_FACTOR {drift_factor()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
