"""UX-252: the release notes' body is generated from the closed rows.

A hand-written body would be a third copy of facts the task file's Outcome
and the closed row already hold, so only the head is written.

Markers are closed-row counts, the unit the release ledger uses:

    bga release-notes --from 238 --to 250
"""

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dev_close_task

REPO = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "docs/backlog/scenarios"

# The order topics appear in a release body. A reader scanning for
# "what changed for me" wants the contract and CLI news first and the
# process news last; alphabetical would bury `contracts` under `cli`.
TOPIC_ORDER = ("contracts", "cli", "analysis", "capture", "viewer", "store", "guards", "docs")

_ID = re.compile(r"UX-(\d+)")
_TOPIC = re.compile(r"\*\*Topic:\*\*\s*(\w+)")


#: closed.md links are relative to docs/backlog/scenarios/; the body lands at the root.
_REL_LINK = re.compile(r"\]\((?![a-z]+:|/|#|docs/)")


def _rows():
    """Every closed row, in file order — which is the order they closed."""
    rows = []
    for line in dev_close_task.closed_rows():
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
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


_LINKED = re.compile(r"\[(?P<text>.*)\]\((?P<url>[^)]*)\)")


def _first_sentence(text, limit=200):
    """The row's summary is a paragraph; a release body wants a line."""
    linked = _LINKED.fullmatch(text.strip())
    # a linked title is one unit: only the length limit may shorten it, never a `;` inside it
    cut = linked["text"] if linked else re.split(r"(?<=[.;])\s", text, maxsplit=1)[0].strip()
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0] + "…"
    return f"[{cut}]({linked['url']})" if linked else cut


def render(start: int, end: int) -> str:
    """The generated half of one release's notes."""
    rows = _rows()
    if not 0 <= start <= end <= len(rows):
        raise ValueError(
            f"marker range {start}..{end} does not fit {len(rows)} closed "
            f"rows - markers are closed-row counts, not item numbers"
        )
    window = rows[start:end]
    if not window:
        return "No scenarios closed between these markers.\n"

    grouped = {}
    for row in window:
        grouped.setdefault(_topic(row["id"]), []).append(row)

    ordered = [topic for topic in TOPIC_ORDER if topic in grouped] + sorted(set(grouped) - set(TOPIC_ORDER))
    lines = [f"{len(window)} scenarios closed (closed-row markers {start} → {end}).", ""]
    for topic in ordered:
        lines.append(f"**{topic}**")
        lines.append("")
        for row in grouped[topic]:
            lines.append(f"- {row['link']} — {_first_sentence(row['summary'])}")
        lines.append("")
    return _REL_LINK.sub("](docs/backlog/scenarios/", "\n".join(lines) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bga release-notes", description="Generate a release's body from the closed backlog rows."
    )
    parser.add_argument(
        "--from", dest="start", type=int, required=True, help="Closed-row marker of the previous release."
    )
    parser.add_argument(
        "--to",
        dest="end",
        type=int,
        default=None,
        help="Closed-row marker of this release (default: every row there is now).",
    )
    args = parser.parse_args(argv)
    end = args.end if args.end is not None else len(_rows())
    try:
        sys.stdout.write(render(args.start, end))
    except ValueError as problem:
        parser.error(str(problem))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
