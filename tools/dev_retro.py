#!/usr/bin/env python3
"""UX-999: what bookkeeping cost this window, grouped by the command
that shows it - the input to a weekly `retro`.

    python tools/dev_retro.py
    python tools/dev_retro.py --since 2026-09-01

Reads only lines **added** since `--since` (`git log -p --since`, so a
line filed before the window is never counted) to three sources: the
bookkeeping ledger (`UX-998`, `docs/backlog/bookkeeping.md`), the
friction cell of every new `docs/audits/agent-runs.md` row, and the
`Class:`/`Guard:` fields of every task file whose Status turned green
in the window. `--since` defaults to the newest `docs/audits/retro-*.md`
date, else 7 days back.

Each finding's class is the first `tools/dev_*.py`, `tests/unit/
test_*.py` or `` `make <target>` `` token in its text; none of the
three is `unclassed`. A bookkeeping line edited in place (a status
change) carries the same `path`/`what` pair and is one finding, not
two. It prints; it proposes nothing and commits nothing - the `retro`
skill reads this and writes the proposal.
"""
import argparse
import collections
import datetime
import pathlib
import re

import dev_records

REPO = pathlib.Path(__file__).resolve().parents[1]
BOOKKEEPING = "docs/backlog/bookkeeping.md"
LEDGER = "docs/audits/agent-runs.md"
SCENARIOS = "docs/backlog/scenarios"

RETRO_DATE = re.compile(r"^retro-(\d{4}-\d{2}-\d{2})\.md$")
BOOKKEEPING_LINE = re.compile(
    r"^- r\d+ · [^·]+ · [^·]+ · `(?P<path>[^`]+)` · "
    r"(?P<what>[^·]+) · `[^`]+`\s*$")
TOKEN = re.compile(r"tools/dev_[\w]+\.py|tests/unit/test_[\w]+\.py|`make ([a-z][\w-]*)`")
STATUS_GREEN = re.compile(r"\*\*Status:\*\*\s*\U0001f7e2")
LABELS = ("Route", "Rejected", "Files", "Guard", "Mutation", "Class", "Split", "Question")
LABEL_LINE = re.compile(rf"^({'|'.join(LABELS)}):", re.M)


def default_since(repo, today=None):
    """The newest `retro-YYYY-MM-DD.md` date, else 7 days back."""
    today = today or datetime.date.today()
    audits = repo / "docs/audits"
    dates = sorted(m.group(1) for p in (audits.glob("retro-*.md") if audits.is_dir() else [])
                   if (m := RETRO_DATE.match(p.name)))
    return dates[-1] if dates else (today - datetime.timedelta(days=7)).isoformat()


def added_lines(repo, relpath, since):
    """`(iso_date, text)` per line a commit since `since` added to
    `relpath`, or `None` if the path does not exist at HEAD.

    `-C repo` rather than a `cwd=` kwarg: `dev_records._git` (`UX-997`)
    already carries the forced `S603` finding this call would otherwise
    duplicate under a new identity, and it fixes `cwd=REPO`.
    """
    if not (repo / relpath).exists():
        return None
    out = dev_records._git(
        "-C", str(repo), "log", "-p", "--since", since, "--date=short",
        "--pretty=format:@@retro@@%ad", "--", relpath, check=True).stdout
    date, found = None, []
    for line in out.splitlines():
        if line.startswith("@@retro@@"):
            date = line[len("@@retro@@"):]
        elif line.startswith("+") and not line.startswith("+++"):
            found.append((date, line[1:]))
    return found


def class_key(text):
    match = TOKEN.search(text)
    if not match:
        return None
    return f"make {match.group(1)}" if match.group(1) else match.group(0)


def bookkeeping_findings(added):
    """`(findings, weeks)` from `added_lines(repo, BOOKKEEPING, since)`:
    `findings` is `[(class_key_or_None, text)]`, one per distinct
    `path`/`what` pair - a status change re-adds the same pair and is
    not filed twice. `weeks` counts one distinct pair per ISO week of
    its first sighting."""
    seen, findings, weeks = set(), [], collections.Counter()
    for date, line in added:
        match = BOOKKEEPING_LINE.match(line)
        if not match:
            continue
        key = (match.group("path"), match.group("what"))
        if key in seen:
            continue
        seen.add(key)
        findings.append((class_key(line), line))
        if date:
            iso = datetime.date.fromisoformat(date).isocalendar()
            weeks[f"{iso[0]}-W{iso[1]:02d}"] += 1
    return findings, weeks


def ledger_findings(repo, since):
    added = added_lines(repo, LEDGER, since)
    if added is None:
        return []
    out = []
    for _date, line in added:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) != 9 or not cells[0].isdigit():
            continue
        out.append((class_key(cells[-1]), cells[-1]))
    return out


def decision_fields(text):
    decision = text.split("\n## Decision", 1)[1] if "\n## Decision" in text else ""
    spans = [(m.start(), m.group(1)) for m in LABEL_LINE.finditer(decision)]
    fields = {}
    for i, (start, label) in enumerate(spans):
        end = spans[i + 1][0] if i + 1 < len(spans) else len(decision)
        fields[label] = decision[start:end]
    return fields


def closed_findings(repo, since):
    """`Class:`/`Guard:` text of every task file whose Status line
    turned green in the window."""
    out = []
    scenarios = repo / SCENARIOS
    if not scenarios.is_dir():
        return out
    for path in sorted(scenarios.glob("UX-*.md")):
        added = added_lines(repo, str(path.relative_to(repo)), since)
        if not added or not any(STATUS_GREEN.search(line) for _d, line in added):
            continue
        fields = decision_fields(path.read_text(encoding="utf-8"))
        for label in ("Class", "Guard"):
            if label in fields:
                out.append((class_key(fields[label]), fields[label]))
    return out


def report(repo, since):
    ledger_added = added_lines(repo, BOOKKEEPING, since)
    bookkeeping, weeks = ((None, {}) if ledger_added is None
                          else bookkeeping_findings(ledger_added))
    findings = list(bookkeeping or []) + ledger_findings(repo, since) + closed_findings(repo, since)
    counts = collections.Counter(k for k, _t in findings if k)
    unclassed = sum(1 for k, _t in findings if k is None)
    lines = [f"since {since}: {len(findings)} finding(s)", "", "classes by count:"]
    if counts:
        for key, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"  {key:40s}{count:5d}")
    else:
        lines.append("  (none)")
    total = len(findings)
    share = unclassed / total if total else 0.0
    lines += ["", f"unclassed: {unclassed} of {total} ({share:.1%})", "",
             "bookkeeping lines per ISO week:"]
    if ledger_added is None:
        lines.append("  no ledger yet")
    elif not weeks:
        lines.append("  (none)")
    else:
        lines += [f"  {week}   {count}" for week, count in sorted(weeks.items())]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--since", help="YYYY-MM-DD; default the newest "
                        "retro document's date, else 7 days back")
    parser.add_argument("--repo", type=pathlib.Path, default=REPO,
                        help="repository root (tests point this at a scratch repo)")
    args = parser.parse_args(argv)
    since = args.since or default_since(args.repo)
    print(report(args.repo, since))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
