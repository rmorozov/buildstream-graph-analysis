"""UX-400: every population is tested at zero, one and many.

The escape ledger for population-shape bugs was three entries long,
and every one of them was found by an audit round rather than by the
suite:

- **zero** - six sections vanished without a word on an incremental
  run (`UX-388`, found only because round 63 ran the cycle twice);
- **one** - superlatives and labels written for populations read wrong
  over a single row (`UX-365`'s class);
- **many** - the volume budget was unheld at the size people build at
  until the capacity sweep found it (`UX-367`).

Each was fixed *where it was seen*. Nothing asserted the next section
handles all three, so the next section shipped the same three bugs:
the suite tests a section on the population its fixture happens to
have, and a fixture has one size.

**The instrument, not the findings.** This file renders every
published record population at three sizes and asserts the contract at
each. `UX-400`'s Out of Scope says a real failure it turns up is its
own filing, so what a leg finds today is a **declared ledger** -
population, leg, and the id it was filed under - and every clause
asserts what it measured *equals* its ledger. Equality in both
directions is the point: a new section that fails a leg reddens
because it is not in the ledger, and a fixed one reddens because it
still is, which is what stops a ledger becoming a place to put
failures instead of a list of them.

**In the shim, not the browser.** Ten populations times three sizes is
thirty renders; a browser boot each would put this in the large tier
for a claim that is about the *document* the renderer produces, and
`UX-360`'s volume budget already measures pixels at scale in Chrome.
Everything this sweep reads - the section, its empty marker, the rows
a reader can see, the badge over them - is in the DOM either way.

Four things the first draft of this file measured wrong, each of which
would have been filed as a defect in the page:

- it swept `element_join`, which `DRAWN_ELSEWHERE` says is merged into
  the element table on purpose (`UX-338`), and read the deliberate
  `null` as a section that vanished;
- it counted `<tr>` elements, and `foldTheMiddle` and the Top-N preset
  both *hide* rows rather than removing them - so a table bounded to
  25 of 120 read as 121 rows drawn;
- it scanned the whole section for comparative words, and matched
  `Top 25 by duration_us` in an `<option>` - a control offering a
  ranking, not a claim that one was made;
- it matched `Biggest wait category` inside a finding's own headline,
  which is the payload's sentence about a measurement, not the
  renderer's sentence about a population.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is required")

#: Two planes, so the sweep reaches the sections a single-plane fixture
#: does not publish - which is how it found the two below.
RUN = REPO / "tests/fixtures/macro_micro/run"


def _read_const(name):
    """The viewer's own number, never a second copy of it."""
    source = (REPO / "bga/viewer/structured.js").read_text(encoding="utf-8")
    return int(source.split(f"{name} = ", 1)[1].split(";", 1)[0].strip())


#: `UX-262`'s threshold: above this a table opens bounded.
BOUND = _read_const("TABLE_OPENS_BOUNDED_ABOVE")

#: The same number, as measured when this sweep was written - and the
#: reason it is written twice. Sizing `MANY` off `BOUND` alone made the
#: many leg undiscriminating: raising the viewer's threshold raised the
#: sweep's population with it, so the tables stayed bounded and nothing
#: reddened. `UX-392` learned the same lesson about its gate. The
#: clause below is what makes the second copy safe.
BOUND_AS_MEASURED = 40

#: `UX-367`'s size - three times the threshold, so a bound that holds
#: is unmistakable and one that does not cannot be a rounding accident.
MANY = BOUND_AS_MEASURED * 3

_SWEEP = r"""
globalThis._makeNode = (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null };
const app = await import(process.env.BGA_VIEWER);
const chapters = await import(process.env.BGA_REPO + "/bga/viewer/chapters.js");
const format = await import(process.env.BGA_REPO + "/bga/viewer/format.js");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const schema = JSON.parse(readFileSync(process.env.BGA_SCHEMA, "utf8"));
const many = Number(process.env.BGA_MANY);

const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const all = (n, pred, out = []) => {
  if (!n) return out;
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};

// Discovered from the payload, not listed here: a sweep that only sees
// what it was told about cannot catch the next section, which is the
// whole reason each of the three bugs above waited for an audit round.
const scalar = (v) => v === null || typeof v !== "object";
const records = Object.entries(payload)
  .filter(([, v]) => Array.isArray(v) && v.length
                     && v.every((r) => r && typeof r === "object"
                                        && !Array.isArray(r)))
  .map(([k]) => k);
// `UX-419`: **and the maps.** The rule above discovers a population as
// an array of objects, and `renderPairs` draws a second shape it cannot
// see - one measure per key. That hole is why nothing bounded
// `by_binary` or `wall_clock_share_us`, and it is the half of `UX-419`
// worth more than the bound: an instrument with a shape-shaped hole
// lets the next section of that shape through too.
const maps = Object.entries(payload)
  .filter(([, v]) => v && typeof v === "object" && !Array.isArray(v)
                     && Object.keys(v).length
                     && Object.values(v).every(scalar))
  .map(([k]) => k);
const elsewhere = Object.keys(app.DRAWN_ELSEWHERE ?? {});
const swept = [...records, ...maps].filter((k) => !elsewhere.includes(k));
const shape = Object.fromEntries([...records.map((k) => [k, "record"]),
                                  ...maps.map((k) => [k, "map"])]);

// Each population at a size, in the shape the payload publishes it in.
const sized = (key, n) => {
  const held = payload[key];
  if (shape[key] === "map") {
    const names = Object.keys(held), out = {};
    for (let i = 0; i < n; i++) out[`${names[i % names.length]}-${i}`] =
      held[names[i % names.length]];
    return out;
  }
  const out = [];
  for (let i = 0; i < n; i++) out.push(held[i % held.length]);
  return out;
};

const draw = (key, rows) => {
  const node = schema.properties?.[key];
  try {
    const section = app.renderSection(
      key, rows, app.hintsOf(node), node, null, payload);
    if (!section) return { drawn: false };
    // The rows a reader can see. `foldTheMiddle` and the Top-N preset
    // both set `hidden` rather than removing the row, so that Ctrl-F,
    // the export and `Copy shown rows` keep seeing the whole table.
    const trs = all(section, (n) => n.tagName === "tr");
    return {
      drawn: true,
      empty: section.attrs?.["data-empty"] ?? null,
      says_none: text(section).includes("found none"),
      rows: trs.length,
      shown: trs.filter((tr) => !tr.hidden).length,
      // `renderFindings` draws an article per finding, not a table -
      // so a population that grows without a table grows unbounded in
      // a shape counting rows cannot see. Read visible-and-total, for
      // the reason the rows are: `UX-413`'s `boundCards` hides the
      // cards past the bound rather than removing them, and counting
      // the elements would read a bounded list as an unbounded one.
      cards: all(section, (n) => n.tagName === "article").length,
      cards_shown: all(section, (n) => n.tagName === "article")
        .filter((card) => !card.hidden).length,
      // `UX-419`: and a map's pairs, which are neither rows nor cards.
      // A `<dt>` and its `<dd>` are one thing to a reader, so the
      // count is of terms.
      pairs: all(section, (n) => n.tagName === "dt").length,
      pairs_shown: all(section, (n) => n.tagName === "dt")
        .filter((dt) => !dt.hidden).length,
      badges: all(section, (n) => (n.attrs?.class || "") === "badge")
        .map(text),
      // `UX-412`: the copy control's label carries the same count in
      // the same words, so a fix to one and not the other would leave
      // a reader `1 rows` beside `Copy 1 row`.
      copies: all(section, (n) => (n.attrs?.class || "") === "copy-rows")
        .map(text),
    };
  } catch (error) {
    return { threw: String(error && error.message) };
  }
};

const out = {};
for (const key of swept) {
  out[key] = {
    zero: draw(key, sized(key, 0)),
    one: draw(key, sized(key, 1)),
    many: draw(key, many === 0 ? sized(key, 0) : sized(key, many)),
  };
}

// Where the ordering authority files each of them. `chapterFor` reads
// the table first and the section's rail second, exactly as the page
// does - so this is the chapter a reader would find it under.
//
// `UX-414`: through `format.heading`, which is what the page calls.
// This read `format.RAIL`, and `RAIL` is a module-private constant
// that `format.js` does not export - so the expression was
// `hints[undefined]`, every rail came back `undefined`, and every
// unlisted section resolved to the fallback chapter. That produced a
// ledger of two sections said to be in "Everything else" which are
// not, and it is the fifth harness bug this sweep has had. `heading`
// also applies the page's own `?? "raw"` default, so a section with
// no declared rail lands where a reader would find it rather than in
// a bucket the page never puts it in.
const placed = {};
for (const key of swept) {
  const hints = app.hintsOf(schema.properties?.[key]);
  placed[key] = chapters.chapterFor(key, format.heading(key, hints).rail);
}

process.stdout.write(JSON.stringify({
  records, maps, shape, elsewhere, swept, placed, out,
  registered: chapters.CHAPTERS.flatMap((c) => c.sections),
  unchaptered: chapters.UNCHAPTERED.id,
}) + "\n");
"""


@pytest.fixture(scope="module")
def swept(tmp_path_factory):
    from bga import schemas

    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    into = tmp_path_factory.mktemp("sweep")
    (into / "payload.json").write_text(done.stdout, encoding="utf-8")
    (into / "schema.json").write_text(
        json.dumps(schemas.schema(schemas.ANALYZE)), encoding="utf-8")
    result = subprocess.run(
        [node, "--input-type=module", "-e", _SWEEP],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ,
                 BGA_REPO=str(REPO),
                 BGA_VIEWER=str(REPO / "tests" / "viewer.mjs"),
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs"),
                 BGA_PAYLOAD=str(into / "payload.json"),
                 BGA_SCHEMA=str(into / "schema.json"),
                 BGA_MANY=str(MANY)))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


#: `UX-419`: the three shapes a population is drawn in, and the one
#: question every clause below asks of them - *how many of these can a
#: reader see, out of how many there are*. Rows came first, `UX-413`
#: added cards, and the map went unread for six rounds because nothing
#: named the shape. A clause that reads one shape is a clause the next
#: shape walks past.
DRAWN_AS = (("shown", "rows"), ("cards_shown", "cards"),
            ("pairs_shown", "pairs"))


def _seen(leg):
    """`(visible, total)` for whichever shape this leg drew, or None."""
    for visible, total in DRAWN_AS:
        if leg.get(total):
            return leg.get(visible, 0), leg[total]
    return None


@needs_node
class TestTheSweepReachesEveryPopulation:
    """The instrument's own coverage, before any leg is read."""

    def test_it_discovers_the_populations_rather_than_listing_them(
            self, swept):
        assert len(swept["swept"]) >= 10, swept["swept"]
        # A spot check that discovery found the ones three separate
        # filings were about, so a discovery rule that quietly stopped
        # matching reddens here rather than sweeping nothing.
        for named in ("findings", "next_steps", "critical_path_detail",
                      "latent_heavies", "provenance"):
            assert named in swept["swept"], swept["swept"]

    def test_nothing_published_is_left_out(self, swept):
        """Every published population is either swept or has a written
        reason not to be. `DRAWN_ELSEWHERE` is that reason and it is a
        sentence per key, so this cannot be satisfied by a bare skip
        list.

        `UX-419`: **and maps count as published.** This read
        `swept["records"]` only, so a whole shape could be left out
        without the clause noticing - which is exactly what happened,
        for six rounds."""
        missed = [key for key in (*swept["records"], *swept["maps"])
                  if key not in swept["swept"]
                  and key not in swept["elsewhere"]]
        assert missed == [], missed

    def test_it_sweeps_both_shapes(self, swept):
        """What keeps the clause above from being satisfied by an empty
        set of maps: the payload really does publish both, and the
        sweep really does reach both."""
        drawn = {swept["shape"][key] for key in swept["swept"]}
        assert drawn == {"record", "map"}, drawn
        maps = [k for k in swept["swept"] if swept["shape"][k] == "map"]
        assert len(maps) >= 5, maps
        for named in ("by_binary", "wall_clock_share_us"):
            assert named in maps, maps

    def test_the_threshold_is_the_one_this_sweep_was_sized_for(self):
        """`MANY` is three times the threshold *as measured*, not three
        times whatever the viewer currently declares - see the note on
        `BOUND_AS_MEASURED`. Moving `TABLE_OPENS_BOUNDED_ABOVE` reddens
        here, which is where the two copies are reconciled."""
        assert BOUND == BOUND_AS_MEASURED, (
            f"the viewer bounds above {BOUND}; this sweep is sized for "
            f"{BOUND_AS_MEASURED} and renders {MANY} rows. Re-measure "
            f"the ledgers before moving the constant here")

    def test_no_population_throws_at_any_size(self, swept):
        threw = {f"{key}/{leg}": seen["threw"]
                 for key, legs in swept["out"].items()
                 for leg, seen in legs.items() if seen.get("threw")}
        assert threw == {}, threw

    #: Empty, and it was empty all along: the two entries it held under
    #: `UX-414` were an artefact of this file reading the rail through
    #: `format.RAIL`, which `format.js` does not export. Every rail came
    #: back `undefined` and every unlisted section resolved here. The
    #: reading goes through `format.heading` now, which is what the page
    #: calls - and `chapterFor` falls back to the rail, so a section
    #: with one is never unplaced. What this clause still catches is a
    #: section with neither an entry nor a rail, which is what
    #: "Everything else" is for.
    UNPLACED = {}

    def test_every_swept_population_is_filed_under_a_chapter(self, swept):
        """The acceptance test's enumeration clause, in the form the
        registry can actually carry.

        The item asks for "the enumeration count equals the chapters
        registry's count". Measured, those are not the same number and
        cannot be: the registry files 57 sections and 11 of the
        payload's keys are record populations - the rest are scalars,
        objects and drawn-elsewhere keys. What makes a new section
        unable to dodge the sweep is the pair of directions above
        (discovered from the payload, and nothing published left out)
        plus this: each one resolves to a *named* chapter.
        """
        fallback = {key: chapter for key, chapter in swept["placed"].items()
                    if chapter == swept["unchaptered"]}
        assert fallback.keys() == self.UNPLACED.keys(), (
            f"filed under 'Everything else': {sorted(fallback)}; the "
            f"ledger says {sorted(self.UNPLACED)}. A new one means a "
            f"section with no chapter; a missing one means the ledger "
            f"outlived its fix and should be deleted with it")


@needs_node
class TestZero:
    """`UX-388`'s rule, swept rather than spot-checked.

    Clean on its first run - which is the answer for `UX-388`'s fix
    that no fixture-shaped guard could give, because it says the rule
    holds for every population rather than for the six that vanished.
    """

    def test_a_declared_collection_still_draws_its_section(self, swept):
        gone = [key for key, legs in swept["out"].items()
                if not legs["zero"].get("drawn")]
        assert gone == [], (
            f"{gone} vanish at zero rows. That is the incremental run - "
            f"the common case - losing a section without a word")

    def test_it_says_the_analysis_found_none(self, swept):
        silent = [key for key, legs in swept["out"].items()
                  if not legs["zero"].get("says_none")]
        assert silent == [], silent

    def test_the_rail_can_tell_an_empty_one_apart(self, swept):
        unmarked = [key for key, legs in swept["out"].items()
                    if legs["zero"].get("empty") != "true"]
        assert unmarked == [], unmarked


@needs_node
class TestOne:
    """`UX-365`'s class: what a page written for a population says over
    a single row."""

    #: Empty since `UX-412`. It held nine entries - every table that
    #: draws its own badge - because `badgeText(1, 1)` returned
    #: `1 rows`: one shared helper, one wrong sentence, nine places a
    #: reader meets it. Pluralising where the count is written is what
    #: made the whole ledger go at once, and is why the entry that
    #: comes back will be a *new* call site rather than a missed one.
    PLURAL = {}

    def test_one_row_still_draws_a_section(self, swept):
        missing = [key for key, legs in swept["out"].items()
                   if not legs["one"].get("drawn")]
        assert missing == [], missing

    def test_no_badge_pluralises_a_single_row(self, swept):
        lying = {key: legs["one"]["badges"]
                 for key, legs in swept["out"].items()
                 if any(badge.startswith("1 ") and badge.endswith("s")
                        and " of " not in badge
                        for badge in legs["one"].get("badges") or [])}
        assert lying.keys() == self.PLURAL.keys(), (
            f"badges over one row: {lying}; the ledger says "
            f"{sorted(self.PLURAL)}")

    def test_no_copy_control_pluralises_a_single_row(self, swept):
        """`UX-412`'s second call site. The badge and this label are
        written from the same count and used to disagree with the same
        noun, which is why the fix is one helper rather than two
        edits."""
        lying = {key: legs["one"]["copies"]
                 for key, legs in swept["out"].items()
                 if any("1 rows" in label
                        for label in legs["one"].get("copies") or [])}
        assert lying == {}, lying

    def test_the_copy_controls_are_there_to_be_read(self, swept):
        """What keeps the clause above from passing on an empty set -
        the mistake `UX-403`'s census exists to find."""
        seen = sum(len(legs["one"].get("copies") or [])
                   for legs in swept["out"].values())
        assert seen >= 5, f"only {seen} copy control(s) rendered at one row"

    def test_a_map_of_many_is_bounded_like_a_table(self, swept):
        """`UX-419` named, so the shape cannot go quiet again.

        The clauses above read whichever shape a section drew, which is
        the right rule and also the one that hides a regression: if
        every map stopped drawing pairs, `_seen` would return `None`
        and they would all pass. This asserts the maps are there and
        bounded, by name."""
        maps = {key: _seen(legs["many"]) for key, legs in swept["out"].items()
                if swept["shape"][key] == "map"}
        drawing = {key: seen for key, seen in maps.items() if seen}
        assert len(drawing) >= 5, maps
        for key, (shown, total) in drawing.items():
            if total <= BOUND:
                continue
            assert shown <= BOUND, (key, shown, total)

    def test_a_population_of_one_is_never_bounded(self, swept):
        """A Top-N over one row would hide the only row there is."""
        hiding = {key: legs["one"] for key, legs in swept["out"].items()
                  if legs["one"].get("rows")
                  and legs["one"]["shown"] != legs["one"]["rows"]}
        assert hiding == {}, hiding


@needs_node
class TestMany:
    """`UX-367`: the size people build at, not the size a fixture has."""

    #: Empty since `UX-413`, and empty is the measurement: every
    #: published population is bounded at 120, whether or not it has a
    #: column worth ranking by and whether it is drawn as rows or as
    #: cards. It held five entries when this sweep was written - four
    #: tables with nothing numeric in them, which got no preset control
    #: and therefore no bound, and `findings`, which draws articles and
    #: which the row bound could not see at all.
    UNBOUNDED = {}

    def test_a_long_population_opens_bounded(self, swept):
        drawn_whole = {}
        for key, legs in swept["out"].items():
            seen = _seen(legs["many"])
            # The header row rides along with the body, so a table's
            # bound is `BOUND` rows plus it; a card or a pair has no
            # header, so `BOUND` is the whole allowance.
            allowed = BOUND + (1 if legs["many"].get("rows") else 0)
            if seen and seen[0] > allowed:
                drawn_whole[key] = seen[0]
        assert drawn_whole.keys() == self.UNBOUNDED.keys(), (
            f"drawing every one of {MANY} at once: {drawn_whole}; the "
            f"ledger says {sorted(self.UNBOUNDED)}")

    def test_no_control_singularises_a_population(self, swept):
        """`UX-412`'s other direction, and the reason this clause
        exists at all: a `plural` that dropped the count test entirely
        still passed every clause in `TestOne`, because `1 row` is what
        those assert. Agreement is two claims, and the many leg is
        where the second one can be read."""
        lying = {}
        for key, legs in swept["out"].items():
            said = [*(legs["many"].get("copies") or []),
                    *(legs["many"].get("badges") or [])]
            wrong = [text for text in said
                     if re.search(r"\b(?!1\b)[\d,]+ row\b", text)]
            if wrong:
                lying[key] = wrong
        assert lying == {}, lying

    def test_a_bounded_table_says_what_it_is_bounding(self, swept):
        """`UX-208`: a reader who cannot see the denominator cannot
        tell a filtered table from a small one."""
        silent = {}
        for key, legs in swept["out"].items():
            seen = _seen(legs["many"])
            if key in self.UNBOUNDED or not seen or seen[0] == seen[1]:
                continue
            badges = legs["many"].get("badges") or []
            if not any(f" of {MANY}" in badge for badge in badges):
                silent[key] = badges
        assert silent == {}, silent

    def test_the_bound_holds_at_the_threshold_the_viewer_declares(
            self, swept):
        """The ledger's other half: everything not in it is bounded to
        the viewer's own number, so raising `TABLE_OPENS_BOUNDED_ABOVE`
        without saying so moves this rather than passing quietly."""
        bounded = {key: _seen(legs["many"])
                   for key, legs in swept["out"].items()
                   if key not in self.UNBOUNDED and _seen(legs["many"])}
        assert bounded, "nothing was bounded; the sweep measured nothing"
        over = {key: seen for key, seen in bounded.items()
                if seen[0] > BOUND + 1}
        assert over == {}, over
