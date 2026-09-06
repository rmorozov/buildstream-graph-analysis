"""`UX-702`: `bga analyze`'s own wall clock and peak RSS, held to CI's
own past reading rather than to a ratio.

    python3 tools/dev_perf_ratchet.py --merge CANDIDATE LOG [LOG ...]
    python3 tools/dev_perf_ratchet.py --against tests/ci_reference.json \\
        --carry PATH --base REF LOG [LOG ...]

`UX-531` measured `bga analyze` superlinear; nothing recorded whether a
later round moves it. `UX-420`'s three failures rule out comparing one
CI runner's clock to anything but its own past reading, so this reads
`tests/ci_reference.json`'s `analyze_wall_s`/`analyze_rss_mb` - carried
in beside the tier rows by `dev_tier_drift.adopt` - against **two
consecutive runs**' `/usr/bin/time -v` logs on the largest fixture
(`tests/pages.xl_run`, 4,002 elements), by an absolute margin (seconds,
MB - never a ratio, `UX-420`'s Motivation), and only when the branch's
diff touched `bga/analyzer.py`.

Never run inside `make test`: the reading is CI's own clock, and no
number taken on another machine compares with it (Out of Scope).
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import dev_touching

ANALYZER_FILE = "bga/analyzer.py"

#: Stated starting values, not measurements - there is no CI-to-CI
#: reading of this fixture yet to size them from, the same state
#: `UX-420`'s `CI_DRIFT_FACTOR` started in. A local orientation reading,
#: which does not compare with CI's (Out of Scope): 4,002 elements,
#: `bga analyze` 11.5s/718 MB, `bga view --export` (cold) 12.9s/721 MB.
ANALYZE_WALL_MARGIN_S = 5.0
ANALYZE_RSS_MARGIN_MB = 50.0

_WALL_RE = re.compile(
    r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([\d:.]+)")
_RSS_RE = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")


def parse_time_v(text):
    """`(wall_s, rss_mb)` from one `/usr/bin/time -v` report.

    Raises on text that is not one, rather than returning a misleading
    zero - the mistake `tests/ci_reference.json`'s own shape has
    already caught a probe making (`CLAUDE.md`).
    """
    wall, rss = _WALL_RE.search(text), _RSS_RE.search(text)
    if not wall or not rss:
        raise ValueError(f"not a /usr/bin/time -v report: {text[:200]!r}")
    seconds = 0.0
    for part in wall.group(1).split(":"):
        seconds = seconds * 60 + float(part)
    return seconds, int(rss.group(1)) / 1024


def measured(paths):
    """The worse of however many `/usr/bin/time -v` logs are given.

    The Required Fix names two commands, `bga analyze` and `bga view
    --export`; each is its own cold path into the analyzer - a
    published `analyze.json` makes `view` skip it - so both are
    measured and the higher of the two on each axis is judged: a
    regression reachable through either command must be caught by one
    reading rather than by remembering to check two.
    """
    wall = rss = 0.0
    for path in paths:
        one_wall, one_rss = parse_time_v(
            pathlib.Path(path).read_text(encoding="utf-8"))
        wall, rss = max(wall, one_wall), max(rss, one_rss)
    return {"analyze_wall_s": round(wall, 2), "analyze_rss_mb": round(rss, 1)}


def merge(candidate_path, readings, source):
    """Beside the tier rows: fold `readings` into the candidate
    `dev_tier_drift.py --record` already wrote at `candidate_path`, so
    the one artifact and the one `--adopt` job that already exist carry
    both (`UX-503`'s shape, not a second job)."""
    document = (json.loads(candidate_path.read_text(encoding="utf-8"))
                if candidate_path.is_file() else {"measured_on": source})
    document.update(readings)
    candidate_path.write_text(json.dumps(document, indent=2) + "\n",
                              encoding="utf-8")
    return document


def touches_analyzer(base):
    """Whether the branch's diff could plausibly have moved the
    analyzer's cost. `None` where it cannot be read - no base, or an
    unresolved one - and read by the caller as "report anyway": the
    same choice `dev_tier_drift.explained_by` makes, because a broken
    fetch must not silence the gate.
    """
    if not base:
        return None
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
        capture_output=True, text=True, cwd=REPO)
    if resolved.returncode != 0:
        return None
    return ANALYZER_FILE in dev_touching.changed_files(base=base)


def exceeded(times, reference):
    """`(wall_over, rss_over)` for this run alone, against an absolute
    margin. `None` for either axis the reference does not carry yet -
    the run that meets an unrecorded key has nothing to be slower than
    (`UX-503`'s shape, on a scalar instead of a file)."""
    wall_over = rss_over = None
    if "analyze_wall_s" in reference and "analyze_wall_s" in times:
        wall_over = (times["analyze_wall_s"] - reference["analyze_wall_s"]
                    >= ANALYZE_WALL_MARGIN_S)
    if "analyze_rss_mb" in reference and "analyze_rss_mb" in times:
        rss_over = (times["analyze_rss_mb"] - reference["analyze_rss_mb"]
                   >= ANALYZE_RSS_MARGIN_MB)
    return wall_over, rss_over


def confirmed(wall_over, rss_over, history):
    """`UX-442`'s rule, on two quantities instead of one: neither
    reports off one sample - the run behind this one on the same
    branch must have exceeded the same margin too."""
    before = history or {}
    return (bool(wall_over) and bool(before.get("wall")),
            bool(rss_over) and bool(before.get("rss")))


def carried(path):
    """The previous run's verdict on this branch, or `{}` for none -
    absent, unreadable, or a cache that did not restore."""
    try:
        held = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return held.get("exceeded") or {}


def carry(path, wall_over, rss_over, source):
    """Write what this run found, for the next run on this branch to
    agree or disagree with (`UX-442`)."""
    pathlib.Path(path).write_text(json.dumps(
        {"exceeded": {"wall": bool(wall_over), "rss": bool(rss_over)},
         "measured_on": source}, indent=2) + "\n", encoding="utf-8")


def _done(code, message, args):
    if args.summary:
        pathlib.Path(args.summary).write_text(message + "\n",
                                              encoding="utf-8")
    if args.annotate and code:
        from tools.dev_tier_drift import annotation
        print(annotation(message, path=args.against or "unknown",
                         title="analyzer gate"))
    return code


def _against(readings, args):
    """`--against`: this run's reading, checked against `args.against`'s
    own record. Split out of `main` so each rule reads as one clause -
    unrecorded, not confirmed yet, confirmed but no cause, confirmed and
    caused - rather than one function carrying all four."""
    ref_path = pathlib.Path(args.against)
    reference = (json.loads(ref_path.read_text(encoding="utf-8"))
                if ref_path.is_file() else {})
    wall_over, rss_over = exceeded(readings, reference)
    if wall_over is None and rss_over is None:
        message = (f"{ref_path} holds no analyze_wall_s/analyze_rss_mb yet, "
                   f"so nothing is being checked (UX-702). Merge this run's "
                   f"reading and let the adopt job carry it in.")
        print(message, file=sys.stderr)
        return _done(0, message, args)

    history = carried(args.carry) if args.carry else {}
    wall_confirmed, rss_confirmed = confirmed(wall_over, rss_over, history)
    if args.carry:
        carry(args.carry, wall_over, rss_over, args.source)

    reading_line = (f"analyze+export: {readings['analyze_wall_s']}s "
                    f"(recorded {reference.get('analyze_wall_s')}s, margin "
                    f"{ANALYZE_WALL_MARGIN_S:g}s), "
                    f"{readings['analyze_rss_mb']} MB (recorded "
                    f"{reference.get('analyze_rss_mb')} MB, margin "
                    f"{ANALYZE_RSS_MARGIN_MB:g} MB)")
    if not (wall_confirmed or rss_confirmed):
        message = f"{reading_line} - within margin, or not confirmed yet."
        print(message)
        return _done(0, message, args)

    if touches_analyzer(args.base) is False:
        message = (f"{reading_line} - two consecutive runs over margin, but "
                   f"the diff against {args.base} does not touch "
                   f"{ANALYZER_FILE}, so nothing is being failed on it "
                   f"(UX-702's own scope).")
        print(message, file=sys.stderr)
        return _done(0, message, args)

    message = (f"{ANALYZER_FILE} changed and {reading_line} - two "
              f"consecutive runs over margin.")
    print(message, file=sys.stderr)
    return _done(1, message, args)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logs", nargs="*",
                        help="/usr/bin/time -v report(s) for this run")
    parser.add_argument("--merge", metavar="CANDIDATE",
                        help="fold this run's reading into the tier "
                             "candidate at PATH, for --adopt to carry")
    parser.add_argument("--against", metavar="REFERENCE",
                        help="tests/ci_reference.json - check this run "
                             "against its analyze_wall_s/analyze_rss_mb")
    parser.add_argument("--carry", metavar="PATH", default=None)
    parser.add_argument("--base", metavar="REF", default=None)
    parser.add_argument("--source", default="unknown")
    parser.add_argument("--summary", metavar="PATH", default=None)
    parser.add_argument("--annotate", action="store_true",
                        help="on a red run, print a check-run annotation "
                             "(UX-621's route - a job's own API entry "
                             "carries no output field)")
    args = parser.parse_args(argv)

    if not args.logs:
        parser.error("at least one /usr/bin/time -v log is required")
    readings = measured(args.logs)

    if args.merge:
        merge(pathlib.Path(args.merge), readings, args.source)
        print(f"{args.merge}: analyze_wall_s={readings['analyze_wall_s']}, "
              f"analyze_rss_mb={readings['analyze_rss_mb']}")
    if not args.against:
        return 0
    return _against(readings, args)


if __name__ == "__main__":
    sys.exit(main())
