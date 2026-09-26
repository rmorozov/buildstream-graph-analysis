"""UX-1018 (styleguide §6e.1): a chapter and its own first section
both rendered `h2` at 17px/700 - one outline level standing in for
three, so a reader could not tell a chapter from its section without
reading either.

`h2` (chapter, `--font-h1`), `h3` (section, `--font-h2`) and `h4`
(block, body weight 600) now - `chapters.js`'s `promoteHeadingLevels`
retags every section it collects, once, regardless of which module
built it. This file boots the golden export and walks the outline.
"""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_RANK = {"H1": 1, "H2": 2, "H3": 3, "H4": 4}

#: Every rendered heading, forced open first - a folded chapter hides
#: all but its own first section otherwise.
_OUTLINE = """
(() => {
  document.querySelectorAll('section[data-chapter]').forEach(
    (n) => n.setAttribute('data-open', 'true'));
  document.querySelectorAll('section[data-section][data-collapsed]').forEach(
    (n) => n.removeAttribute('data-collapsed'));
  return [...document.querySelectorAll('h1, h2, h3, h4')]
    .filter((n) => n.getBoundingClientRect().width > 0)
    .map((n) => ({tag: n.tagName,
                   size: parseFloat(getComputedStyle(n).fontSize)}));
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    from tools.bga_view import export

    run = tmp_path_factory.mktemp("outline-golden") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("outline-golden-page") / "report.html"
    export(str(run), str(page))
    return page.as_uri()


@needs_browser
def test_exactly_one_h1(browser, golden):
    outline = browser.measure(golden, _OUTLINE)
    ones = [n for n in outline if n["tag"] == "H1"]
    assert len(ones) == 1, f"{len(ones)} h1s: {outline[:5]}"


@needs_browser
def test_no_level_is_skipped(browser, golden):
    outline = browser.measure(golden, _OUTLINE)
    ranks = [_RANK[n["tag"]] for n in outline]
    jumps = [(a, b) for a, b in zip(ranks, ranks[1:]) if b - a > 1]
    assert jumps == [], f"a level was skipped: {jumps} in {ranks}"


@needs_browser
def test_chapter_titles_are_strictly_larger_than_section_titles(browser, golden):
    outline = browser.measure(golden, _OUTLINE)
    chapters = [n["size"] for n in outline if n["tag"] == "H2"]
    sections = [n["size"] for n in outline if n["tag"] == "H3"]
    assert chapters and sections, f"need both to compare: {outline[:10]}"
    assert min(chapters) > max(sections), (
        f"a chapter title ({min(chapters)}px) is not larger than every "
        f"section title ({max(sections)}px)")
