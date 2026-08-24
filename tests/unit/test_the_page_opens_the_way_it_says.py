"""UX-256: the page's default open state is a census, not a claim.

The report asked for *"a checker if everything is really collapsed by
default"*. Measured in Chromium on the exported page of a
1,202-element run, the answer is that the policy is the opposite of
that, deliberately:

```text
<details> on the page   49
open on load             3   — all three labelled "Why"
sections                12   — all open, by design
```

Both defaults are decisions with reasons already written down, and
neither should quietly become the other:

- `nav.js`: *"Default-open, always: a report that hid itself on first
  load would answer the navigation complaint by making the document
  harder to read, not easier."* (`UX-199`)
- `views.js` opens the provenance chain on the **top action** only —
  the one claim a reader is most likely to challenge (`UX-227`).

So the defect was never "things are open". It was that **nothing
checked the rule that does hold**, in either direction: a change that
opened forty of the forty-nine, or closed the one that should be open,
would have shipped with nothing reddening.

This is `UX-235`'s skip census in a second place — a count with named,
reasoned exceptions beats a prose claim that everything is fine.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWS = (REPO / "bga/viewer/views.js").read_text(encoding="utf-8")
NAV = (REPO / "bga/viewer/nav.js").read_text(encoding="utf-8")

# Every place the viewer opens a `<details>` on first load, and why.
# An addition here is a decision someone wrote down; an addition
# without one is a diff nobody read.
OPEN_BY_DEFAULT = {
    "renderWhyRanked": (
        "UX-227: the provenance chain on the *top* action only - the one "
        "claim a reader is most likely to challenge, and the one whose "
        "evidence is worth the vertical space"),
}


def _code(source):
    """Source with comments stripped.

    A guard that greps for `setAttribute("open"` finds it in every
    comment that explains why something is or is not opened. That is
    the subject-versus-argument failure `UX-239` named, and this file
    would have shipped with it.
    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.M)


def _opening_sites(source):
    """Function names containing a call that opens a `<details>`."""
    code = _code(source)
    sites = []
    current = "<module>"
    for line in code.splitlines():
        named = re.match(r"\s*(?:export\s+)?function\s+(\w+)", line)
        if named:
            current = named.group(1)
        if re.search(r'setAttribute\(\s*"open"|\.open\s*=\s*true', line):
            sites.append(current)
    return sites


class TestTheOpenSetIsNamed:
    def test_every_place_that_opens_something_is_accounted_for(self):
        unexplained = sorted(set(_opening_sites(VIEWS)) - set(OPEN_BY_DEFAULT))
        assert unexplained == [], (
            f"the viewer opens a <details> in {unexplained} and this census "
            f"does not say why. Add it to OPEN_BY_DEFAULT with a reason, or "
            f"stop opening it - a page that opens by default is vertical "
            f"space every reader pays for (UX-254).")

    def test_the_census_names_only_places_that_exist(self):
        """An exemption for a function that is gone quietly widens the
        rule it is an exception to."""
        stale = sorted(set(OPEN_BY_DEFAULT) - set(_opening_sites(VIEWS)))
        assert stale == [], f"census entries for nothing: {stale}"

    def test_exactly_one_thing_opens_by_default(self):
        """The measurement, pinned. Three `<details>` are open on the
        real page and all three come from this one site - the top
        action's chain, rendered once per top action."""
        assert len(set(_opening_sites(VIEWS))) == 1, _opening_sites(VIEWS)

    def test_each_exemption_carries_a_reason_and_its_item(self):
        for name, reason in OPEN_BY_DEFAULT.items():
            assert re.search(r"UX-\d+", reason), f"{name}: no item id"
            assert len(reason) > 60, f"{name}: the reason is a label"


class TestSectionsAreOpenOnPurpose:
    def test_sections_are_default_open_and_the_reason_survives(self):
        """`UX-199`'s reasoning, pinned where the next person who thinks
        collapsing them would be tidier will meet it."""
        assert "Default-open, always" in NAV, (
            "nav.js no longer states the default-open policy, so the next "
            "change to it will be made without the argument against it")

    def test_a_reader_can_still_collapse_everything(self):
        """Default-open is only defensible because collapsing is one
        click and is remembered."""
        code = _code(NAV)
        assert "Collapse all" in code and "Expand all" in code
        assert "writeCollapsed" in code, (
            "what a reader collapses is no longer remembered, which makes "
            "default-open a decision they have to re-make every load")

    def test_nothing_collapses_a_section_on_first_load(self):
        """The other direction. A stored preference may collapse a
        section; the *page* may not decide to on its own."""
        code = _code(NAV)
        collapsed = code.split("export function collapsible", 1)[1]
        assert "readCollapsed(storage)" in collapsed, (
            "the collapsed set no longer comes from storage alone, so the "
            "page may now hide a section a reader never hid")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
