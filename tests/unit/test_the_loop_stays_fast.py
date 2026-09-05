"""UX-336: the levers that made the loop fast, held in place.

Four of them are configuration, and configuration rots silently: a
`Makefile` target loses a flag in a merge, a dev extra is dropped when
someone tidies `pyproject.toml`, and the suite goes back to ten minutes
without anything going red. The wall-clock numbers themselves are *not*
guarded — they are a property of the machine, and a guard on them would
fail on a slower laptop for no defect. What is guarded is that the
mechanism is still wired up, and that the selector still selects.

holds: rules.md#make-test-touching-while-you-work-the-tier-when-it-is-wider
holds: rules.md#a-number-or-mechanism-you-moved-annotate-the-file-asserting-it
"""
import functools
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task
import dev_touching

MAKEFILE = (REPO / "Makefile").read_text(encoding="utf-8")
PYPROJECT = (REPO / "pyproject.toml").read_text(encoding="utf-8")


class _Done:
    """What `subprocess.run` hands back, for a `main()` that must not
    actually start pytest."""

    def __init__(self, returncode, stdout):
        self.returncode, self.stdout, self.stderr = returncode, stdout, ""


class TestTheSuiteStillRunsInParallel:

    def test_every_test_target_carries_the_parallel_flag(self):
        """375s -> 148.7s in the audit's trial, 642s -> 194s re-measured
        here. A target that loses `$(PYTEST_XDIST)` gets the old number
        back and says nothing."""
        targets = re.findall(r"^(test[a-z-]*):\n\t(.+)$", MAKEFILE, re.M)
        assert targets, "no test targets found; the Makefile shape moved"
        missing = [name for name, body in targets
                   if "pytest" in body and "$(PYTEST_XDIST)" not in body]
        assert not missing, (
            f"{missing} run pytest without $(PYTEST_XDIST). Every tier runs "
            "parallel or the loop is back where UX-336 found it.")

    def test_the_flag_defaults_to_auto_and_can_be_turned_off(self):
        assert re.search(r"^PYTEST_XDIST \?= -n auto$", MAKEFILE, re.M), (
            "PYTEST_XDIST is not defaulted to `-n auto`, or is no longer "
            "overridable with `?=` - the off switch is what makes `-x` and "
            "`pdb` usable")

    def test_xdist_is_a_declared_dev_dependency(self):
        assert "pytest-xdist" in PYPROJECT, (
            "pytest-xdist is not in the dev extras, so a fresh "
            "`pip install -e '.[dev]'` cannot run `make test`")
        assert '"pytest-xdist' in PYPROJECT.split("[project.optional-dependencies]")[1].split("\n]")[0], (
            "pytest-xdist is mentioned but not in the dev extra list")

    def test_ci_still_runs_the_small_tier_single_process(self):
        """The one thing parallelism can hide: an ordering assumption.
        CI runs the tier both ways so a test that only passes because
        xdist happened to separate it cannot ship."""
        ci = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "PYTEST_XDIST= " in ci, (
            "no CI step runs a tier single-process; a suite that is only "
            "ever run parallel has untested parallel-safety")


@functools.lru_cache(maxsize=1)
def _selection_sizes():
    """`{module: how many files a one-module diff selects}`.

    `UX-662`: the two clauses below are two readings of one sweep, and
    each ran it - `select()` greps every test file per module, so the
    pair cost twice what the measurement does. Cached because the tree
    does not change inside a run; the clauses that vary the map
    replace `dev_touching.touch_map` and never reach here.
    """
    return {m: len(dev_touching.select([m])[0])
            for m in dev_touching.touch_map()}


class TestTheSelectorStillSelects:

    # `UX-606`: measured over all 85 mapped modules, not one. The
    # ceilings sit above min 11 / median 17 / p90 40 / max 124
    # (`UX-624`, which added the `from x import y` spelling) with room,
    # so ordinary drift is quiet and a shape change is loud.
    CEILING = {"median": 20, "p90": 45, "max": 130}
    POPULATION_FLOOR = 60
    #: `UX-645`: **11 census + 14 of your own**. The census floor is
    #: inside this bound because those files run - the figure is what
    #: pytest is handed - and it is the same 11 under all 87 mapped
    #: modules, so 44% of the bound is spent before a module's own
    #: tests are counted. Derived below rather than trusted.
    HANDFUL = 25
    CENSUS_FLOOR = 11

    # Wide because the module's name is how a test invokes it, not
    # because the selector is wrong. `UX-606` argued each one.
    WIDE = {
        "bga/cli.py", "tools/bga_view.py", "tools/bst_native_build_tracer.py",
        "bga/ingest/models.py", "bga/report/text.py", "bga/analyzer.py",
        "tools/bga_snapshot.py", "bga/run_store.py", "bga/compare.py",
        "bga/findings.py", "tools/native_trace/trackevent.py",
        "tools/bga_timeline.py", "tools/native_trace_to_chrome_trace.py",
        "tools/bst_extract_run.py", "bga/tools_dispatch.py",
        "bga/attribution/blame_chain.py", "bga/correlate.py",
        "bga/report/json.py", "tools/native_trace/bwrap_shim.py",
        "bga/schemas.py", "bga/report/_shared.py",
        # `UX-624`: 14 -> 27. A one-word stem is not a token, so every
        # one of its 16 importers reached it only as `from bga import
        # contracts`; the width is those edges, not a looser rule.
        "bga/contracts.py",
        # `UX-644`: 36 = 23 map + 11 census + 4 named. The first member
        # here that is wide by map and not by name: its entry is 23,
        # one under `MAP_ENTRY_CAP`, so it counts in full.
        "bga/report/rate.py",
    }

    def test_a_one_module_change_selects_a_handful_not_the_suite(self):
        """The worked example, and `UX-606` measured the population it
        used to stand for. `store_aggregate` is a distinctive two-word
        name, which is why 25 holds here; the selector's own contract
        is the distribution below.

        `UX-606` measured min 11 / median 16 / p90 38 / max 116;
        `UX-624` re-measured it at min 11 / median 17 / p90 40 / max
        124 after the import spelling joined the grep."""
        selected, _ = dev_touching.select(["bga/store_aggregate.py"])
        assert 1 <= len(selected) <= 25, (
            f"a one-module diff selected {len(selected)} files. The point is "
            "to be faster than the tier; selecting everything is not.")
        assert "tests/unit/test_the_aggregate_says_what_it_mixes.py" in selected, (
            "the file whose whole subject is the changed module was not "
            f"selected: {selected}")

    def test_the_selection_is_a_fraction_of_the_suite(self):
        """`UX-606`. The claim `store_aggregate` used to carry alone,
        measured over every module the map names — 85 of them against
        456 test files:

            min 11 · median 16 · p90 38 · max 116 (`bga/cli.py`, 25%)

        The ceilings carry headroom over those, and each failure names
        the figure it read, because the point is a selector faster than
        the tier and not a number for its own sake."""
        sizes = sorted(_selection_sizes().values())
        assert len(sizes) >= self.POPULATION_FLOOR, (
            f"only {len(sizes)} modules in the map — the population is "
            f"broken, not the selector")
        total = len(dev_touching.test_files())
        got = {"median": sizes[len(sizes) // 2],
               "p90": sizes[int(0.9 * len(sizes))],
               "max": sizes[-1]}
        over = {k: v for k, v in got.items() if v > self.CEILING[k]}
        assert not over, (
            f"the selection outgrew its measured shape: {got} against "
            f"{self.CEILING}, over a suite of {total} files")

    def test_the_wide_modules_are_named_and_not_merely_tolerated(self):
        """The clause that makes a *new* wide module loud. Width is
        honest in two shapes, so the old ≤25 bound was the wrong one:
        by **name**, where the module's name is what a test says to
        invoke it — 116 files name `bga.cli` because they run the CLI
        — and by **map**, where a coverage entry under
        `MAP_ENTRY_CAP` carries a module tests never name
        (`UX-644`: `bga/report/rate.py`, 23 of its 36). A module
        joining or leaving the set has to be argued here, beside its
        name."""
        wide = {m for m, size in _selection_sizes().items()
                if size > self.HANDFUL}
        assert wide == self.WIDE, (
            f"joined: {sorted(wide - self.WIDE)}; "
            f"left: {sorted(self.WIDE - wide)}")

    def test_an_over_wide_map_entry_is_not_a_selection(self, monkeypatch):
        """`UX-605`. `--cov-context=test` attributes a module's
        import-time lines to every test that imports it, so the map CI
        adopted in `0bc5aff` named 200 of 449 files for
        `bga/progress.py`. A selection that wide is not one."""
        wide = dev_touching.test_files()[:dev_touching.MAP_ENTRY_CAP + 1]
        monkeypatch.setattr(dev_touching, "touch_map",
                            lambda: {"bga/store_aggregate.py": wide})
        selected, why = dev_touching.select(["bga/store_aggregate.py"])
        assert len(selected) <= 25, (
            f"the map widened the selection to {len(selected)}")
        assert not [n for n in selected if "map" in why.get(n, [])], (
            "an entry over the bound still contributed to the selection")

    def test_a_narrow_entry_in_the_same_map_is_still_used(self, monkeypatch):
        """The half that stops the cap becoming 'ignore the map'. The
        import chain a grep cannot see is why `UX-524` exists."""
        unrelated = "tests/unit/test_the_loop_stays_fast.py"
        monkeypatch.setattr(
            dev_touching, "touch_map",
            lambda: {"bga/store_aggregate.py": [unrelated],
                     "bga/progress.py": dev_touching.test_files()})
        selected, why = dev_touching.select(["bga/store_aggregate.py"])
        assert unrelated in selected and "map" in why[unrelated], (
            f"a one-file map entry was dropped with the wide ones: {why}")

    def test_the_map_in_the_tree_says_which_entries_it_cannot_use(self):
        """`wide_entries()` is what `--why` prints, so it is derived
        here rather than trusted. Written first as "every reported
        entry is over the cap", it stayed green when the reporter was
        made to report nothing - vacuous both ways. Equality reddens.

        48 of 85 on the map `0bc5aff` adopted; 0 on a clean map, which
        is the same assertion."""
        mapped = dev_touching.touch_map()
        cap = dev_touching.MAP_ENTRY_CAP
        derived = {k: len(v) for k, v in mapped.items() if len(v) > cap}
        assert dev_touching.wide_entries() == derived, (
            "what --why reports is not what the map holds")

    def test_the_bound_is_a_census_floor_plus_the_module_s_own(self):
        """`UX-645`. The bound means two things at once unless the
        floor inside it is named, and a named floor rots unless it is
        derived: 25 is `11 + 14` only while the census is 11 files."""
        floor = len(dev_touching.census_set())
        assert floor == self.CENSUS_FLOOR, (
            f"the census is {floor} files, not {self.CENSUS_FLOOR} - the "
            f"bound now means {self.HANDFUL - floor} of a module's own "
            f"tests, and `HANDFUL`'s note says otherwise")
        assert 0 < floor < self.HANDFUL, floor

    @pytest.mark.parametrize("module", ["bga/store_aggregate.py",
                                        "bga/cli.py"])
    def test_the_floor_is_under_every_module_and_not_a_selection(
            self, module):
        """The half that makes the arithmetic true rather than stated.
        Measured over all 87 mapped modules, every selection carries
        the whole census set and the narrowest is the floor itself; the
        two here are the median-ish and the widest.

        The narrow end is deliberately not named: this file is one the
        selector greps, so a module named here stops being a module no
        test names (it moved the published figure 11 -> 12 when it
        was, which is the measurement destroying its own subject)."""
        census = set(dev_touching.census_set())
        whole = set(dev_touching.select([module])[0])
        assert census <= whole, (
            f"{module} is missing {sorted(census - whole)} of the census "
            f"floor, so the floor is not a floor")
        own = set(dev_touching.select([module], census=False)[0])
        assert whole - own <= census, (
            f"{module}: {sorted(whole - own - census)} appeared with the "
            f"census and is not a census file")

    def test_a_change_nothing_names_is_a_finding_the_floor_cannot_hide(
            self, monkeypatch, capsys):
        """`UX-645`'s consequence, and why the two populations are
        reported. One of the 87 mapped modules selects the floor and
        nothing else; keyed on the whole selection the tool called that
        a pass, because the floor is never empty. The module is not
        named here for the reason the clause above gives."""
        census = dev_touching.census_set()
        monkeypatch.setattr(dev_touching, "changed_files",
                            lambda *a, **_: ["bga/nothing_names_this.py"])
        monkeypatch.setattr(
            dev_touching, "select",
            lambda *a, **_: (census, {n: ["census"] for n in census}))
        monkeypatch.setattr(dev_touching.subprocess, "run",
                            lambda *a, **k: _Done(0, "1 passed in 0.1s"))
        dev_touching.main([])
        said = capsys.readouterr().err
        assert "No test file names any of 1 changed file(s)" in said, said
        assert "not a pass" in said, said

    def test_the_split_is_reported_and_not_only_the_total(self):
        """A count a reader takes for "tests that see my change" when
        44% of it is the same under every module."""
        census = dev_touching.census_set()
        why = {n: ["census"] for n in census}
        why[census[0]] = ["census", "bga/cli.py"]
        named = dev_touching.naming([*census, "tests/unit/test_cli.py"], why)
        assert named == [census[0], "tests/unit/test_cli.py"], named

    def test_a_changed_test_file_runs_itself(self):
        selected, _ = dev_touching.select(
            ["tests/unit/test_the_loop_stays_fast.py"])
        assert "tests/unit/test_the_loop_stays_fast.py" in selected

    def test_a_shared_harness_change_selects_everything(self):
        """The honest edge: `conftest.py` and `tiers.py` are changes to
        every test, and a selector that pretended otherwise would be
        wrong on exactly the days it matters."""
        selected, why = dev_touching.select(["tests/conftest.py"])
        assert len(selected) == len(dev_touching.test_files())
        assert "*" in why

    def test_a_documentation_change_selects_the_guards_that_read_it(self):
        selected, _ = dev_touching.select(["docs/guides/cli.md"])
        assert "tests/unit/test_docs_links_and_commands.py" in selected, (
            "a guide changed and the guard that reads guides was not "
            f"selected - grep, not the import graph, is the whole reason "
            f"this works: {selected}")

    def test_a_one_word_module_stem_is_not_used_as_a_token(self):
        """`findings` is also an English word this project uses
        constantly - measured, 57 files matched against 7 for
        `store_aggregate`. The stem is only distinctive with a `_`."""
        assert "findings" not in dev_touching.tokens_for("bga/findings.py")
        assert "store_aggregate" in dev_touching.tokens_for(
            "bga/store_aggregate.py")


class TestAnImportIsASpellingTheGrepKnows:
    """`UX-624`. A one-word stem is not a token, so `bga/schemas.py` was
    spelled only `bga.schemas` - and its 70 importers all write `from
    bga import schemas`. The map covered for that until `UX-605` capped
    it, and then `test_every_number_says_what_it_is.py`, which is the
    census of every declared quantity, stopped being selected at all.
    """

    GUARD = "tests/unit/test_every_number_says_what_it_is.py"

    def test_the_map_entry_really_is_over_the_cap(self):
        """Non-vacuity, first: the clause below claims the *grep* now
        reaches the guard. That claim is empty unless the map cannot -
        so read the width the cap rejects rather than assuming it."""
        entry = dev_touching.touch_map().get("bga/schemas.py", ())
        assert len(entry) > dev_touching.MAP_ENTRY_CAP, (
            f"bga/schemas.py maps {len(entry)} files, inside the "
            f"{dev_touching.MAP_ENTRY_CAP} cap - this item's premise is gone "
            f"and the clause below no longer tests the grep")
        assert self.GUARD in entry, (
            f"{self.GUARD} is not in the map entry either - the item's "
            f"subject has moved")

    def test_the_guard_the_cap_dropped_is_selected_again(self):
        """The acceptance clause. `--why` has to say the changed path,
        not `map` or `census`: those are the two routes that would make
        this pass without the grep having improved at all."""
        selected, why = dev_touching.select(["bga/schemas.py"])
        assert self.GUARD in selected, (
            f"{self.GUARD} reads every declared quantity in bga/schemas.py "
            f"and a schemas-only diff selected {len(selected)} files without "
            f"it")
        assert why[self.GUARD] == ["bga/schemas.py"], (
            f"selected, but not by the grep: {why[self.GUARD]}")

    def test_another_name_written_first_still_matches(self):
        """`from bga import contracts, schemas` is the same import as
        `from bga import schemas`, and 25 edges across 8 modules hung
        on which name the author happened to write first."""
        pattern = re.compile(dev_touching.import_pattern("bga/schemas.py"))
        for line in ("from bga import schemas",
                     "from bga import contracts, schemas",
                     "from bga import provenance, contracts, schemas"):
            assert pattern.search(line), line

    def test_it_does_not_match_a_longer_name_that_starts_the_same(self):
        """The false edge the word boundary buys: a sibling module
        whose name extends this one is a different module."""
        pattern = re.compile(dev_touching.import_pattern("bga/schemas.py"))
        assert not pattern.search("from bga import schemas_registry")
        assert not pattern.search("from bga.viewer import schemas")

    def test_a_package_init_is_still_not_a_spelling(self):
        """`UX-522` removed `__init__` as a token because fifteen
        packages' inits each 'selected' the skip census. This door does
        not reopen it."""
        assert dev_touching.import_pattern("bga/graph/__init__.py") is None
        assert dev_touching.import_pattern("docs/guides/cli.md") is None


class TestTheCloseHelperRefusesTheJudgementParts:

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    def test_check_reports_a_clean_tree_as_clean(self):
        done = self._run("--check")
        assert done.returncode == 0, done.stdout + done.stderr

    def test_the_outcome_skeleton_leaves_every_measurement_blank(self):
        """A pre-filled figure is an invitation to the unmeasured claim
        the `verify` skill exists to prevent.

        `UX-506` restated this from one literal phrase to the property:
        **every fenced block is a placeholder**. The literal made the
        clause a copy of the skeleton's wording, so rewording it reddened
        a guard about measurement for a reason that had nothing to do
        with one.
        """
        import re
        done = self._run("UX-336", "--outcome", "--round", "47")
        assert done.returncode == 0, done.stderr
        fences = re.findall(r"```text\n(.*?)```", done.stdout, re.S)
        assert fences, "the skeleton asks for no pasted output at all"
        for body in fences:
            assert body.strip().startswith("<") and body.strip().endswith(">"), (
                f"the skeleton pre-fills a measurement: {body.strip()!r}")
        for heading in ("## Outcome", "Mutations verified red and reverted",
                        "Deviation from the Required Fix"):
            assert heading in done.stdout, heading

    @staticmethod
    def _backlog_with_an_open_row(tmp_path):
        """A copy of the backlog with one synthetic open row in it.

        Both refusals below need an id that is open and has no Outcome.
        They used to name a real one, and `UX-337` closing turned this
        file red for a reason that had nothing to do with the loop -
        the guard was coupled to which task happened to be unfinished.
        A row this test writes itself cannot go stale, and the copy is
        deliberate: falsifying the refusal made the clause perform the
        move, and a guard that edits the repository when the code under
        test misbehaves is worse than what it is testing.
        """
        import shutil

        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        uid, slug = "UX-999", "UX-0999-a-row-this-guard-wrote"
        (scenarios / f"{slug}.md").write_text(
            f"# {uid}: a row this guard wrote\n\n"
            f"**Priority:** Low | **Status:** \U0001f534 Not Started | "
            f"**Serves:** nobody | **Topic:** guards\n\n"
            f"## Motivation\n\nNo Outcome section, which is the point.\n",
            encoding="utf-8")
        readme = scenarios / "README.md"
        text = readme.read_text(encoding="utf-8")
        marker = "\n## UX-333"
        assert marker in text, "the open table's end moved"
        row = (f"| {uid} | [a row this guard wrote]({slug}.md) | guards "
               f"| Low | — | \U0001f534 |\n")
        readme.write_text(text.replace(marker, "\n" + row + marker, 1),
                          encoding="utf-8")
        return uid, scenarios

    def test_move_refuses_without_the_one_line_nobody_can_write_for_you(
            self, tmp_path):
        uid, scenarios = self._backlog_with_an_open_row(tmp_path)
        done = self._run(uid, "--move", "--scenarios", str(scenarios))
        assert done.returncode != 0
        assert "--note" in done.stderr

    def test_move_refuses_a_task_file_with_no_outcome(self, tmp_path):
        uid, scenarios = self._backlog_with_an_open_row(tmp_path)
        before = (scenarios / "README.md").read_bytes()
        done = self._run(uid, "--move", "--note", "x" * 20,
                         "--scenarios", str(scenarios))
        assert done.returncode == 2, done.stdout + done.stderr
        assert "no Outcome section" in done.stderr, done.stderr
        assert (scenarios / "README.md").read_bytes() == before, (
            "a refused --move still wrote to the index")

    def test_the_verify_skill_cites_the_helper(self):
        """A scaffold nobody is told about is a scaffold nobody uses."""
        skill = (REPO / ".claude/skills/verify/SKILL.md").read_text(
            encoding="utf-8")
        assert "dev_close_task.py" in skill
        assert "make test-touching" in skill


class TestTheIndexIsDerivedNotMerged:
    """`UX-501`: the two aggregates at the top of the backlog index.

    The `N scenarios: **M open**` sentence and the per-topic table say
    nothing the row lists do not already say. Hand-maintained, they were
    the line every parallel track collided on. Measured on two branches
    of a throwaway repository, each closing one item, with `--move`
    writing the counts as it used to:

    ```text
    CONFLICT (content): Merge conflict in scenarios/README.md
    506 scenarios: **16 open**, 490 closed.      <- 14 rows
    ```

    Both halves at once: the topic table conflicted (the two items'
    topic rows are adjacent, so git reads them as one hunk) and the
    counts sentence *auto-merged* - both sides had written the same
    decrement from the same base - into a number neither branch meant
    and nothing then checked.

    So `move` stops writing them, `--check --write` derives them from
    the rows once after the merge, and a fourth `--check` property
    asserts the derivation ran.
    """

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    def test_the_index_says_what_its_rows_say(self):
        """The tree's own header against the derivation. This is the
        clause that catches a header edited by hand, in either
        direction."""
        sentence, table = close_task.index_header()
        text = (REPO / "docs/backlog/scenarios/README.md").read_text(
            encoding="utf-8")
        assert sentence in text, (
            "the counts sentence is not what the rows say; run "
            "`python tools/dev_close_task.py --check --write`")
        assert table in text, (
            "the topic table is not what the rows say; run "
            "`python tools/dev_close_task.py --check --write`")

    def test_the_totals_account_for_every_row(self):
        """The property the hand-written table failed: its Total column
        summed to **495** over 504 rows, so nine items were in no topic
        at all and nothing said which. A derived table cannot lose one -
        every row lands in a bucket, `unclassified` included."""
        _sentence, table = close_task.index_header()
        totals = [int(line.split("|")[3])
                  for line in table.splitlines() if line.startswith("| ")
                  and not line.startswith("| Topic")]
        rows = (len(close_task.row_ids(close_task.INDEX))
                + len(close_task.row_ids(close_task.CLOSED)))
        assert sum(totals) == rows, (
            f"the topic table accounts for {sum(totals)} of {rows} rows")

    def test_no_row_is_left_in_the_unclassified_bucket(self, monkeypatch):
        """`UX-507`: the bucket is empty, and this is the clause that
        says so.

        The acceptance test named `test_the_totals_account_for_every_row`
        for this, and that clause **does not discriminate**: its property
        - every row lands in a bucket - holds *with* `unclassified`
        present, by design, and its own docstring says so. Measured by
        the track that classified the rows: dropping one `**Topic:**`
        header left it green while the derived table grew
        `| unclassified | 0 | 1 |`. So the bucket needs a clause of its
        own, and this is it.
        """
        unknown = sorted(uid for uid, topic in close_task.topics().items()
                         if topic == close_task.TOPIC_UNKNOWN)
        assert unknown == [], (
            f"{len(unknown)} row(s) are in no topic: {unknown[:5]}. Every "
            f"task file carries a `**Topic:**` header from UX-507 on; a "
            f"new one filed without it lands here")

    def test_the_bucket_is_still_reachable(self, tmp_path, monkeypatch):
        """The clause above passes on an empty set, which is how a guard
        stops discriminating (`UX-512`, same round). This runs the
        mutation the acceptance test asks for - drop one header - as a
        standing clause rather than by hand, on a copy, and reads the
        derived table for the bucket that must reappear.

        `TOPIC_UNKNOWN` therefore stays in `dev_close_task.py`. `UX-507`'s
        Required Fix said it "can go" and its Out of Scope forbade
        touching the tool; the Out of Scope is right, and this is why -
        the fallback is what reports a row filed without a header, and
        deleting it would make the next such row silently uncounted.
        """
        import shutil
        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        victim = next(iter(sorted(scenarios.glob("UX-0001-*.md"))))
        text = victim.read_text(encoding="utf-8")
        assert "**Topic:**" in text, victim.name
        victim.write_text(re.sub(r" \| \*\*Topic:\*\* [a-z]+", "", text,
                                 count=1), encoding="utf-8")

        monkeypatch.setattr(close_task, "SCENARIOS", scenarios)
        monkeypatch.setattr(close_task, "INDEX", scenarios / "README.md")
        monkeypatch.setattr(close_task, "CLOSED", scenarios / "closed.md")
        of = close_task.topics()
        assert [uid for uid, topic in of.items()
                if topic == close_task.TOPIC_UNKNOWN] == ["UX-01"], (
            "dropping a `**Topic:**` header did not put that row in the "
            "unclassified bucket, so the clause above would pass over a "
            "row nobody classified")
        _sentence, table = close_task.index_header()
        assert "| unclassified | 0 | 1 |" in table, table

    def test_a_hand_edited_count_is_reported_and_then_restored(
            self, tmp_path):
        """The acceptance test's mutation, on a copy. `--check` alone
        must report and not repair: a checker that silently fixed what
        it checks could never fail, which is the rot the whole `--check`
        list exists to avoid."""
        import shutil
        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        readme = scenarios / "README.md"
        was = readme.read_text(encoding="utf-8")
        readme.write_text(
            re.sub(r"^\d+ scenarios: \*\*\d+ open\*\*", "999 scenarios: **7 open**",
                   was, count=1, flags=re.M), encoding="utf-8")

        told = self._run("--check", "--scenarios", str(scenarios))
        assert told.returncode == 1, told.stdout
        assert "the counts sentence says" in told.stdout, told.stdout
        assert readme.read_text(encoding="utf-8") != was, (
            "`--check` repaired the file it was asked to check")

        fixed = self._run("--check", "--write", "--scenarios", str(scenarios))
        assert fixed.returncode == 0, fixed.stdout
        assert readme.read_text(encoding="utf-8") == was, (
            "`--write` did not restore the header the rows imply")

    def test_write_needs_check(self):
        """`--write` on its own would be a command that edits the index
        and says nothing about it."""
        done = self._run("--write")
        assert done.returncode != 0
        assert "give both" in done.stderr, done.stderr

    def test_closing_a_task_no_longer_writes_the_aggregates(self):
        """The change itself, read off the source rather than run: a
        `move` that writes the header puts both tracks on the same line
        again, and the clause above would still pass because a single
        close computes the right number.

        Read as text because the discriminating case is a two-branch
        merge, and this file is the fast tier."""
        body = (REPO / "tools/dev_close_task.py").read_text(encoding="utf-8")
        move = body.split("def move(", 1)[1].split("\ndef ", 1)[0]
        assert "write_index()" not in move, (
            "`move` writes the derived header again, so two tracks each "
            "closing one item collide on it - UX-501's own measurement")
        assert "--check --write" in move, (
            "`move` neither writes the header nor says what does")

    def test_the_merge_recipe_is_written_down(self):
        """A tool nobody is told to run after a merge is a tool that
        does not run after a merge."""
        skill = (REPO / ".claude/skills/decompose/SKILL.md").read_text(
            encoding="utf-8")
        assert "--check --write" in skill, (
            "the decompose skill's shared-files section does not name the "
            "command that resolves the counts")


class TestTheSkeletonFitsTheRegister:
    """`UX-506`: the shape the skeleton asks for is the shape that fits.

    Counted over round 74's range (`UX-440`..`UX-496`), under the
    skeleton `UX-336` printed:

    ```text
    Outcomes written              56
    median length                117 lines
    longest                      284
    over the 80-line cap         45   (80 %)
    ```

    The skeleton was never over the cap - the prose under it was - but
    it *invited* the prose: a heading reading "what the fix had to be,
    and why that shape" asks for a narrative and gets one. It is gone;
    what the headings now name is what a later round reads.

    Two things the skeleton must keep, and a clause each. It seeds
    `dev_process_bands.py`'s census - the phrases that tool counts are
    printed by this skeleton and by nothing else - and it states the cap,
    so a session sees the budget while writing rather than when the
    guard reds.
    """

    def _printed(self):
        return close_task.OUTCOME_SKELETON.format(
            round="NN", date="YYYY-MM-DD", n=2,
            cap=close_task.OUTCOME_CAP)

    def test_the_skeleton_seeds_the_process_census(self):
        """`dev_process_bands.py` counts phrases this repository already
        writes by convention rather than fields anyone fills in - and the
        convention is this skeleton. A reworded heading silently drops a
        row of a census over 288 closed items to zero, and nothing else
        would say so."""
        import dev_process_bands as bands
        printed = self._printed()
        for key in ("falsified",):
            pattern = next(p for k, _h, p in bands.SIGNALS if k == key)
            assert pattern.search(printed), (
                f"the skeleton no longer prints what `{key}` counts; "
                f"dev_process_bands.py reads the committed record for "
                f"this phrase and would report 0 %")
        assert "Deviation from the Required Fix" in printed, (
            "the deviation heading is what `deviated` is measured from, "
            "in both directions")

    def test_it_leaves_room_under_the_cap(self):
        """A skeleton that filled the budget would make the cap
        unreachable, which is a different defect from the one this item
        is about."""
        printed = len(self._printed().strip().splitlines())
        assert printed < close_task.OUTCOME_CAP * 0.6, (
            f"the skeleton is {printed} lines of a {close_task.OUTCOME_CAP}-"
            f"line budget; there is no room left for the measurements")

    def test_it_states_the_cap_the_guard_holds(self):
        """One copy. A skeleton that names a different number than the
        guard enforces sends every session to the wrong budget."""
        assert str(close_task.OUTCOME_CAP) in self._printed(), (
            "the skeleton does not tell a session what the budget is")
        source = (REPO / "tests/unit/test_the_register_is_terse.py").read_text(
            encoding="utf-8")
        assert f"OUTCOME_CAP = {close_task.OUTCOME_CAP}" in source, (
            f"the tool prints a cap of {close_task.OUTCOME_CAP} and the "
            f"guard holds a different one")

    def test_it_asks_for_no_narrative(self):
        """The heading this item removed, by name. A skeleton that asks
        "why that shape" gets a page of design history, and the task
        file is not where design history goes - the register is."""
        printed = self._printed()
        for asked in ("why that shape", "Counts are what the run printed"):
            assert asked not in printed, (
                f"the skeleton still asks for {asked!r}")
class TestTheDerivedCountSeesAnUnstagedRow:
    """`UX-617`: `--check` answers "is the tree I am about to commit
    consistent", and `git ls-files` reads the **index**.

    A task file written and not yet staged is invisible to it, so the
    natural order - write the row, derive the counts, stage, commit -
    shipped the count one short and the helper reported clean:

    ```text
    $ python tools/dev_close_task.py --check
    0 problem(s) over 5 propert(y/ies), 617 backlog row(s)
    $ git add … && make test
    FAILED test_a_counted_figure_is_derived.py::…[scenarios]
      architecture.md says 619 …; git has 620
    ```

    Four times in round 84, each costing a full-suite run. The
    population is now the index **plus** untracked and non-ignored -
    what a commit from here would carry.
    """

    @staticmethod
    def _repo(tmp_path):
        """A git repo with one committed scenario file and one written
        but unstaged, plus the opening sentence that counts them."""
        repo = tmp_path / "repo"
        (repo / "docs/backlog/scenarios").mkdir(parents=True)
        (repo / "docs/backlog/tasks").mkdir(parents=True)
        (repo / "docs/design").mkdir(parents=True)
        (repo / "docs/backlog/scenarios/UX-0001-committed.md").write_text(
            "# UX-1\n", encoding="utf-8")
        (repo / "docs/design/architecture.md").write_text(
            "It counts 1 `docs/backlog/scenarios/` files and "
            "0 `docs/backlog/tasks/` files.\n\n## Chapter\n\n1 more.\n",
            encoding="utf-8")
        for argv in (["init", "-q"],
                     ["config", "user.email", "a@b"],
                     ["config", "user.name", "a"],
                     ["add", "docs", "-f"],
                     ["commit", "-qm", "one"]):
            subprocess.run(["git", *argv], cwd=repo, check=True,
                           capture_output=True, text=True)
        (repo / "docs/backlog/scenarios/UX-0002-unstaged.md").write_text(
            "# UX-2\n", encoding="utf-8")
        return repo

    @staticmethod
    def _pointed_at(repo, monkeypatch):
        monkeypatch.setattr(close_task, "REPO", repo)
        monkeypatch.setattr(close_task, "SCENARIOS",
                            repo / "docs/backlog/scenarios")
        monkeypatch.setattr(close_task, "ARCHITECTURE",
                            repo / "docs/design/architecture.md")

    def test_the_count_is_what_a_commit_from_here_would_carry(
            self, tmp_path, monkeypatch):
        """One file in the index, one written beside it. The index's
        answer is 1 and the commit's is 2."""
        repo = self._repo(tmp_path)
        self._pointed_at(repo, monkeypatch)
        assert close_task._backlog_counts()["scenarios"] == 2, (
            "the derived count still reads the index alone, so a row "
            "written and not yet staged ships the count one short")

    def test_check_names_the_unstaged_row_instead_of_reporting_clean(
            self, tmp_path, monkeypatch):
        """`UX-617`'s acceptance test. The count alone reads as "the
        sentence is stale"; the name says which half of the tree
        moved, which is the thing four sessions had to work out."""
        repo = self._repo(tmp_path)
        self._pointed_at(repo, monkeypatch)
        problems = close_task._architecture_is_derived()
        assert len(problems) == 1, problems
        assert "UX-0002-unstaged.md" in problems[0], (
            f"`--check` reported a count mismatch without naming the "
            f"file that is not staged: {problems[0]}")

    def test_a_nested_worktree_and_an_ignored_file_are_not_counted(
            self, tmp_path, monkeypatch):
        """The half `UX-577` bought and this widening could have spent.
        A checkout holds `.claude/worktrees/<agent>/`, a whole second
        copy of the tree; git lists it as one entry and does not
        descend, and `--exclude-standard` drops what `.gitignore`
        names. A recursive glob counts both."""
        repo = self._repo(tmp_path)
        (repo / ".gitignore").write_text(
            "*.scratch.md\n", encoding="utf-8")
        (repo / "docs/backlog/scenarios/notes.scratch.md").write_text(
            "x\n", encoding="utf-8")
        subprocess.run(["git", "worktree", "add", "-q",
                        ".claude/worktrees/agent-1", "-b", "w1"],
                       cwd=repo, check=True, capture_output=True, text=True)
        self._pointed_at(repo, monkeypatch)
        assert close_task._backlog_counts()["scenarios"] == 2, (
            "the count grew past the two files in `docs/backlog/"
            "scenarios/` - an ignored file or the copy of the whole "
            "tree under `.claude/worktrees/` is being counted (UX-577)")

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    @staticmethod
    def _index_off_by_a_count(tmp_path):
        """A backlog copy whose counts sentence disagrees with its rows."""
        import shutil
        scenarios = tmp_path / "scenarios"
        shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
        readme = scenarios / "README.md"
        readme.write_text(
            re.sub(r"^\d+ scenarios: \*\*\d+ open\*\*",
                   "999 scenarios: **7 open**",
                   readme.read_text(encoding="utf-8"), count=1, flags=re.M),
            encoding="utf-8")
        return scenarios

    def test_write_names_the_files_it_changed(self, tmp_path):
        """The second shape, and the one that caught the row filing
        `UX-617`: `--write` also rewrites the index's counts sentence,
        so a caller who staged before deriving ships the rewrite
        unstaged. A `--write` that says nothing cannot be re-staged
        after."""
        scenarios = self._index_off_by_a_count(tmp_path)
        done = self._run("--check", "--write", "--scenarios", str(scenarios))
        assert done.returncode == 0, done.stdout + done.stderr
        assert "--write changed 1 file(s)" in done.stdout, (
            "`--write` rewrote the index and did not say so\n" + done.stdout)
        assert "README.md" in done.stdout.split("--write changed")[1], (
            "`--write` says it changed something without naming it\n"
            + done.stdout)

    def test_write_says_so_when_it_changed_nothing(self, tmp_path):
        """The clause that stops the report becoming "it always writes".
        Measured on the tree: a derived index rewrites nothing, and a
        caller told to stage a file that did not move stages noise."""
        scenarios = self._index_off_by_a_count(tmp_path)
        self._run("--check", "--write", "--scenarios", str(scenarios))
        again = self._run("--check", "--write", "--scenarios", str(scenarios))
        assert "--write changed no file(s)." in again.stdout, (
            "a second `--write` over a derived index still reports a "
            "change\n" + again.stdout)


class TestTheCloseHelperRunsTheGrepNobodyRan:
    """`UX-493`: fixing guide §3.6's grep, run rather than remembered.

    Round 73 moved `golden`'s export bound 406,000 -> 411,000 and left
    `UX-479`'s Outcome saying it stands. The verdict stays judgement -
    `UX-132` declined to make that a test - but the grep is not, and
    the grep is the half that was skipped.
    """

    #: The real shape: a Python literal moved, prose that quotes it.
    MOVED = ("--- a/tests/unit/test_the_report_you_can_attach.py\n"
             "+++ b/tests/unit/test_the_report_you_can_attach.py\n"
             "@@ -664,1 +664,1 @@\n"
             '-    ("golden", GOLDEN, 406_000),\n'
             '+    ("golden", GOLDEN, 411_000),\n')
    SAYS_IT = ("# UX-479\n\n## Outcome\n\n"
               "golden's 406,000 stands. Both recorded figures were stale.\n")

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"),
             "--figures", *argv],
            capture_output=True, text=True, cwd=str(REPO), timeout=120)

    @staticmethod
    def _scenarios(tmp_path, says=SAYS_IT):
        where = tmp_path / "scenarios"
        where.mkdir()
        (where / "UX-0479-a-bound.md").write_text(says, encoding="utf-8")
        return where

    @staticmethod
    def _diff(tmp_path, text):
        path = tmp_path / "the.diff"
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_moved_figure_the_backlog_still_writes_is_named(self, tmp_path):
        where = self._scenarios(tmp_path)
        done = self._run("--diff", str(self._diff(tmp_path, self.MOVED)),
                         "--scenarios", str(where))
        assert done.returncode == 0, done.stdout + done.stderr
        assert "406,000" in done.stdout, done.stdout
        assert "UX-0479-a-bound.md:5" in done.stdout, (
            "the diff writes 406_000 and the backlog writes 406,000; a "
            "reader matching the literal spelling sees neither\n"
            + done.stdout)

    def test_the_same_commits_own_record_does_not_cancel_the_figure(
            self, tmp_path):
        """`UX-469` wrote `406,000 -> 411,000` into its own task file.

        Subtracting added figures across the whole diff cancels exactly
        the figure the commit moved, and the replay printed nothing.
        Kept per file.
        """
        diff = self.MOVED + (
            "--- a/docs/backlog/scenarios/UX-0469-fields.md\n"
            "+++ b/docs/backlog/scenarios/UX-0469-fields.md\n"
            "@@ -215,0 +215,1 @@\n"
            "+`golden`'s bound moved 406,000 -> 411,000 with the split.\n")
        where = self._scenarios(tmp_path)
        done = self._run("--diff", str(self._diff(tmp_path, diff)),
                         "--scenarios", str(where))
        assert "UX-0479-a-bound.md:5" in done.stdout, done.stdout

    def test_a_figure_nothing_writes_is_reported_clean_not_silently(
            self, tmp_path):
        where = self._scenarios(tmp_path, says="# UX-479\n\nNo figure.\n")
        done = self._run("--diff", str(self._diff(tmp_path, self.MOVED)),
                         "--scenarios", str(where))
        assert done.returncode == 0, done.stdout + done.stderr
        assert "1 figure(s) removed" in done.stdout, done.stdout
        assert "none still written" in done.stdout, (
            "a clean run has to say it checked, not print nothing\n"
            + done.stdout)

    def test_the_closing_items_own_file_is_not_reported_against_itself(
            self, tmp_path):
        where = self._scenarios(tmp_path)
        done = self._run("UX-479", "--diff",
                         str(self._diff(tmp_path, self.MOVED)),
                         "--scenarios", str(where))
        assert "none still written" in done.stdout, done.stdout
