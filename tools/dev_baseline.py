"""UX-694: a finding baseline - zero-tolerance for a new finding.

    python3 tools/dev_baseline.py --write     # bootstrap, or full rewrite
                                                # (needs --force to add)
    python3 tools/dev_baseline.py --check      # make lint's line
    python3 tools/dev_baseline.py --shrink     # drop only what nothing
                                                # matches now

Runs ruff (json) for S, C901, PLR0912, PLR0913, PLR0915, SIM115 - not in
the gate's own `--select` (`pyproject.toml`) - over bga, tools,
.claude/hooks (never tests - `tests/**` is a different ledger). A
finding's identity is `(tool, rule, file, the source line's text with
interior whitespace collapsed, nth occurrence of that identity in the
file)`: never a line number, so a line inserted above, or a reformat of
one already flagged, does not move it out from under the baseline.
`tests/quality_baseline.json` holds the list, sorted, one entry per
line. `--write` refuses to add a new entry without `--force`; `--check`
also refuses an entry `git show HEAD:` doesn't carry, unstaged or not;
`--shrink` only ever removes what nothing matches any more. A file
ruff cannot parse aborts everything rather than risk reading its
absence as a fix.
"""
import argparse
import collections
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
FAMILIES = ("S", "C901", "PLR0912", "PLR0913", "PLR0915", "SIM115")
DEFAULT_PATHS = ("bga", "tools", ".claude/hooks")
DEFAULT_BASELINE = REPO / "tests" / "quality_baseline.json"


class RuffFailure(Exception):
    """ruff's answer cannot be trusted: a bad exit, or a file it could not parse."""


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
        raise RuffFailure(f"ruff exited {run.returncode}: {run.stderr.strip()}")
    raw = json.loads(run.stdout or "[]")
    # `invalid-syntax`: ruff reports the parse error and nothing else for
    # that file - a real finding already baselined there would read as
    # fixed, when the file is merely unreadable right now.
    unparsable = sorted({item["filename"] for item in raw
                          if item.get("code") == "invalid-syntax"})
    if unparsable:
        raise RuffFailure("ruff could not parse: " + ", ".join(unparsable))
    return raw


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
        text = (" ".join(text_lines[row - 1].split())
                if 0 < row <= len(text_lines) else "")
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


def write_baseline(path, findings, families, version, forced_by=None):
    findings = sorted(findings, key=sort_key)
    body = ",\n".join(f"    {json.dumps(f, sort_keys=True)}" for f in findings)
    forced = f'  "forced_by": {json.dumps(forced_by)},\n' if forced_by else ""
    text = ("{\n"
            f'  "ruff_version": {json.dumps(version)},\n'
            f'  "families": {json.dumps(sorted(set(families)))},\n'
            + forced
            + '  "findings": [\n' + (body + "\n" if body else "") + "  ]\n"
            "}\n")
    pathlib.Path(path).write_text(text, encoding="utf-8")


def diff(current, baseline):
    cur = {identity(f): f for f in current}
    base = {identity(f): f for f in baseline}
    new = [cur[k] for k in sorted(cur.keys() - base.keys())]
    stale = [base[k] for k in sorted(base.keys() - cur.keys())]
    return new, stale


def head_document(path):
    """The baseline `git show HEAD:<path>` carries, or `None` if that
    fails - no repo, no HEAD, or the path isn't tracked yet."""
    path = pathlib.Path(path).resolve()
    top = subprocess.run(["git", "-C", str(path.parent), "rev-parse",
                          "--show-toplevel"], capture_output=True,
                         text=True, check=False)
    if top.returncode != 0:
        return None
    toplevel = pathlib.Path(top.stdout.strip())
    rel = path.relative_to(toplevel).as_posix()
    show = subprocess.run(["git", "-C", str(toplevel), "show", f"HEAD:{rel}"],
                          capture_output=True, text=True, check=False)
    if show.returncode != 0:
        return None
    try:
        document = json.loads(show.stdout)
        document["findings"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    return document


def gained_since_head(path, working_findings, forced_by=None):
    """`UX-694`: the shrink guard - a line in `path` that `HEAD` never
    carried. A `--write --force --reason UX-NNN` is the one way there,
    and it authorises the gain until it lands: a `forced_by` HEAD does
    not carry yet."""
    head = head_document(path)
    if head is None:
        return []
    if forced_by and forced_by != head.get("forced_by"):
        return []
    carried = {identity(f) for f in head["findings"]}
    return [f for f in working_findings if identity(f) not in carried]


def do_write(args, current, existing):
    if args.force and not args.reason:
        print("--force needs --reason UX-NNN: the id that authorises adding "
              "a finding, written into the baseline's header")
        return 2
    if existing is not None and not args.force:
        new, _stale = diff(current, existing["findings"])
        if new:
            print(f"{len(new)} new finding(s) - rerun with --force to add, "
                  "or fix and use --shrink:")
            for f in new:
                print(f"  new: {describe(f)}")
            return 1
    write_baseline(args.baseline, current, FAMILIES, ruff_version(),
                   forced_by=args.reason if args.force else None)
    print(f"wrote {len(current)} finding(s) to {args.baseline}")
    return 0


def do_check(args, current, existing):
    if existing is None:
        print(f"no baseline at {args.baseline} - run --write first")
        return 1
    new, stale = diff(current, existing["findings"])
    gained = gained_since_head(args.baseline, existing["findings"],
                               existing.get("forced_by"))
    for f in new:
        print(f"new: {describe(f)}")
    for f in stale:
        print(f"stale: {describe(f)}")
    for f in gained:
        print(f"gained: {describe(f)} - only --write --force --reason "
              "UX-NNN may add a line")
    if not new and not stale and not gained:
        print(f"clean: {len(current)} finding(s) match {args.baseline}")
        return 0
    return 1


def do_shrink(args, current, existing):
    if existing is None:
        print(f"no baseline at {args.baseline} - run --write first")
        return 1
    new, stale = diff(current, existing["findings"])
    if stale:
        drop = {identity(f) for f in stale}
        kept = [f for f in existing["findings"] if identity(f) not in drop]
        write_baseline(args.baseline, kept, existing.get("families", FAMILIES),
                       existing.get("ruff_version", ruff_version()),
                       forced_by=existing.get("forced_by"))
        plural = "y" if len(stale) == 1 else "ies"
        print(f"removed {len(stale)} stale entr{plural}")
    else:
        print("nothing stale")
    if new:
        print(f"{len(new)} new finding(s) remain - shrink does not add:")
        for f in new:
            print(f"  new: {describe(f)}")
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--shrink", action="store_true")
    parser.add_argument("--force", action="store_true",
                         help="with --write, allow adding new entries")
    parser.add_argument("--reason", default=None,
                         help="with --force, the UX- id that authorises the add")
    parser.add_argument("--baseline", type=pathlib.Path, default=DEFAULT_BASELINE)
    parser.add_argument("--root", type=pathlib.Path, default=REPO)
    parser.add_argument("--paths", nargs="+", default=None)
    args = parser.parse_args(argv)
    if sum((args.write, args.check, args.shrink)) != 1:
        parser.error("exactly one of --write, --check, --shrink")

    paths = args.paths or list(DEFAULT_PATHS)
    try:
        raw = ruff_findings(args.root, paths, FAMILIES)
    except RuffFailure as exc:
        print(f"error: {exc}")
        return 2
    current = normalize(raw, args.root)
    existing = load_baseline(args.baseline)

    if args.write:
        return do_write(args, current, existing)
    if args.shrink:
        return do_shrink(args, current, existing)
    return do_check(args, current, existing)


if __name__ == "__main__":
    sys.exit(main())
