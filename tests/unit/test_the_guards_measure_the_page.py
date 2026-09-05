"""UX-359: the page a guard measures is the page a user gets.

Round 55 measured `bga view` from the fixtures **in place** and got
numbers no guard had ever produced:

```text
macro_micro                      height  sections  words  buttons  strips
the page a user gets           24,689px        58  8,174      381      19
the page every guard measured  21,346px        55  6,845      341      18
```

The cause is one line, copy-pasted into every browser guard in the
repository:

```python
run = tmp_path_factory.mktemp(f"shape-{name}") / "run"
shutil.copytree(fixture, run)
```

`macro_micro`'s Plane 2 report is a **sibling** of `run/`, not a member
of it - `run_store.sibling_plane2` looks at `../plane2.json` from a
directory named `run` - so `copytree` of the run leaves it behind and
the export never sees Plane 2. Every budget in the repository was
calibrated against a page 3,343 px shorter than the one users get, and
the missing 14% is the half the second plane exists to produce.

`tests/pages.py` copies the **snapshot** instead. This file holds the
copy to the page it stands in for, and holds the guards to the copy.

It also cost round 55 a retracted finding. Measuring through a run-only
copy, I concluded the page never rendered `plane2_absence` and printed
a contradicting sentence instead. It renders it, correctly, and
differently per fixture - `NOT_CAPTURED` on `golden`,
`CAPTURED_NO_RAW_LOG` on `macro_micro`. The copy had turned the rich
fixture into the poor one. An instrument that silently converts your
best fixture into your worst is worse than no instrument, which is why
`TestTheOldIdiomStillLosesIt` asserts the loss rather than trusting
that it is gone.
"""
import ast
import json
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: What a page is, for the purpose of "these two are the same page".
#: Not the byte-for-byte HTML: an export stamps the run's absolute path
#: into the blast command and the two copies live at different paths, so
#: byte equality would fail for a reason that is not this rule.
_LOOK = """
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  const main = document.querySelector("main") || document.body;
  const text = main.textContent || "";
  return {
    sections: [...main.querySelectorAll("section[data-section]")]
      .map((s) => s.getAttribute("data-section")).sort(),
    words: text.trim().split(/\\s+/).filter(Boolean).length,
    buttons: document.querySelectorAll("button").length,
    inputs: document.querySelectorAll("input").length,
    svg: document.querySelectorAll("svg").length,
    strips: document.querySelectorAll('[data-role="density"]').length,
    // `UX-329`'s three sentences, told apart. Which one renders is the
    // fact the run-only copy silently changed.
    absence: text.includes("raw Plane 2 log") ? "CAPTURED_NO_RAW_LOG"
      : text.includes("Plane 2 was not captured") ? "NOT_CAPTURED"
      : text.includes("declined") ? "DECLINED" : "none",
  };
})()
"""


def _payload_keys(page: pathlib.Path):
    """The embedded payload's top-level keys, off the exported file.

    The browser-free half of the claim: `#bga-report` is what the page
    boots from, so a document the copy lost is a key the copy's export
    does not carry - measurable wherever the suite runs.
    """
    html = page.read_text(encoding="utf-8")
    found = re.search(
        r'<script type="application/json" id="bga-report">(.*?)</script>',
        html, re.S)
    assert found, f"{page.name} has no embedded payload"
    return sorted(json.loads(found.group(1)))


def _names_in(node):
    """Every bare name in an expression or assignment target."""
    return [child.id for child in ast.walk(node)
            if isinstance(child, ast.Name)]


def _called(node):
    """The called function's last name: `shutil.copytree` -> `copytree`."""
    function = node.func
    if isinstance(function, ast.Attribute):
        return function.attr
    if isinstance(function, ast.Name):
        return function.id
    return None


def _run_only_copy(fixture, into):
    """The idiom this item removed, kept here as the counter-example.

    Deliberately not imported from `pages`: a helper that still offers
    the broken copy is a helper somebody reaches for. It lives in the
    guard that proves it is broken and nowhere else.
    """
    run = pathlib.Path(into) / "run"
    shutil.copytree(fixture, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    return run


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


class TestTheCopyIsStillNecessary:
    """The precondition, asserted rather than assumed.

    `pages.snapshot_copy` exists to drop `expected_output.json`. If that
    file ever leaves the tree, the copy is dead weight and this should
    say so out loud rather than let `snapshot_copy` quietly become a
    slower synonym for exporting in place.
    """

    def test_a_fixture_still_carries_the_file_the_copy_drops(self):
        carried = [label for label, fixture in pages.FIXTURES.items()
                   if pages.has_expected_output(fixture)]
        assert carried, (
            "no fixture carries expected_output.json any more - "
            "`pages.snapshot_copy` has nothing left to do, and the guards "
            "should export in place instead of copying")

    def test_the_copy_drops_it(self, tmp_path):
        for label, fixture in pages.FIXTURES.items():
            run = pages.snapshot_copy(fixture, tmp_path / label)
            assert not (run / "expected_output.json").exists(), label


class TestTheCopyCarriesTheSiblings:
    def test_the_sibling_report_travels(self, tmp_path):
        """The mechanism, named. `macro_micro` has the sibling and
        `golden` does not, so this asserts the copy reproduces *what the
        fixture has* rather than that every copy gains a file."""
        from bga import run_store

        for label, fixture in pages.FIXTURES.items():
            before = run_store.sibling_plane2(str(fixture))
            after = run_store.sibling_plane2(
                str(pages.snapshot_copy(fixture, tmp_path / f"sib-{label}")))
            assert (before is None) == (after is None), (
                f"{label}: the fixture has a Plane 2 sibling "
                f"({before is not None}) and its copy does not "
                f"({after is not None})")

    def test_the_population_has_a_fixture_with_a_sibling(self):
        """Without this the clause above is 0 of 0 twice over."""
        from bga import run_store

        with_sibling = [label for label, fixture in pages.FIXTURES.items()
                        if run_store.sibling_plane2(str(fixture))]
        assert with_sibling == ["macro_micro"], with_sibling


class TestTheOldIdiomStillLosesIt:
    """The counter-example, so the clauses above are a distinction.

    If a later change made the run-only copy work too - the report moved
    inside `run/`, say - every assertion in this file would pass while
    asserting nothing. This reddens instead, and points at the change.
    """

    def test_copying_the_run_alone_drops_the_report(self, tmp_path):
        from bga import run_store

        fixture = pages.FIXTURES["macro_micro"]
        lost = _run_only_copy(fixture, tmp_path)
        assert run_store.sibling_plane2(str(fixture)) is not None
        assert run_store.sibling_plane2(str(lost)) is None, (
            "the run-only copy now finds the Plane 2 report; this guard's "
            "counter-example has stopped being one, and every clause here "
            "is passing for a new reason")

    def test_the_two_copies_export_different_documents(self, tmp_path):
        """And the loss reaches the payload, not just the filesystem."""
        import tools.bga_view as view

        fixture = pages.FIXTURES["macro_micro"]
        whole = pages.export_page(fixture, tmp_path / "whole")
        lost_run = _run_only_copy(fixture, tmp_path / "lost")
        lost = tmp_path / "lost" / "report.html"
        view.export(str(lost_run), str(lost))

        kept, dropped = _payload_keys(whole), _payload_keys(lost)
        assert set(dropped) < set(kept), (
            f"the run-only copy no longer loses documents: "
            f"{sorted(set(kept) - set(dropped))}")


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheCopyExportsTheSameDocument:
    def test_the_payload_keys_match(self, tmp_path, label):
        """Browser-free, so this runs everywhere the suite does."""
        fixture = pages.FIXTURES[label]
        copied = pages.export_page(fixture, tmp_path / "copied")
        in_place = pathlib.Path(
            pages.in_place_uri(fixture, tmp_path / "in-place")[len("file://"):])
        assert _payload_keys(copied) == _payload_keys(in_place), label


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheCopyRendersTheSamePage:
    def test_the_two_pages_agree(self, browser, tmp_path, label):
        """The claim the item is about, measured on the booted page."""
        fixture = pages.FIXTURES[label]
        copied = browser.measure(
            pages.export_uri(fixture, tmp_path / "copied"), _LOOK, 1440, 900)
        in_place = browser.measure(
            pages.in_place_uri(fixture, tmp_path / "in-place"),
            _LOOK, 1440, 900)
        assert copied == in_place, (
            f"{label}: the page a guard measures is not the page a user "
            f"gets\n  copied:   {copied}\n  in place: {in_place}")

    def test_the_measurement_can_tell_them_apart(
            self, browser, tmp_path, label):
        """`_LOOK` has to be able to see the difference, or the clause
        above passes on any two pages. Asserted where the difference is
        known to exist, and stated as a skip where it is not."""
        import tools.bga_view as view

        fixture = pages.FIXTURES[label]
        if label != "macro_micro":
            pytest.skip("golden has no Plane 2 sibling to lose")
        whole = browser.measure(
            pages.export_uri(fixture, tmp_path / "whole"), _LOOK, 1440, 900)
        lost_run = _run_only_copy(fixture, tmp_path / "lost")
        lost_page = tmp_path / "lost" / "report.html"
        view.export(str(lost_run), str(lost_page))
        lost = browser.measure(lost_page.as_uri(), _LOOK, 1440, 900)
        assert whole != lost, (
            "`_LOOK` reports the same page with and without Plane 2; it "
            "cannot see what this file exists to compare")
        assert whole["sections"] != lost["sections"], (whole, lost)


class TestNoGuardReinventsTheCopy:
    """The rule, applied to the source. Every guard that had this got it
    by copy-paste from the one before, so a clause that only fixed
    today's list would be fixing the instance again.

    The population is **guards that export a page from `macro_micro`**,
    and both halves of that are load-bearing. A module that copies a run
    to build a *store* - `test_a_capture_that_cannot_start.py`'s debris
    tree, `test_the_printed_sentences_are_contracts.py`'s store run -
    loses the sibling too, and it does not matter there: nothing in
    those guards reads Plane 2, and widening the rule to reach them
    would make it a rule about `copytree` rather than about the page. A
    module that copies `golden` loses nothing at all, because `golden`
    has no siblings to lose.
    """

    def _modules(self):
        """Guards that export a viewer page and copy a directory."""
        for path in sorted((REPO / "tests/unit").glob("test_*.py")):
            text = path.read_text(encoding="utf-8")
            if "bga_view" in text and "copytree" in text:
                yield path, text

    @staticmethod
    def _copies_macro(text):
        """Whether any `copytree` in this source copies a macro_micro run.

        Parsed rather than pattern-matched, and that is a correction two
        mutations forced. The first draft required the destination to be
        spelled `… / "run"` - the idiom binds it a line earlier, so a
        guard reverted to the idiom passed. The second draft read the
        source token against module-level names - the idiom's source is
        a **loop variable**:

            for name, fixture in FIXTURES.items():
                shutil.copytree(fixture, run)

        so it passed too. Resolving a name to what bound it, whether
        that was an assignment or a `for`, is the smallest thing that
        actually reads the shape this rule is about.
        """
        try:
            tree = ast.parse(text)
        except SyntaxError:      # pragma: no cover - a broken guard
            return False

        bound = {}      # name -> the source text that bound it
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    for name in _names_in(target):
                        bound.setdefault(name, []).append(
                            ast.get_source_segment(text, node.value) or "")
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                for name in _names_in(node.target):
                    bound.setdefault(name, []).append(
                        ast.get_source_segment(text, node.iter) or "")

        def macro(source, seen=frozenset()):
            """Does this expression's text, or anything that bound a name
            in it, mention `macro_micro`?

            Transitive, which the dict-of-fixtures shape needs:
            `fixture` is bound by `FIXTURES.items()`, and it is
            `FIXTURES` two steps back that names the path.
            """
            if "macro_micro" in source:
                return True
            try:
                names = _names_in(ast.parse(source, mode="eval").body)
            except SyntaxError:      # pragma: no cover
                return False
            for name in names:
                if name in seen:
                    continue
                onwards = seen | {name}
                if any(macro(binding, onwards)
                       for binding in bound.get(name, ())):
                    return True
            return False

        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and _called(node) == "copytree" and node.args
                    and macro(ast.get_source_segment(text, node.args[0])
                              or "")):
                return True
        return False

    def test_the_population_is_not_empty(self):
        found = [path.name for path, _ in self._modules()]
        assert len(found) >= 10, found

    def test_the_walk_can_see_a_macro_micro_copy(self):
        """The instrument. If `_copies_macro` stopped recognising the
        shape, the clause below would pass over a repository full of
        them - so it is exercised against the idiom itself."""
        assert self._copies_macro(
            'MACRO = REPO / "tests/fixtures/macro_micro/run"\n'
            'shutil.copytree(MACRO, tmp / "run")\n')
        assert self._copies_macro(
            'shutil.copytree(REPO / "tests/fixtures/macro_micro/run",'
            ' snap / "run")\n')
        # The idiom as it was actually written, with the destination
        # bound a line earlier. A mutation reverting one guard to this
        # passed the first draft of the clause below.
        assert self._copies_macro(
            'MACRO = REPO / "tests/fixtures/macro_micro/run"\n'
            'run = tmp_path_factory.mktemp("shape") / "run"\n'
            'shutil.copytree(MACRO, run)\n')
        # And through the loop variable, which is how every one of the
        # converted guards actually spelled it.
        assert self._copies_macro(
            'FIXTURES = {"macro_micro": REPO / "tests/fixtures/macro_micro/run"}\n'
            'for name, fixture in FIXTURES.items():\n'
            '    shutil.copytree(fixture, run)\n')
        assert not self._copies_macro(
            'GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"\n'
            'shutil.copytree(GOLDEN, tmp / "run")\n')

    def test_every_macro_micro_page_goes_through_the_helper(self):
        bad = []
        for path, text in self._modules():
            if "snapshot_copy" in text or "from pages import" in text:
                continue
            # The one legitimate other answer: copy the run *and* the
            # sibling by hand, which is what the Plane 2 agreement guard
            # does and says it does in its own docstring.
            if "PLANE2_NAME" in text or "plane2.json" in text:
                continue
            if self._copies_macro(text):
                bad.append(path.name)
        assert bad == [], (
            "a guard copies a `macro_micro` run to build a page without "
            "going through `tests/pages.py`, which silently drops the "
            "Plane 2 report:\n  " + "\n  ".join(bad))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
