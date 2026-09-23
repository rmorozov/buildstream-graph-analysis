"""UX-998: a bookkeeping finding is one line, not a task file.

    python3 tools/dev_bookkeeping.py --add PATH WHAT COMMAND \
        --class CLASS --round N [--new-class]
    python3 tools/dev_bookkeeping.py --sweep
    python3 tools/dev_bookkeeping.py --mark KEY --status swept|promoted|dropped|open \
        --round N [--ux UX-NNN] [--reason TEXT]

One line in `docs/backlog/bookkeeping.md` per drift: filed round,
status, class, where, what, and the command that shows it. `--add`
writes a line; `--sweep` lists the open ones, oldest first, with the
sweeps each has survived; `--mark` resolves one. A key is never
written - `sha1("<path> · <what>")[:7]` derives it, so two lines
naming the same drift collide by construction. Every write is
transactional: the candidate text is validated first, and a write
that would leave an open line past `SWEEP_LIMIT` sweeps, name an
unknown class, duplicate a key, or point an open line at a path that
does not exist is refused rather than made.
"""
import argparse
import collections
import hashlib
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "backlog" / "bookkeeping.md"
SCENARIOS = REPO / "docs" / "backlog" / "scenarios"

#: No open line survives a fourth sweep unresolved - it is promoted or
#: dropped by then. Mutated 3 -> 4 in the `falsify` pass.
SWEEP_LIMIT = 3

CLASS_RE = re.compile(r"^[a-z][a-z0-9-]*$")

#: The one line format. The trailing `` `(?P<command>[^`]+)` `` clause is
#: the mutation target: loosened to `(.+)$` it accepts a command with no
#: backticks and the format clause stops catching that shape.
LINE_RE = re.compile(
    r"^- r(?P<filed>\d+) · (?P<status>open|swept r\d+ UX-\d+|"
    r"promoted r\d+ UX-\d+|dropped r\d+ [^`·]+) · "
    r"(?P<cls>[a-z][a-z0-9-]*) · `(?P<path>[^`]+)` · "
    r"(?P<what>[^`·]+) · `(?P<command>[^`]+)`$"
)

STATUS_ROUND_RE = re.compile(r"^(?:swept|promoted|dropped) r(\d+)\b")
PROMOTED_RE = re.compile(r"^promoted r\d+ UX-(\d+)$")

Entry = collections.namedtuple(
    "Entry", "lineno filed status cls path what command")

#: `--add` and `--mark` each take more inputs than a five-argument cap
#: allows named separately, so the where/what/how three and the two
#: paths each collapse into one argument.
Finding = collections.namedtuple("Finding", "path what command")
Paths = collections.namedtuple("Paths", "ledger repo_root")
DEFAULT_PATHS = Paths(LEDGER, REPO)


def derive_key(path, what):
    #: not a security hash - a short, stable id for one ledger line.
    return hashlib.sha1(f"{path} · {what}".encode(),
                        usedforsecurity=False).hexdigest()[:7]


def parse_entries(text):
    entries, problems = [], []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("- "):
            continue
        match = LINE_RE.match(line)
        if not match:
            problems.append(f"line {lineno}: malformed entry: {line!r}")
            continue
        fields = match.groupdict()
        entries.append(Entry(lineno, int(fields["filed"]), fields["status"],
                              fields["cls"], fields["path"], fields["what"],
                              fields["command"]))
    return entries, problems


def sweep_rounds(entries):
    """Every round a sweep touched *some* line, read off the whole
    ledger's own resolutions - a sweep is a batch, so any resolution at
    round N is proof one happened then. No separate counter is kept."""
    rounds = set()
    for entry in entries:
        match = STATUS_ROUND_RE.match(entry.status)
        if match:
            rounds.add(int(match.group(1)))
    return rounds


def sweeps_survived(entry, rounds):
    return sum(1 for n in rounds if n > entry.filed)


def validate(text, repo_root=REPO):
    entries, problems = parse_entries(text)
    rounds = sweep_rounds(entries)
    seen = {}
    for entry in entries:
        key = derive_key(entry.path, entry.what)
        if key in seen:
            problems.append(
                f"line {entry.lineno}: key {key} duplicates line {seen[key]}")
        else:
            seen[key] = entry.lineno
        if entry.status == "open":
            path = entry.path.split(":", 1)[0]
            if not (repo_root / path).exists():
                problems.append(
                    f"line {entry.lineno}: open line's path does not exist: {path}")
            if sweeps_survived(entry, rounds) >= SWEEP_LIMIT:
                problems.append(
                    f"line {entry.lineno}: open past {SWEEP_LIMIT} sweeps")
        promoted = PROMOTED_RE.match(entry.status)
        if promoted:
            uid = int(promoted.group(1))
            if not list(
                (repo_root / "docs/backlog/scenarios").glob(f"UX-{uid:04d}-*.md")
            ):
                problems.append(
                    f"line {entry.lineno}: promoted names UX-{uid}, no task file")
    return problems


def add(finding, cls, round_no, paths=DEFAULT_PATHS, new_class=False):
    ledger, repo_root = paths
    text = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    entries, problems = parse_entries(text)
    if problems:
        raise ValueError("ledger already malformed:\n" + "\n".join(problems))
    if not CLASS_RE.match(cls):
        raise ValueError(f"bad class {cls!r}: must match {CLASS_RE.pattern}")
    if cls not in {e.cls for e in entries} and not new_class:
        raise ValueError(f"unknown class {cls!r}; pass --new-class to add it")
    line = (f"- r{round_no} · open · {cls} · `{finding.path}` · "
           f"{finding.what} · `{finding.command}`")
    new_text = (text if text.endswith("\n") or not text else text + "\n") + line + "\n"
    problems = validate(new_text, repo_root=repo_root)
    if problems:
        raise ValueError("refused:\n" + "\n".join(problems))
    ledger.write_text(new_text, encoding="utf-8")
    return line


def sweep(paths=DEFAULT_PATHS):
    entries, problems = parse_entries(paths.ledger.read_text(encoding="utf-8"))
    if problems:
        raise ValueError("\n".join(problems))
    rounds = sweep_rounds(entries)
    open_entries = sorted((e for e in entries if e.status == "open"),
                           key=lambda e: e.filed)
    return [(e, sweeps_survived(e, rounds)) for e in open_entries]


def mark(key, status, round_no, detail=None, paths=DEFAULT_PATHS):
    """`detail` is the resolving `UX-<id>` for `swept`/`promoted`, or the
    reason text for `dropped` - the two mutually exclusive extra fields
    a status can carry, collapsed into the fifth argument."""
    ledger, repo_root = paths
    text = ledger.read_text(encoding="utf-8")
    entries, problems = parse_entries(text)
    if problems:
        raise ValueError("ledger already malformed:\n" + "\n".join(problems))
    target = next((e for e in entries if derive_key(e.path, e.what) == key), None)
    if target is None:
        raise ValueError(f"no entry with key {key}")
    if status in ("swept", "promoted"):
        if not detail:
            raise ValueError(f"a resolving UX-id is required for {status}")
        new_status = f"{status} r{round_no} {detail}"
    elif status == "dropped":
        if not detail:
            raise ValueError("a reason is required for dropped")
        new_status = f"dropped r{round_no} {detail}"
    elif status == "open":
        new_status = "open"
    else:
        raise ValueError(f"unknown status {status!r}")
    rebuilt = (f"- r{target.filed} · {new_status} · {target.cls} · "
              f"`{target.path}` · {target.what} · `{target.command}`")
    lines = text.splitlines()
    lines[target.lineno - 1] = rebuilt
    new_text = "\n".join(lines) + "\n"
    problems = validate(new_text, repo_root=repo_root)
    if problems:
        raise ValueError("refused:\n" + "\n".join(problems))
    ledger.write_text(new_text, encoding="utf-8")
    return rebuilt


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", nargs=3, metavar=("PATH", "WHAT", "COMMAND"))
    group.add_argument("--sweep", action="store_true")
    group.add_argument("--mark", metavar="KEY")
    parser.add_argument("--class", dest="cls")
    parser.add_argument("--new-class", action="store_true")
    parser.add_argument("--round", type=int)
    parser.add_argument("--status", choices=("swept", "promoted", "dropped", "open"))
    parser.add_argument("--ux")
    parser.add_argument("--reason")
    args = parser.parse_args(argv)

    try:
        if args.add is not None:
            if args.round is None or not args.cls:
                parser.error("--add needs --class and --round")
            path, what, command = args.add
            print(add(Finding(path, what, command), args.cls, args.round,
                      new_class=args.new_class))
        elif args.sweep:
            for entry, n in sweep():
                print(f"r{entry.filed} · {n} sweep(s) · {entry.cls} · "
                      f"{entry.path} · {entry.what}")
        else:
            if args.round is None or not args.status:
                parser.error("--mark needs --status and --round")
            print(mark(args.mark, args.status, args.round,
                       detail=args.ux or args.reason))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
