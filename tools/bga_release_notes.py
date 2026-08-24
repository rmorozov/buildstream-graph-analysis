"""UX-252: the release notes' body is generated from the closed rows.

Every closed backlog row already carries a one-line statement of what
was wrong and a summary of what shipped, written at the moment the work
was verified — which is the only moment anyone knows the detail. There
are 238 of them.

Hand-writing a release body would make a **third** copy of those facts,
after the task file's Outcome and the closed row. Two hand-maintained
copies of one fact drifting apart is this repository's most-repeated
defect by a wide margin; a third would be choosing to reproduce it
knowingly. So the body is generated and only the *head* is written —
the theme, the contract delta, and what a consumer has to do about it,
which is the half worth reading and the half no generator can produce.

Markers are **closed-row counts**, the same unit the release ledger and
`docs/audits/architecture-review.md` already use: `--from 238 --to 250`
emits the rows that closed between those two states. Counts rather than
dates because `closed.md` is append-ordered by when a row closed, and a
count is what both ledgers already record.

    bga release-notes --from 238 --to 250
"""
import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CLOSED = REPO / "docs/backlog/scenarios/closed.md"
SCENARIOS = REPO / "docs/backlog/scenarios"

# The order topics appear in a release body. A reader scanning for
# "what changed for me" wants the contract and CLI news first and the
# process news last; alphabetical would bury `contracts` under `cli`.
TOPIC_ORDER = ("contracts", "cli", "analysis", "capture", "viewer",
               "store", "guards", "docs")

_ID = re.compile(r"UX-(\d+)")
_TOPIC = re.compile(r"\*\*Topic:\*\*\s*(\w+)")


def _rows():
    """Every closed row, in file order — which is the order they closed."""
    rows = []
    for line in CLOSED.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| UX-"):
            continue
        cells = [cell.strip() for cell in
                 re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 6:
            continue
        rows.append({"id": cells[0], "summary": cells[1], "link": cells[5]})
    return rows


def _topic(item_id):
    """From the task file, which is where the style guide says it lives.

    A row whose file is gone, or whose header has no `Topic:`, is
    reported as `uncategorised` rather than dropped: a release note that
    silently omits an item is worse than one with an untidy heading.
    """
    number = _ID.match(item_id)
    if not number:
        return "uncategorised"
    for path in SCENARIOS.glob(f"UX-{int(number.group(1)):04d}-*.md"):
        found = _TOPIC.search(path.read_text(encoding="utf-8")[:2000])
        if found:
            return found.group(1)
    return "uncategorised"


def _first_sentence(text, limit=200):
    """The row's summary is a paragraph; a release body wants a line."""
    cut = re.split(r"(?<=[.;])\s", text, maxsplit=1)[0].strip()
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0] + "…"
    return cut


def render(start: int, end: int) -> str:
    """The generated half of one release's notes."""
    rows = _rows()
    if not 0 <= start <= end <= len(rows):
        raise ValueError(
            f"marker range {start}..{end} does not fit {len(rows)} closed "
            f"rows - markers are closed-row counts, not item numbers")
    window = rows[start:end]
    if not window:
        return "No scenarios closed between these markers.\n"

    grouped = {}
    for row in window:
        grouped.setdefault(_topic(row["id"]), []).append(row)

    ordered = ([topic for topic in TOPIC_ORDER if topic in grouped]
               + sorted(set(grouped) - set(TOPIC_ORDER)))
    lines = [f"{len(window)} scenarios closed "
             f"(closed-row markers {start} → {end}).", ""]
    for topic in ordered:
        lines.append(f"**{topic}**")
        lines.append("")
        for row in grouped[topic]:
            lines.append(f"- {row['link']} — {_first_sentence(row['summary'])}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bga release-notes",
        description="Generate a release's body from the closed backlog rows.")
    parser.add_argument("--from", dest="start", type=int, required=True,
                        help="Closed-row marker of the previous release.")
    parser.add_argument("--to", dest="end", type=int, default=None,
                        help="Closed-row marker of this release "
                             "(default: every row there is now).")
    args = parser.parse_args(argv)
    end = args.end if args.end is not None else len(_rows())
    try:
        sys.stdout.write(render(args.start, end))
    except ValueError as problem:
        parser.error(str(problem))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
