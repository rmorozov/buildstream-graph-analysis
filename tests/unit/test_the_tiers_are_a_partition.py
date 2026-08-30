"""UX-238: the suite is four tiers, and the lists are exceptions.

`pytest tests/` is 373s. Measured per file, 160 of 220 files cost 18.2s
between them and 7 cost 159s - so a session that runs everything after
every edit spends six minutes to learn what twenty seconds would say.

The tiers are assigned from that measurement in `tests/tiers.py` and
applied by a collection hook, so no test file carries a marker by hand
and a new file inherits `small` for free. What that buys has to be paid
for by guards on three things: the lists name real files, the tiers
partition the suite, and the default tier stays fast.
"""
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))

import tiers  # noqa: E402  - needs the path above


def _test_files():
    return {p.relative_to(REPO).as_posix()
            for p in (REPO / "tests").rglob("test_*.py")}


class TestTheListsNameRealFiles:
    def test_every_listed_file_exists(self):
        """A renamed file leaves its line behind, and the line then
        tiers nothing - which is invisible, because the file it names
        silently becomes small."""
        listed = set(tiers.LARGE) | set(tiers.MEDIUM)
        missing = sorted(listed - _test_files())
        assert missing == [], (
            f"tests/tiers.py names file(s) that do not exist: {missing}")

    def test_no_file_is_in_two_tiers(self):
        both = sorted(set(tiers.LARGE) & set(tiers.MEDIUM))
        assert both == [], f"listed in both LARGE and MEDIUM: {both}"

    def test_the_floors_are_ordered_and_the_budget_clears_them(self):
        assert tiers.MEDIUM_FLOOR_S < tiers.LARGE_FLOOR_S
        # A single large file must be able to blow the small budget on
        # its own, or the budget cannot catch the thing it is for.
        assert tiers.SMALL_TIER_BUDGET_S > tiers.LARGE_FLOOR_S


#: `UX-403`: what a file has to be listed *for*.
#:
#: Every other clause in this file reads the two lists against each
#: other or against the filesystem, and the census found what that
#: cannot see: a file that belongs in a tier and is simply **absent**
#: from both lists is "small on purpose" and nothing says otherwise.
#: Deleting a 50-second entry from `LARGE` left this file green on all
#: fourteen clauses it had.
#:
#: Timing the suite from inside itself is what the module docstring
#: rejects, and rightly. What can be read without timing anything is
#: *construction*: a file that boots a real Chrome cannot be small, and
#: says so in its own imports. Four were, when this was written.
BOOTS_A_BROWSER = re.compile(r"from tests\.browser import|from browser import"
                             r"|find_chrome\(")


class TestNothingSlowByConstructionIsSmall:
    def test_every_browser_guard_is_listed(self):
        """The one class of slowness that is legible from the source.

        Not a proxy for the whole table being right - a file can be
        slow for a dozen reasons this cannot see, and `UX-418` carries
        the direction that needs a measurement. This is the direction
        that does not.
        """
        listed = set(tiers.LARGE) | set(tiers.MEDIUM)
        small = sorted(
            path for path in _test_files()
            if BOOTS_A_BROWSER.search((REPO / path).read_text(encoding="utf-8"))
            and path not in listed)
        assert small == [], (
            f"{len(small)} file(s) boot a real browser from the small "
            f"tier: {small}. Measure each with `--durations=0` and list "
            f"it in tests/tiers.py")

    def test_the_rule_has_something_to_check(self):
        """A pattern that stopped matching would empty the clause above
        and pass forever."""
        found = [path for path in _test_files()
                 if BOOTS_A_BROWSER.search(
                     (REPO / path).read_text(encoding="utf-8"))]
        assert len(found) > 20, (
            f"only {len(found)} browser guards found; the pattern has "
            f"stopped matching the harness")


class TestTheTiersPartitionTheSuite:
    def test_every_test_file_is_in_exactly_one_tier(self):
        """`small` is the default, so this is really: every file is
        listed at most once, and everything else is small on purpose."""
        files = _test_files()
        counts = {f: (f in tiers.LARGE) + (f in tiers.MEDIUM) for f in files}
        assert all(n <= 1 for n in counts.values())
        small = {f for f, n in counts.items() if n == 0}
        assert len(small) + len(tiers.LARGE) + len(tiers.MEDIUM) == len(files)
        assert small, "every file ended up listed - the default tier is empty"

    def test_the_hook_applies_the_marker_the_table_declares(self):
        """The table is data; this is the part that has to actually
        happen at collection time."""
        target = tiers.LARGE[0]
        for marker, expected in (("large", True), ("small", False)):
            out = subprocess.run(
                [sys.executable, "-m", "pytest", target, "-m", marker,
                 "--collect-only", "-q", "-p", "no:cacheprovider"],
                capture_output=True, text=True, cwd=REPO)
            collected = re.search(r"(\d+)/(\d+) tests collected", out.stdout) \
                or re.search(r"(\d+) tests? collected", out.stdout)
            got = bool(collected and int(collected.group(1)))
            assert got is expected, (
                f"{target} under -m {marker}: expected "
                f"{'tests' if expected else 'nothing'}, got {out.stdout[-300:]}")


class TestTheDefaultTierStaysFast:
    #: `UX-363`: the small tier runs twice in CI and each run has its
    #: own budget. The pairs are (what the workflow line looks like,
    #: the constant it has to equal).
    STEPS = ((r"timeout (\d+) make test-small", "SMALL_TIER_BUDGET_S"),
             (r"PYTEST_XDIST= timeout (\d+) make test-small",
              "SMALL_TIER_BUDGET_1P_S"))

    @staticmethod
    def _workflow():
        return (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    @pytest.mark.parametrize("pattern,constant", STEPS)
    def test_ci_enforces_the_budget_the_table_declares(self, pattern,
                                                       constant):
        """The budget is a timeout in CI rather than a wall-clock
        assertion in a test: timing a suite from inside itself is the
        kind of guard that goes flaky and then gets muted. What is
        checkable here is that the two numbers agree.

        `UX-363`: **both** steps, because for three rounds only one was
        checked. The old clause searched for the first `timeout` in the
        file and stopped, so the single-process step's number was
        guarded by nothing and could drift from the table freely.
        """
        workflow = self._workflow()
        assert "make test-small" in workflow, (
            "CI does not run the small tier, so its budget is unenforced")
        budget = re.search(pattern, workflow)
        assert budget, f"no small-tier step matching {pattern!r}, so no budget"
        declared = getattr(tiers, constant)
        # `int(declared)` was the comparison until round 66, and it
        # truncated: a declared 31.5 read as equal to `timeout 31`, so
        # the two copies could disagree by up to a second and this
        # clause - whose whole job is that they do not - saw nothing.
        # Found by mutating the constant rather than by reading it.
        # `timeout` takes whole seconds, so a fractional budget is not a
        # near-miss to be tolerated but a number CI cannot express.
        assert declared == int(declared), (
            f"{constant} is {declared}s, and a CI `timeout` is whole "
            f"seconds - there is no workflow line this can equal")
        assert int(budget.group(1)) == declared, (
            f"CI budgets {budget.group(1)}s, tests/tiers.py declares "
            f"{declared}s as {constant} - two copies of one number")

    def test_the_two_steps_have_different_numbers_from_each_other(self):
        """The parallel step is matched by a prefix of the
        single-process step's line, so a regex that is too loose reads
        one number twice and calls it agreement. This is what makes the
        clause above a pair rather than the same check run twice."""
        workflow = self._workflow()
        found = {name: int(re.search(pattern, workflow).group(1))
                 for pattern, name in self.STEPS}
        assert len(set(found.values())) == 2, (
            f"both steps read as the same budget: {found} - the patterns "
            f"are not distinguishing the two lines")

    @pytest.mark.parametrize("slowest,fastest,budget", (
        ("SMALL_TIER_CI_SLOW_S", "SMALL_TIER_CI_FAST_S",
         "SMALL_TIER_BUDGET_S"),
        ("SMALL_TIER_CI_SLOW_1P_S", "SMALL_TIER_CI_FAST_1P_S",
         "SMALL_TIER_BUDGET_1P_S")))
    def test_each_budget_is_reachable_and_still_a_bound(self, slowest,
                                                        fastest, budget):
        """`UX-363`, and the reason it was filed: a bound nothing can
        reach is not a bound.

            measured  <  budget  <  measured + LARGE_FLOOR_S

        The left half says the budget is not tripped by normal running.
        The right half is the job: one file above the large floor
        landing in the default tier has to trip it. For three rounds
        only the left half was true - 90s against a tier that each
        re-tier moved further down, until a file at *twice* the large
        floor tripped neither step and the guard that had caught three
        drifts would have missed the fourth.

        Re-measure both numbers when a re-tier moves the tier; that is
        the edit, and it moves the budgets with it rather than leaving
        them where a previous round happened to put them.
        """
        slow = getattr(tiers, slowest)
        fast = getattr(tiers, fastest)
        bound = getattr(tiers, budget)
        assert fast <= slow, (
            f"{fastest} ({fast}s) is not faster than {slowest} ({slow}s); "
            f"the two measurements are the wrong way round")
        # Each half against the measurement that makes it hard. The
        # first draft used one number for both and the second clause
        # then checked the bound against the *slow* run, which is the
        # side that makes any budget look sized: 32s passed against a
        # 21.4s tier while the same runner's 13.8s day let a floor-sized
        # file through. Caught by reading the first green run's log.
        assert slow < bound, (
            f"{budget} is {bound}s and the tier's slowest run measures "
            f"{slow}s - the budget is below normal running and will red "
            f"on an ordinary bad day")
        assert bound < fast + tiers.LARGE_FLOOR_S, (
            f"{budget} is {bound}s against a {fast}s tier at its fastest, "
            f"so a file of {tiers.LARGE_FLOOR_S}s - the large floor - can "
            f"land in the default tier without tripping it. That is the "
            f"slack `UX-363` was filed for; re-measure and restate rather "
            f"than widening this")

    def test_the_makefile_offers_every_tier(self):
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        for target in ("test-small", "test-medium", "test-large", "test-fast"):
            assert f"\n{target}:" in makefile, f"no `make {target}`"

    def test_the_markers_are_registered(self):
        config = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        for marker in ("small:", "medium:", "large:", "bst:"):
            assert marker in config, f"{marker} is not a registered marker"


class TestTheCensusKnowsItWasFiltered:
    """`UX-235`'s census checks the *suite's* skip tally. A tier run
    sees a third of it, and a hook that reported anyway would be
    claiming to have looked at what it did not - the exact shape that
    item exists to prevent.

    The first version of this guard built a session with `markexpr` set
    and asserted a clean exit. It passed with the gate deleted: the
    census is empty inside a one-file test run, so there was nothing to
    complain about either way. It plants a tally that *would* complain
    now, and checks both directions - which is the only way the gate is
    visible at all.
    """

    @staticmethod
    def _session(markexpr, monkeypatch):
        import conftest

        monkeypatch.setattr(
            conftest, "_SKIPS",
            {"a reason nobody declared": 40}, raising=False)

        class _Option:
            keyword = None

        _Option.markexpr = markexpr

        class _Manager:
            @staticmethod
            def get_plugin(_name):
                return None

        class _Config:
            option = _Option()
            args = ["tests"]
            pluginmanager = _Manager()

        class _Session:
            config = _Config()
            exitstatus = 0

        session = _Session()
        conftest.pytest_sessionfinish(session, 0)
        return session.exitstatus

    def test_a_tier_run_does_not_assert_a_whole_suite_census(self, monkeypatch):
        assert self._session("small", monkeypatch) == 0, (
            "a filtered run reported a whole-suite census")

    def test_an_unfiltered_run_still_does(self, monkeypatch):
        """The other direction, and the one that makes the first mean
        something: the same planted tally must fail a full run."""
        assert self._session("", monkeypatch) == 1, (
            "the census stopped firing on a full run - the gate is not a "
            "gate, it is an off switch")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
