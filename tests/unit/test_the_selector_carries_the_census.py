"""UX-522: the guards a grep can never reach, run every time.

`dev_touching.py` selects test files by **grep**: a file that names the
changed module. Its own docstring says why that is a selector and not a
gate. Round 75 measured what the gap costs:

```text
defects the per-item `make test` caught                 5
  of which `test-touching`'s set could not name         2
```

Both misses are one class. A **census** guard's subject is the tree -
the register cap over every task file, the skip census over every
guard, the context map over every module - so it names none of them,
and no diff can point at it. `tests/tiers.py::CENSUS` declares them and
`dev_touching.census_set()` unions them in unconditionally.

The list is **derived, not typed**, and this file is the derivation. A
census guard is a file that

1. walks a path rooted at the repository - `REPO.glob`, `SCENARIOS
   .glob`, `TESTS.rglob` - rather than at a `tmp_path`; and
2. no grep from any source module selects, so listing it is the only
   way it ever runs.

Condition 2 is why `__init__` is no longer a token: fifteen
`__init__.py` files each "selected" the skip census, which is a guard
about skip reasons. That false edge alone hid one of round 75's two
misses from this derivation.
"""
import ast
import inspect
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests"))

import dev_close_task
import dev_touching
import tiers

#: What a walk over a tree is spelled, in this suite.
WALKS = {"glob", "rglob", "iterdir", "walk", "listdir", "scandir"}

#: Names a guard reaches the repository root through. A path built from
#: one of these is the tree; a `tmp_path` is a fixture.
ROOTS = {"REPO", "ROOT", "REPO_ROOT", "PROJECT", "HERE"}

#: `UX-718`: declared census guards this file's AST check cannot see -
#: their subject is a fixed, named population, not a walked directory.
#: `test_a_committed_analysis_matches_the_analyzer.py` compares two
#: committed fixtures against a live analyzer run; nothing here globs.
NOT_A_TREE_WALK = {"tests/unit/test_a_committed_analysis_matches_the_analyzer.py"}

#: `UX-730`: round 98 measured the gap `WALKS` leaves - a guard whose
#: population is a **named index file** (`INDEX`, `CLOSED`,
#: `tests/touch_map.json`) reached through a tool's own reader shows no
#: `WALKS` name of its own. Rather than parse every tool the suite
#: imports, the six functions below are curated and each is checked, in
#: `TestPopulationDelegatesActuallyDelegate`, against its *own* source
#: for the same evidence `WALKS` looks for directly. A guard that calls
#: one is a census guard by the same argument as a guard that globs
#: itself - it just does it through a name this file has to be told.
#:
#: The other half of the gap this row measured - a guard that shells
#: out (`git ls-files`, a pytest collection run) rather than calling a
#: named tool function - is not covered here. A first pass at detecting
#: it mechanically surfaced 13 pre-existing guards this item's own
#: Motivation never counted, which is a population-migration decision
#: past what a bounded task should take unasked; see this item's
#: Outcome.
POPULATION_DELEGATES = {"spread", "test_files", "touch_map",
                         "table_statuses", "backlog_files",
                         "shape_disagreements"}

#: The modules those names are trusted from. A same-named method on an
#: unrelated object - `dev_tier_drift.spread`, a statistical spread -
#: is not this, so the call is only counted when its base resolves to
#: one of these.
DELEGATE_MODULES = {"dev_touching", "dev_close_task"}

#: A delegate call whose own root is a fixture, not the repository -
#: `test_the_touching_map_is_measured.py` calls `touch_map()` after
#: `monkeypatch.setattr(dev_touching, "TESTS", tmp_path)`, exercising
#: the empty-map fallback rather than the real population. Excluded the
#: way `NOT_A_TREE_WALK` excludes the opposite case, and for the same
#: reason: this AST check has no view of what a decorator monkeypatches.
DELEGATED_UNDER_A_FIXTURE = {"tests/unit/test_the_touching_map_is_measured.py"}


def _base(node):
    """The leftmost `Name` of an attribute/subscript/binop chain."""
    while True:
        if isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        elif isinstance(node, ast.BinOp):
            node = node.left
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            return node.id if isinstance(node, ast.Name) else None


def _walks_the_repo(path):
    """`UX-718`: `rooted` also picks up a `def f(root=REPO):` default -
    `test_the_context_map_is_the_tree.py`'s tree walk is `root.iterdir()`
    inside such a function, invisible to a module-level-only scan."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rooted = set(ROOTS)
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and _base(node.value) in rooted):
            rooted.add(node.targets[0].id)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaulted = fn.args.args[len(fn.args.args) - len(fn.args.defaults):]
            for arg, default in zip(defaulted, fn.args.defaults):
                if _base(default) in rooted:
                    rooted.add(arg.arg)
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr in WALKS and _base(n.func.value) in rooted
               for n in ast.walk(tree))


def _sources():
    """Every source module a diff could name.

    `__init__.py` is excluded: its stem is not a token any more, and
    including it here would make this derivation reproduce the false
    edge the fix removed.
    """
    return [str(p.relative_to(REPO))
            for root in ("bga", "tools")
            for p in (REPO / root).rglob("*.py")
            if "__pycache__" not in p.parts and p.name != "__init__.py"]


def _guard_files():
    return sorted(p for p in (REPO / "tests").rglob("test_*.py")
                  if "__pycache__" not in p.parts)


def _delegate_names(tree):
    """`{local name}` bound to a trusted module, and to a function
    imported directly by name from one."""
    modules, functions = set(), set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] in DELEGATE_MODULES:
                    modules.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            base = (node.module or "").split(".")[-1]
            if base == "tools":
                for alias in node.names:
                    if alias.name in DELEGATE_MODULES:
                        modules.add(alias.asname or alias.name)
            elif base in DELEGATE_MODULES:
                for alias in node.names:
                    if alias.name in POPULATION_DELEGATES:
                        functions.add(alias.asname or alias.name)
    return modules, functions


def _delegates_a_population(path):
    """`UX-730`: a call to `POPULATION_DELEGATES`, on a name resolved
    to `DELEGATE_MODULES` by an import this file can read - directly
    (`module.spread()`) or by the function's own name when it was
    imported that way (`table_statuses as _table_statuses`)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules, functions = _delegate_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in POPULATION_DELEGATES
                and _base(node.func.value) in modules):
            return True
        if isinstance(node.func, ast.Name) and node.func.id in functions:
            return True
    return False


@pytest.fixture(scope="module")
def derived():
    reachable = set()
    for module in _sources():
        reachable.update(dev_touching.select([module], census=False)[0])
    walked = {str(p.relative_to(REPO)) for p in _guard_files()
              if _walks_the_repo(p)
              and str(p.relative_to(REPO)) not in reachable}
    # `UX-730`: not filtered by `reachable`. The event that invalidates
    # these - a file added elsewhere in `tests/` or the backlog - is
    # not one `_sources()` ever asks about; being selected for an edit
    # to the delegate tool itself answers a different question than the
    # one this derivation exists for.
    delegated = {str(p.relative_to(REPO)) for p in _guard_files()
                 if _delegates_a_population(p)} - DELEGATED_UNDER_A_FIXTURE
    return sorted(walked | delegated)


class TestTheDeclarationIsTheDerivation:
    def test_every_derived_census_guard_is_declared(self, derived):
        """The direction that matters: a new guard of this shape is
        added to the list, or the round that added it learns why not."""
        missing = sorted(set(derived) - set(tiers.CENSUS))
        assert missing == [], (
            f"{len(missing)} guard(s) walk the repository tree and no grep "
            f"selects them, so they run only if listed in tests/tiers.py's "
            f"CENSUS: {missing}")

    def test_nothing_is_declared_that_does_not_read_the_tree(self):
        """The other direction: no padding. Not "not grep-reachable" -
        a guard picks up an incidental mention the moment somebody
        writes a module's name in its prose, and losing it from the
        census then would be the list wagged by a docstring. Reading
        the tree is the property that makes it a census guard; being
        unreachable is only what makes it *cost* something to omit.

        `UX-718`: `NOT_A_TREE_WALK` is the same argument for a guard
        whose subject is a fixed, named population - no glob, no
        `git ls-files` - so this AST check cannot see it either.
        Its own regression clause below is the argument instead.

        `UX-730`: a delegate call is the same shape a second way - the
        walk happens in the tool it calls, not here - so it is accepted
        as evidence too, and `TestPopulationDelegatesActuallyDelegate`
        is the regression clause for it."""
        for named in tiers.CENSUS:
            if named in NOT_A_TREE_WALK:
                continue
            assert (_walks_the_repo(REPO / named)
                    or _delegates_a_population(REPO / named)), (
                f"{named} is declared census but walks no repository tree "
                f"and delegates no known population")

    def test_the_set_stays_the_size_it_was_measured_at(self):
        """The price, asserted. Every `test-touching` run pays this
        set; at 19 files it is 36.6s at `-n auto` (`UX-730`: 14 files/
        10.80s before) against a ~4s selection, and the round that
        doubles it should have to say so. The bound is a ceiling, not a
        target."""
        assert len(tiers.CENSUS) <= 19, (
            f"{len(tiers.CENSUS)} census files - re-measure the set's "
            f"seconds and move this bound with the number")

    def test_the_two_misses_round_75_measured_are_in_it(self):
        """The item's own evidence, made a clause. `UX-503`'s register
        cap and `UX-502`'s skip census are the two defects that reached
        a commit past a green `test-touching`."""
        for named in ("tests/unit/test_the_register_is_terse.py",
                      "tests/unit/test_every_skip_reason_is_declared.py"):
            assert named in tiers.CENSUS, named

    def test_the_module_this_derivation_cannot_see_is_in_it(self):
        """`UX-718`: `test_the_context_map_is_the_tree.py` names 18
        modules in its own text, so `derived` above finds it reachable
        and never flags its absence - the fixture only proves *some*
        module reaches it, not that a *new* one does. Typed here for
        the same reason as the round-75 pair above: this class of miss
        has no sound general derivation, only a clause per instance."""
        assert "tests/unit/test_the_context_map_is_the_tree.py" in tiers.CENSUS

    def test_the_second_miss_the_same_round_measured_is_in_it(self):
        """`UX-718`: `test_a_committed_analysis_matches_the_analyzer.py`
        reddened all four CI jobs on `89b1ddf` after `test-touching`
        passed locally at 251 files - one round, two misses of one
        class, and neither is `derived`'s shape (it walks nothing;
        `NOT_A_TREE_WALK` above says why)."""
        assert ("tests/unit/test_a_committed_analysis_matches_the_analyzer.py"
                in tiers.CENSUS)

    def test_every_declared_file_exists(self):
        for named in tiers.CENSUS:
            assert (REPO / named).exists(), named


class TestPopulationDelegatesActuallyDelegate:
    """`UX-730`: `POPULATION_DELEGATES` is padding the moment one of its
    six names stops reading the tree, a named index file or a
    subprocess - checked against each function's own source rather than
    assumed, the way `test_nothing_is_declared_that_does_not_read_the_tree`
    holds `NOT_A_TREE_WALK` to the same standard."""

    OWNERS = {
        "spread": dev_touching.spread,
        "test_files": dev_touching.test_files,
        "touch_map": dev_touching.touch_map,
        "table_statuses": dev_close_task.table_statuses,
        "backlog_files": dev_close_task.backlog_files,
        "shape_disagreements": dev_close_task.shape_disagreements,
    }

    def test_the_set_is_not_empty(self):
        """The vacuity floor. An empty `POPULATION_DELEGATES` would let
        every clause below - and `derived`'s use of it - pass at
        nothing."""
        assert POPULATION_DELEGATES, "no delegate is declared"
        assert set(self.OWNERS) == POPULATION_DELEGATES, (
            "OWNERS and POPULATION_DELEGATES have drifted apart")

    @pytest.mark.parametrize("name", sorted(POPULATION_DELEGATES))
    def test_each_delegate_still_reads_the_tree_or_an_index(self, name):
        source = inspect.getsource(self.OWNERS[name])
        markers = ("rglob(", "glob(", "INDEX", "CLOSED", "touch_map(",
                   "test_files(", "task_file(", "backlog_files(", "ls-files")
        assert any(marker in source for marker in markers), (
            f"{name} no longer shows any of the markers this set was "
            f"curated for - re-derive POPULATION_DELEGATES")


class TestTheSelectorRunsThem:
    def test_a_docs_only_diff_still_runs_the_census(self):
        """The acceptance clause. Before this, a diff touching only
        `docs/` selected whatever happened to name the file - and the
        register cap, which reads every task file, was not in it."""
        selected, why = dev_touching.select(
            ["docs/backlog/scenarios/UX-0522-the-selector-runs-last-and-carries-the-census.md"])
        for named in tiers.CENSUS:
            assert named in selected, named
            assert "census" in why[named]

    def test_the_census_is_in_every_selection(self):
        selected, _ = dev_touching.select(["bga/findings.py"])
        assert set(tiers.CENSUS) <= set(selected)

    def test_the_drift_tool_asks_for_the_grep_half(self, monkeypatch):
        """`UX-476` asks the opposite question of the selector: not
        "what should run" but "what does this diff account for". A
        census guard runs whatever the diff is, so unioning it there
        makes every reported slow file explained by every branch -
        which is what `test_an_empty_diff_is_an_empty_set_and_not_none`
        caught at this round's batch gate, after the union landed."""
        from tools import dev_tier_drift
        from tools import dev_touching as imported

        # `dev_tier_drift` reaches it as `tools.dev_touching`, which is
        # a different module object from this file's `dev_touching`.
        asked = {}
        monkeypatch.setattr(imported, "changed_files", lambda *a, **k: [])
        monkeypatch.setattr(imported, "select",
                            lambda changed, census=True: (
                                asked.setdefault("census", census), ([], {}))[1])
        dev_tier_drift.explained_by("HEAD")
        assert asked["census"] is False

    def test_why_says_which_set_chose_it(self):
        """`--why` is the instrument a session reads when the selector
        surprises it; a set it cannot name is a set nobody can audit."""
        _, why = dev_touching.select(["bga/findings.py"])
        assert why["tests/unit/test_the_register_is_terse.py"] == ["census"]


class TestTheStemIsNotADunder:
    def test_init_is_not_a_token(self):
        """The false edge this item removed. `__init__` is the stem of
        every package's `__init__.py`, so it matched any guard that
        mentions one - fifteen modules "selected" the skip census."""
        assert "__init__" not in dev_touching.tokens_for("bga/__init__.py")

    def test_a_real_stem_still_is(self):
        """And the behaviour it must not have cost: `store_aggregate`
        is a token because a test naming it is about it."""
        assert "store_aggregate" in dev_touching.tokens_for(
            "bga/store_aggregate.py")

    def test_the_skip_census_is_no_longer_selected_by_a_package_init(self):
        """The measured consequence, in the direction of the defect."""
        selected, _ = dev_touching.select(["bga/graph/__init__.py"],
                                          census=False)
        assert "tests/unit/test_every_skip_reason_is_declared.py" not in selected

    def test_the_import_spelling_did_not_swallow_the_two_misses(self):
        """`UX-624` widened the grep with `from <package> import
        <module>`. Condition 2 of this derivation *is* grep
        reachability, so a spelling loose enough to reach a census
        guard would delete it from `derived` and the declaration would
        become padding nobody could re-derive. The two round-75 misses
        are the ones with a measured cost, so they are the ones asserted
        still unreachable."""
        reachable = set()
        for module in _sources():
            reachable.update(dev_touching.select([module], census=False)[0])
        assert len(reachable) > 100, (
            f"only {len(reachable)} files reachable - the derivation's input "
            f"collapsed, so the clause below would pass vacuously")
        for named in ("tests/unit/test_the_register_is_terse.py",
                      "tests/unit/test_every_skip_reason_is_declared.py"):
            assert named not in reachable, (
                f"{named} is round-75's own miss and a grep now reaches it")
