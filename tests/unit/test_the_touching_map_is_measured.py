"""UX-524: the class a grep cannot see, closed by CI's own coverage.

`dev_touching` selects test files by **grep** - a file that names the
changed module - and its docstring says why that beats an import graph
here: half this suite's guards read a document or a fixture and import
nothing. The price is the other direction, a Python test that reaches a
module through an import chain and never spells its name.

`UX-500`'s round counted two misses in five, both census-class
(`UX-522`). This is the remaining one, and the instrument is already
running: CI's suite under `--cov-context=test` records, per test, every
module line it executed.

Three properties, and the third is the one that makes it safe to run on
every push:

- the map **adds** to the grep and the census, never replaces them;
- an absent or empty map costs the selection nothing - a clone that has
  not fetched it falls back, and `--why` says which set chose what;
- `--adopt` adds edges and removes none, so a run that could not reach
  a module (no browser, no `bst`) cannot quietly narrow the selector.

Measured before it was believed: **+20% wall clock** with the coverage
context (33.2s -> 40.0s on a twelve-file subset), which is why it runs
on 3.12 and never on 3.11 - the interpreter whose seconds `UX-503`'s
tier reference is made of.
"""
import json
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_touch_map
import dev_touching

WORKFLOW = REPO / ".github/workflows/ci.yml"
MAP = REPO / "tests/touch_map.json"


def _database(path, rows):
    """A coverage database with `rows` of `(module path, context)`."""
    db = sqlite3.connect(str(path))
    db.executescript(
        "CREATE TABLE file (id integer primary key, path text);"
        "CREATE TABLE context (id integer primary key, context text);"
        "CREATE TABLE line_bits (file_id integer, context_id integer);")
    files, contexts = {}, {}
    for module, context in rows:
        files.setdefault(module, len(files) + 1)
        contexts.setdefault(context, len(contexts) + 1)
    for module, ident in files.items():
        db.execute("INSERT INTO file VALUES (?, ?)", (ident, str(REPO / module)))
    for context, ident in contexts.items():
        db.execute("INSERT INTO context VALUES (?, ?)", (ident, context))
    for module, context in rows:
        db.execute("INSERT INTO line_bits VALUES (?, ?)",
                   (files[module], contexts[context]))
    db.commit()
    db.close()
    return path


class TestTheMapIsWhatTheRunExecuted:
    def test_a_context_becomes_an_edge(self, tmp_path):
        found = dev_touch_map.read(_database(tmp_path / "c", [
            ("bga/findings.py", "tests/unit/test_a.py::test_one|run")]))
        assert found == {"bga/findings.py": ["tests/unit/test_a.py"]}

    def test_one_file_is_one_edge_however_many_tests(self, tmp_path):
        """A row per *test* would be 5,900 rows nobody can read, and
        the selector runs files."""
        found = dev_touch_map.read(_database(tmp_path / "c", [
            ("bga/findings.py", "tests/unit/test_a.py::test_one|run"),
            ("bga/findings.py", "tests/unit/test_a.py::test_two|run")]))
        assert found == {"bga/findings.py": ["tests/unit/test_a.py"]}

    def test_a_module_outside_the_source_roots_is_not_a_row(self, tmp_path):
        """A test's coverage of `tests/` is itself, which the selector
        already knows, and site-packages is nobody's diff."""
        found = dev_touch_map.read(_database(tmp_path / "c", [
            ("tests/support/x.py", "tests/unit/test_a.py::test_one|run"),
            ("bga/findings.py", "tests/unit/test_a.py::test_one|run")]))
        assert list(found) == ["bga/findings.py"]

    def test_a_row_with_no_context_is_dropped(self, tmp_path):
        """A run without `--cov-context` writes rows with a null
        context; a map built from those would be every module against
        nothing, and it must not be an empty *edge*."""
        found = dev_touch_map.read(_database(tmp_path / "c", [
            ("bga/findings.py", "")]))
        assert found == {}


class TestAdoptAddsAndNeverRemoves:
    def test_a_new_edge_is_added(self):
        merged = dev_touch_map.adopt({"bga/a.py": ["tests/unit/test_a.py"]},
                                     {"bga/a.py": ["tests/unit/test_b.py"]})
        assert merged == {"bga/a.py": ["tests/unit/test_a.py",
                                       "tests/unit/test_b.py"]}

    def test_an_edge_the_run_could_not_reach_survives(self):
        """The clause that makes this safe on every push. A runner with
        no browser executes no viewer guard, and a map that replaced
        would delete those edges and narrow the selector silently."""
        merged = dev_touch_map.adopt({"bga/a.py": ["tests/unit/test_a.py"]},
                                     {"bga/b.py": ["tests/unit/test_b.py"]})
        assert merged["bga/a.py"] == ["tests/unit/test_a.py"]

    def test_a_new_module_is_a_new_row(self):
        merged = dev_touch_map.adopt({}, {"bga/a.py": ["tests/unit/test_a.py"]})
        assert merged == {"bga/a.py": ["tests/unit/test_a.py"]}


class TestTheSelectorUnionsIt:
    def test_a_mapped_test_is_selected_and_why_says_map(self, monkeypatch):
        """The acceptance clause: a module no test names by string
        still selects the tests that executed it."""
        monkeypatch.setattr(dev_touching, "touch_map", lambda: {
            "bga/findings.py": ["tests/unit/test_the_touching_map_is_measured.py"]})
        selected, why = dev_touching.select(["bga/findings.py"])
        assert "tests/unit/test_the_touching_map_is_measured.py" in selected
        assert "map" in why["tests/unit/test_the_touching_map_is_measured.py"]

    def test_a_row_naming_a_file_that_is_gone_is_ignored(self, monkeypatch):
        """The map is adopted and never pruned, so it outlives the
        guards in it. A selection carrying a path pytest cannot open is
        an error message instead of a run."""
        monkeypatch.setattr(dev_touching, "touch_map", lambda: {
            "bga/findings.py": ["tests/unit/test_deleted_in_round_79.py"]})
        selected, _ = dev_touching.select(["bga/findings.py"])
        assert "tests/unit/test_deleted_in_round_79.py" not in selected

    def test_an_absent_map_costs_the_selection_nothing(self, monkeypatch):
        """A clone that has not fetched it, and the state this lands
        in: the grep and the census still answer."""
        monkeypatch.setattr(dev_touching, "touch_map", lambda: {})
        selected, why = dev_touching.select(["bga/findings.py"])
        assert selected
        assert not any("map" in sets for sets in why.values())

    def test_the_committed_map_parses(self):
        assert isinstance(json.loads(MAP.read_text(encoding="utf-8")), dict)

    def test_a_map_that_will_not_parse_is_an_empty_map(self, monkeypatch,
                                                       tmp_path):
        """The input class a file adopted by a bot really has: a push
        that raced, a truncated download. `touch_map` reading it must
        fall back, not take the selector down with it - a broken
        bookkeeping file that stops every `test-touching` run is worse
        than no map at all."""
        (tmp_path / "touch_map.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(dev_touching, "TESTS", tmp_path)
        assert dev_touching.touch_map() == {}


class TestItComesFromCIAndNotFromHere:
    def test_the_workflow_measures_it_off_the_timing_interpreter(self):
        """`UX-503`'s tier reference is 3.11's seconds. Coverage costs
        +20%, so measuring the map there would move every row in a
        document this repository compares runs against."""
        held = WORKFLOW.read_text(encoding="utf-8")
        # The `if:` that *follows* the flags, not the one before them:
        # reading backwards found the previous step's condition, and
        # the clause passed with the coverage moved onto 3.11.
        after = held.split("--cov-context=test", 1)[1]
        condition = [line for line in after.splitlines()
                     if line.strip().startswith("if:")][0]
        assert "3.12" in condition, condition
        assert "3.11" not in condition, condition

    def test_the_workflow_adopts_it_only_on_the_default_branch(self):
        held = WORKFLOW.read_text(encoding="utf-8")
        job = held.split("touch-map-adopt:")[1].split("\n  agent-config:")[0]
        assert "github.event_name == 'push'" in job
        assert "default_branch" in job

    def test_the_tool_offers_no_local_record_route(self):
        """`UX-447`: a reference from another clock. `--write` reads a
        database this machine happens to have; what it must not have is
        a switch that writes `tests/touch_map.json` from it."""
        source = (REPO / "tools/dev_touch_map.py").read_text(encoding="utf-8")
        writes = source.split("if args.adopt:")[1].split("return 0")[0]
        assert "MAP.write_text" in writes
        after = source.split("measured = read(args.database)")[1]
        assert "MAP.write_text" not in after


class TestTheAdoptedMapPaysForItsReaders:
    """`UX-662`: the map's readers, and the entries adopting it stales.

    `8751a7e` adopted a map on `main`; the next branch to merge went red
    on the drift gate with **zero** failing tests, for seconds its own
    diff never spent. The entry was not wrong when it was recorded - the
    tree under it changed - so the adopting commit retires it, and the
    next reference candidate re-records it on that run's clock.
    """

    def test_the_readers_are_the_map_s_own_row_not_a_typed_list(self):
        """The map names the guards that read it, so nothing is typed
        beside it to fall out of date the next time one is added."""
        merged = {dev_touch_map.READER: ["tests/unit/test_a.py"],
                  "bga/elsewhere.py": ["tests/unit/test_b.py"]}
        assert dev_touch_map.readers(merged) == ["tests/unit/test_a.py"]
        assert dev_touch_map.readers({}) == []

    def test_the_named_reader_is_a_module_that_reads_the_map(self):
        """`READER` is the one typed name left, and a constant naming a
        module that does not read the map would retire the wrong rows in
        silence - the shape of defect this whole item is about."""
        source = (REPO / dev_touch_map.READER).read_text(encoding="utf-8")
        assert MAP.name in source, dev_touch_map.READER

    def test_retire_drops_the_name_from_files_and_from_samples(self):
        """Both, not either: `against` reads `samples` for `UX-496`'s
        band, so an entry left there is still judged against."""
        reference = {"files": {"a.py": 1.0, "b.py": 2.0},
                     "samples": {"a.py": [1.0], "b.py": [2.0]}}
        document, retired = dev_touch_map.retire(reference, ["a.py"])
        assert retired == ["a.py"]
        assert document["files"] == {"b.py": 2.0}
        assert document["samples"] == {"b.py": [2.0]}

    def test_a_name_the_reference_does_not_carry_retires_nothing(self):
        reference = {"files": {"b.py": 2.0}, "samples": {"b.py": [2.0]}}
        document, retired = dev_touch_map.retire(reference, ["a.py"])
        assert retired == []
        assert document == reference

    def test_a_retired_entry_is_recorded_by_the_gate_not_confirmed(self):
        """The claim the whole design rests on. Dropping an entry must
        turn the gate's verdict from one that fails the branch into one
        that prints the row - otherwise this trades a red gate for a
        red gate."""
        import dev_tier_drift
        reference = {"files": {f"f{n}.py": 10.0 for n in range(5)},
                     "samples": {f"f{n}.py": [10.0] for n in range(5)}}
        times = dict({f"f{n}.py": 10.0 for n in range(5)}, **{"f0.py": 90.0})

        verdict, _, rows = dev_tier_drift.against(times, reference)
        assert verdict == "drift"
        assert [row[0] for row in rows] == ["f0.py"]
        assert rows[0][2] == 10.0, "judged against a number it has"

        retired, names = dev_touch_map.retire(reference, ["f0.py"])
        assert names == ["f0.py"]
        verdict, _, rows = dev_tier_drift.against(times, retired)
        assert [row[0] for row in rows] == ["f0.py"], "still printed"
        assert rows[0][2] is None, "and carried with no number to fail on"

    def test_the_adopting_commit_carries_the_reference_it_retired_from(self):
        """One commit, or the retire is a change nobody pushed."""
        held = WORKFLOW.read_text(encoding="utf-8")
        job = held.split("touch-map-adopt:")[1].split("\n  agent-config:")[0]
        add = [line for line in job.splitlines()
               if line.strip().startswith("git add")][0]
        assert "tests/ci_reference.json" in add, add
        assert "tests/touch_map.json" in add, add

    def test_the_map_is_adopted_after_the_rows_measured_without_it(self):
        """`tier-reference-adopt` adopts from a candidate measured with
        the map as it was *before* this run. Landing second, it would
        put back exactly what the retire took out."""
        held = WORKFLOW.read_text(encoding="utf-8")
        job = held.split("touch-map-adopt:")[1].split("\n  agent-config:")[0]
        needs = [line for line in job.splitlines()
                 if line.strip().startswith("needs:")][0]
        assert "tier-reference-adopt" in needs, needs
