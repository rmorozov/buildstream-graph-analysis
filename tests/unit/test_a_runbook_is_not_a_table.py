"""UX-669: the next steps render once, as steps.

Measured on `macro_micro`, exported and booted at 1440x900. Before:

```text
(a) decision panel     ol.next-steps > li.next-step[data-step]   3 steps
(b) section next_steps <table data-table="next_steps">  Why | Run | From
    Run cell     bga blast core.bst /tmp/.../run   wrapped over 3 lines
    From cell    critical_path_detail               a raw key (§4b)
```

Both sites drew the same three reasons and the same three commands, and
the table's `From` column printed the payload key. §1 sends "array of
objects" to a table, which is right for a population and wrong for
three commands a reader runs in order.

`bga:runbook` on `next_steps` is the declaration; §1e is the rule. The
panel keeps the steps, the section becomes one link to it, and
`follows_from` renders as the target section's own question.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Both sites, read together. A clause that only counted the panel
#: would pass with the table still drawn beside it, which is the whole
#: defect - so every reading below names the *pair*.
_READ = r"""
(() => {
  for (const b of document.querySelectorAll("section.chapter")) {
    b.setAttribute("data-open", "true");
  }
  const section = document.querySelector('[data-section="next_steps"]');
  const panel = document.querySelector("#decision");
  const step = (li) => ({
    id: li.getAttribute("data-step"),
    follows: li.getAttribute("data-follows-from"),
    commands: li.querySelectorAll("code.next-command").length,
    links: [...li.querySelectorAll("a[href^='#']")].map((a) => ({
      href: a.getAttribute("href"),
      text: a.textContent,
      exists: !!document.getElementById(a.getAttribute("href").slice(1)),
    })),
  });
  return {
    section: section && {
      tables: section.querySelectorAll("table").length,
      steps: section.querySelectorAll("[data-step]").length,
      links: [...section.querySelectorAll("a[href^='#']")].map((a) => ({
        href: a.getAttribute("href"),
        text: a.textContent,
        exists: !!document.getElementById(a.getAttribute("href").slice(1)),
      })),
    },
    panel: panel && {
      steps: [...panel.querySelectorAll("li[data-step]")].map(step),
    },
    // The control. `provenance` is an array of objects on both
    // fixtures, it is **not** a runbook, and it reaches the runbook
    // branch's own `if` - which most of this page's tables, drawn by
    // the chapter renderers, never do.
    control_table: document.querySelectorAll(
      'table[data-table="provenance"]').length,
  };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def read(browser, tmp_path_factory):
    """Both committed fixtures: `golden` publishes two steps and
    `macro_micro` three, so the link's count is read against two
    different populations rather than one."""
    return {label: browser.measure(uri, _READ, 1440, 900)
            for label, uri in pages.pages(tmp_path_factory, "u669").items()}


@pytest.fixture(scope="module")
def declared(tmp_path_factory):
    """`next_steps` as the pipeline published it, per fixture."""
    from tools.bga_view import payloads

    out = {}
    for label, fixture in pages.FIXTURES.items():
        run = pages.snapshot_copy(fixture, tmp_path_factory.mktemp(f"u669d-{label}"))
        out[label] = payloads(str(run))["report.json"].get("next_steps") or []
    return out


class TestTheRunbookIsDeclaredAndNotSniffed:
    def test_next_steps_carries_the_runbook_hint(self):
        """The page chooses nothing: the shape is on the declaration,
        the way every other `bga:*` hint is."""
        from bga import schemas

        assert schemas._ANALYZE_HINTS["next_steps"][schemas.RUNBOOK] is True

    def test_the_hint_survives_the_read(self):
        """`hintsOf` copies a fixed list of names off a schema node, so
        a hint absent from that list is declared and never seen."""
        text = (REPO / "bga" / "viewer" / "format.js").read_text()
        assert 'export const RUNBOOK = "bga:runbook";' in text
        start = text.index("export function hintsOf(")
        assert "RUNBOOK" in text[start:start + 600]

    def test_no_other_section_is_declared_a_runbook(self):
        """One shape, one member. `constraints` and `findings[].evidence`
        are the other `{reason, ...}` arrays and neither is ordered or
        runnable - a second runbook would be a mapping, not a shape."""
        from bga import schemas

        wearing = [key for key, hint in schemas._ANALYZE_HINTS.items()
                   if isinstance(hint, dict) and hint.get(schemas.RUNBOOK)]
        assert wearing == ["next_steps"]


@needs_browser
class TestTheSectionIsALinkAndNotASecondCopy:
    def test_the_section_holds_no_table(self, read):
        assert {label: page["section"]["tables"] for label, page in read.items()} \
            == {"golden": 0, "macro_micro": 0}

    def test_the_section_lists_no_step(self, read):
        """Panel and section never both list `[data-step]`."""
        for label, page in read.items():
            assert page["section"]["steps"] == 0, label
            assert page["panel"]["steps"], label

    def test_the_section_is_one_link_to_the_panel(self, read, declared):
        """The label is pasted, not recomputed: a clause that built the
        sentence the way the renderer builds it would pass on two
        matching mistakes."""
        assert {label: [one["text"] for one in page["section"]["links"]]
                for label, page in read.items()} == {
            "golden": ["2 steps, in the decision panel"],
            "macro_micro": ["3 steps, in the decision panel"]}
        for label, page in read.items():
            links = page["section"]["links"]
            assert [one["href"] for one in links] == ["#decision"], label
            assert links[0]["exists"], label
            assert links[0]["text"].startswith(f"{len(declared[label])} "), label

    def test_the_other_reason_array_still_draws_a_table(self, read):
        """The branch is the hint's, not `renderSection`'s. Counting
        *any* table on the page was the first version of this clause
        and it was vacuous: the element and preset tables are built
        elsewhere, so it stayed green with every array turned into a
        runbook - and so did counting `critical_path_detail`, which
        reaches this section through a chapter renderer instead.
        `provenance` is on both fixtures and goes through the branch."""
        assert {label: page["control_table"] for label, page in read.items()} \
            == {"golden": 1, "macro_micro": 1}


@needs_browser
class TestEachStepIsWhyThenCommandThenCitation:
    def test_the_panel_lists_every_published_step(self, read, declared):
        for label, page in read.items():
            assert [step["id"] for step in page["panel"]["steps"]] \
                == [step["id"] for step in declared[label]], label

    def test_each_step_carries_exactly_one_command(self, read):
        for label, page in read.items():
            assert [step["commands"] for step in page["panel"]["steps"]] \
                == [1] * len(page["panel"]["steps"]), label

    def test_each_step_carries_one_in_page_link_that_resolves(self, read):
        for label, page in read.items():
            for step in page["panel"]["steps"]:
                assert len(step["links"]) == 1, (label, step["id"])
                assert step["links"][0]["exists"], (label, step["id"])

    def test_the_citation_is_a_question_and_never_a_key(self, read):
        """§4b. The table this replaces printed `critical_path_detail`
        in its `From` cell; the link is labelled with what that section
        asks, or - for a step that follows a finding - the finding's own
        claim."""
        for label, page in read.items():
            for step in page["panel"]["steps"]:
                text = step["links"][0]["text"]
                assert text.startswith("from: "), (label, step["id"])
                assert step["follows"] not in text, (label, step["id"])
