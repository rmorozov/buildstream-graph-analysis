"""UX-365: the list opens with an action, and a superlative names its scope.

Round 58 read the findings the way an outside user does - top down, act
on the first. On `tests/fixtures/macro_micro` that was:

```text
#0  info  cache-hit-ratio  "...so a 0% hit ratio is the intent rather
                             than a finding"
#1  info  confidence       a score, not an action
#2  high  wait-category    "Biggest Opportunity: 5.9% of wall-clock
                             time is UNTRACKED HEAD (2.72s)"
#5  high  joint-saving     "the top 3 are worth 23.1s (50% of build)"
```

Two defects, and they compound.

**The first two entries are `info`, and the first disclaims itself.**
The page's own decision chapter is right - it opens "What should I do?"
and names `core.bst saves 12.1 s` - so a reader who trusts the top of
the page is served while a reader who trusts the *findings* is not. The
findings are what `--format json` and the CI comment read.

**The word "Biggest" was on the smallest of the three.** 2.72s against
a sibling worth 23.1s, and `headline.top_actions` agreed with the
sibling. The measurement was never wrong: `wait-category` really is the
largest of the non-execution *wait categories*. The scope was missing,
so a true claim over one population read as a claim over the report.

Both fixes are re-orderings and re-wordings, not new analysis. Nothing
was dropped, which `TestNothingWasLostInTheReorder` is here to hold:
the cheapest way to make a list open with an action is to delete the
entries that are not one.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402

#: Words that assert a maximum. A finding using one is claiming
#: something about every other candidate, so it either names the
#: population it won or it is not written (§1c).
SUPERLATIVES = ("biggest", "largest", "worst", "greatest", "top ")

#: Nouns that name no population at all. "Biggest Opportunity" scopes
#: nothing - every finding is an opportunity - which is what made the
#: 2.72s entry read as the report's maximum.
UNSCOPED = ("opportunity", "problem", "issue", "win", "thing", "one")

#: Severities that are an action rather than a description.
ACTIONABLE = ("critical", "high")


def _findings(label):
    from tools.bga_view import payloads

    return payloads(str(pages.FIXTURES[label]))["report.json"]["findings"]


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestTheListOpensWithAnAction:
    def test_the_first_finding_is_not_a_description(self, label):
        """The clause the defect fails. Not "sort by severity" - the
        order carries decisions a blanket sort would break (`UX-54`
        puts a failed build first, `UX-116` puts capacity after the
        memory envelope it consumes). The claim is narrower: a reader
        who reads one finding reads an actionable one, whenever the
        report has any."""
        found = _findings(label)
        severities = [f.get("severity") for f in found]
        if not any(s in ACTIONABLE for s in severities):
            pytest.skip(f"{label} publishes no actionable finding to lead with")
        assert severities[0] in ACTIONABLE, (
            f"{label} opens with {severities[0]!r} "
            f"({found[0].get('id')!r}) while {severities.count('high')} "
            f"actionable finding(s) wait below it")

    def test_no_finding_disclaims_itself_above_an_action(self, label):
        """The sharper half of the same reading. `cache-hit-ratio` said
        of itself that a 0% hit ratio "is the intent rather than a
        finding" - and was the first thing in the list of findings."""
        found = _findings(label)
        actions = [i for i, f in enumerate(found)
                   if f.get("severity") in ACTIONABLE]
        if not actions:
            pytest.skip(f"{label} publishes no actionable finding")
        # Above the **first** action, not above every one. Several
        # actionable findings sit late for reasons of their own -
        # `UX-116` puts the capacity recommendation after the memory
        # envelope it consumes - and a clause demanding that nothing
        # actionable follow a description would be re-litigating those
        # rather than holding this one.
        for index, finding in enumerate(found):
            title = (finding.get("title") or "").lower()
            if "rather than a finding" not in title:
                continue
            assert index > actions[0], (
                f"{label}: {finding.get('id')!r} says it is not a finding "
                f"and sits at {index}, above the first action at "
                f"{actions[0]}")


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestASuperlativeNamesItsPopulation:
    def test_no_title_claims_an_unscoped_maximum(self, label):
        """§1c. A word asserting a maximum is a claim about every other
        candidate; where the tool has not compared them, it says what it
        measured and stops."""
        bad = []
        for finding in _findings(label):
            title = (finding.get("title") or "")
            lowered = title.lower()
            for word in SUPERLATIVES:
                at = lowered.find(word)
                if at < 0:
                    continue
                rest = lowered[at + len(word):].lstrip()
                # What it is biggest *of* - the first word after the
                # superlative, up to the colon that ends the label.
                scope = rest.split(":")[0].strip()
                if not scope or scope.split()[0] in UNSCOPED:
                    bad.append((finding.get("id"), title[:70]))
        assert bad == [], (
            f"{label}: superlative(s) naming no population: {bad}")

    def test_the_scoped_superlative_still_says_it(self, label):
        """The other direction, so the fix cannot be deleting the word.
        A report with a wait-category finding says which category won."""
        titles = [(f.get("id"), f.get("title") or "") for f in _findings(label)]
        waits = [t for i, t in titles if i in ("wait-category",
                                               "execution-bound")]
        if not waits:
            pytest.skip(f"{label} publishes no wait-category finding")
        for title in waits:
            assert re.search(r"biggest wait category", title, re.I), (
                f"{label}: the wait-category finding no longer says what it "
                f"is the biggest of: {title!r}")


class TestNothingWasLostInTheReorder:
    """The cheapest way to open a list with an action is to delete
    everything that is not one. These hold the population."""

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_the_context_findings_are_still_published(self, label):
        published = {f.get("id") for f in _findings(label)}
        # `confidence` is published for every run. `cache-hit-ratio`
        # and `run-mode-incremental` are conditional - `golden`
        # publishes neither - so the population clause below checks
        # where they are when they exist rather than that they do.
        assert "confidence" in published, published

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_context_follows_every_action_it_frames(self, label):
        """Where they went, asserted as a relationship rather than an
        index: the run's description sits below the actions, and the
        blocking facts - if this run has any - stay above them."""
        found = _findings(label)
        order = {f.get("id"): i for i, f in enumerate(found)}
        actions = [i for i, f in enumerate(found)
                   if f.get("severity") in ACTIONABLE
                   and f.get("id") not in ("build-failed", "failed-task-time")]
        if not actions:
            pytest.skip(f"{label} publishes no actionable finding")
        for context in ("cache-hit-ratio", "confidence"):
            if context in order:
                assert order[context] > min(actions), (
                    f"{label}: {context!r} is at {order[context]}, above the "
                    f"first action at {min(actions)}")

    def test_a_failed_build_still_leads(self):
        """`UX-54`, which this item had to not break: a capture whose
        elements failed says so before any efficiency number. Asserted
        against the module rather than a fixture, because neither
        committed fixture failed."""
        import inspect

        from bga import findings as module

        source = inspect.getsource(module.compute_findings)
        blocking = source.index("_run_blocking_findings")
        context = source.index("_run_context_findings")
        assert blocking < context, (
            "the run's blocking facts no longer precede its description; "
            "UX-54's failed build would be reported after the numbers it "
            "invalidates")
        assert "UX-54" in inspect.getsource(module._run_blocking_findings), (
            "the blocking half no longer carries the reason it is first")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
