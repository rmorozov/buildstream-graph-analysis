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
const records = Object.entries(payload)
  .filter(([, v]) => Array.isArray(v) && v.length
                     && v.every((r) => r && typeof r === "object"
                                        && !Array.isArray(r)))
  .map(([k]) => k);
const elsewhere = Object.keys(app.DRAWN_ELSEWHERE ?? {});
const swept = records.filter((k) => !elsewhere.includes(k));

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
      badges: all(section, (n) => (n.attrs?.class || "") === "badge")
        .map(text),
    };
  } catch (error) {
    return { threw: String(error && error.message) };
  }
};

const out = {};
for (const key of swept) {
  const lots = [];
  for (let i = 0; i < many; i++) lots.push(payload[key][i % payload[key].length]);
  out[key] = {
    zero: draw(key, []),
    one: draw(key, payload[key].slice(0, 1)),
    many: draw(key, lots),
  };
}

// Where the ordering authority files each of them. `chapterFor` reads
// the table first and the section's `bga:rail` second, exactly as the
// page does - so this is the chapter a reader would find it under.
const placed = {};
for (const key of swept) {
  const rail = app.hintsOf(schema.properties?.[key])[format.RAIL];
  placed[key] = chapters.chapterFor(key, rail);
}

process.stdout.write(JSON.stringify({
  records, elsewhere, swept, placed, out,
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
        """Every record population is either swept or has a written
        reason not to be. `DRAWN_ELSEWHERE` is that reason and it is a
        sentence per key, so this cannot be satisfied by a bare skip
        list."""
        missed = [key for key in swept["records"]
                  if key not in swept["swept"]
                  and key not in swept["elsewhere"]]
        assert missed == [], missed

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

    #: `UX-414`: two sections a reader only ever sees on a two-plane
    #: run land in the fallback chapter. `chapters.js` says that
    #: chapter "is not a hiding place" and points at
    #: `test_the_report_has_chapters`, which does assert it is empty -
    #: on a fixture with no Plane 2, where neither section exists.
    UNPLACED = {"restructuring": "UX-414", "binary_cost": "UX-414"}

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

    #: `UX-412`: `badgeText(1, 1)` returns `1 rows`. Every table that
    #: draws its own badge says it, which is why the ledger is the
    #: whole set rather than a couple of sections - one shared helper,
    #: one wrong sentence, nine places a reader meets it.
    PLURAL = {
        "readers": "UX-412",
        "next_steps": "UX-412",
        "critical_path_detail": "UX-412",
        "optimization_horizon": "UX-412",
        "latent_heavies": "UX-412",
        "serialization_point_risks": "UX-412",
        "restructuring": "UX-412",
        "binary_cost": "UX-412",
        "provenance": "UX-412",
    }

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
            many = legs["many"]
            # The header row rides along with the body, so the bound is
            # `BOUND` rows plus it.
            if many.get("shown", 0) > BOUND + 1:
                drawn_whole[key] = many["shown"]
            elif many.get("cards_shown", 0) > BOUND:
                drawn_whole[key] = many["cards_shown"]
        assert drawn_whole.keys() == self.UNBOUNDED.keys(), (
            f"drawing every one of {MANY} at once: {drawn_whole}; the "
            f"ledger says {sorted(self.UNBOUNDED)}")

    def test_a_bounded_table_says_what_it_is_bounding(self, swept):
        """`UX-208`: a reader who cannot see the denominator cannot
        tell a filtered table from a small one."""
        silent = {}
        for key, legs in swept["out"].items():
            many = legs["many"]
            if key in self.UNBOUNDED or not many.get("rows"):
                continue
            badges = many.get("badges") or []
            if not any(f" of {MANY}" in badge for badge in badges):
                silent[key] = badges
        assert silent == {}, silent

    def test_the_bound_holds_at_the_threshold_the_viewer_declares(
            self, swept):
        """The ledger's other half: everything not in it is bounded to
        the viewer's own number, so raising `TABLE_OPENS_BOUNDED_ABOVE`
        without saying so moves this rather than passing quietly."""
        bounded = {key: legs["many"]["shown"]
                   for key, legs in swept["out"].items()
                   if key not in self.UNBOUNDED and legs["many"].get("rows")}
        assert bounded, "nothing was bounded; the sweep measured nothing"
        assert all(shown <= BOUND + 1 for shown in bounded.values()), bounded
