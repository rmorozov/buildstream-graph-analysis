"""UX-390: attribution and its hints were one population in two sections.

The user asked whether the two could be one section. Measured on the
round-63 capture, they were one population already - the key sets are
identical:

```text
attribution        execution_on_chain_us dependency_wait_us resource_wait_us
                   scheduler_wait_us idle_us retry_wait_us
                   untracked_head_us untracked_tail_us
attribution_hints  (the same eight)
SAME KEY SET       True
```

Eight buckets, two `<h2>` sections, each carrying a different sentence
about the same field. A reader met a number in one chapter and its
explanation in another, and nothing in either said they were the same
eight things - `UX-288`'s one-population rule at section level.

The hints half also printed its keys raw, unit suffix and all:

```text
Execution on chain us
Dependency wait us
```

`UX-351` established that a label does not print the unit the value
already carries. That section predated it and was never swept - and
the merge fixes it for free, because the row's label now comes from the
map whose members declare `duration_us`.

**Two sentences, not one.** The schema's `description` says what a
bucket *is* and travels with the contract; the hint says what to do
about it **on this run** - `resource_wait_us`'s names whether this
run's capacity checks could run at all. So the hint is not a
description, and `bga:explained_by` is what lets the page draw both on
one row without sniffing for a key named `<something>_hints`
(`UX-201`).
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import schemas                                       # noqa: E402
from tests import pages                                       # noqa: E402
from tests.browser import NO_BROWSER, Browser, find_chrome     # noqa: E402

RUN = REPO / "tests/fixtures/macro_micro/run"

#: The suffixes a rendered label must never end in: the value already
#: prints the unit (`UX-351`).
UNIT_SUFFIXES = (" us", " bytes", " s", " ms")


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def seen(tmp_path_factory):
    if find_chrome() is None:
        pytest.skip(NO_BROWSER)
    look = """(() => {
      const of = (key) => {
        const s = document.querySelector(`section[data-section="${key}"]`);
        if (!s) return null;
        // Paired, not two lists: a rendering that collected the
        // sentences at the foot of the section would give the same
        // two counts and is the two-section defect at half the
        // distance. Found by the mutation that did exactly that and
        // left every clause green.
        const rows = [];
        for (const term of s.querySelectorAll("dt")) {
          const value = term.nextElementSibling;
          rows.push({
            label: (term.textContent || "").replace(/\\s*\\?\\s*$/, "").trim(),
            advice: [...(value?.querySelectorAll("p.run-advice") ?? [])]
              .map((p) => (p.textContent || "").trim()),
          });
        }
        return {
          rows,
          labels: rows.map((r) => r.label),
          advice: rows.flatMap((r) => r.advice),
          loose: [...s.querySelectorAll("p.run-advice")].length,
        };
      };
      return { attribution: of("attribution"),
               hints: of("attribution_hints"),
               sections: [...document.querySelectorAll("section[data-section]")]
                 .map((s) => s.getAttribute("data-section")) };
    })()"""
    into = tmp_path_factory.mktemp("attribution")
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], into)
    with Browser(find_chrome()) as browser:
        return browser.measure(uri, look, 1440, 900)


class TestThePopulationIsStillOne:
    def test_the_two_keys_carry_the_same_bucket_names(self, payload):
        """The premise, re-measured on the committed fixture.

        If the payload ever stopped publishing one hint per bucket this
        item's whole argument would be gone, and the merge would be
        hiding rows rather than joining them.
        """
        assert set(payload["attribution"]) == set(payload["attribution_hints"])
        assert len(payload["attribution"]) == 8


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestOneSection:
    def test_the_hints_have_no_section_of_their_own(self, seen):
        assert seen["hints"] is None, (
            "`attribution_hints` still draws a second `<h2>` over the "
            "same eight bucket names")
        assert "attribution_hints" not in seen["sections"]

    def test_no_hint_was_lost_in_the_merge(self, seen, payload):
        """The clause that makes "merge" mean merge rather than delete.

        The count of explained buckets must not drop - which is the
        one way this fix could look right and be a deletion.
        """
        assert len(seen["attribution"]["advice"]) == len(
            payload["attribution_hints"]), seen["attribution"]["advice"]
        for bucket, hint in payload["attribution_hints"].items():
            assert any(hint.strip() in shown
                       for shown in seen["attribution"]["advice"]), bucket

    def test_the_advice_is_on_the_row_of_its_bucket(self, seen, payload):
        """Not collected at the foot of the section.

        A list of eight sentences under a list of eight numbers is the
        two-section defect at half the distance - and it passes any
        clause that only counts the two, which is what the first
        version of this one did.
        """
        rows = seen["attribution"]["rows"]
        assert rows, seen
        assert seen["attribution"]["loose"] == len(
            seen["attribution"]["advice"]), (
            "a `run-advice` paragraph is in the section but not inside "
            "any bucket's `<dd>`")
        for row in rows:
            assert len(row["advice"]) == 1, row
        # Each bucket's own sentence, matched by the label it sits under.
        for bucket, hint in payload["attribution_hints"].items():
            label = bucket.removesuffix("_us").replace("_", " ").capitalize()
            mine = [row for row in rows if row["label"].lower() == label.lower()]
            assert mine, (label, [row["label"] for row in rows])
            assert mine[0]["advice"] == [hint.strip()], mine[0]

    def test_no_label_prints_the_unit_the_value_carries(self, seen):
        """`UX-351`, on the eight labels that never got the sweep."""
        offenders = [label for label in seen["attribution"]["labels"]
                     if label.endswith(UNIT_SUFFIXES)]
        assert offenders == [], offenders
        assert "Execution on chain" in seen["attribution"]["labels"]


class TestItIsDeclaredRatherThanSniffed:
    def test_the_contract_says_where_the_advice_lives(self):
        node = schemas.schema(schemas.ANALYZE)["properties"]["attribution"]
        assert node.get(schemas.EXPLAINED_BY) == "attribution_hints", (
            "a page that looked for `<key>_hints` would be the "
            "name-guessing UX-201 removed")

    def test_the_advice_is_not_the_schema_sentence(self, payload):
        """Two sentences, and the run computes one of them.

        `resource_wait_us`'s hint names whether *this run's* capacity
        checks could run, which no contract description could say - so
        the hint cannot become a `description` and the declaration is
        the only way the page can find it.
        """
        described = schemas.schema(schemas.ANALYZE)["properties"][
            "attribution"]["properties"]["resource_wait_us"]["description"]
        computed = payload["attribution_hints"]["resource_wait_us"]
        assert described != computed
        assert "this run" in computed, computed
