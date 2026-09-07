"""`UX-761`: a merged `implementer` row is read by a `verifier` first.

`fixing-guide.md` §3 states the rule; this reads `agent-runs.md` for
it. Scoped to what merges - `UX-744`'s `reverted, reopened` is not the
subject - and floored at round **104**, not 103: round 103's own
`UX-705`/`UX-742` rows carry full Agent-tool cost profiles
indistinguishable from the rows that *were* paired, and the ledger's
schema has no value for session-direct work, so excluding them by name
could not be shown provably right. They are two of the "thirteen
tracks merged unread" `round-103.md`'s opening line describes, not an
exception to the rule it states.

holds: rules.md#a-merged-implementer-row-is-read-by-a-verifier-first-a-hold-isnt-lifted-until-answered-or-declined-in-the-task-file
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import dev_process_bands

REPO = pathlib.Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs/audits/agent-runs.md"

#: Round 103 is where `round-103.md:12-14` says the practice started,
#: but two of its own rows are unpaired and cannot be told apart from
#: paired ones by the ledger's schema or by shape - so 103 is not a
#: floor this guard can defend. 104 is the first round with none.
FIRST_PAIRED_ROUND = 104

TASK_ID = re.compile(r"UX-\d+")


def _task_id(cell):
    found = TASK_ID.search(cell)
    return found.group(0) if found else None


def merged_track_rows(runs=None):
    """`(round, task_id, task_cell)` for every `implementer` row from
    `FIRST_PAIRED_ROUND` on whose outcome says merged."""
    runs = dev_process_bands.ledger_runs(LEDGER) if runs is None else runs
    found = []
    for run in runs:
        if run["agent"] != "implementer":
            continue
        if int(run["round"]) < FIRST_PAIRED_ROUND:
            continue
        if "merged" not in run["outcome"]:
            continue
        found.append((run["round"], _task_id(run["task"]), run["task"]))
    return found


def _verifier_ids_by_round(runs):
    by_round = {}
    for run in runs:
        if run["agent"] != "verifier":
            continue
        by_round.setdefault(run["round"], set()).add(_task_id(run["task"]))
    return by_round


def unpaired(runs=None):
    """The subset of `merged_track_rows` with no same-round `verifier`
    row naming its id - matched by id, so a verifier row that ran in
    the same round but named a different task does not count."""
    runs = dev_process_bands.ledger_runs(LEDGER) if runs is None else runs
    by_round = _verifier_ids_by_round(runs)
    return [(round_, task_id, task) for round_, task_id, task
            in merged_track_rows(runs)
            if task_id is None or task_id not in by_round.get(round_, set())]


def test_the_population_is_not_trivial():
    population = merged_track_rows()
    assert len(population) >= 2, (
        "a guard over an empty or single-row population passes whatever "
        f"the ledger does; the real ledger gives {population}")


def test_every_merged_track_from_the_floor_on_is_paired():
    missing = unpaired()
    assert not missing, (
        f"merged implementer row(s) with no same-round verifier row "
        f"naming their id: {missing} - the row does not merge until "
        "the verifier's finding is answered, or the task file records "
        "why it was declined (fixing-guide.md §3)")
