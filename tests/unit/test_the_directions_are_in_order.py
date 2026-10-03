"""UX-1293: `directions.md`'s `##` headings are its Directions, in numeric order, and nothing else."""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
DIRECTIONS = REPO / "docs/design/directions.md"
HISTORY = REPO / "docs/audits/directions-history.md"


def _headings():
    in_fence = False
    found = []
    for line in DIRECTIONS.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            found.append(line)
    return found


def test_every_heading_is_a_direction_in_order():
    headings = _headings()
    numbers = [re.match(r"## Direction (\d+):", h) for h in headings]
    strays = [h for h, m in zip(headings, numbers) if m is None]
    assert strays == [], f"directions.md carries non-Direction chapters - they belong in {HISTORY.name}: {strays}"
    order = [int(m.group(1)) for m in numbers]
    assert len(order) >= 20, order
    assert order == list(range(1, len(order) + 1)), f"Directions out of order: {order}"


def test_the_history_holds_the_chapters_that_left():
    text = HISTORY.read_text(encoding="utf-8")
    for heading in ("## Round history", "## Verification Log", "## Implementation status"):
        assert heading in text, f"{HISTORY.name} lost {heading!r}"
