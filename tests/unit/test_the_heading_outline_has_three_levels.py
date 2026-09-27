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
  // `UX-1015`: a folded section is `hidden="until-found"`, not `data-open`.
  document.querySelectorAll('section[data-chapter] > section[hidden]').forEach(
    (n) => n.removeAttribute('hidden'));
  return [...document.querySelectorAll('h1, h2, h3, h4')]
    .filter((n) => n.getBoundingClientRect().width > 0)
    .map((n) => ({tag: n.tagName,
                   id: n.id,
                   text: n.textContent,
                   size: parseFloat(getComputedStyle(n).fontSize),
                   section: n.parentElement?.matches('section[data-section]')
                     && n.parentElement.parentElement?.matches('section[data-chapter]')}));
})()
"""

#: `UX-1047`: `#wordmark` is text, not a heading - the census above
#: only walks `h1`-`h4`, so this checks the element the outline is not
#: allowed to include.
_WORDMARK = """
(() => {
  const w = document.getElementById('wordmark');
  return w && {tag: w.tagName, role: w.getAttribute('role')};
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


@needs_browser
def test_no_section_title_wears_the_chapter_level(browser, golden):
    """The role, not the tag census: a chapter's section heads are `h3`."""
    outline = browser.measure(golden, _OUTLINE)
    heads = [n["tag"] for n in outline if n["section"]]
    assert heads and "H2" not in heads, f"section heads: {sorted(set(heads))}"


@needs_browser
def test_the_h1_is_the_run_not_the_wordmark(browser, golden):
    """UX-1047 (styleguide §6e.1): the outline's `h1` names the run."""
    outline = browser.measure(golden, _OUTLINE)
    ones = [n for n in outline if n["tag"] == "H1"]
    assert len(ones) == 1, f"{len(ones)} h1s: {outline[:5]}"
    assert ones[0]["id"] == "run-name", ones[0]
    # `UX-1047`: this fixture is a bare `run` dir with no store above
    # it (no `<stamp>/run`), so the h1 reads the literal name, "run" -
    # the tests below cover the climb-to-a-stamp branch and its guard.
    assert ones[0]["text"].strip() == "run", ones[0]


@needs_browser
def test_the_h1_ties_the_chapter_size_rather_than_falling_under_it(browser, golden):
    """§6e.1's one allowed tie: `h1` and `h2` share `--font-h1`."""
    outline = browser.measure(golden, _OUTLINE)
    font_h1 = browser.measure(
        golden,
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--font-h1').trim()")
    ones = [n["size"] for n in outline if n["tag"] == "H1"]
    chapters = [n["size"] for n in outline if n["tag"] == "H2"]
    assert ones and chapters, f"need both to compare: {outline[:5]}"
    assert ones[0] >= max(chapters), (
        f"the h1 ({ones[0]}px) is smaller than a chapter ({max(chapters)}px)")
    assert ones[0] == pytest.approx(float(font_h1.removesuffix("px"))), (
        ones[0], font_h1)


@needs_browser
def test_the_wordmark_is_not_a_heading(browser, golden):
    """§6e.1: the outline's `h1` is the run - the wordmark is text."""
    wordmark = browser.measure(golden, _WORDMARK)
    assert wordmark, "no #wordmark on the page"
    assert wordmark["tag"] not in {"H1", "H2", "H3", "H4", "H5", "H6"}, wordmark
    assert wordmark["role"] != "heading", wordmark


#: The h1's text alone - `run.name`'s "run" case climbs a directory
#: only when what it climbs to is a stamp (`app.js`'s `runDisplayName`,
#: `bga/run_store.py`'s `_STAMP`), never merely a run's parent.
_HEADING_TEXT = "document.getElementById('run-name')?.textContent ?? null"


@needs_browser
def test_a_stamped_run_reads_the_stamp(browser, tmp_path_factory):
    """`<store>/<stamp>/run`: the h1 climbs to the stamp."""
    from tools.bga_view import export

    stamp = "20260105T000000Z"
    run = tmp_path_factory.mktemp("stamped") / stamp / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("stamped-page") / "report.html"
    export(str(run), str(page))
    heading = browser.measure(page.as_uri(), _HEADING_TEXT)
    assert heading.strip() == stamp, heading


@needs_browser
def test_a_same_second_snapshot_s_disambiguator_still_reads_the_stamp(
        browser, tmp_path_factory):
    """`bga/run_store.py:new_snapshot_dir`'s `<stamp>-01` for a second
    snapshot inside one second - still a stamp, not a bare basename."""
    from tools.bga_view import export

    stamp = "20260105T000000Z-01"
    run = tmp_path_factory.mktemp("stamped-dup") / stamp / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("stamped-dup-page") / "report.html"
    export(str(run), str(page))
    heading = browser.measure(page.as_uri(), _HEADING_TEXT)
    assert heading.strip() == stamp, heading


@needs_browser
def test_a_bare_run_dir_reads_run(browser, tmp_path_factory):
    """No store above it: `run.name` is shown as-is, "run"."""
    from tools.bga_view import export

    run = tmp_path_factory.mktemp("case-bare-run") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("case-bare-run-page") / "report.html"
    export(str(run), str(page))
    heading = browser.measure(page.as_uri(), _HEADING_TEXT)
    assert heading.strip() == "run", heading


@needs_browser
def test_macro_micro_via_export_uri_does_not_read_snapshot(browser, tmp_path_factory):
    """`tests/pages.py:export_uri` copies into `<into>/snapshot/run` -
    "snapshot" is that copy's own directory name, never a stamp."""
    sys.path.insert(0, str(REPO / "tests"))
    import pages

    uri = pages.export_uri(pages.FIXTURES["macro_micro"],
                            tmp_path_factory.mktemp("macro-micro"))
    heading = browser.measure(uri, _HEADING_TEXT)
    assert heading.strip() != "snapshot", heading
