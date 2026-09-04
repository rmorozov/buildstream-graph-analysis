"""UX-643: the role decides what is promoted, never what exists.

`READERS` carried five roles and the page showed all five everything;
the selector's only effect was one lead finding in one slot. A filter
was refused because the map is incomplete - 11 sections of 51 have a
derivable role - and because "hide what is not mine" collides with two
standing rules: focus never removes, and marks are never a filter.

So the role **demotes**. Measured on the exported page, sections
promoted and expanded against sections folded into `UX-347`'s chapter
and `UX-199`'s section fold:

```text
                 sections   R1   R2   R3   R4   R5
golden                 46    6    1    2    2    -
macro_micro            66    6    2    2    3    1
```

The rest of every column is folded and none of it is removed: the DOM
node count and every section's text are identical under all five roles
and back at "anyone".

**The map is derived, not judged.** `schemas._SECTION_READERS` is the
join of `provenance._CLAIMS`' evidence paths with
`findings.FINDING_READERS`, and the first clause below recomputes it -
a finding that changes reader reddens here rather than leaving a stale
role on the page.

**A browser guard** for everything below that: `data-collapsed` and
`data-open` are CSS, and whether a folded section is still reachable is
a question about layout that `tests/dom_shim.mjs` cannot answer.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)


def _derived():
    """`{section key: {role}}`, recomputed from the two tables.

    The section a finding's evidence lives in is the first segment of
    its `provenance` path; the reader is `FINDING_READERS`'. Two shapes
    contribute nothing and both are the map being incomplete rather
    than this join being wrong: `graph-width` and `memory-envelope`
    publish an empty path tuple, and `wait-category`,
    `blast-radius-reach` and `blast-radius-structural` compute their
    paths from the document, so there is no static answer to read.
    """
    from bga import findings, provenance

    role = {uid: short for uid, short, _label, _question in findings.READERS}
    joined = {}
    for finding, reader in findings.FINDING_READERS.items():
        claim = provenance._CLAIMS.get(finding)
        paths = claim[0] if claim else ()
        if not isinstance(paths, (tuple, list)):
            continue
        for path in paths:
            joined.setdefault(re.split(r"[.\[]", path)[0], set()).add(role[reader])
    return joined


class TestTheMapIsDerivedNotJudged:
    def test_the_table_is_the_join_of_the_two_it_reads(self):
        """The whole producer half. `total_duration_us` is in the join
        and is a scalar rather than a section, so it is the one key the
        table drops - stated here so dropping a second one reddens."""
        from bga import schemas

        joined = _derived()
        assert set(joined) - set(schemas._SECTION_READERS) == {"total_duration_us"}
        typed = {key: set(roles)
                 for key, roles in schemas._SECTION_READERS.items()}
        derived = {key: roles for key, roles in joined.items()
                   if key != "total_duration_us"}
        assert typed == derived, (
            "the authored map and the join of `provenance._CLAIMS` with "
            f"`findings.FINDING_READERS` disagree: typed {typed}, "
            f"derived {derived}")

    def test_every_declared_role_is_one_the_roster_has(self):
        """A section cannot serve a reader `findings.READERS` does not
        name; `READER_ROLES` is read off the roster for that reason."""
        from bga import schemas

        said = {role for roles in schemas._SECTION_READERS.values()
                for role in roles}
        assert said <= set(schemas.READER_ROLES), said - set(schemas.READER_ROLES)
        assert len(said) == len(schemas.READER_ROLES), (
            f"only {sorted(said)} of {list(schemas.READER_ROLES)} are served "
            f"by any section; a role no section serves is a role the picker "
            f"offers an empty page to")


#: Drive the picker through every option and read the page each time.
#:
#: `textOf` reads the document's words and no control's own label: the
#: `R1`-`R5` tag this item adds, and `UX-199`'s collapse caret, which is
#: `▾` open and `▸` shut and would report "the text changed" on every
#: fold. `decision` is excluded from the comparison for the same reason
#: one level up - `UX-372` already swaps a lead finding into it, which
#: is a change this item did not make.
_DRIVE = r"""
(() => {
  const textOf = (node) => {
    if (node.nodeType === 3) return node.textContent || "";
    if (node.nodeType !== 1) return "";
    if (node.hasAttribute("data-reader-tag")) return "";
    if (node.hasAttribute("data-collapse")) return "";
    return [...node.childNodes].map(textOf).join("");
  };
  const shape = () => {
    const sections = [...document.querySelectorAll("section[data-section]")];
    return {
      nodes: document.querySelectorAll("*").length,
      keys: sections.map((s) => s.getAttribute("data-section")),
      text: sections
        .filter((s) => s.getAttribute("data-section") !== "decision")
        .map((s) => textOf(s).replace(/\s+/g, " ").trim()).join(" | "),
      promoted: sections.filter((s) => s.hasAttribute("data-promoted"))
        .map((s) => s.getAttribute("data-section")),
      folded: sections.filter(
        (s) => s.getAttribute("data-collapsed") === "true"
               || s.closest('section.chapter[data-open="false"]'))
        .map((s) => s.getAttribute("data-section")),
      tagged: sections.filter(
        (s) => (s.querySelector("[data-reader-tag]")?.textContent || "").trim())
        .map((s) => s.getAttribute("data-section")),
      declares: Object.fromEntries(sections.map((s) => [
        s.getAttribute("data-section"),
        (s.querySelector("[data-reader-tag]")?.getAttribute("data-readers")
         || "").split(/\s+/).filter(Boolean)])),
    };
  };
  const select = document.querySelector("select[data-role=reader]");
  if (!select) return { picker: false };
  const landed = shape();
  const roles = {};
  for (const option of [...select.options].filter((o) => o.value)) {
    select.value = option.value;
    select.dispatchEvent(new Event("change"));
    roles[option.value] = {
      ...shape(),
      tag: document.querySelector("[data-role=reader-lead]")
             ?.getAttribute("data-reader") || null,
      role: [...document.querySelectorAll("[data-promoted]")]
        .map((n) => n.getAttribute("data-promoted"))[0] ?? null,
    };
  }

  // Reachability, under the last role chosen: an unmapped section in a
  // shut chapter, opened the way a reader opens it - the chapter's own
  // control, then the section's. Both already existed; neither is this
  // item's.
  const unmapped = [...document.querySelectorAll("section[data-section]")]
    .find((s) => !s.querySelector("[data-reader-tag]")
                 && s.closest('section.chapter[data-open="false"]'));
  let reached = null;
  if (unmapped) {
    const box = unmapped.closest("section.chapter");
    const before = unmapped.getAttribute("data-collapsed");
    box.querySelector("[data-chapter-open]")?.click();
    // Pressed only when it is shut, which is what a reader does with a
    // fold. Blind pressing would make this clause fail whenever the
    // fold above it did, and read as a reachability defect.
    if (unmapped.getAttribute("data-collapsed") === "true") {
      unmapped.querySelector("[data-collapse]")?.click();
    }
    reached = {
      key: unmapped.getAttribute("data-section"), before,
      collapsed: unmapped.getAttribute("data-collapsed"),
      chapterOpen: box.getAttribute("data-open"),
      height: unmapped.offsetHeight,
      words: (unmapped.textContent || "").trim().split(/\s+/).length,
    };
  }

  select.value = "";
  select.dispatchEvent(new Event("change"));
  return { picker: true, landed, roles, reached, anyone: shape() };
})()
"""


@pytest.fixture(scope="module")
def driven(tmp_path_factory):
    with Browser(chrome) as opened:
        return {label: opened.measure(uri, _DRIVE, 1440, 900)
                for label, uri in pages.pages(tmp_path_factory, "role").items()}


@needs_browser
@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
class TestARoleDemotesRatherThanHides:
    def test_a_role_promotes_what_it_serves_and_folds_the_rest(self, driven,
                                                              label):
        """The item. Every section declaring the chosen role is promoted
        and expanded; every other section on the page is folded, whether
        it declares another role or none at all."""
        page = driven[label]
        assert page["picker"], "no reader picker - nothing below measures"
        assert len(page["roles"]) >= 4, sorted(page["roles"])
        for chosen, seen in page["roles"].items():
            role = seen["role"]
            assert role, f"{chosen} promoted nothing and named no role"
            want = sorted(key for key, roles in seen["declares"].items()
                          if role in roles)
            assert want, f"{chosen}: no section declares {role}"
            assert sorted(seen["promoted"]) == want, (chosen, seen["promoted"])
            expanded = set(seen["keys"]) - set(seen["folded"])
            assert expanded - set(want) - {"decision"} == set(), (
                f"{chosen}: {sorted(expanded - set(want) - {'decision'})} are "
                f"expanded and are not this role's")
            assert set(want) - set(seen["folded"]) == set(want), (
                f"{chosen}: a promoted section is folded: "
                f"{sorted(set(want) & set(seen['folded']))}")

    def test_nothing_is_removed_and_no_sections_text_changes(self, driven,
                                                             label):
        """Focus never removes, and the export stays Ctrl-F honest. The
        node count moves only by `UX-372`'s lead block, which is four
        nodes and is added rather than taken away."""
        page = driven[label]
        landed = page["landed"]
        for chosen, seen in page["roles"].items():
            assert seen["keys"] == landed["keys"], (
                f"{chosen}: the section list changed")
            assert seen["text"] == landed["text"], (
                f"{chosen}: a section's text changed - "
                f"{len(seen['text'])} chars against {len(landed['text'])}")
            assert seen["nodes"] >= landed["nodes"], (
                f"{chosen}: {landed['nodes'] - seen['nodes']} DOM nodes were "
                f"removed; the role demotes and must not hide")

    def test_the_tag_is_worn_only_by_the_promoted(self, driven, label):
        """`UX-305`: emphasis is a budget spent once. The mark is on the
        sections one chosen role owns - never on the eight or ten that
        declare a role, and never on all 46 or 66."""
        page = driven[label]
        for chosen, seen in page["roles"].items():
            assert sorted(seen["tagged"]) == sorted(seen["promoted"]), (
                chosen, seen["tagged"], seen["promoted"])
            declaring = [k for k, r in seen["declares"].items() if r]
            assert len(seen["tagged"]) < len(declaring) + 1
            assert len(seen["tagged"]) < len(seen["keys"]) / 2, (
                f"{chosen} marks {len(seen['tagged'])} of {len(seen['keys'])} "
                f"sections; that is a page of emphasis, not a budget")

    def test_an_unmapped_section_stays_reachable(self, driven, label):
        """A section with no declared role is folded under every role -
        and two presses of controls that already existed put it back on
        screen, with its words."""
        page = driven[label]
        reached = page["reached"]
        assert reached, "no unmapped section was folded into a shut chapter"
        assert reached["chapterOpen"] == "true", reached
        assert reached["collapsed"] == "false", reached
        assert reached["height"] > 0, (
            f"{reached['key']} is folded and cannot be brought back on "
            f"screen: {reached}")
        assert reached["words"] > 3, reached

    def test_anyone_promotes_nothing_and_restores_the_landed_page(self,
                                                                  driven,
                                                                  label):
        """`UX-372`'s rule kept: with nobody chosen the page is what it
        was. Node count, section list, folds and marks all return."""
        page = driven[label]
        landed, anyone = page["landed"], page["anyone"]
        assert anyone["promoted"] == [], anyone["promoted"]
        assert anyone["tagged"] == [], anyone["tagged"]
        assert anyone["keys"] == landed["keys"]
        assert anyone["nodes"] == landed["nodes"], (anyone["nodes"],
                                                    landed["nodes"])
        assert sorted(anyone["folded"]) == sorted(landed["folded"]), (
            f"the fold did not come back: "
            f"{sorted(set(anyone['folded']) ^ set(landed['folded']))[:5]}")
