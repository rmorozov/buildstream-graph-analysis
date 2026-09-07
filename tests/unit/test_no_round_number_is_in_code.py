"""UX-696: the register's "no round in code" row, ratcheted.

A round number in a module makes a reader chase `git log` to learn a
reason. The reason belongs in the line; the history belongs in the task
file. Existing ones are listed with the count they had and may only
shrink, like the docstring row in `test_the_register_is_terse.py`.

This lives in its own file rather than beside that row: listing module
paths makes a file grep-reachable, and `test_the_selector_carries_the
_census.py` pins the register guard as round 75's own miss - a file
only the census selects. Naming the modules here is right, because a
diff touching one of them should run this.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

#: `UX-696`: the register's "no round in code" row, held the same way.
#: A round number in a module makes a reader chase `git log` to learn a
#: reason; the reason belongs in the line itself and the history in the
#: task file. Grandfathered by path, and each may only shrink.
#:
#: `UX-696`'s census read `grep -rn "round [0-9]" bga tools` and counted
#: 31 lines. That instrument is case-sensitive and the population is
#: not: 21 further lines open a sentence with `Round N`, so the real
#: count is 53 over 25 files. This reads case-insensitively - a
#: case-sensitive guard would have let two fifths of them through, which
#: is the census's own miss rather than a later drift.
ROUNDS_IN_CODE = {
    "bga/analyzer.py": 1,
    "bga/blast.py": 1,
    "bga/cache_effectiveness.py": 2,
    "bga/compare.py": 1,
    "bga/correlate.py": 3,
    "bga/findings.py": 5,
    "bga/producer.py": 1,
    "bga/provenance.py": 1,
    "bga/report/ci_comment.py": 1,
    "bga/report/json.py": 1,
    "bga/schemas.py": 3,
    "bga/suspend.py": 1,
    "tools/bga_snapshot.py": 3,
    "tools/bga_timeline.py": 2,
    "tools/bga_view.py": 2,
    "tools/bst_baseline_set.py": 3,
    "tools/bst_native_build_tracer.py": 7,
    "tools/bst_rebuild_set.py": 1,
    "tools/bst_run_wrapped.py": 2,
    "tools/dev_close_task.py": 6,
    "tools/dev_perfetto_queries.py": 1,
    "tools/dev_tier_drift.py": 2,
    "tools/dev_touching.py": 1,
    "tools/dev_track_cost.py": 1,
    "tools/gen_synthetic_scale_run.py": 1,
}

ROUND_REFERENCE = re.compile(r"round \d+", re.I)


def _code_modules():
    return sorted(REPO.glob("bga/**/*.py")) + sorted(REPO.glob("tools/**/*.py"))


def _round_references(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
               if ROUND_REFERENCE.search(line))



class TestNoRoundInCode:
    """`UX-696`. The third register row, ratcheted like the first."""

    def test_a_listed_file_only_loses_round_references(self):
        grew = []
        for rel, recorded in sorted(ROUNDS_IN_CODE.items()):
            path = REPO / rel
            if not path.exists():
                continue
            n = _round_references(path)
            if n > recorded:
                grew.append(f"{rel}: {n} references, recorded {recorded}")
        assert grew == [], (
            f"a round number in code is history, and these gained one: "
            f"{grew}. The why goes in the line; the round goes in the task "
            f"file")

    def test_a_file_that_lost_them_all_leaves_the_table(self):
        """Otherwise the table rots into a list of files that are fine,
        and the next reader cannot tell the ratchet from the amnesty."""
        clean = [rel for rel in sorted(ROUNDS_IN_CODE)
                 if (REPO / rel).exists() and not _round_references(REPO / rel)]
        assert clean == [], (
            f"these carry no round reference any more - remove them from "
            f"ROUNDS_IN_CODE so the table cannot rot: {clean}")

    def test_an_unlisted_module_carries_none(self):
        """The half that catches a new one. Every module not in the
        table must be at zero, which is what makes the table a closed
        population rather than a sample."""
        offenders = []
        for path in _code_modules():
            rel = path.relative_to(REPO).as_posix()
            if rel in ROUNDS_IN_CODE:
                continue
            n = _round_references(path)
            if n:
                offenders.append(f"{rel}: {n}")
        assert offenders == [], (
            f"round numbers in a module not on the grandfathered list: "
            f"{offenders}")

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
