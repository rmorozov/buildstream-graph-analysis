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
sys.path.insert(0, str(REPO))

import tiers

# `UX-421`: the half of `UX-363`'s inequality that a step timeout could
# not hold moved to the per-file rule, so this file now checks that
# rule rather than asserting about a wall clock.
from tools import dev_tier_drift as drift


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

    def test_the_floors_are_ordered_and_the_backstop_clears_them(self):
        assert tiers.MEDIUM_FLOOR_S < tiers.LARGE_FLOOR_S
        # `UX-421`: the backstop no longer has to be *reachable* by one
        # large file - the per-file rule catches that, and this catches
        # a hang. It still has to be above the tier plus such a file,
        # or it would red on the case the other instrument is reporting
        # and bury the legible message under a timeout.
        assert (tiers.SMALL_TIER_BACKSTOP_S
                > tiers.SMALL_TIER_CI_SLOW_S + tiers.LARGE_FLOOR_S)


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


def _code(path):
    """`path`'s source with string literals and comments removed.

    Round 67: the pattern above is a text scan, and a text scan cannot
    tell code from data. `test_the_agent_configuration_holds.py` names
    `find_chrome()` inside a *string* - it is test data for a hook that
    decides whether a skip is conditional - and was reported as a
    browser guard sitting in the small tier. It runs in 0.26s and boots
    nothing.

    The same defect, in the same week, as `.claude/hooks/no-bulk-add.sh`
    blocking a command that merely quotes the pattern it looks for, and
    as `UX-420`'s ratio judging a quantity at the noise floor: an
    instrument reading a proxy rather than the thing.

    Tokenising is the fix rather than a longer regex, because the class
    of confusion is unbounded and the token stream simply does not have
    it. A file that will not tokenise falls back to its raw text, which
    is the conservative direction: a false name is a red clause somebody
    reads, a missed one is a slow file nobody sees.
    """
    source = path.read_text(encoding="utf-8")
    try:
        import io
        import tokenize as _tokenize
        kept = [tok.string for tok in
                _tokenize.generate_tokens(io.StringIO(source).readline)
                if tok.type not in (_tokenize.STRING, _tokenize.COMMENT)]
    except Exception:                                  # pragma: no cover
        return source
    return " ".join(kept)


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
            if BOOTS_A_BROWSER.search(_code(REPO / path))
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
    STEPS = ((r"timeout (\d+) make test-small", "SMALL_TIER_BACKSTOP_S"),
             (r"PYTEST_XDIST= timeout (\d+) make test-small",
              "SMALL_TIER_BACKSTOP_1P_S"))

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

    def test_the_two_steps_are_different_lines_of_the_workflow(self):
        """The parallel step is matched by a prefix of the
        single-process step's line, so a regex that is too loose reads
        one line twice and calls it agreement. This is what makes the
        clause above a pair rather than the same check run twice.

        `UX-421` had to rewrite it: the two backstops are deliberately
        the *same* number now, so comparing the values no longer
        distinguishes anything and the old clause would have passed
        while reading one line twice. The positions are what differ.
        """
        workflow = self._workflow()
        where = {name: re.search(pattern, workflow).start()
                 for pattern, name in self.STEPS}
        assert len(set(where.values())) == 2, (
            f"both patterns matched the same workflow line: {where} - "
            f"the single-process step is going unchecked")

    @pytest.mark.parametrize("slowest,backstop", (
        ("SMALL_TIER_CI_SLOW_S", "SMALL_TIER_BACKSTOP_S"),
        ("SMALL_TIER_CI_SLOW_1P_S", "SMALL_TIER_BACKSTOP_1P_S")))
    def test_each_backstop_is_far_above_normal_running(self, slowest,
                                                       backstop):
        """`UX-421` retired `UX-363`'s inequality:

            measured  <  budget  <  measured + LARGE_FLOOR_S

        The right half was the job - one file above the large floor
        landing in the default tier had to trip it - and it is gone,
        because a wall-clock step timeout cannot do that job. Round 66
        is the proof: `test (3.9)` was killed at its 30s budget while
        3.10, 3.11 and 3.12 passed the same step on the same commit at
        26, 26 and 19s. Nothing about the tier differed. The bound was
        being asked to separate two causes it cannot see apart, and by
        round 67 the two halves left a second of room between them.

        What is left is the left half, with room: a backstop catches a
        hang, so it must sit far enough above ordinary running that no
        runner reaches it. `test_the_per_file_rule_is_what_catches_a
        _large_file_now` is where the retired half went.
        """
        slow = getattr(tiers, slowest)
        bound = getattr(tiers, backstop)
        assert bound >= slow * 3, (
            f"{backstop} is {bound}s against a slowest-seen {slow}s. A "
            f"backstop that close to normal running is a budget again, "
            f"and UX-421 is the record of why that does not work")
        assert bound == int(bound), (
            f"{backstop} is {bound}s, and a CI `timeout` is whole "
            f"seconds - there is no workflow line this can equal")

    def test_the_per_file_rule_is_what_catches_a_large_file_now(self):
        """The half the backstop gave up, held somewhere it works.

        A file above `LARGE_FLOOR_S` that has landed in the default
        tier reaches CI as a file whose seconds disagree with the
        reference's, and `tools/dev_tier_drift.py --against` reports it
        **by name** with the runner's shift already divided out. That
        is the property `UX-363`'s inequality was standing in for, and
        it is checked here against the real rule rather than asserted
        about a timeout.
        """
        reference = {f"tests/unit/test_small_{index}.py": 0.4
                     for index in range(60)}
        reference.update({f"tests/unit/test_real_{index}.py": 6.0
                          for index in range(30)})
        times = dict(reference)
        # One small file grows past the large floor - the exact event
        # the budget existed for - while the whole runner is 30% slower,
        # which is the confound that made the budget unusable.
        times = {name: seconds * 1.3 for name, seconds in times.items()}
        victim = "tests/unit/test_small_0.py"
        times[victim] = tiers.LARGE_FLOOR_S + 1.0
        verdict, _shift, rows = drift.against(times, {"files": reference})
        assert verdict == "drift", verdict
        assert [row[0] for row in rows] == [victim], rows

    def test_a_slower_runner_alone_is_not_reported(self):
        """The other direction, and the one the budget got wrong. The
        table from round 66 - four jobs of one run, spread 19s to 30s,
        tier unchanged - must stay quiet.

        **This clause needs a double mutation to redden, and that is a
        property of the rule rather than a weakness here.** Under a
        uniform shift `times[name] - known[name] * shift` is exactly
        zero for every file, so the seconds gate holds the row back
        whatever the ratio gate does - and `ratio / shift` is exactly
        1.0, so the ratio gate holds it back whatever the seconds gate
        does. Either gate alone is sufficient. Only P5, which makes
        *both* read the raw ratio, turns a slower runner into drift.

        Two wrong guesses were recorded before that was established -
        the first draft used 6s files on the theory that the seconds
        gate was doing the excluding, which is the `CLAUDE.md` defect
        of a guard whose setup another gate already excludes. The files
        are 20s now because at that size the arithmetic is legible in
        the fixture; it is not what makes the clause discriminate.
        """
        reference = {f"tests/unit/test_real_{index}.py": 20.0
                     for index in range(30)}
        for factor in (30.0 / 19.0, 1.3, 1.0):
            times = {name: seconds * factor
                     for name, seconds in reference.items()}
            verdict, _shift, rows = drift.against(times, {"files": reference})
            assert (verdict, rows) == ("ok", []), (factor, verdict, rows)

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
