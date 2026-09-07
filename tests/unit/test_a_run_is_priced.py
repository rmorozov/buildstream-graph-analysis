"""`UX-666`: a subagent's cost is written down, and something reads it.

The ledger (`docs/audits/agent-runs.md`) had a habit problem in both
directions: nothing required the row, and nothing read the table. These
clauses hold the two halves - `dev_track_cost.py --append` writes the
row and re-derives the count sentence, `dev_process_bands.py --runs`
reads the table back, and every round document from 90 on prices the
agents it launched.

The population is `UX-744`'s round register, not a glob over
`docs/audits/round-*.md`: a glob cannot see a round that skipped its
document, which is the shape `CLAUDE.md` warns about. The register's
own newest round is excluded by construction (fixing-guide.md §7a),
so this file never demands a document from a round still in progress.
"""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import dev_process_bands, dev_round_register, dev_track_cost

REPO = pathlib.Path(__file__).resolve().parents[2]
LEDGER = REPO / "docs/audits/agent-runs.md"
AUDITS = REPO / "docs/audits"

#: The round the ledger's own rows start pricing at, from `UX-666`'s
#: Required Fix - "every round document from 90 on".
FIRST_PRICED_ROUND = 90

LEDGER_HEAD = """# Agent runs

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 90 | researcher | sonnet | a | 100k | 10 | 5 m | complete | — |
| 91 | verifier | sonnet | b | 50k | 20 | 2 m | complete | — |

What the two rows already say: something.
"""


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / "agent-runs.md"
    path.write_text(LEDGER_HEAD, encoding="utf-8")
    return path


class TestTheRowIsWritten:
    """`dev_track_cost.py --append`: the row lands, and the sentence
    below the table is derived from the count rather than typed."""

    def test_the_row_goes_after_the_tables_last_row(self, ledger):
        dev_track_cost.append_row("| 92 | implementer | sonnet | c | 1k | 1 "
                                  "| 1 m | merged | — |", ledger)
        rows = [line for line in ledger.read_text(encoding="utf-8").splitlines()
                if line.startswith("| ") and line.split("|")[1].strip().isdigit()]
        assert [row.split("|")[1].strip() for row in rows] == ["90", "91", "92"], (
            "the appended row belongs after the table's last row, in "
            f"round order; the table now reads {rows}")

    def test_the_count_sentence_is_re_derived(self, ledger):
        said = dev_track_cost.append_row("| 92 | implementer | sonnet | c | 1k "
                                         "| 1 | 1 m | merged | — |", ledger)
        assert said == "three"
        assert "What the three rows already say" in ledger.read_text(
            encoding="utf-8"), (
            "appending a third row must leave the summary saying 'three'; "
            "a typed count is the defect UX-666 was filed on")

    def test_nothing_else_in_the_document_moves(self, ledger):
        before = ledger.read_text(encoding="utf-8")
        dev_track_cost.append_row("| 92 | a | b | c | 1k | 1 | 1 m | d | e |",
                                  ledger)
        after = ledger.read_text(encoding="utf-8")
        assert after.startswith("# Agent runs\n")
        assert len(after.splitlines()) == len(before.splitlines()) + 1

    def test_the_word_is_built_not_tabled(self):
        assert dev_track_cost.count_word(37) == "thirty-seven"
        assert dev_track_cost.count_word(19) == "nineteen"
        assert dev_track_cost.count_word(40) == "forty"
        assert all(dev_track_cost.count_word(n) for n in range(1, 100))


class TestTheTableIsRead:
    """`dev_process_bands.py --runs`: the ledger's own rows, priced by
    agent kind and model. Until `UX-666` nothing in the tree read it."""

    def test_the_separator_is_not_a_run(self, ledger):
        runs = dev_process_bands.ledger_runs(ledger)
        assert len(runs) == 2, (
            "the header and the `|---|` separator split into nine cells "
            f"too; only a row whose first cell is a round number is a run: "
            f"{runs}")
        assert [run["round"] for run in runs] == ["90", "91"]

    def test_the_real_ledger_parses_to_its_own_row_count(self):
        rows = [line for line in LEDGER.read_text(encoding="utf-8").splitlines()
                if line.startswith("| ")]
        # `rows` includes the header; the separator starts `|---`.
        assert len(dev_process_bands.ledger_runs()) == len(rows) - 1

    def test_an_unfilled_token_cell_is_unknown_and_not_zero(self, tmp_path):
        path = tmp_path / "l.md"
        path.write_text(
            "| round | agent | model | task | tokens | tool calls | wall | "
            "outcome | friction |\n|---|---|---|---|---|---|---|---|---|\n"
            "| 82 | researcher | main | cut | — | — | — | cut, re-run | — |\n"
            "| 83 | researcher | main | ran | 100k | 10 | 5 m | complete | — |\n"
            "\nWhat the two rows already say: x.\n", encoding="utf-8")
        runs = dev_process_bands.ledger_runs(path)
        assert runs[0]["tokens"] is None and runs[0]["wall"] is None
        report = "\n".join(dev_process_bands.runs_report(runs, 2))
        assert "100k" in report, (
            "the median of one priced run and one unpriced is the priced "
            f"one; averaging the cut run in as 0 reads a proxy:\n{report}")
        assert "no token figure: 1 of 2" in report

    def test_the_band_prices_by_kind_and_model(self, ledger):
        report = "\n".join(dev_process_bands.runs_report(
            dev_process_bands.ledger_runs(ledger), 2))
        assert "researcher" in report and "verifier" in report
        assert "100k" in report and "50k" in report

    def test_the_flag_runs_on_the_real_ledger(self):
        out = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_process_bands.py"),
             "--runs", "12"], capture_output=True, text=True, check=True)
        assert "run(s) in the ledger" in out.stdout
        assert "No band is drawn" in out.stdout, (
            "the runs band reports and does not verdict, for the reason "
            f"the other bands do not:\n{out.stdout}")


def _registered_rounds():
    """`UX-744`'s written register, `FIRST_PRICED_ROUND` on. The newest
    round is already excluded there - a round in progress cannot yet
    have written its document (fixing-guide.md §7a) - so this class
    never demands one from it."""
    return sorted((n for n in dev_round_register.written_rounds()
                   if int(n) >= FIRST_PRICED_ROUND), key=int)


#: `UX-757`: named, not patterned - any other round arriving unpriced
#: still reds.
UNPRICEABLE_ROUND_WAIVER = {
    "101": ("2026-09-07", "3805321: transcripts unrecoverable after a "
                           "context rebuild, a guessed row worse than "
                           "a missing one"),
}


class TestEveryRegisteredRoundPricesItsAgents:
    """`UX-666`'s third bullet, over `UX-744`'s register rather than a
    glob: a glob cannot see a round that skipped its document, which
    is exactly the silence this row was filed on. A round document
    that launched agents carries the table; one that launched none
    says so - except the one round `UNPRICEABLE_ROUND_WAIVER` names,
    where the ledger cannot answer either way."""

    def test_the_population_is_not_empty(self):
        assert len(_registered_rounds()) >= 6, (
            "this class asserts nothing if the register is empty - "
            f"registered rounds from {FIRST_PRICED_ROUND} on are "
            f"{_registered_rounds()}")

    @pytest.mark.parametrize("number", _registered_rounds())
    def test_it_carries_a_document_or_is_waived(self, number):
        path = AUDITS / f"round-{number}.md"
        assert path.exists(), (
            f"round {number} is in the register and has no "
            f"docs/audits/round-{number}.md - UX-666 was filed on "
            "exactly this silence, which a glob over the documents "
            "that exist cannot see")
        text = path.read_text(encoding="utf-8")
        if "no agents launched" in text:
            return
        assert "\n## Agents" in text, (
            f"round-{number}.md must carry a `## Agents` section or say "
            "'no agents launched'; a round that priced its runs nowhere "
            "is what UX-666 was filed on")
        if number in UNPRICEABLE_ROUND_WAIVER:
            return
        section = text.split("\n## Agents", 1)[1].split("\n## ", 1)[0]
        rows = [line for line in section.splitlines() if line.startswith("| ")]
        assert len(rows) >= 2, (
            f"round-{number}.md's `## Agents` section has a heading and "
            f"{len(rows)} table line(s) - a header with no run under it "
            "prices nothing")

    def test_the_ledger_prices_every_round_that_documents_agents(self):
        priced = {run["round"] for run in dev_process_bands.ledger_runs()}
        missing = [number for number in _registered_rounds()
                   if (AUDITS / f"round-{number}.md").exists()
                   and "no agents launched" not in
                   (AUDITS / f"round-{number}.md").read_text(encoding="utf-8")
                   and number not in priced
                   and number not in UNPRICEABLE_ROUND_WAIVER]
        assert not missing, (
            f"round(s) {missing} document agents that the ledger does not "
            "price; the table is where the next round chooses a model")


class TestTheRoundRegisterIsDerived:
    """`UX-744`: the register is a derivation, never a hand-kept list -
    `dev_round_register.py --check`'s own pattern, over the file this
    task commits."""

    def test_the_written_table_matches_the_derivation(self):
        assert dev_round_register.check() == [], (
            "docs/audits/round-register.md disagrees with "
            "dev_round_register.written_rounds() - run --write")

    def test_the_register_names_99_through_103(self):
        registered = set(dev_round_register.rounds())
        assert {"99", "100", "101", "102", "103"} <= registered, (
            f"the register names {sorted(registered, key=int)} - these "
            "five rounds are real (closed ids, a naming commit, or a "
            "ledger row each) and must appear")

    def test_the_ledgers_round_column_is_a_subset(self):
        ledger_rounds = {run["round"] for run in dev_process_bands.ledger_runs()}
        registered = set(dev_round_register.rounds())
        assert ledger_rounds <= registered, (
            f"the ledger prices round(s) {ledger_rounds - registered} that "
            "the register does not name")


#: `UX-744`'s verifier: `commit_signal()` cannot tell a commit that
#: *documents* a round from one that is *in* it. `UX-757` retroactively
#: documented round 101 and legitimately names it in prose while doing
#: so, dragging round 101's date to `UX-757`'s own (round 106's).
#: Dated and reasoned, not silently passed - a *new* mismatch still
#: reds `test_a_documented_rounds_date_matches_its_document` below.
DATE_MISMATCH_WAIVER = {
    "101": ("2026-09-07", "UX-757's retroactive documentation commits "
                           "name round 101 in prose; commit_signal() "
                           "reads that as round 101's own work"),
}


def _documented_rounds():
    """Every round `dev_round_register.rounds()` names, `FIRST_PRICED
    _ROUND` on, that also has a `docs/audits/round-N.md`. Below that
    boundary a multi-day round's own opening date legitimately differs
    from the register's latest-commit date (round 76 opens 09-01,
    closes 09-02; round 85 opens 09-03, closes 09-04) - a different
    measurement, not the contamination this class exists to catch."""
    return sorted((n for n in dev_round_register.rounds()
                    if int(n) >= FIRST_PRICED_ROUND
                    and (AUDITS / f"round-{n}.md").exists()), key=int)


class TestARegisteredRoundsDateMatchesItsDocument:
    """`UX-744`'s verifier: the ids-closed column was wrong on four of
    the five rounds it was demonstrated on, for this same reason, and
    was dropped rather than shipped wrong. This is the same check kept
    on what remains - the register's date against the round's own
    document, for every round one exists for."""

    def test_the_population_is_not_empty(self):
        assert len(_documented_rounds()) >= 6, (
            "this class asserts nothing if no registered round has a "
            f"document: {_documented_rounds()}")

    @pytest.mark.parametrize("number", _documented_rounds())
    def test_a_documented_rounds_date_matches_its_document(self, number):
        register_date = dev_round_register.rounds()[number]["date"]
        document_date = dev_round_register.document_date(number)
        if number in DATE_MISMATCH_WAIVER:
            assert register_date != document_date, (
                f"round {number} is waived for a mismatch that no "
                "longer reproduces - drop it from DATE_MISMATCH_WAIVER")
            return
        assert register_date == document_date, (
            f"round {number}: the register says {register_date}, "
            f"docs/audits/round-{number}.md says {document_date}")


class TestATrackIsPricedByShape:
    """`UX-708`: the ledger had no shape column and needs none - the
    shape is `UX-706`'s derivation over the task file, joined on the id
    the row already names. A prose cell would be one more sentence
    nothing reads back."""

    def test_the_shape_comes_from_the_file_not_the_cell(self, tmp_path):
        run = {"agent": "implementer", "task": "`UX-706` a thing (mechanical)"}
        # `UX-706`'s own file derives its shape; the cell says otherwise
        # on purpose, and the cell must lose.
        assert dev_process_bands.shape_of(run) != "mechanical"
        assert dev_process_bands.shape_of(run) in ("bounded", "judgement")

    def test_a_run_naming_no_task_has_no_shape(self):
        assert dev_process_bands.shape_of(
            {"agent": "researcher", "task": "spec vs code"}) is None

    def test_an_unknown_id_is_no_shape_rather_than_a_crash(self):
        assert dev_process_bands.shape_of(
            {"agent": "implementer", "task": "`UX-99999` gone"}) is None

    def test_only_implementer_runs_are_shaped(self):
        report = "\n".join(dev_process_bands.shape_report(
            dev_process_bands.ledger_runs()))
        tracks = [r for r in dev_process_bands.ledger_runs()
                  if r["agent"] == "implementer"]
        assert f"{len(tracks)} implementer run(s)" in report, (
            "a researcher's sweep has no task shape; folding it in would "
            f"price a different question:\n{report}")

    def test_a_cell_that_disagrees_is_named_not_silently_resolved(self):
        """A row whose file derives `judgement` can still have handed a
        track a *bounded* slice - a burn-down batch is exactly that - so
        the split is reported with the disagreeing rows beside it."""
        tracks = [r for r in dev_process_bands.ledger_runs()
                  if r["agent"] == "implementer"]
        off = dev_process_bands.disagreements(tracks)
        report = "\n".join(dev_process_bands.shape_report(
            dev_process_bands.ledger_runs()))
        if off:
            assert f"differs on {len(off)} of {len(tracks)}" in report
            for task, _said, _derived in off:
                assert task in report
        else:
            assert "the row's own word differs" not in report

    def test_the_advisory_names_what_the_rows_measured(self):
        """`UX-708`'s deliverable is one sentence in `CLAUDE.md`, and it
        is the sentence the split decides. A number in it and no run
        behind it is the defect this repository files rows about."""
        claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        tracks = [r for r in dev_process_bands.ledger_runs()
                  if r["agent"] == "implementer"]
        # The split `--runs` prints, not the cell's own word: review 19
        # found the sentence citing a command that produced a different
        # number, which is the defect this file exists to stop.
        judgement = [r for r in tracks
                     if dev_process_bands.shape_of(r) == "judgement"]
        assert f"{len(judgement)} of {len(tracks)} runs" in claude, (
            f"CLAUDE.md's pipeline should say '{len(judgement)} of "
            f"{len(tracks)} runs'; the ledger has {len(tracks)} implementer "
            f"rows, {len(judgement)} of them judgement-shaped")

