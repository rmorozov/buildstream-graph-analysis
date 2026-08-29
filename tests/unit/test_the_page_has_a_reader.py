"""UX-372: the page has one reader, and now it has five.

Round 58 asked whether the report shows the biggest problem *per role*.
It did not, because nothing in the payload knew roles existed:
`bga:role` is a **column** role - what a cell is for a renderer - and
`docs/design/roles.md` had named eight readers since round 27 without a
single field saying which one an answer serves.

So the page opened with one question, answered once. Measured on
`tests/fixtures/macro_micro` before this item:

```text
finding                   severity  serves
time-concentration        high      the person who can change core.bst
joint-saving              high      the same person
optimization-horizon      high      the same person
...
capacity-recommendation   high      the CI owner - finding 9 of 11
```

Three top actions, all the same advice: shorten this element, then that
one, then the third. Right for R1. No answer at all for R5, whose lever
was nine findings down, or for R2, who wanted to know whether *their*
element was a problem.

Every one of those answers was already computed. What was missing was
any statement of who each is for, so the reader did the routing.

**The default is load-bearing.** `TestTheDefaultStillAnswers` is why:
the cheapest way to make a page route by role is to make it say nothing
until somebody picks one, and this filing rules that out in as many
words.

**The producer decides, the page looks up.** `leads_with` is computed
in `bga/findings.py` beside the findings it ranks, so the CI comment
and the report cannot route differently (Direction 7). The page reads
a field.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Drive the picker through every option it offers and record what the
#: chapter leads with each time. The lead node is re-queried after every
#: change - the handler replaces it, and a cached node is the instrument
#: error round 58 made twice.
_DRIVE = r"""
(() => {
  const lead = () => {
    const n = document.querySelector("[data-role=reader-lead]");
    return n ? { reader: n.getAttribute("data-reader"),
                 finding: n.getAttribute("data-finding"),
                 text: (n.textContent || "").replace(/\s+/g, " ").trim() }
             : null;
  };
  const before = { lead: lead(),
                   actions: [...document.querySelectorAll(".actions .action")]
                     .map((r) => r.getAttribute("data-element")),
                   diagnosis: (document.querySelector(".decision .diagnosis")
                               || {}).textContent || "" };
  const select = document.querySelector("select[data-role=reader]");
  if (!select) return { picker: false, before };
  const seen = [];
  for (const option of [...select.options]) {
    select.value = option.value;
    select.dispatchEvent(new Event("change"));
    seen.push({ chose: option.value, label: option.textContent,
                got: lead() });
  }
  return { picker: true, before, seen,
           labelled: Boolean(document.querySelector(
             `label[for=${JSON.stringify(select.getAttribute("id"))}]`)) };
})()
"""


def _payload(label):
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES[label]))["report.json"]


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def driven(browser, tmp_path_factory):
    into = tmp_path_factory.mktemp("u372")
    out = {}
    for label in sorted(pages.FIXTURES):
        uri = pages.export_uri(pages.FIXTURES[label], into,
                               name=f"{label}.html")
        out[label] = browser.measure(uri, _DRIVE, 1440, 900)
    return out


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestEveryFindingNamesItsReader:
    def test_every_published_finding_declares_one(self, label):
        """The clause the defect fails: it was zero of eleven."""
        naked = [f.get("id") for f in _payload(label).get("findings") or []
                 if not f.get("reader")]
        assert naked == [], (
            f"{label}: finding(s) serving nobody in particular: {naked}")

    def test_the_readers_are_more_than_one(self, label):
        """`UX-372`'s own falsification. One reader with every finding
        is the page before this item wearing a new field."""
        readers = _payload(label).get("readers") or []
        assert len(readers) > 1, (
            f"{label} publishes {len(readers)} reader(s); a role model "
            f"with one role is the page that had none")

    def test_the_index_agrees_with_the_findings(self, label):
        """Two statements of one fact is how they drift. `readers[]` is
        an index over `findings[].reader`, so it can be rebuilt from it
        and must match when it is."""
        payload = _payload(label)
        published = {}
        for finding in payload.get("findings") or []:
            published.setdefault(finding.get("reader"), []).append(
                finding.get("id"))
        for entry in payload.get("readers") or []:
            assert entry["findings"] == published.get(entry["id"]), entry
            assert entry["leads_with"] in entry["findings"], entry

    def test_a_reader_with_nothing_to_say_is_not_offered(self, label):
        """The dead-control rule (`UX-194`) at the contract level: the
        index carries readers this run has findings for, and no
        others."""
        from bga.findings import READERS

        payload = _payload(label)
        offered = [e["id"] for e in payload.get("readers") or []]
        served = {f.get("reader") for f in payload.get("findings") or []}
        assert offered == [uid for uid, _r, _l, _q in READERS
                           if uid in served], (
            f"{label}: offered {offered}, has findings for {sorted(served)}")


class TestTheAssignmentIsExhaustive:
    """A map with a hole defaults silently, and a finding serving
    nobody is the state this item found. Held against the source rather
    than against a fixture: the module can emit twenty-one ids and
    the larger fixture publishes eleven."""

    #: Every `_finding(...)` call's first argument. **Not** the severity
    #: form: the scan this was written with read
    #: `'<id>', SEVERITY_<BAND>` and found nineteen of the twenty-one
    #: ids, silently missing `memory-envelope` and
    #: `capacity-recommendation` - the two whose severity is computed
    #: into a local and passed as a variable. Both belong to
    #: `capacity-operator`, so an instrument blind to exactly them
    #: would have been blind to the reader this item was filed about.
    #: Caught by mutation M1, which deleted `capacity-recommendation`
    #: from the map and left this clause silent.
    _EMITS = r"_finding\(\s*'([a-z0-9-]+)'"

    def _emitted(self):
        import re

        from bga import findings as module

        source = pathlib.Path(module.__file__).read_text(encoding="utf-8")
        found = set(re.findall(self._EMITS, source))
        assert len(found) >= 21, (
            f"the id scan found {len(found)}; it has stopped seeing calls "
            f"it used to see")
        return found

    def test_every_id_the_module_can_emit_has_a_reader(self):
        from bga.findings import FINDING_READERS

        missing = sorted(self._emitted() - set(FINDING_READERS))
        assert missing == [], (
            f"finding id(s) with no reader in FINDING_READERS: {missing} - "
            f"a new finding must name who it is for rather than defaulting "
            f"to nobody")

    def test_the_map_names_no_finding_that_does_not_exist(self):
        """The other direction. A stale entry is not harmless: it is the
        evidence that the map was maintained, and it is not."""
        from bga.findings import FINDING_READERS

        stale = sorted(set(FINDING_READERS) - self._emitted())
        assert stale == [], (
            f"FINDING_READERS names finding id(s) nothing emits: {stale}")

    def test_no_reader_is_named_that_the_vocabulary_lacks(self):
        from bga.findings import FINDING_READERS, READERS

        known = {uid for uid, _r, _l, _q in READERS}
        stray = sorted(set(FINDING_READERS.values()) - known)
        assert stray == [], f"reader(s) outside READERS: {stray}"

    def test_every_reader_in_the_vocabulary_serves_something(self):
        """The other direction: a role in the closed set that no finding
        ever names is a selector option that can never appear."""
        from bga.findings import FINDING_READERS, READERS

        used = set(FINDING_READERS.values())
        idle = [uid for uid, _r, _l, _q in READERS if uid not in used]
        assert idle == [], (
            f"reader(s) no finding serves: {idle} - either give them one "
            f"or take them out of the vocabulary")

    def test_the_ids_are_the_role_models_own(self):
        """`roles.md` has named these readers since round 27. Two
        vocabularies for one idea is what `UX-353` was filed for."""
        from bga.findings import READERS

        text = (REPO / "docs/design/roles.md").read_text(encoding="utf-8")
        for _uid, role, _label, _question in READERS:
            assert f"| {role} |" in text, (
                f"{role} is not a row in docs/design/roles.md")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestChoosingAReaderChangesTheAnswer:
    def test_the_picker_is_offered(self, driven, label):
        assert driven[label]["picker"] is True, (
            f"{label} publishes more than one reader and the page offers no "
            f"way to be one")

    def test_the_control_has_a_label(self, driven, label):
        """`UX-334`: a form control the browser can name."""
        assert driven[label]["labelled"] is True

    def test_every_option_leads_with_something(self, driven, label):
        """A selector that reorders nothing is furniture. Every option
        but the default produces a lead block."""
        blank = [row["chose"] for row in driven[label]["seen"]
                 if row["chose"] and not row["got"]]
        assert blank == [], (
            f"{label}: option(s) that change nothing: {blank}")

    def test_two_readers_do_not_get_the_same_answer(self, driven, label):
        """The clause that makes the routing mean something. Distinct
        readers, distinct leads - if every option landed on the same
        finding the page would still have one reader."""
        leads = [row["got"]["finding"] for row in driven[label]["seen"]
                 if row["got"]]
        assert len(set(leads)) == len(leads), (
            f"{label}: {len(leads)} readers, {len(set(leads))} distinct "
            f"lead(s): {leads}")

    def test_the_lead_is_the_published_one(self, driven, label):
        """Direction 7, asserted at the seam: the page shows what
        `readers[].leads_with` says, not something it ranked itself."""
        declared = {e["id"]: e["leads_with"]
                    for e in _payload(label).get("readers") or []}
        for row in driven[label]["seen"]:
            if not row["got"]:
                continue
            assert row["got"]["finding"] == declared.get(row["chose"]), row

    def test_the_lead_carries_the_readers_question(self, driven, label):
        """Not just a finding id: the block says what was asked, so the
        answer reads as an answer."""
        asked = {e["id"]: e["question"]
                 for e in _payload(label).get("readers") or []}
        for row in driven[label]["seen"]:
            if not row["got"]:
                continue
            assert asked[row["chose"]] in row["got"]["text"], row


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheDefaultStillAnswers:
    """The filing's own constraint, in as many words: *this must not
    become a page that answers nothing until you fill in a form.*"""

    def test_nobody_chosen_leads_with_nothing_extra(self, driven, label):
        assert driven[label]["before"]["lead"] is None, (
            f"{label} shows a reader's answer before anybody said who they "
            f"are")

    def test_the_diagnosis_is_there_before_any_choice(self, driven, label):
        assert driven[label]["before"]["diagnosis"].strip(), (
            f"{label} says nothing until a reader is chosen")

    def test_the_actions_are_there_before_any_choice(self, driven, label):
        assert driven[label]["before"]["actions"], (
            f"{label} ranks nothing until a reader is chosen")

    def test_choosing_nobody_again_puts_it_back(self, driven, label):
        """The default is reachable, not just initial - a one-way
        selector is a page that answers nothing after one click."""
        back = [row for row in driven[label]["seen"] if not row["chose"]]
        assert back and back[0]["got"] is None, back


class TestTheHeadlineWins:
    """`UX-365`'s defect, one field over.

    Severity-then-published-order gave R1 `wait-category` on
    `macro_micro` - "5.9% of wall-clock is UNTRACKED HEAD", 2.72s -
    while `headline.top_actions` and the decision chapter both named
    `time-concentration`, worth 23.1s. A page that routed one way and
    led another is the round-58 finding recreated.
    """

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_the_ranked_finding_leads_for_whoever_owns_it(self, label):
        payload = _payload(label)
        ranked = next((a.get("finding_id")
                       for a in payload["headline"].get("top_actions") or []
                       if a.get("finding_id")), None)
        if not ranked:
            pytest.skip(f"{label} ranks no action to defer to")
        owners = [e for e in payload.get("readers") or []
                  if ranked in e["findings"]]
        assert owners, (
            f"{label}: the headline ranks {ranked!r} and no reader claims it")
        for entry in owners:
            assert entry["leads_with"] == ranked, (
                f"{label}: {entry['id']} leads with {entry['leads_with']!r} "
                f"while the headline this page opens with names {ranked!r}")

    def test_the_deference_is_the_rule_and_not_the_data(self):
        """Both fixtures happen to rank a finding R1 owns, so the clause
        above could pass on a `reader_index` that ignored the headline
        entirely if severity order agreed. This drives the function with
        a headline that disagrees."""
        from bga.findings import reader_index

        findings = [
            {"id": "wait-category", "severity": "high"},
            {"id": "time-concentration", "severity": "medium"},
        ]
        plain = reader_index(findings)
        assert plain[0]["leads_with"] == "wait-category", plain
        deferred = reader_index(
            findings,
            {"top_actions": [{"finding_id": "time-concentration"}]})
        assert deferred[0]["leads_with"] == "time-concentration", deferred


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
