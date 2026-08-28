"""UX-360: folding paid the distance, and nothing measured the volume.

Round 52's complaint was distance: twenty screens, the element table
6.8 screens down, the run identity 19.6. `UX-347` answered it with
chapters that fold, and the answer worked. Round 55 measured what the
answer cost:

```text
                    round 52      round 55 landed / opened
golden height      11,286 px       3,548 / 13,844
macro  height      18,148 px       5,588 / 24,689
golden words          3,448         5,034
macro  words          5,026         8,174
```

**The page a reader lands on is a third of what it was. The page in
total is a third bigger.** Distance was paid for with a fold, and the
volume behind the fold went unmeasured and grew — because nothing
measured it. `UX-347` bought a distance budget; "it is behind a
chapter" was a complete answer to any question about page weight.

The growth is not waste and this file does not claim it is. Round 53
and 54 built the shape channel, narrowed the table tools, moved the
schema's sentences behind a door and lifted two namespaces; round 56
landed the join's withheld fields, the provenance's rule and two new
shapes. Each was right. Together they are half again as much page, and
the round that adds the next thing needs a number to check itself
against.

**Two budgets, and they are a pair.** Landed distance is what `UX-347`
bought; total volume is what it cost. This file asserts both in one
guard so that a change trading one for the other has to say so — which
is the whole point, because the trade is exactly what happened and
nobody noticed for four rounds.

The bounds are set with headroom against the measurement below rather
than at it: a budget that reddens on the commit that lands it teaches
the next person to raise it rather than to think.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Measured on the finished page at 1440x900, round 59, exported with
#: `pages.export_uri` (`UX-359`), chapters opened and `details` left as
#: they are found:
#:
#: ```text
#:              elements   landed   opened    words  controls  nodes
#: golden              4    3,501   14,560    5,280       410   2,409
#: macro_micro        11    5,541   28,257    9,883       660   6,548
#: scale           1,202    4,397   54,968   35,031     1,925  22,977
#: ```
#:
#: `UX-367`: **the third row is the point.** Round 56 set one pair of
#: bounds against two 11-element fixtures, and nothing measured the
#: page at a size anyone builds at. Every opened bound was exceeded by
#: 1.6-2.8x where no guard looked.
#:
#: Two things the third row says that the first two could not.
#:
#: **The fold holds.** Landed height at 1,202 elements is *4,397 px* -
#: lower than `macro_micro`'s 5,541, and a fifth of the opened page.
#: `UX-347`'s answer scales, which is not something the 11-element
#: measurement could have shown. One landed bound serves every class.
#:
#: **The volume does not, and it is one section.** Of 33,864 words,
#: `wall_clock_share_us` is **27,657** - 82% - with 1,204 of the 1,922
#: controls and 30,859 of the 54,968 px. It is a flat
#: `{uid|BUILD|BUILD|0: microseconds}` map rendered one row per
#: element, uncapped, three sections from an element table capped at 25
#: (`UX-366`). Every other section together is 6,200 words.
#:
#: So the large class's bounds are set where the page *is*, and the
#: item that moves it is `UX-366`; this file's `not_slack` clause is
#: what will force them down when it does.
#:
#: Moving a bound is a filed reason, in the item that moves it, the way
#: `test_the_report_you_can_attach.py` records every size restatement.
#:
#: **The round-58 filing's scale figures were measured wrong**, and the
#: table above supersedes them. It reported 70,577 px against
#: `macro_micro`'s 28,213 - but 70,577 was measured with every
#: `<details>` forced open and 28,213 with them closed, so the row
#: compared two instruments. Same instrument, both ways:
#:
#: ```text
#:               chapters open   + every details open
#: macro_micro          28,257                 45,829
#: scale                54,968                 70,551
#: ```
#:
#: The overrun is real either way and smaller than filed: 1.6x, not
#: 2.1x. `_LOOK` opens chapters only, because that is what a reader
#: gets from "Expand all"; a `details` is a second, deliberate click.
LANDED_HEIGHT_PX = 7_000

#: `UX-367`: the opened bounds, per size class, largest class last.
#: Each row is `(elements at most, opened px, words, controls, nodes)`,
#: and a run is measured against the first row it fits. A page that is
#: 55,000 px at 1,202 elements may be acceptable; what was not
#: acceptable is that nobody had decided.
#:
#: `UX-366` added the fifth column, because closing it found the other
#: four blind to what it changed. Lifting the element table's cap put
#: **1,177 more rows in the DOM**, hidden - and the page measured:
#:
#: ```text
#:                  height    words  controls    DOM nodes
#: before           54,968   33,864     1,922       12,305
#: after            54,968   35,031     1,925       22,977
#: ```
#:
#: Height does not move because a hidden row occupies none, controls
#: barely move, and **`words` is nearly blind to a table**: the cells
#: carry no whitespace between them, so `textContent` renders a whole
#: six-column row as `layer00/mod023.bst9.0 s645falsecmakefalse` - one
#: "word". A budget that cannot see the page's biggest population
#: doubling is not measuring volume. `nodes` is the one that can.
#:
#: It earned itself one item later. `UX-370` projected Plane 2's
#: `by_binary`, `binary_cost` and `configure_phase` into the report and
#: `macro_micro` went 4,586 -> 6,548 DOM elements; the nodes clause is
#: what fired, and the small class's bound moved 5,500 -> 7,900 with
#: that as its reason. Height, words and controls all stayed inside
#: their bounds, so nothing else would have noticed.
BUDGETS = (
    (50, 34_000, 12_000, 800, 7_900),
    (4_000, 66_000, 41_000, 2_300, 27_500),
)


def budget_for(elements):
    """The row `elements` is measured against.

    Deliberately not clamped: a run past the last class has no decided
    budget, and inheriting the largest one silently would be the same
    failure this item is about one size up.
    """
    for row in BUDGETS:
        if elements <= row[0]:
            return row
    raise AssertionError(
        f"{elements:,} elements is past every size class in BUDGETS; "
        f"decide a bound for that size rather than inheriting one")


_LOOK = """
(() => {
  const state = () => {
    const main = document.querySelector("main") || document.body;
    return {
      height: document.documentElement.scrollHeight,
      // Words and controls are a fact about the **document**, not
      // about the fold: the chapters hide their sections with CSS, so
      // `textContent` reads them either way. That is why the volume
      // budget is one number rather than a landed and an opened one -
      // the volume is there from the first byte, and folding moved
      // only how far a reader scrolls past it.
      words: (main.textContent || "").trim().split(/\\s+/)
        .filter(Boolean).length,
      controls: document.querySelectorAll("button, input, select, a").length,
      // `UX-366`: the one measure that sees a table. Elements rather
      // than nodes, because a text node per cell would make this a
      // second word count.
      nodes: document.querySelectorAll("*").length,
      sections: main.querySelectorAll("section[data-section]").length,
      shown: [...main.querySelectorAll("section[data-section]")]
        .filter((s) => s.getBoundingClientRect().height > 0).length,
    };
  };
  const landed = state();
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  return { landed, opened: state() };
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


#: `UX-367`: the population, which is no longer only the fixtures.
#: The seeded 1,202-element run is generated rather than committed
#: (`pages.scale_run`), so it costs a subprocess and not a megabyte in
#: the tree, and it is the only member that exercises the large class.
LABELS = sorted(pages.FIXTURES) + ["scale"]


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    made = pages.pages(tmp_path_factory, "volume")
    into = tmp_path_factory.mktemp("volume-scale")
    made["scale"] = pages.export_uri(pages.scale_run(into), into,
                                     name="scale.html")
    return made


@pytest.fixture(scope="module")
def sizes(tmp_path_factory):
    """`{label: element count}`, read from the payload each page was
    exported from - so the class a page is measured against is a fact
    about the run rather than a constant beside the label."""
    from tools.bga_view import payloads

    runs = dict(pages.FIXTURES)
    runs["scale"] = pages.scale_run(tmp_path_factory.mktemp("volume-count"))
    return {label: len(payloads(str(run))["report.json"]
                       ["elements"]["element_durations"])
            for label, run in runs.items()}


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", LABELS)
class TestBothBudgetsAreBound:
    """One class, on purpose. `UX-347`'s distance budget lives in
    `test_the_chain_folds_and_clicks_are_counted.py` and is met; this
    holds it *beside* the volume it was paid for with, so a change that
    folds more to grow more reddens rather than passing two guards."""

    def test_the_landed_page_is_short(self, browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        landed = out["landed"]
        assert landed["height"] <= LANDED_HEIGHT_PX, (
            f"{label}: the page a reader lands on is {landed['height']} px, "
            f"over the {LANDED_HEIGHT_PX} px budget")

    def test_the_whole_page_is_bounded_too(self, browser, booted, sizes,
                                           label):
        """The sibling `UX-347` did not have. A fold is not a licence:
        answering the distance budget says nothing about this one.

        `UX-367`: against the bounds for **this run's size class**. One
        pair of numbers for every run was the defect - it made the two
        11-element fixtures the only page anyone had decided about.
        """
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        opened = out["opened"]
        klass, height, words, controls, nodes = budget_for(sizes[label])
        assert opened["nodes"] <= nodes, (
            f"{label}: {opened['nodes']} DOM elements, over the {nodes} "
            f"budget for runs up to {klass} elements - the measure that "
            f"sees a table growing, which height and words do not")
        assert opened["height"] <= height, (
            f"{label}: the whole document is {opened['height']} px, over "
            f"the {height} px budget for runs up to {klass} elements - "
            f"folding it further is not an answer to this clause")
        assert opened["words"] <= words, (
            f"{label}: {opened['words']} words, over the {words} budget "
            f"for runs up to {klass} elements")
        assert opened["controls"] <= controls, (
            f"{label}: {opened['controls']} controls, over the {controls} "
            f"budget for runs up to {klass} elements")

    def test_the_page_still_folds(self, browser, booted, label):
        """Without this, the landed clause is satisfied by a page that
        renders nothing, and the pair stops being a trade at all."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        landed, opened = out["landed"], out["opened"]
        assert landed["shown"] < opened["shown"], (landed, opened)
        assert landed["height"] < opened["height"], (landed, opened)
        assert opened["sections"] >= 40, opened

    def test_the_budgets_are_not_slack(self, browser, booted, sizes, label):
        """A bound nothing can reach is not a bound. The largest run in
        a class has to be within a factor of two of every budget, or the
        number was chosen to be safe rather than to be a limit.

        `UX-367` made this the clause with teeth: `UX-366` is about to
        cut `wall_clock_share_us` down, and when it does, the large
        class's bounds stop being met from below and have to be
        restated. That is the guard doing its job, not breaking.
        """
        largest = {}
        for other in LABELS:
            klass = budget_for(sizes[other])[0]
            if sizes[other] >= sizes.get(largest.get(klass), -1):
                largest[klass] = other
        klass, height, words, controls, nodes = budget_for(sizes[label])
        if largest[klass] != label:
            pytest.skip(f"{largest[klass]} is the largest run in this class")
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        opened = out["opened"]
        for measured, bound, name in (
                (out["landed"]["height"], LANDED_HEIGHT_PX, "landed height"),
                (opened["height"], height, "opened height"),
                (opened["words"], words, "words"),
                (opened["controls"], controls, "controls"),
                (opened["nodes"], nodes, "DOM elements")):
            assert measured * 2 > bound, (
                f"the {name} budget for runs up to {klass} elements is "
                f"{bound} and {label} measures {measured}; a bound with "
                f"that much slack is a number nobody will ever meet")


class TestEverySizeClassIsActuallyMeasured:
    """`UX-367`'s own defect, as a clause.

    The item exists because the population was two 11-element fixtures
    while the bounds claimed to govern every page. Splitting the bounds
    by size does not fix that on its own: a class with no run in the
    population is a pair of numbers nothing can redden, which is the
    same hole one level up.

    Found by the mutation sweep rather than by writing it: deleting
    `"scale"` from `LABELS` left the whole file green.
    """

    def test_every_class_has_a_run_behind_it(self, sizes):
        covered = {budget_for(sizes[label])[0] for label in LABELS}
        missing = [row[0] for row in BUDGETS if row[0] not in covered]
        assert not missing, (
            f"no run in the population falls in the class(es) bounded at "
            f"{missing} elements - those bounds govern nothing. The "
            f"population is {sizes}")

    def test_a_run_past_every_class_is_refused_and_not_clamped(self):
        """The other half of the population claim, and the second one
        the sweep found unheld: `budget_for` clamping to the last row
        instead of refusing passed every clause, because no run in the
        population is big enough to reach the branch.

        Inheriting the largest class silently is this item's defect at
        the next size up - a bound stated for 4,000 elements quietly
        governing 40,000 is exactly "nobody decided".
        """
        largest = BUDGETS[-1][0]
        assert budget_for(largest) == BUDGETS[-1]
        with pytest.raises(AssertionError, match="past every size class"):
            budget_for(largest + 1)

    def test_the_largest_class_is_reached_by_a_real_run(self, sizes):
        """Narrower and harder to satisfy by accident: the *last* class
        is the one the item was filed about, and a run has to be in it
        rather than merely near it."""
        largest = BUDGETS[-1][0]
        biggest = max(sizes.values())
        assert budget_for(biggest)[0] == largest, (
            f"the biggest run measured has {biggest:,} elements and falls "
            f"in the class bounded at {budget_for(biggest)[0]:,} - nothing "
            f"reaches the {largest:,} class these bounds were written for")
        assert biggest > 100, (
            f"{biggest:,} elements is not a scale probe; the item this "
            f"clause belongs to is about measuring where the page is used")


@needs_browser
@pytest.mark.medium
class TestTheBudgetIsWrittenWhereItIsRead:
    """§3e states the rule and this file holds it. The two have to agree
    on the numbers, or the guide is describing a different page - which
    is what `UX-352` was filed for one document over."""

    def test_the_style_guide_states_every_budget(self):
        """`UX-367`: **every** number, over every size class. The old
        clause read four constants, so splitting the bounds by size
        would have left half of them stated nowhere while it passed."""
        text = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        section = text.split("## 3e.", 1)[1].split("\n## ", 1)[0]
        numbers = [LANDED_HEIGHT_PX]
        for row in BUDGETS:
            numbers.extend(row)
        for number in numbers:
            assert f"{number:,}" in section, (
                f"§3e does not state the {number:,} bound this file "
                f"asserts")

    def test_the_size_classes_are_stated_too(self):
        """A budget per class is only readable if the guide says which
        class a run falls in - the number the class is named by is as
        load-bearing as the bounds inside it."""
        text = (REPO / "docs/design/styleguide.md").read_text(encoding="utf-8")
        section = text.split("## 3e.", 1)[1].split("\n## ", 1)[0]
        assert len(BUDGETS) > 1, "one class is not a per-size budget"
        for row in BUDGETS:
            assert f"{row[0]:,}" in section, (
                f"§3e does not name the size class for runs up to "
                f"{row[0]:,} elements")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
