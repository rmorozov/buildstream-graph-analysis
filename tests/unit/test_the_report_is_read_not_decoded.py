"""UX-269..UX-272: truncation, the critical path, the rail, the header.

Four of the nine observations from a real run. Each was measured before
it was acted on, and two of them are measurements that **disagreed**
with the request — recorded here so the argument survives.

```text
UX-269  field lengths, measured: 678 chars `copy_text`, 572
        `capacity_model_note`, 293 `attribution_hints.resource_wait_us`.
        A flat cap is wrong: a paragraph meant to be copied and a caveat
        on a number want opposite treatment.
UX-270  the critical path was a row inside `signals`, and the one member
        that rendered a whole `<section>` into a `<dd>`.
UX-271  the rail is flat at 30+ sections. A third column was requested
        and is declined - Direction 12 - because a structural tree makes
        the document's shape the organising principle and a third column
        leaves under 900px of reading width at 1440.
UX-272  the header is 92px at 1440 and 134px at 390: 0.1-0.2 screens of
        a 13-15 screen document. Worth tidying because it is *sticky*,
        not because it is where the space goes.
```
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
# `UX-337`: `app.js` was one file when these clauses were written. The
# formatters and the schema-hint readers moved to `format.js`, and the
# machinery that turns a value into an interrogable table moved to
# `structured.js` - unchanged, in a commit that was a move. These
# clauses are about what the viewer declares, not about which file
# declares it, so they read all three; pointing them at `app.js` alone
# would have quietly stopped seeing the constants they defend.
# `UX-450` added a fourth: the section walk left `app.js` for
# `sections.js`, and `liftedCriticalPath`'s caller went with it.
APP_MODULES = ("app.js", "sections.js", "format.js", "structured.js")
APP = "\n".join((REPO / "bga/viewer" / _name).read_text(encoding="utf-8")
                for _name in APP_MODULES)
NAV = (REPO / "bga/viewer/nav.js").read_text(encoding="utf-8")
CSS = (REPO / "bga/viewer/style.css").read_text(encoding="utf-8")
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _run(script):
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60,
                          env={**os.environ, "BGA_DOM_SHIM":
                               (REPO / "tests/dom_shim.mjs").as_uri()})
    assert done.returncode == 0, done.stderr
    import json
    return json.loads(done.stdout)


def _declarations(css):
    """`css` with comments stripped.

    A guard that greps a stylesheet finds its own argument: the comment
    explaining why `--head` changes at the breakpoint contains the
    string `--head`, so deleting the rule left the check green. That is
    the subject-versus-argument failure this repository has now filed
    eleven times (`UX-239`).
    """
    import re as _re

    return _re.sub(r"/\*.*?\*/", "", css, flags=_re.S)


def _media_blocks(query):
    """Every `@media <query> { … }` body, brace-matched.

    Not `CSS.split(query)[1]`: that returns everything *after* the first
    breakpoint, including unrelated rules further down the file, so the
    first draft of the guards below passed with the rule they check
    deleted. Two mutations proved it.
    """
    bodies = []
    at = 0
    while True:
        at = CSS.find(f"@media {query}", at)
        if at == -1:
            return bodies
        start = CSS.index("{", at)
        depth, i = 0, start
        while i < len(CSS):
            if CSS[i] == "{":
                depth += 1
            elif CSS[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        bodies.append(_declarations(CSS[start:i + 1]))
        at = i


_TEXT = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const long = "word ".repeat(80);
const out = {};
for (const name of ["copy_text", "capacity_model_note", "resource_wait_us",
                    "anything_note", "plain"]) {
  const drawn = app.renderText(name, long);
  out[name] = { tag: drawn.tagName, kept: (drawn.attrs["data-raw"] ?? "").length };
}
out.short = { tag: app.renderText("plain", "fine").tagName, kept: 4 };
console.log(JSON.stringify(out));
"""


@needs_node
class TestALongValueIsTruncatedAndASentenceIsNot:
    def test_a_long_value_truncates_with_the_whole_thing_kept(self):
        out = _run(_TEXT)
        assert out["copy_text"]["tag"] == "details", out
        assert out["copy_text"]["kept"] == 400, (
            "the full value is not carried on the cell, so a reader who "
            "opens it does not get what was measured")

    def test_a_declared_explanation_is_never_truncated(self):
        """The half that matters: hiding a caveat by default is how a
        reader stops seeing it."""
        out = _run(_TEXT)
        for name in ("capacity_model_note", "resource_wait_us",
                     "anything_note"):
            assert out[name]["tag"] == "span", f"{name} was truncated"

    def test_a_short_value_is_left_alone(self):
        assert _run(_TEXT)["short"]["tag"] == "span"

    def test_the_cap_and_the_exemptions_are_declared(self):
        assert "export const CELL_TEXT_CAP" in APP
        assert "export const EXPLANATIONS" in APP
        for name, why in re.findall(r'^\s{2}(\w+): "([^"]+)"', APP, re.M)[:0]:
            pass  # the reasons are prose; the census below checks them

    def test_every_exemption_carries_a_reason(self):
        block = APP.split("export const EXPLANATIONS = {", 1)[1]
        block = block.split("\n};", 1)[0]
        entries = re.findall(r"(\w+):\s*\"(.*?)\"(?:\s*\+\s*\"(.*?)\")*", block,
                             re.S)
        assert len(entries) >= 4, block
        for entry in entries:
            reason = "".join(part for part in entry[1:] if part)
            assert len(reason) > 25, entry


class TestTheCriticalPathIsItsOwnSection:
    def test_it_is_lifted_out_of_the_pair_list(self):
        """`UX-344` lifted the namespace it used to be a row of, so the
        skip is gone and the *document* publishes it as a key. What is
        still `UX-270`'s claim is that the page draws it as a section of
        its own, with the chain's own fold, rather than as a table in a
        pair list."""
        assert 'export const LIFTED_SECTION = "critical_path_detail"' in APP
        assert "liftedCriticalPath(payload, schema)" in APP

    def test_it_is_rendered_as_a_section_of_its_own(self):
        assert "export function liftedCriticalPath" in APP
        block = APP.split("export function liftedCriticalPath", 1)[1]
        block = block.split("\n}", 1)[0]
        assert "renderTable(" in block, (
            "the lifted view uses buildTable, so it is a cell rather than a "
            "section and nothing can link to it")

    def test_a_run_without_a_path_renders_nothing_rather_than_an_empty_box(self):
        assert "if (!Array.isArray(rows) || !rows.length) return null;" in APP


class TestTheRailNestsRatherThanGrowingAColumn:
    def test_the_rail_has_a_second_level(self):
        assert "export function subsections" in NAV
        assert 'className = "toc-sub"' in NAV

    def test_the_rail_actually_calls_it(self):
        """The wiring, not the definition. `void subsections;` left
        every other guard in this class green - a non-discriminating
        mutation, and the reason this test exists."""
        builder = NAV.split("for (const key of members) {", 1)[1]
        builder = builder.split("nav.append(list);", 1)[0]
        assert "subsections(section, doc)" in builder, (
            "the rail no longer builds its second level, so it is flat "
            "again (UX-271)")
        assert "item.append(inner)" in builder

    def test_the_nested_list_is_bounded_and_says_what_it_hid(self):
        """`UX-208`'s rule: a reader who cannot see the denominator
        cannot tell a bounded list from a short one."""
        assert "export const SUBSECTIONS_SHOWN" in NAV
        block = NAV.split("export function subsections", 1)[1].split("\n}\n", 1)[0]
        assert "more`" in block or "more\"" in block, block[-400:]

    def test_the_third_column_stays_declined_with_its_argument(self):
        """`UX-271` declined a third navigation column. The argument
        lives beside the code that answers the need instead, so the
        next person to propose it meets it."""
        assert "UX-271" in NAV
        assert "third column" in NAV, (
            "the declined alternative is no longer recorded, so it will be "
            "re-proposed without the measurement against it")

    def test_the_grid_still_has_two_content_columns(self):
        """The measurement behind the refusal: a third column would
        leave under 900px of reading width at 1440 (`UX-254`)."""
        rule = re.findall(r"body\[data-has-toc\]\s*\{([^}]*)\}", CSS)
        joined = "\n".join(rule)
        assert "grid-template-areas" in joined
        assert joined.count("rail") >= 1 and joined.count("main") >= 1


class TestTheHeaderIsOneRowWhereThereIsRoom:
    """`UX-255` made the header a two-column band so the actions could
    stand beside the name; `UX-317` (styleguide §2b.2) took the actions
    out of the header entirely, so the band is one column of identity
    and the grid it needed is gone with them.

    What survives here is the part that was never about the actions: the
    sticky offset must follow the header's height, and nothing may
    silently drop out of the page. The header's own budget and the
    actions' new home are `tests/unit/test_apparatus_in_its_place.py`'s.
    """

    def test_it_is_one_column_of_identity(self):
        block = "\n".join(re.findall(
            r"body\[data-has-toc\] > header\s*\{([^}]*)\}", CSS))
        assert "display: block" in block, block
        assert "grid-template-areas" not in block, (
            "the header is laying out columns again - §2b.2 says it carries "
            "identity only, and the second column existed for the actions")

    def test_the_actions_have_their_own_band(self):
        """They did not disappear: `UX-198`'s fallback link and
        `UX-314`'s download sentence are still on the page, in the group
        with the control they explain."""
        assert "body[data-has-toc] > .actions-group" in CSS, (
            "the actions group has no place in the layout")

    def test_the_sticky_offset_follows_the_header_it_offsets(self):
        """Measured in Chromium after `UX-317`: 92px at 1440x900, 134px
        at 390x844. `--head` is what every anchor's `scroll-margin-top`
        reads, so one value for both lands a jump under the heading at
        the narrow width."""
        blocks = _media_blocks("(max-width: 60rem)")
        assert any("--head" in b for b in blocks), (
            "`--head` does not change with the header's height, so an anchor "
            "lands under the heading at 390px")

    def test_nothing_was_removed_from_the_page(self):
        html = (REPO / "bga/viewer/index.html").read_text(encoding="utf-8")
        for slot in ("run-name", "run-path", "run-producer", "actions",
                     "actions-fallback", "actions-download"):
            assert f'id="{slot}"' in html, (
                f"{slot} left the page - each is there for a filed reason "
                f"(UX-255, UX-198, UX-314)")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
