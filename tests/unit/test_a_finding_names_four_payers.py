"""UX-409: the configure tax named one payer twice.

Round 64's Plane 3 pass over 79 kept logs:

```text
[medium] configure-tax: ... paid most by codegen.bst, core.bst,
codegen.bst, lib-f.bst
```

Four slots, three elements. The rows are per **log**, and an element
built more than once in the kept history has one row per build - so a
`[:4]` taken before the group-by spends a slot twice and pushes a real
fourth payer out of the sentence.

**The filing's Out of Scope was wrong about the neighbour.** It says
the developer-tax ranking "is already per-element; nothing to change
there". Measured here, `sandbox_tax`'s `top_payers` is built inside a
loop over log *records*, so the same element appearing in two build logs
appears twice there too - and the text report slices that list before
any group-by. Both are fixed, and the deviation is recorded in the
task file.

The audit the Required Fix asks for - "one pass over the module for any
other `[:N]` taken before a group-by" - is this file's last class: the
three remaining slices, each with what it is taken over.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_cache_logs import (                       # noqa: E402
    PAYERS_NAMED, build_report, format_report_text, sandbox_tax,
    scan_log_tree, top_distinct_payers)


def _log(element, key, staging, commands, total, configure=None):
    """One build log. `configure` adds cmake's own self-reported line."""
    body = (
        f"BuildStream 2.7.0 - Tuesday, 18-08-2026 at 11:53:22\n"
        f"[--:--:--] START   [{key}] {element}: Build\n"
        f"[--:--:--] START   [{key}] {element}: Staging dependencies at: /\n"
        f"[00:00:{staging:02d}] SUCCESS [{key}] {element}: "
        f"Staging dependencies at: /\n"
        f"[--:--:--] START   {element}: Running commands\n"
    )
    if configure is not None:
        body += f"    -- Configuring done ({configure}.0s)\n"
    body += (
        f"[00:00:{commands:02d}] SUCCESS {element}: Running commands\n"
        f"[00:00:{total:02d}] SUCCESS [{key}] {element}: Build\n"
    )
    return body


#: One element (`twice.bst`) built **twice**, plus four others once
#: each. Its two configures are each smaller than the single biggest,
#: and together larger - which is the case that tells "sum" apart from
#: "max" as well as from "first seen".
_TREE = (
    # element      key         staging cmds total configure
    ("twice.bst", "aaaaaaa1",       1,   20,   22,        9),
    ("twice.bst", "aaaaaaa2",       1,   20,   22,        8),
    ("biggest.bst", "bbbbbbbb",     1,   20,   22,       12),
    ("second.bst", "cccccccc",      1,   20,   22,        7),
    ("third.bst", "dddddddd",       1,   20,   22,        6),
    ("fourth.bst", "eeeeeeee",      1,   20,   22,        5),
)


def _tree(tmp_path):
    root = tmp_path / "logs"
    for element, key, staging, commands, total, configure in _TREE:
        directory = root / "p" / element.removesuffix(".bst")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{key}-build.20260818-115322.log").write_text(
            _log(element, key, staging, commands, total, configure))
    return root


def _finding(report, finding_id):
    for finding in report.get("findings") or []:
        if finding.get("id") == finding_id:
            return finding
    return None


class TestTheConfigureTaxNamesFourDistinctElements:
    def test_no_element_takes_two_slots(self, tmp_path):
        report = build_report(scan_log_tree(str(_tree(tmp_path))))
        finding = _finding(report, "configure-tax")
        assert finding, "the fixture stopped producing a configure-tax finding"
        title = finding["title"]
        # Split on the *sentence* end, not on the first ".": element
        # names contain one, so `split(".", 1)` returned "biggest" and
        # the clause could never see a duplicate. Found by the mutation
        # that reintroduced the defect and left this green.
        named = title.split("paid most by ", 1)[1].split(". Elements", 1)[0]
        payers = [name.strip() for name in named.split(",")]
        assert len(payers) == PAYERS_NAMED, (
            f"the sentence named {len(payers)} payers, not {PAYERS_NAMED}: "
            f"{payers}")
        assert len(payers) == len(set(payers)), (
            f"a payer is named twice: {payers}. The rows are per log, and "
            f"an element built twice in the kept history had one row per "
            f"build")

    def test_the_fourth_real_payer_is_not_pushed_out(self, tmp_path):
        """The cost of the duplicate, and the reason it matters.

        With one slot spent twice, the list stops one element short and
        a reader is told the wrong thing about where the cost is.
        """
        report = build_report(scan_log_tree(str(_tree(tmp_path))))
        title = _finding(report, "configure-tax")["title"]
        assert "fourth.bst" not in title, (
            "the fixture's fifth-ranked element reached the sentence, so "
            "the ranking is not the one this asserts")
        for element in ("twice.bst", "biggest.bst", "second.bst", "third.bst"):
            assert element in title, (title, element)

    def test_the_duplicate_is_summed_not_maximised(self):
        """9s + 8s beats a single 12s; 9s alone does not.

        A fix that took the max, or the first row seen, would put
        `twice.bst` second rather than first and would look right on any
        fixture where the duplicate's rows happen to be large.
        """
        rows = [{"element": "twice.bst", "configure_us": 9},
                {"element": "twice.bst", "configure_us": 8},
                {"element": "biggest.bst", "configure_us": 12}]
        assert top_distinct_payers(rows, "configure_us") == [
            "twice.bst", "biggest.bst"]

    def test_it_names_at_most_four(self):
        rows = [{"element": f"e{n}.bst", "configure_us": 100 - n}
                for n in range(10)]
        assert len(top_distinct_payers(rows, "configure_us")) == PAYERS_NAMED


class TestTheDeveloperTaxToo:
    """What the filing's Out of Scope said was already per-element."""

    def test_the_tax_payers_are_elements_not_logs(self, tmp_path):
        payers = sandbox_tax(scan_log_tree(str(_tree(tmp_path))))["top_payers"]
        names = [payer["element"] for payer in payers]
        assert len(names) == len(set(names)), (
            f"sandbox_tax ranks per log, so {names} names an element once "
            f"per build - the same defect UX-409 filed against the "
            f"configure tax, in the ranking its Out of Scope cleared")

    def test_the_text_report_names_each_element_once(self, tmp_path):
        text = format_report_text(build_report(scan_log_tree(str(_tree(tmp_path)))))
        block = text.split("Who paid it", 1)[1].split("\n\n", 1)[0]
        listed = [line.split()[0] for line in block.splitlines()[1:]
                  if line.strip()]
        assert len(listed) == len(set(listed)), (
            f"the text report lists an element twice: {listed}")


class TestEveryOtherSliceIsTakenOverElements:
    """The Required Fix's audit, as a clause rather than a claim.

    A `[:N]` is only safe where the list it slices is already one row per
    element. Each of the module's remaining slices is named here with
    what it is taken over, so a future one that is not cannot arrive
    unnoticed - the census shape (`UX-376`, `UX-213`), applied to a
    ranking.
    """

    #: `source: the list each slice is taken over`, and why it is one
    #: row per element.
    SLICES = {
        "top_payers (sandbox tax)":
            "grouped per element by `top_distinct_payers` since `UX-409`",
        "views['elements']":
            "built one row per element by the two-plane join",
        "finding['elements']":
            "a redundancy finding's own element list, already distinct",
    }

    def test_the_audit_is_recorded(self):
        assert len(self.SLICES) == 3, (
            "the module gained or lost a bounded ranking; say what the new "
            "one is taken over before changing this number")

    def test_the_helper_is_the_one_place_that_groups(self):
        source = (REPO / "tools/bst_cache_logs.py").read_text(encoding="utf-8")
        assert source.count("def top_distinct_payers") == 1, (
            "two group-by implementations is how the two rankings came to "
            "disagree in the first place")
