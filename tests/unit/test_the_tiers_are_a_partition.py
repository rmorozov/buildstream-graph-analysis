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
    def test_ci_enforces_the_budget_the_table_declares(self):
        """The budget is a timeout in CI rather than a wall-clock
        assertion in a test: timing a suite from inside itself is the
        kind of guard that goes flaky and then gets muted. What is
        checkable here is that the two numbers agree."""
        workflow = (REPO / ".github/workflows/ci.yml").read_text(
            encoding="utf-8")
        assert "make test-small" in workflow, (
            "CI does not run the small tier, so its budget is unenforced")
        budget = re.search(r"timeout (\d+) make test-small", workflow)
        assert budget, "the small-tier step has no timeout, so no budget"
        assert int(budget.group(1)) == int(tiers.SMALL_TIER_BUDGET_S), (
            f"CI budgets {budget.group(1)}s, tests/tiers.py declares "
            f"{tiers.SMALL_TIER_BUDGET_S}s - two copies of one number")

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
