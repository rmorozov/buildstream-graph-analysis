"""UX-694: a finding baseline - zero-tolerance for a new finding.

    python3 tools/dev_baseline.py --write     # bootstrap, or full rewrite
                                                # (needs --force to add)
    python3 tools/dev_baseline.py --check      # make lint's line
    python3 tools/dev_baseline.py --shrink     # drop only what nothing
                                                # matches now

Runs ruff (json) for S, C901, PLR0912, PLR0913, PLR0915, SIM115 - not in
the gate's own `--select` (`pyproject.toml`) - over bga, tools, tests,
.claude/hooks. A finding's identity is `(tool, rule, file, the source
line's text stripped, nth occurrence of that identity in the file)`:
never a line number, so a line inserted above one does not move it out
from under the baseline. `tests/quality_baseline.json` holds the list,
sorted, one entry per line. `--write` refuses to add a new entry
without `--force`; `--shrink` only ever removes what nothing matches
any more.
"""
import argparse
import collections
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
FAMILIES = ("S", "C901", "PLR0912", "PLR0913", "PLR0915", "SIM115")
DEFAULT_PATHS = ("bga", "tools", "tests", ".claude/hooks")
DEFAULT_BASELINE = REPO / "tests" / "quality_baseline.json"


def ruff_version():
    out = subprocess.run(["ruff", "--version"], stdout=subprocess.PIPE,
                          text=True, check=True).stdout
    return out.strip().split()[-1]


def ruff_findings(root, paths, families):
    cmd = ["ruff", "check", *[str(p) for p in paths],
           "--select", ",".join(sorted(families)),
           "--output-format", "json"]
    run = subprocess.run(cmd, cwd=root, capture_output=True,
                          text=True, check=False)
    if run.returncode not in (0, 1):
        raise SystemExit(f"ruff failed: {run.stderr}")
    return json.loads(run.stdout or "[]")


def normalize(raw, root):
    """`raw` ruff findings -> the identity list, ordered and nth-assigned."""
    root = pathlib.Path(root).resolve()
    lines_of = {}
    decorated = []
    for item in raw:
        rule = item.get("code")
        if not rule:
            continue
        path = pathlib.Path(item["filename"])
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        row = item["location"]["row"]
        if path not in lines_of:
            lines_of[path] = path.read_text(
                encoding="utf-8", errors="replace").splitlines()
        text_lines = lines_of[path]
        text = text_lines[row - 1].strip() if 0 < row <= len(text_lines) else ""
        decorated.append((rel, row, rule, text))
    decorated.sort(key=lambda t: (t[0], t[1]))
    counts = collections.Counter()
    findings = []
    for file, _row, rule, text in decorated:
        key = (rule, file, text)
        counts[key] += 1
        findings.append({"tool": "ruff", "rule": rule, "file": file,
                          "line": text, "nth": counts[key]})
    return findings


def identity(entry):
    return (entry["tool"], entry["rule"], entry["file"], entry["line"], entry["nth"])


def describe(entry):
    return (f"{entry['tool']} {entry['rule']} {entry['file']} "
            f"(#{entry['nth']}) {entry['line']}")


def sort_key(entry):
    return (entry["file"], entry["rule"], entry["nth"], entry["line"])


def load_baseline(path):
    path = pathlib.Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(path, findings, families, version):
    findings = sorted(findings, key=sort_key)
    body = ",\n".join(f"    {json.dumps(f, sort_keys=True)}" for f in findings)
    text = ("{\n"
            f'  "ruff_version": {json.dumps(version)},\n'
            f'  "families": {json.dumps(sorted(set(families)))},\n'
            '  "findings": [\n' + (body + "\n" if body else "") + "  ]\n"
            "}\n")
    pathlib.Path(path).write_text(text, encoding="utf-8")


def diff(current, baseline):
    cur = {identity(f): f for f in current}
    base = {identity(f): f for f in baseline}
    new = [cur[k] for k in sorted(cur.keys() - base.keys())]
    stale = [base[k] for k in sorted(base.keys() - cur.keys())]
    return new, stale


def do_write(args, current, existing):
    if existing is not None and not args.force:
        new, _stale = diff(current, existing["findings"])
        if new:
            print(f"{len(new)} new finding(s) - rerun with --force to add, "
                  "or fix and use --shrink:")
            for f in new:
                print(f"  new: {describe(f)}")
            return 1
    write_baseline(args.baseline, current, FAMILIES, ruff_version())
    print(f"wrote {len(current)} finding(s) to {args.baseline}")
    return 0


def do_check(args, current, existing):
    if existing is None:
        print(f"no baseline at {args.baseline} - run --write first")
        return 1
    new, stale = diff(current, existing["findings"])
    for f in new:
        print(f"new: {describe(f)}")
    for f in stale:
        print(f"stale: {describe(f)}")
    if not new and not stale:
        print(f"clean: {len(current)} finding(s) match {args.baseline}")
        return 0
    return 1


def do_shrink(args, current, existing):
    if existing is None:
        print(f"no baseline at {args.baseline} - run --write first")
        return 1
    _new, stale = diff(current, existing["findings"])
    if not stale:
        print("nothing stale")
        return 0
    drop = {identity(f) for f in stale}
    kept = [f for f in existing["findings"] if identity(f) not in drop]
    write_baseline(args.baseline, kept, existing.get("families", FAMILIES),
                   existing.get("ruff_version", ruff_version()))
    plural = "y" if len(stale) == 1 else "ies"
    print(f"removed {len(stale)} stale entr{plural}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--shrink", action="store_true")
    parser.add_argument("--force", action="store_true",
                         help="with --write, allow adding new entries")
    parser.add_argument("--baseline", type=pathlib.Path, default=DEFAULT_BASELINE)
    parser.add_argument("--root", type=pathlib.Path, default=REPO)
    parser.add_argument("--paths", nargs="+", default=None)
    args = parser.parse_args(argv)
    if sum((args.write, args.check, args.shrink)) != 1:
        parser.error("exactly one of --write, --check, --shrink")

    paths = args.paths or list(DEFAULT_PATHS)
    raw = ruff_findings(args.root, paths, FAMILIES)
    current = normalize(raw, args.root)
    existing = load_baseline(args.baseline)

    if args.write:
        return do_write(args, current, existing)
    if args.shrink:
        return do_shrink(args, current, existing)
    return do_check(args, current, existing)


if __name__ == "__main__":
    sys.exit(main())
