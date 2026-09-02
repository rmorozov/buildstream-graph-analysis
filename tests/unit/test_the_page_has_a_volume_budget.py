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
import collections
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
#: `UX-419` restated the large class's **opened height**, and
#: `test_the_budgets_are_not_slack` is what asked for it - exactly the
#: way that clause's docstring predicted a bound would come to be
#: restated. A `dl` had no bound at all, so every map drew every pair;
#: bounding them halved the opened page. Measured either side of the
#: change, one instrument, all three runs:
#:
#: ```text
#:                        landed   opened    words   controls    nodes
#: golden        before    3,800   15,618    5,565        427    2,498
#:               after     3,800   15,618    5,565        427    2,498
#: macro_micro   before    5,965   31,804   11,127        750    5,686
#:               after     5,965   31,804   11,127        750    5,686
#: scale         before    4,763   55,998   36,536      1,940   24,291
#:               after     4,763   26,242   36,542      1,941   24,294
#: ```
#:
#: Only `scale` moves, because only there does a map hold more than
#: forty pairs - and there only height moves far, for the same reason
#: `UX-366`'s table found only `nodes` did: a bounded pair is `hidden`,
#: so it stops occupying pixels while its text and its nodes stay in
#: the document. The +6 words, +1 control and +3 nodes are the one
#: bound's badge and its "Show all N pairs" button.
#:
#: So the large class's opened height is now **below** the small
#: class's, which reads wrong and is not. Every population on the scale
#: page is bounded; the small fixtures' populations are mostly under
#: their bounds and draw in full, so the 11-element page is the denser
#: of the two once the 1,202-element one stops drawing 1,202 of
#: anything. The other four large-class bounds are still met from below
#: and are left where they are.
#: `UX-479` and `UX-475` moved the small class's **words** and nothing
#: else, and the pair is worth reading together because they are two
#: kinds of addition:
#:
#: ```text
#:                golden words   macro_micro words
#: before round          6,882              11,616
#: after UX-479          7,121              11,979   (+239, +363)
#: after UX-475          7,144              12,002   (+23,  +23)
#: ```
#:
#: The two are different kinds of addition, and the sizes say so.
#: `UX-479` is a **finding that did not exist** - what a change to an
#: element rebuilds, for the reader whose question that is - and a
#: finding is not one sentence: it is the sentence, its provenance
#: record with a cited path per element, its row in the reader's block
#: and its copy text. Hence 363 words on the eleven-element page for
#: one claim, which is the number to remember the next time a finding
#: is proposed. `UX-475` is a sentence that got **longer by one
#: number**: the graph-shape claim now says how many zero-slack
#: elements are off the critical path, which is what tells a mesh from
#: a chain. Twenty-three words, and it replaced a claim rather than
#: adding one.
#:
#: Both were trimmed as far as they read well before this bound moved -
#: the first draft of the chain sentence and its provenance rule
#: measured 12,031, and 29 words came out of it. Two more would have
#: fitted under 12,000, which is exactly the negotiating this file's
#: own note on `PAGE_BUDGET_B`-style bounds warns about, so the number
#: moves instead.
#:
#: 12,600 leaves 598 words. `test_the_budgets_are_not_slack` is
#: satisfied at 2 x 12,002 = 24,004 > 12,600, so this is still a bound
#: something can reach - and at 363 words a finding, it is not room for
#: two more.
#: `UX-526`: the large class is now asserted at **both** ends - 1,202 at
#: its bottom, the seeded 4,002-element run at its top - and its four
#: opened bounds are restated from the top, where they were breached.
#: Measured either side of that item's own change, one instrument:
#:
#: ```text
#:                        opened    words   controls    nodes   <tr> in DOM
#: scale  1,202  before   26,576   37,312      1,949   24,345         1,545
#:               after    26,576    8,247        787    5,925           273
#: xl     4,002  before   27,222  107,352      4,774   73,075         4,800
#:               after    27,222    8,263        812    8,953           306
#: ```
#:
#: Height does not move, for `UX-419`'s reason: a bounded row costs no
#: pixels. Everything else does, because the rows and the pairs the bound
#: does not show now leave the document instead of staying in it hidden.
#: The class boundary moves 4,000 -> 4,100 so the run that measures it is
#: inside it; `budget_for` refuses anything past that rather than
#: inheriting, which is the clause `UX-367` wrote for this exact shape.
#:
#: `UX-527` moved the large class's **nodes** bound one item later,
#: 10,000 -> 5,500, and `test_the_budgets_are_not_slack` is what asked
#: for it - the second time that clause has restated a bound rather than
#: a change being trusted to. The Perfetto picker drew one `<option>`
#: per element; a search box draws the eight that match:
#:
#: ```text
#:                nodes   of which perfetto-questions
#: scale  before   5,925                        1,319
#:        after    4,732                          126
#: xl     before   8,953                        4,119
#:        after    4,960                          126
#: ```
#:
#: Words move by +12 (a longer sentence beside the control) and controls
#: not at all: a `<select>` and an `<input>` are one control each, and an
#: `<option>` was never counted as one. `nodes` is the measure that sees
#: it, for `UX-366`'s reason.
BUDGETS = (
    (50, 34_000, 12_600, 800, 7_900),
    (4_100, 32_000, 9_000, 900, 5_500),
)


#: `UX-371`: repetition, as a share of the page's block characters.
#:
#: Counted over what a reader sees as a unit - every `p`, `li`,
#: `summary`, `td`, `h3`, `h4` longer than `BLOCK_FLOOR_CHARS` - with
#: every chapter and every `details` open. **Sentence-level counting
#: says zero**: the first pass of this measurement split
#: `main.textContent` on full stops and found no duplicates at all,
#: because the repeated blocks sit inside different surrounding text
#: and the splitter never produced identical strings. Any guard here
#: has to count what a reader sees as a unit, not what a regex finds
#: between full stops.
#:
#: Measured round 59, either side of this item's own reduction - one
#: instrument, both readings, because round 58's 21.6% figure came from
#: a different block population and could not be compared with either:
#:
#: ```text
#:                      blocks  distinct  repeated chars  of total  share
#: golden      before       81        61           1,876    11,048  17.0%
#:             after        77        61           1,434     9,730  14.7%
#: macro_micro before      180       138           4,769    26,919  17.7%
#:             after       176       138           4,401    25,681  17.1%
#: ```
#:
#: **Distinct is unchanged on both**, which is the half that says a
#: copy was removed rather than a claim.
#:
#: Repetition is paid for out of the same budget as volume, which is
#: why it is asserted in this file rather than beside a prose guard:
#: a fifth of the page said twice is a fifth of the page.
REPEATED_SHARE_MAX = 0.21

#: Below this a repeated string is a **label** - a column header, a
#: unit, a control name - and it repeats because it labels repeated
#: things, which is what a table is. Above it, it is a sentence.
BLOCK_FLOOR_CHARS = 40

#: The distinct blocks each fixture publishes, so the share above
#: cannot be met by deleting claims. Losing a claim is not
#: deduplicating it, and the cheapest way to drive a repetition ratio
#: down is to say less.
DISTINCT_BLOCKS = {"golden": 61, "macro_micro": 138}


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


_LOOK = r"""
(() => {
  // `UX-399`: measure the page with the layout optimisation forced off.
  //
  // `content-visibility: auto` gives an open chapter's offscreen
  // sections a placeholder size until they have been rendered once, so
  // `scrollHeight` becomes an estimate that converges as the reader
  // scrolls. The volume budget is a question about **content** - how
  // much there is to read - not about how much of it the compositor
  // has painted, so it is asked of the fully laid-out document.
  //
  // Turning it off here would hide its removal, so the other half of
  // this pair lives in `test_the_browser_is_the_library.py`: the
  // shipped stylesheet really does carry the optimisation.
  """ + pages.FULL_LAYOUT_JS + r"""
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
      words: (main.textContent || "").trim().split(/\s+/)
        .filter(Boolean).length,
      controls: document.querySelectorAll("button, input, select, a").length,
      // `UX-366`: the one measure that sees a table. Elements rather
      // than nodes, because a text node per cell would make this a
      // second word count.
      nodes: document.querySelectorAll("*").length,
      // `UX-371`: what a reader sees as a unit, and how much of it is
      // said more than once.
      blocks: [...main.querySelectorAll("p, li, summary, td, h3, h4")]
        .map((n) => (n.textContent || "").replace(/\s+/g, " ").trim())
        .filter((t) => t.length > 40),
      sections: main.querySelectorAll("section[data-section]").length,
      shown: [...main.querySelectorAll("section[data-section]")]
        .filter((s) => s.getBoundingClientRect().height > 0).length,
    };
  };
  const landed = state();
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
  }
  // `UX-371` counts repetition over everything a reader can reach, so
  // the folds come open too - after the height measurements above,
  // which are about what "Expand all" gives.
  const opened = state();
  for (const fold of document.querySelectorAll("details")) fold.open = true;
  return { landed, opened, everything: state() };
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
#: `UX-526` added the fourth: `scale` is the large class's bottom and
#: `xl` its top, and a class measured only at its bottom was the same
#: defect `UX-367` closed one size down.
LABELS = sorted(pages.FIXTURES) + ["scale", "xl"]

#: The generated members, and what builds each.
_GENERATED = {"scale": pages.scale_run, "xl": pages.xl_run}


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    made = pages.pages(tmp_path_factory, "volume")
    for label, build in _GENERATED.items():
        into = tmp_path_factory.mktemp(f"volume-{label}")
        made[label] = pages.export_uri(build(into), into,
                                       name=f"{label}.html")
    return made


@pytest.fixture(scope="module")
def sizes(tmp_path_factory):
    """`{label: element count}`, read from the payload each page was
    exported from - so the class a page is measured against is a fact
    about the run rather than a constant beside the label."""
    from tools.bga_view import payloads

    runs = dict(pages.FIXTURES)
    for label, build in _GENERATED.items():
        runs[label] = build(tmp_path_factory.mktemp(f"volume-{label}-count"))
    return {label: len(payloads(str(run))["report.json"]
                       ["elements"]["element_durations"])
            for label, run in runs.items()}


@pytest.fixture(scope="module")
def looked(browser, booted):
    """`_LOOK`, once per page rather than once per clause.

    `UX-526`: four clauses over four pages is sixteen visits, and the
    4,002-element page is the expensive one. `_LOOK` returns the landed
    and the opened state from a single visit, so a second visit can only
    repeat it.
    """
    return {label: browser.measure(booted[label], _LOOK, 1440, 900)
            for label in LABELS}


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", LABELS)
class TestBothBudgetsAreBound:
    """One class, on purpose. `UX-347`'s distance budget lives in
    `test_the_chain_folds_and_clicks_are_counted.py` and is met; this
    holds it *beside* the volume it was paid for with, so a change that
    folds more to grow more reddens rather than passing two guards."""

    def test_the_landed_page_is_short(self, looked, label):
        landed = looked[label]["landed"]
        assert landed["height"] <= LANDED_HEIGHT_PX, (
            f"{label}: the page a reader lands on is {landed['height']} px, "
            f"over the {LANDED_HEIGHT_PX} px budget")

    def test_the_whole_page_is_bounded_too(self, looked, sizes, label):
        """The sibling `UX-347` did not have. A fold is not a licence:
        answering the distance budget says nothing about this one.

        `UX-367`: against the bounds for **this run's size class**. One
        pair of numbers for every run was the defect - it made the two
        11-element fixtures the only page anyone had decided about.
        """
        opened = looked[label]["opened"]
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

    def test_the_page_still_folds(self, looked, label):
        """Without this, the landed clause is satisfied by a page that
        renders nothing, and the pair stops being a trade at all."""
        out = looked[label]
        landed, opened = out["landed"], out["opened"]
        assert landed["shown"] < opened["shown"], (landed, opened)
        assert landed["height"] < opened["height"], (landed, opened)
        assert opened["sections"] >= 40, opened

    def test_the_budgets_are_not_slack(self, looked, sizes, label):
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
        out = looked[label]
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
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestRepetitionIsSpentFromTheSameBudget:
    """`UX-371`: a sentence that appears nine times is not a sentence,
    it is a footnote - and the page pays for every copy out of the
    volume budget above.

    Round 58 measured 4,742 repeated block characters on `macro_micro`
    and three of the worst offenders sat on the **first screen at
    once**: the decision chapter drew three top actions and each
    carried the same ranking rule under it. This item states the rule
    once below the list it ranked - the reader came for the actions -
    and leaves the per-row folds to say what differs.
    """

    @staticmethod
    def _counted(browser, booted, label):
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        blocks = out["everything"]["blocks"]
        counts = collections.Counter(blocks)
        total = sum(len(text) for text in blocks)
        repeated = sum(len(text) * (n - 1) for text, n in counts.items()
                       if n > 1)
        return counts, total, repeated

    def test_repetition_is_under_the_budget(self, browser, booted, label):
        counts, total, repeated = self._counted(browser, booted, label)
        share = repeated / total if total else 0
        worst = counts.most_common(3)
        assert share <= REPEATED_SHARE_MAX, (
            f"{label}: {repeated} of {total} block characters are said "
            f"more than once ({share:.1%}), over the "
            f"{REPEATED_SHARE_MAX:.0%} budget. Worst: "
            + "; ".join(f"x{n} {text[:50]!r}" for text, n in worst))

    def test_nothing_was_deleted_to_meet_it(self, browser, booted, label):
        """The discriminating half. The cheapest way to drive a
        repetition ratio down is to say less, so the count of
        *distinct* blocks is held where it was measured."""
        counts, _total, _repeated = self._counted(browser, booted, label)
        floor = DISTINCT_BLOCKS[label]
        assert len(counts) >= floor, (
            f"{label} publishes {len(counts)} distinct blocks, under the "
            f"{floor} measured when this budget was set - a claim was "
            f"lost rather than a copy")

    def test_the_count_is_of_blocks_and_not_sentences(self, browser,
                                                      booted, label):
        """The instrument, asserted. Splitting the page into sentences
        found **zero** duplicates when this was filed, because the
        repeated blocks sit inside different surrounding text. A guard
        written the easy way would pass forever."""
        out = browser.measure(booted[label], _LOOK, 1440, 900)
        blocks = out["everything"]["blocks"]
        assert blocks, f"{label}: the block walk found nothing"
        assert all(len(text) > BLOCK_FLOOR_CHARS for text in blocks), (
            "a block under the label floor reached the count")
        assert len(set(blocks)) < len(blocks), (
            f"{label} has no repeated block at all - either the page "
            f"changed profoundly or this walk has stopped finding them")


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
