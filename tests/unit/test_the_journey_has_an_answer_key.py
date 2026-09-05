"""UX-402: the journey the guides describe, walked by a guard.

Round 45's stranger walk found four bugs forty-four feature rounds
never saw; round 63's found ten more; round 64's found six - among them
a silent forfeiture of all of Plane 2 (`UX-405`) that no test noticed,
because no test walks the journey. The walks are the highest-yield
detector this project has and they run only when an audit round
remembers to.

`examples/06-macro-micro-optimization` is deliberately mis-optimized in
three independently-fixable ways, one per level of the cycle, and each
one is a claim the tool should make on its own:

1. **macro / graph shape** - `lib-a..lib-f` are declared as a six-deep
   chain although none reads another's output;
2. **macro / over-declared dependency** - every `lib-*` build-depends
   on `codegen.bst` and only `lib-f` consumes it;
3. **micro / inside one element** - `core.bst` carries
   `variables: notparallel: True`, so its translation units compile
   one at a time.

That is an **answer key**, which is what lets this assert analytic
outcomes rather than exit codes. Measured walking it here:

```text
bga doctor (no project)              0.6s
cold snapshot (bst build all.bst)   43.9s
incremental snapshot                 3.2s
analyze / correlate / export        ~1s each
```

**The cache is isolated, and that is the point.** `XDG_CACHE_HOME`
moves into the temporary tree, so the first snapshot really builds -
against the host's own cache every element is a hit, every duration is
zero, and every clause below would pass over an empty run. It also
means the guard never touches the developer's artifacts.
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

from bga.findings import CHAIN_BOUND_RATIO

EXAMPLE = REPO / "examples/06-macro-micro-optimization"

#: `UX-456`: how chain-dominated this fixture's cold build has to stay,
#: as against `CHAIN_BOUND_RATIO`, which is what the *verdict* turns on
#: and is not a thing a guard can assert of a measured build. Twenty
#: cold builds of `examples/06` on one machine:
#:
#: ```text
#: n=20   min 0.853143   median 0.859264   max 0.916457
#: below the 0.9 line: 19 of 20
#: ```
#:
#: plus CI's two lowest, 0.888 and 0.897. 0.75 sits 0.103 under the
#: lowest of those twenty-two and 1.6 whole observed ranges below it.
CHAIN_BOUND_FLOOR = 0.75

#: `UX-538`: the same cold build, captured once and committed. The
#: ranking clause reads this rather than a build it performs, because
#: what a live build ranks depends on the box - measured below.
RECORDED = REPO / "tests/fixtures/macro_micro/run"

#: How far `core.bst` leads the runner-up on that recording. Three
#: `analyze` runs of the committed bytes:
#:
#: ```text
#: core 12.05s   runner-up codegen.bst 7.0s   margin 1.7214  x3
#: ```
#:
#: identical every time, because the input is a file. 1.25 sits 0.47
#: under it and above every margin a loaded build produced (1.00-1.48,
#: `UX-489`), so a fixture edited until `core.bst` stops dominating
#: reddens this and an analyzer that moves the number a little does not.
CORE_LEAD_FLOOR = 1.25

#: Answer 1 as the project *declares* it: `lib-a..lib-f` six deep, none
#: reading the one before. `UX-543` asserts this of the recording, for
#: the reason measured on the clause.
DECLARED_CHAIN = (("lib-a.bst", "lib-b.bst"), ("lib-b.bst", "lib-c.bst"),
                  ("lib-c.bst", "lib-d.bst"), ("lib-d.bst", "lib-e.bst"),
                  ("lib-e.bst", "lib-f.bst"))

node = shutil.which("node")

#: One string each, so `UX-213`'s skip census counts them once.
NO_NODE = "node is not installed"
NO_CHROME = "no chrome/chromium for the geometry guards (set BGA_CHROME)"

#: The tail this file appends to the shared probe. The probe boots the
#: export's own inline module; this reads back the two facts `UX-388`
#: is about - which sections were drawn empty, and whether each says so.
#:
#: "Says so" is the presence of a real `.empty-population` sentence,
#: not one phrase. Round 80 measured why: `UX-536` gave one section a
#: better sentence and the phrase test called it silent.
_TAIL = """
const found = [];
// `report`, not `body`: the page appends its sections into the element
// it looks up by id, which this shim synthesises detached. A walk from
// `body` alone finds nothing and reads as "the page drew no empty
// section", which is the very defect UX-388 was filed on - a harness
// that reports it falsely is worse than one that cannot see it.
(function walk(n) {
  for (const c of n.children ?? []) {
    if (String(c.tagName).toLowerCase() === "section"
        && c.attrs["data-empty"] !== undefined) {
      // The **sentence**, not one wording of it. `UX-536` gave
      // `element_join_coverage` its own - "these are not zeros that
      // were measured", which is the truer thing to say and does not
      // contain "found none" - and this clause read the phrase, so a
      // section that said something better read as saying nothing.
      let says = false;
      (function sentence(m) {
        for (const k of m.children ?? []) {
          if (String(k.attrs?.class ?? "").includes("empty-population")
              && (k.textContent || "").trim().length > 20) says = true;
          sentence(k);
        }
      })(c);
      found.push([c.attrs["data-section"] ?? null, says]);
    }
    walk(c);
  }
})(report);
console.log("EMPTY " + JSON.stringify({ found, error }));
"""


def leads(ranked, uid):
    """Whether `uid` is among the horizon rows tied for the top saving.

    `UX-489`: not `ranked[0]["element_uid"] == uid`. Under load this
    fixture's top two savings tie outright on 4 runs of 7, and which of
    a tied pair sorts first is `max()`'s tie-break, not a fact about
    the graph.
    """
    if not ranked:
        return False
    best = max(row.get("saving_us") or 0 for row in ranked)
    return any(row["element_uid"] == uid and (row.get("saving_us") or 0) == best
               for row in ranked)


def _empty_sections(probe_output):
    """[(section, says "found none")], as the probe read them."""
    return sorted(tuple(row) for row in probe_output)

#: One string, so the skip census counts it once (`UX-213`).
WHY_SKIPPED = (
    "the journey needs bst, bwrap and example 06's staged toolchain "
    "(files/toolchain, written by generate_sources.py)")
walkable = pytest.mark.skipif(
    not (shutil.which("bst") and shutil.which("bwrap")
         and (EXAMPLE / "files" / "toolchain").exists()),
    reason=WHY_SKIPPED)

pytestmark = [pytest.mark.large, walkable]


def _run(argv, cwd, env, timeout=600):
    done = subprocess.run(argv, capture_output=True, text=True, cwd=str(cwd),
                          env=env, timeout=timeout)
    return done


@pytest.fixture(scope="module")
def walked(tmp_path_factory):
    """The journey, once: doctor, two snapshots, and what they wrote."""
    into = tmp_path_factory.mktemp("journey")
    project = into / "project"
    # `symlinks=True`: the staged toolchain is a tree of symlinks into
    # the host, several of them dangling, and a copy that resolves them
    # fails on the first one.
    shutil.copytree(EXAMPLE, project, symlinks=True,
                    ignore=shutil.ignore_patterns(".bga", "optimized"))
    env = {**os.environ,
           "PYTHONPATH": str(REPO),
           # The whole point of the isolation: a cold cache, and the
           # developer's own artifacts untouched.
           "XDG_CACHE_HOME": str(into / "cache")}

    doctor = _run([sys.executable, "-m", "tools.bga_doctor", str(project)],
                  project, env, timeout=300)
    cold = _run([sys.executable, "-m", "tools.bga_snapshot",
                 "--", "bst", "build", "all.bst"], project, env)
    assert cold.returncode == 0, cold.stdout[-4000:] + cold.stderr[-4000:]
    warm = _run([sys.executable, "-m", "tools.bga_snapshot",
                 "--", "bst", "build", "all.bst"], project, env)
    assert warm.returncode == 0, warm.stdout[-4000:] + warm.stderr[-4000:]

    runs = sorted((project / ".bga" / "runs").iterdir())
    assert len(runs) == 2, [p.name for p in runs]
    return {"project": project, "env": env, "doctor": doctor,
            "cold": cold, "warm": warm,
            "cold_run": str(runs[0] / "run"), "warm_run": str(runs[1] / "run")}


def _json(walked, argv):
    done = _run([sys.executable, "-m", "bga.cli", *argv],
                walked["project"], walked["env"], timeout=300)
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def cold(walked):
    return _json(walked, ["analyze", walked["cold_run"], "--format", "json"])


@pytest.fixture(scope="module")
def recorded():
    """`UX-538`: the same fixture's cold build, captured once and kept.

    The ranking clause reads this instead of a build it performs, so
    the number it asserts does not depend on how loaded the box is."""
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze",
         str(RECORDED), "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def joined(walked):
    return _json(walked, ["correlate", walked["cold_run"], "--format", "json"])


@pytest.fixture(scope="module")
def recorded_join():
    """`UX-543`: the two planes of the recording `recorded` ranks.

    The chain clause reads this instead of a build it performs: the
    finding keeps only edges whose endpoints the run put on the
    critical path, so a live capture's answer moves with the box.
    `correlate` on the committed bytes at loadavg 9.03, x3: 18 edges,
    `saving_us` 24150000, identical.
    """
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "correlate",
         str(RECORDED), "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def exported(walked, tmp_path_factory):
    """The incremental run as an export, and the probe's reading of it.

    The boot is the one every navigation guard uses, so this reads the
    document a reader gets rather than one assembled here."""
    import tools.bga_view as view

    if node is None:
        pytest.skip(NO_NODE)
    into = tmp_path_factory.mktemp("incremental")
    page = into / "incremental.html"
    view.export(walked["warm_run"], str(page))
    html = page.read_text(encoding="utf-8")
    (into / "inline.mjs").write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text(
        encoding="utf-8").split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]
    (into / "probe.mjs").write_text(probe + _TAIL, encoding="utf-8")
    done = subprocess.run(
        [node, str(into / "probe.mjs")], capture_output=True, text=True,
        cwd=REPO, timeout=120,
        env=dict(os.environ, PAGE=str(page), MOD=str(into / "inline.mjs"),
                 PROTOCOL="file:",
                 BGA_DOM_SHIM=str(REPO / "tests/dom_shim.mjs")))
    assert done.returncode == 0, done.stderr[-3000:]
    line = [ln for ln in done.stdout.splitlines()
            if ln.startswith("EMPTY ")][-1]
    read = json.loads(line[len("EMPTY "):])
    assert read["error"] is None, read["error"]
    return {"page": page, "probe": read["found"]}


class TestTheJourneyRuns:
    """Exit codes first - the floor the analytic clauses stand on."""

    def test_the_doctor_reports_on_the_project(self, walked):
        said = walked["doctor"].stdout
        assert "bga doctor" in said, said[-2000:]
        assert "bst-present" in said and "bwrap-works" in said, said[-2000:]

    def test_the_first_snapshot_is_the_first_of_this_project(self, walked):
        assert "first snapshot of this project" in walked["cold"].stdout

    def test_the_second_says_what_it_is_comparing(self, walked):
        """`UX-126`: the loop is one command run twice, and the second
        run is where the comparison comes from."""
        assert "bga compare @prev @last" in walked["warm"].stdout

    def test_the_capture_kept_both_planes(self, walked):
        beside = pathlib.Path(walked["cold_run"]).parent
        for name in ("analyze.json", "plane2.json", "build.log"):
            assert (beside / name).exists(), sorted(
                p.name for p in beside.iterdir())


class TestWhatTheAnswerKeyMayAssertAboutALiveBuild:
    """`UX-489`: `leads` is the predicate, exercised without a build.

    The clause it serves runs a real `bst build` and cannot be driven
    to its own edges - which is how an exact-first-place assertion
    survived until a loaded run falsified it. These synthesise the
    horizon instead, so the boundary between "tied for the top" and
    "genuinely behind" is checkable in milliseconds.
    """

    @staticmethod
    def _horizon(*pairs):
        return [{"element_uid": uid, "saving_us": saving}
                for uid, saving in pairs]

    def test_a_clear_leader_leads(self):
        assert leads(self._horizon(("core.bst", 6_000_000),
                                   ("codegen.bst", 3_000_000)), "core.bst")

    def test_a_tie_still_leads(self):
        """4 of 7 loaded builds tied outright; on a tie the order is
        `max()`'s tie-break, not a fact about the graph."""
        assert leads(self._horizon(("lib-b.bst", 5_000_000),
                                   ("core.bst", 5_000_000)), "core.bst")

    def test_genuinely_behind_does_not_lead(self):
        """The half that must still fail: an element really overtaking
        `core.bst` is the fixture losing its shape, and reports."""
        assert not leads(self._horizon(("lib-c.bst", 9_000_000),
                                       ("core.bst", 5_000_000)), "core.bst")

    def test_absent_does_not_lead(self):
        assert not leads(self._horizon(("lib-c.bst", 9_000_000)), "core.bst")

    def test_an_empty_horizon_does_not_lead(self):
        assert not leads([], "core.bst")


class TestTheMacroAnswer:
    """1 and 2 of the answer key: the chain, and the edge nobody reads."""

    def test_the_headline_follows_its_own_published_numbers(self, cold):
        """`UX-456`. This clause used to read

            assert headline["diagnosis"] == "chain_bound"

        which asserts which side of `CHAIN_BOUND_RATIO` a **measured**
        `bst build` landed on. It went red twice in round 71, on heads
        whose diffs could not have moved it:

            ea122e5   chain_share 0.897052541648868   -> scheduler_bound
            799b144   chain_share 0.888022115348203   -> scheduler_bound

        and twenty cold builds of this same fixture, measured for the
        item, say the clause was not near the line at all - it was on
        the wrong side of it and passing on load:

            n=20   min 0.853143   median 0.859264   max 0.916457
            below the 0.9 line: 19 of 20

        Nineteen. What kept it green was the runner: CI's two
        excursions are *higher* than this machine's median, so the
        share moves with the load rather than with the build. That is
        the fixing guide's "ratio at the noise floor" in a guard rather
        than an instrument, and worse than the filing supposed.

        What is asserted instead is the **rule**, which is a function of
        two numbers the headline publishes and cannot be decided by a
        runner: the verdict follows the share against the line, whatever
        the build did. `test_the_first_screen_is_a_decision.py` is where
        the two branches are held against fixtures whose numbers are
        fixed - the golden run at 0.875 and `examples/06` at 0.936 - so
        moving this clause off the threshold loses no coverage of the
        classification itself.
        """
        headline = cold["headline"]
        share, line = headline["chain_share"], headline["chain_bound_share"]
        assert share is not None, headline
        assert line == CHAIN_BOUND_RATIO, headline
        expected = "chain_bound" if share >= line else "scheduler_bound"
        assert headline["diagnosis"] == expected, headline

    def test_the_headline_sentence_carries_the_share_it_decided_on(
            self, cold):
        """`UX-220`'s rule on the same field, and side-independent: both
        sentences quote the measured share and the line, so a reader can
        see how close this run sat without re-deriving anything."""
        headline = cold["headline"]
        said = headline["sentence"]
        assert f"{headline['chain_share']:.0%}" in said, said
        assert f"{CHAIN_BOUND_RATIO:.0%}" in said, said
        assert "chain" in said, said

    def test_the_fixture_is_still_a_chain_dominated_build(self, cold):
        """What the answer key actually needs from this build, stated
        with room the runner cannot cross.

        The chain share is *the* property `examples/06` exists to have -
        an answer key drawn on a build whose critical path was a third
        of wall-clock would be answering a different question - so it
        has to be asserted, and asserting nothing about it would make
        the clause above satisfiable by any build at all.

        `CHAIN_BOUND_FLOOR` is sized from the measurement rather than
        chosen: twenty cold builds spanned **0.853 to 0.916**, a range
        of 0.063, and CI's two lowest were 0.888 and 0.897. 0.75 is
        0.103 below the lowest of the twenty-two - about 1.6 times the
        whole observed range - so a loaded runner cannot reach it and a
        round that really does drain the chain still will.
        """
        share = cold["headline"]["chain_share"]
        assert share >= CHAIN_BOUND_FLOOR, (
            f"the cold fixture's critical path is {share:.1%} of "
            f"wall-clock, under the {CHAIN_BOUND_FLOOR:.0%} this fixture "
            f"is kept above; UX-456 measured 0.853-0.916 over twenty cold "
            f"builds, so this is a change in the fixture rather than in "
            f"the runner")

    def test_the_first_thing_to_fix_is_core(self, recorded):
        """`core.bst` is what the six libraries all wait for, so a
        ranking that does not put it at the front has lost the graph -
        asserted of a **recorded** capture, not a live one.

        `UX-489` moved this from exact first place to "tied for the
        top" and it still went red three times in round 80, three
        different ways. Measured on a 4-core box, `examples/06` cold,
        `analyze` on the result - the load the guard must survive is
        the round's own four-track workflow:

        ```text
        load  first in the horizon        core   best   core leads
          1   core.bst                    10.0   10.0   yes
          4   codegen.bst x4              18-22  40-42  no, 0 of 4
          8   codegen.bst                 14-20  20-25  no, 0 of 3
        ```

        At four concurrent workers `codegen.bst` takes the top saving by
        about **2x** in every run. No floor rescues that: the leader
        changes, so `UX-538` took the other option and the ranking now
        reads the committed bytes of the same build. The live capture
        keeps a clause of its own below - that it still produces a
        horizon naming `core.bst` - which is the half load cannot move.
        """
        ranked = recorded["optimization_horizon"]
        assert ranked, "the recorded horizon is empty"
        assert leads(ranked, "core.bst"), [
            (row["element_uid"], row.get("saving_us")) for row in ranked[:3]]
        core = next(row.get("saving_us") or 0 for row in ranked
                    if row["element_uid"] == "core.bst")
        runner_up = max((row.get("saving_us") or 0) for row in ranked
                        if row["element_uid"] != "core.bst")
        assert core >= runner_up * CORE_LEAD_FLOOR, (
            f"core.bst saves {core / 1e6:.2f}s against the runner-up's "
            f"{runner_up / 1e6:.2f}s, a margin of {core / max(runner_up, 1):.2f} "
            f"under the {CORE_LEAD_FLOOR} this recording is kept above; "
            f"UX-538 measured 1.7214 on it three times, so this is the "
            f"fixture or the ranking rule moving, not the runner")

    def test_a_live_capture_still_ranks_something(self, cold):
        """The half a loaded box cannot move, kept live: the build the
        journey really performs still produces a horizon at all.

        Only that. Which element leads is asserted of the recording
        above, because at 4 concurrent workers `codegen.bst` led 4 of 4.
        `core.bst` being *named* was the next thing this clause tried to
        hold, and one 8-way run of `UX-538`'s sweep dropped it out of
        the horizon altogether - so under load not even its presence is
        a fact about this build. A non-empty horizon is; a run with a
        28s chain that ranks nothing is the analyzer, not the box.
        """
        ranked = cold["optimization_horizon"]
        assert ranked, "the horizon is empty on a run with a 28s chain"

    def test_the_terminal_says_it_too(self, walked):
        """The same answer, in the words a reader actually meets."""
        said = walked["cold"].stdout
        assert "core.bst is the first thing to fix" in said, said[-3000:]

    def test_the_never_read_edges_are_the_declared_chain(self, recorded_join):
        """Answer 1, measured: the six libraries are chained and none of
        them reads the one before it - asserted of a **recorded**
        capture, as `UX-538` asserts the ranking one clause up.

        `_unread_gating_edges` keeps only edges whose *both* endpoints
        the run measured onto the critical path, so which links reach
        the finding is a reading of the box as well as of the graph.
        `UX-543` swept it - one capture under N-way CPU contention on a
        4-core machine, `correlate` on the result:

        ```text
        loadavg  workers  wall           chain links in the finding
          0.98-7.68   1    30.9-33.3s    5 of 5, x3
          6.52-6.77   4    28.9-35.7s    5 of 5, x3
          8.03-9.16   8    38.2-42.4s    5 of 5, x4
        ```

        Ten of ten here and one red in round 80: a failure that cannot
        be produced on demand, and **no floor is available for it** - a
        link is in the finding or it is not, and set membership has no
        margin to sit a number under. So the input becomes bytes. The
        live capture keeps `test_a_live_capture_still_finds_a_chain`
        below, and answer 1's other half - which dependency each
        element never opened - stays live in the clause after that,
        because element rows are not filtered by the critical path.
        """
        findings = recorded_join["restructuring"]
        assert findings, "the join found no restructuring opportunity"
        edges = {tuple(edge) for edge in findings[0]["edges"]}
        for before, after in DECLARED_CHAIN:
            assert (before, after) in edges, sorted(edges)

    def test_a_live_capture_still_finds_a_chain(self, joined):
        """The half a loaded box cannot move, kept live: the build the
        journey really performs still reports the six libraries chained
        by an edge nobody reads.

        *Which* links, and all five of them, is asserted of the
        recording above - round 80's live one carried four. One is the
        floor the measured spread cannot cross: `UX-543`'s ten runs at
        loadavg 0.98-9.16 each carried five of five, round 80's red
        carried four, and a build that has stopped being a chain at all
        carries none. So this reddens on the fixture losing its shape
        and not on the runner losing a link.
        """
        findings = joined["restructuring"]
        assert findings, "the join found no restructuring opportunity"
        edges = {tuple(edge) for edge in findings[0]["edges"]}
        assert edges & set(DECLARED_CHAIN), sorted(edges)

    def test_codegen_is_named_unused_by_the_libraries_that_declare_it(
            self, joined):
        """Answer 2. The finding above chains the elements; *which*
        dependency each element never opened is on the element's own
        row, which is where a reader looking at `lib-a.bst` finds it.
        """
        rows = {row["element"]: row for row in joined["elements"]}
        named = [key for key in ("lib-a.bst", "lib-b.bst", "lib-c.bst",
                                 "lib-d.bst", "lib-e.bst")
                 if "codegen.bst" in (rows.get(key, {}).get(
                     "unused_dependencies") or [])]
        assert len(named) >= 4, {
            key: rows.get(key, {}).get("unused_dependencies")
            for key in rows}


class TestTheMicroAnswer:
    """3 of the answer key: `notparallel`, inside one element."""

    def test_plane_two_traced_the_build(self, cold):
        """`UX-405`'s class: a capture that silently forfeited Plane 2
        would leave every clause below vacuous, so the count is asserted
        before anything is read from it."""
        coverage = cold["plane2_coverage"]
        assert coverage["process_count"] > 100, coverage["process_count"]
        assert coverage["max_concurrency"] > 1, coverage

    def test_the_advice_names_notparallel(self, walked):
        """The one recommendation in this project that needs both
        planes: Plane 1 says `core.bst` is the longest, Plane 2 says it
        is not computing while it runs, and only the join can say why.
        """
        done = _run([sys.executable, "-m", "bga.cli", "correlate",
                     walked["cold_run"]],
                    walked["project"], walked["env"], timeout=300)
        assert done.returncode == 0, done.stderr[-2000:]
        assert "notparallel" in done.stdout, done.stdout[-3000:]
        assert "core.bst" in done.stdout

    def test_the_join_says_it_in_the_document_too(self, joined):
        core = [row for row in joined["elements"]
                if row["element"] == "core.bst"]
        assert core, [row["element"] for row in joined["elements"]]
        said = " ".join(rec["text"] for rec in core[0]["recommendations"])
        assert "notparallel" in said, said


class TestTheIncrementalRunIsStillAReport:
    """`UX-388`'s rule, on the run that produced it."""

    def test_the_incremental_run_has_empty_populations(self, walked):
        """The premise: this is the run whose sections vanished."""
        warm = _json(walked, ["analyze", walked["warm_run"],
                              "--format", "json"])
        empty = [key for key, value in warm.items()
                 if isinstance(value, list) and not value]
        assert empty, (
            "the incremental run published no empty collection, so this "
            "file is no longer walking the case UX-388 was filed on")

    def test_the_page_says_the_analysis_found_none(self, exported):
        """Read through the shared node probe, which now can read it.

        This clause needed a real Chrome until `UX-415`: the probe's
        `location.href` was a served URL whatever `PROTOCOL` said, and
        this run's trace is far too large to inline - so it is written
        as a *path*, resolved to `http:` against that base, and the
        boot died inside the Perfetto handoff on a detached element.
        That was the instrument, not the page. With the base following
        the protocol it is an export here as it is in a browser, and
        the clause below measures that the two agree."""
        drawn = _empty_sections(exported["probe"])
        assert drawn, (
            "the incremental page drew no empty section at all - which is "
            "exactly the disappearance UX-388 was filed on")
        silent = [section for section, says in drawn if not says]
        assert silent == [], silent

    def test_a_real_browser_reads_the_same_page(self, exported):
        """`UX-415`'s other half: the shim is only worth its speed if
        it agrees with the thing it stands in for. Chrome renders the
        same export and the two readings must match exactly - a probe
        that drifts from the browser is the defect this whole item is,
        one layer down."""
        from tests.browser import Browser, find_chrome

        chrome = find_chrome()
        if not chrome:
            pytest.skip(NO_CHROME)
        # `section[data-empty]`, not `[data-empty]`: the rail's own
        # link carries the same mark on purpose, so that the map of the
        # report matches the report on an incremental run. Selecting on
        # the bare attribute reads four anchors as four silent
        # sections.
        look = """(() => [...document.querySelectorAll('section[data-empty]')]
            .map((n) => [n.getAttribute('data-section'),
                         Boolean(n.querySelector('.empty-population')
                           && n.querySelector('.empty-population')
                                .textContent.trim().length > 20)]))()"""
        with Browser(chrome) as opened:
            seen = opened.measure(exported["page"].as_uri(), look, 1440, 900)
        assert sorted(map(tuple, seen)) == sorted(_empty_sections(
            exported["probe"])), (
            "the probe and the browser disagree about which sections are "
            "empty and which of them say so")
