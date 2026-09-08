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
import re
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
        # UX-794: the hundredth row raised IndexError on a tens table.
        assert dev_track_cost.count_word(100) == "one hundred"
        assert dev_track_cost.count_word(101) == "one hundred and one"
        assert dev_track_cost.count_word(120) == "one hundred and twenty"
        assert len({dev_track_cost.count_word(n) for n in range(1, 1000)}) == 999


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
        # The discriminating cells first: `dev_junit_tail.py` is what a
        # red CI run is read through and it truncates, so a message that
        # opens with an absolute path spends the whole budget on it.
        written = set(dev_round_register.written_rounds())
        on_disk = set(re.findall(
            r"^\| (\d+) \|", dev_round_register.REGISTER.read_text(
                encoding="utf-8"), re.MULTILINE))
        derived = dev_round_register.rounds()
        odd = sorted(written ^ on_disk, key=int)
        dates = [(n, derived[n]["date"]) for n in odd if n in derived]
        problems = dev_round_register.check()
        # `UX-781`: the set difference alone said "the file disagrees"
        # for a truncated history *and* for a real drift, and a round
        # went to the wrong one. `check()` is what is being asserted;
        # printing everything except its own words was the defect.
        assert problems == [], (
            f"derived-not-written {sorted(written - on_disk, key=int)} "
            f"written-not-derived {sorted(on_disk - written, key=int)} "
            f"dates {dates} check {problems}")

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


#: `UX-782`'s verifier: `first_commit_date()` reads when
#: `docs/audits/round-N.md` was itself first added, independent of
#: what the document's own dateline says. `UX-757` added all four of
#: 99-102 on 2026-09-07, retroactively, from committed material; each
#: document's own "Opens at ..." states the round's actual work date,
#: 2026-09-06. (Rounds 19 and 22, waived under the old commit-subject
#: mechanism, now match cleanly - their own file was added the day
#: their dateline states - and are not carried forward.)
DATE_MISMATCH_WAIVER = dict.fromkeys(
    ("99", "100", "101", "102"),
    ("2026-09-08", "UX-757 added docs/audits/round-N.md for all four "
                   "on 2026-09-07, retroactively, from committed "
                   "material; each document's own dateline states "
                   "2026-09-06, the round's actual work date"))


#: `UX-772`'s verifier: a round whose document states no recognized
#: dateline must red, not silently skip - the same shape the row was
#: filed on, one layer down. These predate the register (round 99)
#: and open with an "Input:"/prose sentence, never "Run on"/"Opens at"
#: - closed history, not rewritten to satisfy a later guard. `(pinned
#: on, reason)`, so a round that gains a real dateline is caught by
#: this class's own check below rather than staying silently waived.
NO_DATELINE_WAIVER = dict.fromkeys(
    ("75", "76", "77", "78", "80", "81", "83", "84", "85", "86"),
    ("2026-09-07", "pre-round-99 audit-cadence document, no stated "
                   "dateline (UX-772)"))
#: Rounds 7-9 open on the CI run that produced the capture - `Run
#: [\`32044281643\`](...)`, a run id and no date anywhere in the
#: document. They entered this population when `UX-781` un-truncated
#: the history the register derives from, not by any change to them.
NO_DATELINE_WAIVER.update(dict.fromkeys(
    ("7", "8", "9"),
    ("2026-09-07", "opens on a CI run id, not a date; states none "
                   "(UX-772, population widened by UX-781)")))
#: Rounds 2-6, moved verbatim out of `docs/design/directions.md`
#: during round 11's housekeeping - closed-history prose, never a
#: dateline. They enter the population under `UX-782`'s committed
#: union (they have no naming commit `git log` could find at all).
NO_DATELINE_WAIVER.update(dict.fromkeys(
    ("2", "3", "4", "5", "6"),
    ("2026-09-08", "moved verbatim from docs/design/directions.md in "
                   "round 11's housekeeping; states no dateline "
                   "(UX-782, population widened to the committed "
                   "union)")))


def _documented_rounds():
    """Every registered round with a `docs/audits/round-N.md` -
    `UX-782`'s committed union makes every document its own round in
    the register directly, so there is no unreachable-date exclusion
    left (round 64 used to need one; it now dates from its own
    document, like any other)."""
    reg = dev_round_register.rounds()
    return sorted((n for n in reg if (AUDITS / f"round-{n}.md").exists()),
                  key=int)


class TestARegisteredRoundsDateMatchesItsDocument:
    """`UX-782`: the register's date is now `document_date()` itself
    (UX-772's dateline), so comparing them is tautological - the
    replacement check reads an independent source, the git commit
    that first added the document (`first_commit_date()`), and skips,
    naming the depth, where a shallow clone cannot answer. `UX-772`'s
    verifier stays: an unrecognized dateline reds unless named in
    `NO_DATELINE_WAIVER` - a silent skip is the defect this class
    exists to catch, not a way to avoid it."""

    def test_the_population_is_not_empty(self):
        assert len(_documented_rounds()) >= 6, (
            "this class asserts nothing if no registered round has a "
            f"document: {_documented_rounds()}")

    def test_the_population_reaches_below_first_priced_round(self):
        below = [n for n in _documented_rounds() if int(n) < FIRST_PRICED_ROUND]
        assert below, (
            f"`FIRST_PRICED_ROUND` ({FIRST_PRICED_ROUND}) stopped exactly "
            "where rounds 76 and 85 fail (UX-772); a population narrowed "
            "back to it buys nothing")

    @pytest.mark.parametrize("number", _documented_rounds())
    def test_a_documents_dateline_matches_its_own_first_commit(self, number):
        document_date = dev_round_register.document_date(number)
        if number in NO_DATELINE_WAIVER:
            assert document_date is None, (
                f"round {number} is waived for stating no dateline, but "
                "now states one - drop it from NO_DATELINE_WAIVER and let "
                "it compare")
            return
        assert document_date is not None, (
            f"round {number} has no register-recognized dateline in "
            f"docs/audits/round-{number}.md ('Run on ...', 'Opens at "
            "...', or a heading's parenthesised date) and is not named "
            "in NO_DATELINE_WAIVER - a document that does not state its "
            "own date is exactly UX-772's defect")
        if dev_round_register.is_shallow():
            pytest.skip(
                f"shallow clone (boundary names "
                f"{dev_round_register.shallow_depth()} commit(s)) - git "
                "log cannot see round "
                f"{number}'s own first commit (UX-782)")
        git_date = dev_round_register.first_commit_date(number)
        if number in DATE_MISMATCH_WAIVER:
            assert git_date != document_date, (
                f"round {number} is waived for a mismatch that no "
                "longer reproduces - drop it from DATE_MISMATCH_WAIVER")
            return
        assert git_date == document_date, (
            f"round {number}: docs/audits/round-{number}.md's own "
            f"dateline says {document_date}, but it was first "
            f"committed on {git_date} - a retroactively-written "
            "document not named in DATE_MISMATCH_WAIVER")


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

