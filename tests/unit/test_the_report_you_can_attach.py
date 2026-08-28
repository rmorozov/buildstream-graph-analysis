"""UX-195: the same page, as one file.

Direction 7's second delivery mode. `bga view --export report.html`
inlines the run's payloads into the static page and writes one
self-contained artifact — no port, no server, no network — for a CI
artifact, for "send me your report", and for the archive a pruned
snapshot leaves behind.

**The property under test is that it is the same page.** Not a second
renderer, not a simplified one: the identical `app.js`, reading its
payloads inline instead of over http, decided in one place. So the
guards below render the *exported file* through the same Node harness
`UX-193` renders the served payload with, and compare.

Measured, on the two runs the item names:

    1,202-element synthetic   report.json   816,573 B
    golden run                report.json    14,797 B
    the page itself (7 files)               39,119 B

At 1,202 elements the payload is 21x the page, which is Direction 7's
own test of whether the viewer stayed thin.
"""
import base64
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""
_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


# UX-287: two bounds, because an export has two halves that grow for
# different reasons. Each is a measurement plus headroom, and each says
# which run it is a bound *for*.
#
#   the page      171,388 B on every run (modules 152,424 + css 17,135
#                 + 1,829 of scaffolding) - grows with source
#   golden   (4)  261,604 B   -> of which data 90,216
#   macro_micro (11) 299,695 B -> of which data 128,307
#
# The synthetic 1,202-element run exports at ~1.07 MB and is not
# committed (`UX-189`), so it is measured in the Outcome rather than
# guarded here.
#
# **The bounds moved once, and the split is what made that legible.**
# Round 39's viewer work (`UX-279`, `UX-280`, `UX-283`, `UX-284`,
# `UX-289`, `UX-292`) took the page 162,909 -> 171,388 B: modules
# +7,788, stylesheet +691. The data grew +2,653 in the same round, all
# of it schema descriptions the page shows as tooltips - which the
# companion guard below proves is documents rather than payload.
#
# That attribution is the difference between a bound that moves on a
# measurement and one that rises whenever it is exceeded, which is what
# `UX-287` was filed about. The page budget did *not* redden - it had
# 612 B left - and the totals did, which is the split working: source
# growth shows in every total and cannot hide behind content.
#
# **Round 41 moved the page bound**, and this is the first time it has
# moved since the split was drawn - which is what it is for. `UX-302`
# added two viewer modules (`shapes.js`, the style guide's §1 dispatch
# table as code; `rawjson.js`, the per-section "view as JSON" toggle)
# and the CSS for the toggle: modules 158,365 -> 163,177 (+4,812),
# stylesheet 17,428 -> 17,995 (+567). Measured either side of the
# change, on the committed runs:
#
#   page          177,624 -> 183,006 B   (+5,382, all source)
#   golden        274,979 -> 280,294 B   (+5,315)
#   macro_micro   314,158 -> 319,473 B   (+5,315)
#
# The page moved by what the source moved by, on both runs, which is
# the split doing its job: nothing here is content growth wearing a
# page's clothes. The guard below measures the page on its own
# synthetic snapshot, which reads 57 B more than the committed runs,
# and that gap predates these items.
#
# **And again for `UX-303`/`UX-304`**, in the same round:
#
#   page          183,006 -> 196,615 B   modules +12,005, styles +1,590
#   golden        280,294 -> 294,976 B   of which data +1,073
#   macro_micro   319,473 -> 334,155 B   of which data +1,073
#
# `drawings.js` is the +12,005: §2's two controls, and the header
# comment that argues for the boundary a self-built strip may not
# cross. **The export inlines modules verbatim, comments included** -
# so this repository's commenting convention is a byte cost every
# reader pays, and 175 KB of the 196 KB page is commented JavaScript.
# Recorded rather than acted on: `EXPORT_BUDGET_B` is 8 MiB and a
# 295 KB attachment is not a problem, but the next round that wants
# the page smaller should start here rather than at the payload.
#
# `UX-312` and `UX-314` moved the page by **+13,255 B**, all of it
# checked-in viewer source and none of it data:
#
#     questions.js   10,748 -> 18,238   (+7,490)  seven new questions
#     perfetto.js     8,329 -> 11,785   (+3,456)  Perfetto's own CSP,
#                                                 quoted where it is used
#     app.js        103,023 -> 104,875  (+1,852)  the transport decision
#     index.html      1,703 ->  2,160     (+457)  the save-it-yourself route
#
# So the numbers below move again, and the reason is the one the
# backstop's docstring already gives: a byte count cannot tell a
# feature from a library, and the guards that can - `the page is the
# modules and nothing else` and `no module looks like a vendored
# library` - both pass on this page. Nothing crept in.
#
# The comment share is the real lever and it is still `UX-307`'s: this
# very block is bytes every reader of an exported report pays for.
#
# **Round 44 (`UX-320`) moved the page again, and corrected the claim
# above.** The +44,601 B of checked-in viewer source this round added:
#
#     app.js        104,875 -> 118,215  (+13,340)  grades, folds, focus,
#                                                  the described value
#     drawings.js    12,545 ->  21,421   (+8,876)  the size scale, the
#                                                  twin, the tick row
#     style.css      34,575 ->  43,052   (+8,477)  §2a/§2b/§3a's rules
#     tablefocus.js       0 ->   6,692   (+6,692)  table focus, new module
#     views.js       98,792 -> 102,947   (+4,155)  the graded figures
#     shapes.js       6,541 ->   8,082   (+1,541)  `shapeOf`
#     index.html      2,160 ->   3,103     (+943)  the actions group
#     viewstate.js   10,686 ->  11,263     (+577)  `tf=` in the fragment
#
# And the correction, which matters more than the numbers. The round-41
# note above says "**The export inlines modules verbatim, comments
# included** ... 175 KB of the 196 KB page is commented JavaScript".
# **It does not.** `tools/bga_view.py`'s `_uncommented` has stripped
# whole-line and block comments from the inlined copy since `UX-205`.
# Measured on the exported page this round:
#
#     page     223,276 B
#       js     198,058 B   89%   trailing `//` comments ~114 B
#       css     22,247 B   10%
#       rest     2,971 B
#
# So the page is code. `UX-307`'s remaining scope is those ~114 B plus
# whatever a real minifier would buy - not the 175 KB the old note
# promised - and a round that wants the page smaller should start from
# this measurement rather than from that sentence.
#
# **Round 45 (`UX-307`) took them, and the estimate above was low.** The
# stripper is literal-aware now, so it reaches trailing comments as well
# as whole-line ones: **153 B**, not ~114, across four sites in three
# modules. Measured on the golden export, which is the fixture the bound
# below is set against:
#
#     page     223,227 B  ->  223,074 B     -153
#     data      98,374 B      98,374 B        +0
#     html     321,770 B     321,617 B      -153
#
# That is 0.07% of the page, and `UX-307` says so in its own Outcome
# rather than presenting the pass as a size win. What the pass actually
# bought is that the export's stripper knows a comment from a string -
# four URL constants and one regex literal in the same bundle look
# exactly like comments and are not.
#
# The +1,073 of *data* on both runs is the two `bga:distribution`
# hints and one `bga:series`, with their descriptions - the schema the
# page carries, which is the half the companion guard below proves is
# documents rather than payload.
# **Round 47 (`UX-334`) moved the page, and CI found what the bound was
# really measuring.** The console work added a viewer module and the
# commentary that argues for it:
#
#     page          223,362 -> 225,002 B   (+1,640, all source)
#     data           98,951 ->  98,986 B      (+35, the payload manifest
#                                              `run.json` now publishes)
#     golden        322,313 -> 323,988 B   (+1,675)
#     macro_micro   361,749 -> 363,424 B   (+1,675)
#
# The page moved by what the source moved by, on both runs - the split
# doing its job again. But the golden bound had **12 B of headroom** on
# the checkout it was last measured on, and it failed in CI at 324,022:
#
#     path len   20  ->  323,829 B
#     path len   61  ->  324,075 B
#     path len  111  ->  324,375 B
#
# The export embeds the run's absolute path - `run.json`'s `run` key and
# the analyze document both carry it - so **the number is a function of
# where the repository is checked out**, at roughly 5 B per character.
# A CI runner's checkout is 34 B of path longer than the container this
# was measured on, and that is the whole of the difference.
#
# Exporting from a copy at a fixed path was tried and declined: the
# committed runs sit inside a store, so `payloads()` finds a
# `compare.json` and a `store.json` beside them that a copy in `tmp_path`
# does not have - measured, macro_micro exports 363,424 B in place and
# 340,467 B copied. The bound would stop bounding the report the fixture
# actually produces.
#
# So the bounds below carry **~4 KB of headroom instead of 12 B**, which
# is about 800 characters of run path, and this note is what stops the
# next reader from reading a tight number as a tight measurement.
# **Round 48 (`UX-335`) moved the page again**, and the page budget is
# the guard that saw it - which is what it is for. Section-boundary
# error containment is new source and nothing else:
#
#     controls.js     2,816 ->   5,289   (+2,473)  `contained`, the
#                                                  failure card, and the
#                                                  measurement that
#                                                  argues for them
#     views.js      103,573 -> 105,711   (+2,138)  the two null-row
#                                                  sites stating their
#                                                  absence
#     app.js        120,600 -> 121,942   (+1,342)  nine renderers routed
#                                                  through `contained`
#
#     page          225,002 -> 227,498 B   (+2,496, all source)
#     data           98,986 ->  98,986 B       (+0)
#     golden        323,988 -> 326,484 B   (+2,496)
#     macro_micro   363,424 -> 365,920 B   (+2,496)
#
# Data did not move by a byte, on either run, which is the split saying
# what it exists to say: this round added code, not payload.
#
# The budget moves to 230,000 - the same ~2.5 KB of headroom the two
# export bounds carry, rather than the 998 B it had left after
# `UX-334`. A budget with one round's growth left in it reddens on the
# next round whatever that round does, and a guard that always reddens
# is a guard nobody reads.
#
# **Round 49 moved both halves, one each**, and the split named which
# item did which. Measured on a checkout whose path is the same length
# as this one's, so the numbers are comparable to the round above
# rather than to a temporary directory:
#
#                       round 48    UX-338    UX-339
#     page               227,498   228,528   228,528   (+1,030, +0)
#     data (golden)       98,986    99,291   101,906     (+305, +2,615)
#     golden             326,484   327,819   330,434
#     macro_micro        365,920   367,255   369,870
#
# `UX-338` is the one round in this note's history that moved *both*:
# +1,030 B of source, where the join merges into the element table and
# a preset gates itself on what it declares it draws, and +305 B of
# payload, because that declaration - `requires` - travels in the
# embedded `schemas.json` where the page can read it.
#
# `UX-339` moved the page by **zero bytes** and the payload by 2,615 on
# both runs, which is what a new contract looks like from here:
# `sweep/v1` is the twelfth document in the embedded inventory and no
# line of viewer source knows it exists. A ceiling could not have told
# that from 2,615 B of new code; the split can, and that is the whole
# argument for keeping it.
PAGE_BUDGET_B = 231_000
MACRO_MICRO = "tests/fixtures/macro_micro/run"
COMMITTED_EXPORTS = [
    # `UX-299` moved both of these by ~300 B: `run.json` now publishes
    # `trace_inline_max_bytes`, the one threshold that decides both
    # whether this file inlines the trace and whether the served page
    # copies it through itself. A number the page must not keep a second
    # copy of, so it travels in the payload.
    # `UX-302` moved both again, by 5,315 B: the §1 dispatch table and
    # the "view as JSON" toggle are two new modules and their styles.
    # Source, not content - see the split above.
    # `UX-338` and `UX-339` moved both again, by 3,950 B - 1,030 of
    # source and 2,920 of payload, split between the two items in the
    # note above. The bounds are restated rather than the twelfth
    # contract left unpublished to fit a number nobody argued.
    ("golden", GOLDEN, 335_000),                       #  330,434 B
    # `UX-297` moved this one by 385 B before that: the two-plane run
    # publishes `plane2_coverage.source`, which says which shape of
    # Plane 2 report served its numbers and what that costs to open. A
    # sentence a reader of a gigabyte capture needs, and the bound is
    # restated rather than the sentence trimmed to fit a number nobody
    # argued.
    # `UX-300` moved both again, by ~2.6 KB: the embedded
    # `store-aggregate/v1` now carries what the store weighs - a
    # `snapshot_bytes` distribution per host class and a document-level
    # total - which is the page telling a reader what their disk holds
    # without their having to go and ask a second command.
    ("macro_micro", MACRO_MICRO, 375_000),             #  369,870 B
]


def _embedded(path):
    """The bytes of documents the page carries, so the rest is the page."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return sum(len(found) for found in re.findall(
        r'<script type="application/json"[^>]*>(.*?)</script>', text, re.S))


@pytest.fixture
def snapshot(tmp_path):
    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree(GOLDEN, snap / "run")
    os.remove(snap / "run" / "expected_output.json")
    with gzip.open(snap / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW)
    return snap


@pytest.fixture
def exported(snapshot, tmp_path):
    from tools.bga_view import export

    path = tmp_path / "report.html"
    result = export(str(snapshot / "run"), str(path))
    return path, result


class TestItNeedsNothingButItself:
    def test_no_reference_reaches_the_network_or_the_filesystem(self, exported):
        """An export opens from a download folder, a CI artifact viewer,
        or an email attachment. Anything it would have to fetch is
        simply not there."""
        text = exported[0].read_text()
        for url in re.findall(r'(?:src|href)="([^"]+)"', text):
            assert url.startswith(("#", "data:", "mailto:")) or \
                url.startswith("https://ui.perfetto.dev"), (
                    f"{url} would have to be fetched")

    def test_no_relative_module_import_survives(self, exported):
        """A browser refuses a relative `import` over `file://`, so the
        two modules are concatenated into one inline block."""
        text = exported[0].read_text()
        assert not re.search(r"""import\s.*from\s+["']\./""", text)
        assert "openInPerfetto" in text, "perfetto.js was not inlined"
        assert "renderFindings" in text, "app.js was not inlined"

    def test_every_payload_is_present_as_a_block(self, exported):
        found = set(re.findall(r'id="bga-([a-z]+)"', exported[0].read_text()))
        assert {"report", "schemas", "run"} <= found, found

    def test_the_blocks_are_named_the_way_the_loader_looks_them_up(
            self, exported):
        """The one that bit: `payloads()` keys by *url*
        (`report.json`), the loader looks up by *name* (`bga-report`).
        Getting it wrong is silent — the block is simply never found and
        the page falls through to `fetch`, which works when served and
        fails on `file://`, so the export looks fine everywhere except
        where it is used."""
        text = exported[0].read_text()
        assert 'id="bga-report"' in text
        assert 'id="bga-report.json"' not in text

    def test_a_payload_containing_a_script_tag_cannot_end_the_block(
            self, snapshot, tmp_path, monkeypatch):
        """An element named after an html file is not hypothetical, and
        a `</script>` anywhere in a payload would end the block early -
        everything after it becoming markup.

        Injected at the `payloads` seam. The first draft set `run_id` in
        `run-context.json` and asserted on the output; `run_id` is
        *computed*, so the string never reached the payload and the test
        passed without exercising the escape at all.
        """
        import tools.bga_view as view

        monkeypatch.setattr(view, "payloads", lambda run: {
            "report.json": {"schema": "analyze/v2", "section": None,
                            "run_id": "a</script><script>alert(1)</script>",
                            "total_duration_us": 1}})
        path = tmp_path / "r.html"
        view.export(str(snapshot / "run"), str(path))
        text = path.read_text()

        assert "alert(1)</script>" not in text, "the block was ended early"
        assert "<\\/script>" in text, "nothing was escaped"
        block = re.search(r'id="bga-report">(.*?)</script>', text)
        assert json.loads(block.group(1).replace("<\\/", "</"))["run_id"] == \
            "a</script><script>alert(1)</script>", "the payload was mangled"


@needs_node
class TestItRendersTheSameThing:
    """The exported file, parsed and rendered by the same harness the
    served payload goes through."""

    def _render_export(self, path):
        script = _EXPORT_HARNESS % json.dumps(str(path))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=90)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_it_renders_the_runs_findings_and_sections(self, exported):
        rendered = self._render_export(exported[0])
        assert "findings" in rendered["sections"], rendered["sections"]
        assert rendered["severities"], "no severity reached the page"

    def test_it_renders_what_the_served_page_renders(self, exported, snapshot):
        """Same payload, same schema, same renderer - so same output.
        A second renderer would show up here as a difference."""
        from tools.bga_view import payloads, schemas_payload

        run = str(snapshot / "run")
        payload = payloads(run)["report.json"]
        schema = schemas_payload()[payload["schema"]]

        served = subprocess.run(
            [node, "--input-type=module", "-e",
             _SERVED_HARNESS % (json.dumps(payload), json.dumps(schema))],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=90)
        assert served.returncode == 0, served.stderr

        assert self._render_export(exported[0])["sections"] == \
            json.loads(served.stdout)["sections"]


class TestTheTimeline:
    def test_it_travels_inline_as_a_data_url(self, exported):
        """So the Perfetto button works from `file://`: `fetch` handles
        `data:` URLs, and the handshake never needed a server."""
        text = exported[0].read_text()
        block = re.search(r'id="bga-trace">"(data:application/gzip;base64,'
                          r'([A-Za-z0-9+/=]+))"', text)
        assert block, "no inline trace"
        # `UX-298`: a Perfetto trace, not a JSON array. `Trace` is
        # `repeated TracePacket packet = 1`, so the first byte of the
        # stream is that field's tag - `(1 << 3) | 2`.
        assert gzip.decompress(base64.b64decode(block.group(2)))[:1] == b"\x0a"
        assert exported[1]["has_timeline"] is True

    def test_a_run_without_one_says_so_rather_than_shipping_a_dead_button(
            self, tmp_path):
        from tools.bga_view import export

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        result = export(str(run), str(tmp_path / "r.html"))

        assert result["has_timeline"] is False
        # UX-329: which absence, not just that there is one. This run is
        # a copy of the golden fixture with no Plane 2 report anywhere
        # near it, and the sentence it used to get - "no raw Plane 2
        # log" - describes a *captured* run whose log was dropped. A
        # reader cannot tell a machine that never traced from a
        # measurement missing only its timeline, and those are the two
        # things this sentence was covering.
        from bga import plane2

        assert result["omitted"] == plane2.NOT_CAPTURED, result["omitted"]
        run_block = re.search(r'id="bga-run">(.*?)</script>',
                              (tmp_path / "r.html").read_text())
        assert json.loads(run_block.group(1))["has_timeline"] is False

    def test_an_oversized_timeline_is_dropped_and_the_reason_recorded(
            self, snapshot, tmp_path, monkeypatch):
        """Recorded, not silent: the report is still worth having, and
        a user who wanted the timeline needs to know where it went."""
        import tools.bga_view as view

        monkeypatch.setattr(view, "TRACE_BUDGET_B", 8)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["has_timeline"] is False
        assert "ceiling" in result["omitted"]
        assert 'id="bga-trace"' not in (tmp_path / "r.html").read_text()


class TestTheSizeDiscipline:
    """Direction 7's rule is a *ratio*: "the data, not the page, is what
    an export weighs". It was guarded by an absolute byte ceiling, and
    across rounds 23, 24 and 25 that ceiling was crossed three times by
    ordinary feature work - the decision panel, the rails, the table
    tools, the view state, the element object - and raised twice.

    A number that moves every time a feature lands is not measuring the
    feature; it is measuring the calendar. So the third time, what is
    measured changed instead of the number:

    1. **Composition** - the page *is* the checked-in modules plus the
       stylesheet and nothing else. This is the one that can tell 6 KB
       of new feature from 6 KB of vendored library, which is what the
       rule was always about.
    2. **The ratio, on a report big enough for it to mean something** -
       Direction 7's sentence as written.
    3. **A loose absolute backstop**, kept deliberately far above the
       current page so that crossing it means something structural
       happened rather than that a round landed.

    Measured today: eight modules at 85,579 B comment-stripped,
    `style.css` at 10,822 B, `index.html` at 1,433 B.
    """

    def test_the_page_is_a_backstop_away_from_where_it_is(self, exported):
        """The loose one, raised in round 26 and - deliberately - given
        the instrument it was standing in for.

        This number has now been crossed in rounds 23, 24, 25 and 26,
        and raised each time. UX-218 named that failure exactly: *a
        number that moves whenever a feature lands is measuring the
        calendar*. The reason it kept being raised is that its stated
        job - "crossing it means something structural happened rather
        than that a round landed" - was one it could not actually do. A
        byte count cannot tell a feature from a library.

        Measured when round 26 crossed it:

            page (data removed)   123,785 B
              modules             109,913 B
              style.css            12,552 B
              index.html            1,433 B
              accounted           123,898 B  = 100.1% of the page
            export total          184,934 B  = 2.20% of the 8 MiB budget

        Every byte is a checked-in module. Nothing crept in, the ratio
        guard still holds at 1,000 elements, and the export is a fortieth
        of what an attachment may weigh. So the backstop fired, someone
        looked, and the answer was "a round landed" - four times.

        Raised to 200,000 and joined by `test_no_module_looks_like_a
        _vendored_library` below, which checks the thing this number was
        a proxy for. If the absolute fires again it should be because
        that one is silent and something genuinely odd is happening.

        It fired a fifth time, at 204,308 B, when `UX-312` and `UX-314`
        landed - and the check the paragraph above describes did its
        job. Both companion guards stayed **silent**: every added byte
        is a checked-in module (`questions.js` +7,490 for seven new
        canned questions, `perfetto.js` +3,456 for Perfetto's own CSP
        quoted where it is used, `app.js` +1,852, `index.html` +457),
        and none of it resembles a vendored library. So this is the
        fifth "a round landed", looked at rather than assumed, and the
        number moves to 210,000.
        """
        html = open(exported[0], encoding="utf-8").read()
        # Every `<script type="application/json">` block and the trace
        # blob are *data*. What is left is the page.
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(page) < PAGE_BUDGET_B, (
            f"the exported page is {len(page)} B with its data removed - "
            f"that is a structural change, not a feature. Check "
            f"`test_the_page_is_the_modules_and_nothing_else` and "
            f"`test_no_module_looks_like_a_vendored_library` first.")

    def test_no_module_looks_like_a_vendored_library(self):
        """What the byte ceiling was a proxy for, measured directly.

        Direction 7's rule is about what the page *is*, not how big it
        got. Hand-written modules are line-wrapped source with comments;
        vendored or minified code is not - it arrives as a small number
        of enormous lines and almost no comment. That difference is
        visible, and unlike a byte count it does not move when a feature
        lands.
        """
        import tools.bga_view as view

        offenders = []
        for name in view._module_order():
            source = open(os.path.join(view.ASSET_DIR, name),
                          encoding="utf-8").read()
            lines = source.splitlines() or [""]
            longest = max(len(line) for line in lines)
            commented = sum(1 for line in lines
                            if line.lstrip().startswith(("//", "/*", "*")))
            if longest > 400:
                offenders.append(f"{name}: a {longest}-character line")
            if len(source) > 4_000 and commented / len(lines) < 0.05:
                offenders.append(
                    f"{name}: {commented}/{len(lines)} commented lines")
        assert offenders == [], (
            f"these do not look like the hand-written modules this page is "
            f"supposed to be: {offenders}")

    def test_the_data_dwarfs_the_page_on_a_report_worth_measuring(
            self, tmp_path):
        """Direction 7's sentence, on a report the sentence is about.

        The small fixtures invert it and always did - on `examples/06`
        the data is 70,754 B against an 82,386 B page - which is a
        property of small reports, not of the viewer, and is why the
        absolute ceiling was the wrong instrument.

        Measured at the scale the rule names (1,000 elements, the
        figure Direction 7 quotes at 1,202): **691,401 B of data
        against a 97,488 B page, 7.1x**. The threshold is set below
        the measurement so that ordinary growth does not trip it and a
        framework arriving does - a guard set at the measurement is a
        guard that fails on the next commit.

        **Re-measured at round 41** (`UX-303`), because it tripped:
        765,103 B of data against a 196,340 B page, **3.90x**. The page
        has doubled since the ratio was set and the data at this scale
        has not, so 4x no longer has headroom.

        **Re-measured at round 44** (`UX-320`), because it tripped
        again - and because the reason round 41 recorded was wrong.
        That note said "the export inlines every module verbatim,
        comments included ... 175 KB of the 196 KB page is commented
        JavaScript". It does not: `_uncommented` has stripped
        whole-line and block comments from the inlined copy since
        `UX-205`. Measured on this page:

        ```text
        page     223,276 B
          js     198,058 B   89%   trailing `//` comments ~114 B
          css     22,247 B   10%
          rest     2,971 B
        data     764,900 B   3.43x
        ```

        So the page is **code**, and `UX-307`'s remaining scope is the
        ~114 B of trailing comments plus whatever a real minifier would
        buy - not the 175 KB the old note promised. The threshold moves
        to **3.3x** with that correction, and the honest statement is
        that this ratio has now moved twice for one cause: the viewer
        grows features and the synthetic run's data does not grow with
        it. What the guard still catches is what it was built for - a
        framework arriving is hundreds of kilobytes of vendor code
        landing at once, which `test_no_module_looks_like_a_vendored_library`
        catches by shape and this catches by weight.

        **Round 45 (`UX-307`) took the trailing comments, and the
        estimate above was low: 153 B, measured, not ~114.** The
        threshold stays at 3.3x, and that is a deliberate refusal
        rather than an oversight. `UX-307`'s acceptance test asks for
        the ratio to be "restated upward with the new measurement",
        which was written when the item was believed to be worth
        175 KB. On this fixture it moves the ratio from 3.4266x to
        3.4289x - the fourth decimal place. Tightening a threshold on
        that would be manufacturing a significance the measurement
        does not have, and the next round to trip this guard would
        inherit a number nobody could account for.

        **Round 52 (`UX-342`) corrected what sits on each side, and the
        threshold moves with the classification rather than with a
        failure.** The embedded schemas were counted as *data*. They are
        not: they were byte-identical across two different runs, which
        is how `UX-342` found them, and a quantity that does not vary
        with the run belongs on the fixed side beside the modules and
        the stylesheet. So the ratio is the run's own data over
        everything that is the same for every run. Measured on this
        fixture, before and after that round:

        ```text
                             before      after
        page (modules, css)  228,291    228,291
        embedded schemas      83,669     43,981
        fixed cost           311,960    272,272
        run's own data       684,801    684,801   <- unchanged
        run data / fixed       2.195      2.515
        old data/page          3.366      3.192
        ```

        The numerator is identical because `UX-342` removed no data - it
        removed 39,688 B of contract for documents the page can never
        hold. Under the old metric that reads as a *regression*, which
        is the tell that the old metric was measuring the wrong thing.

        **`UX-343` moved it a second time in the same round, and twice
        is the signal to stop patching and measure the thing the guard
        is actually for.** Declaring a unit for every number means
        writing a sentence for each (`UX-220`), which grew the embedded
        contract by 23,011 B - so a rule that counts contract as fixed
        cost now falls whenever the schema says *more*, which is the
        opposite of what this guards.

        What it guards is a **framework arriving**: hundreds of
        kilobytes of vendor code landing at once. So the three
        quantities are separated and the ratio is the run's data over
        the viewer's **code** - not over the contract, which is prose,
        and not over both. Measured on this fixture across all three
        states:

        ```text
                            pre-UX-342   post-UX-342   post-UX-343
        code (modules, css)    228,291      228,291       228,423
        contract (schemas)      83,669       43,981        66,992
        this run's data        684,801      684,801       685,026
        data / code              2.999        2.999         2.999
        data / code+contract     2.195        2.515         2.319
        ```

        The code side is **invariant** across both rounds, because
        neither touched it - which is what a metric for "did the page
        balloon" should do. The combined ratio moves under both, in
        opposite directions, for reasons that have nothing to do with
        the page ballooning.

        The bound is **2.9x**. The contract's own size is reported in
        the failure message rather than bounded here: `UX-342`'s guard
        holds it to the schemas the page can resolve, and `UX-220`
        requires each to carry a sentence, so the two rules between them
        already say what it may contain.
        """
        import tools.bga_view as view

        from tests.fixtures.topologies import linear_chain, write_run_dir

        run = write_run_dir(tmp_path, linear_chain(1000))
        out = tmp_path / "big.html"
        view.export(str(run), str(out))
        html = out.read_text(encoding="utf-8")
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        schemas = re.search(
            r'<script type="application/json" id="bga-schemas">(.*?)'
            r"</script>", html, re.S).group(1)
        # `UX-342`: the schemas are apparatus, not this run's data -
        # identical for every run of a given contract set, so they sit
        # beside the modules and the stylesheet rather than beside the
        # measurements.
        code = len(page)
        contract = len(schemas)
        run_data = len(html) - code - contract
        assert run_data > 2.9 * code, (
            f"{run_data} B of this run's data against {code} B of viewer "
            f"code ({run_data / code:.3f}x) - Direction 7's rule is that "
            f"the data is what an export weighs, and at this scale it "
            f"should not be close. The embedded contract is {contract} B, "
            f"which this ratio deliberately does not count: it is prose, "
            f"and it grows when the schema says more")

    def test_the_page_is_the_modules_and_nothing_else(self, exported):
        """What the ceiling is really guarding: that the page is the
        checked-in modules plus the stylesheet, and that nothing else
        crept into it. A ceiling alone cannot tell 4 KB of new feature
        from 4 KB of vendored library; this can.
        """
        import tools.bga_view as view

        html = open(exported[0], encoding="utf-8").read()
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        accounted = sum(len(view._inline_module(name))
                        for name in view._module_order())
        accounted += len(view._uncommented_css(
            open(os.path.join(view.ASSET_DIR, "style.css"),
                 encoding="utf-8").read()))
        accounted += len(open(os.path.join(view.ASSET_DIR, "index.html"),
                              encoding="utf-8").read())
        # The export rewrites the page around those bytes, so an exact
        # equality would be asserting the glue. Anything the modules do
        # not account for is what this is looking for.
        assert len(page) - accounted < 4_000, (
            f"{len(page) - accounted} B of the page comes from neither "
            f"the modules nor the stylesheet")

    def test_the_page_itself_stays_within_its_budget(self, exported):
        """`UX-287`: the half of the size a run cannot change.

        The old backstop asserted a single constant against the golden
        export and had moved five times, always to accommodate the run
        it was measured against - a bound that rises whenever it is
        exceeded is a record, not a limit. Worse, it was measured on a
        **four-element** run, so it bounded the one quantity that barely
        varies while the quantity it was named for went unwatched.

        Measured across all three runs this repository can produce:

        ```text
        run             elements     bytes      data   modules     css   other
        golden                 4   294,976    98,361   175,182  19,585   1,848
        macro_micro           11   334,155   137,540   175,182  19,585   1,848
        ```

        The page is **196,615 B on every run**. That is the number a
        ceiling can honestly guard: it grows when *source* grows, and no
        amount of content can mask it. The totals below guard the other
        half, per fixture - so content can no longer hide behind the
        page, nor the page behind content.
        """
        page = exported[1]["bytes"] - _embedded(exported[0])
        assert page < PAGE_BUDGET_B, f"the page itself is {page} B"

    def test_the_page_costs_the_same_whatever_the_run(self, tmp_path):
        """What justifies splitting the bound in two. If the page's cost
        varied with the run, "the page" would not be a thing to bound
        separately and this whole structure would be wrong."""
        from tools.bga_view import export

        fixed = {}
        for label, run in (("golden", GOLDEN), ("macro_micro", MACRO_MICRO)):
            path = tmp_path / f"{label}.html"
            result = export(str(run), str(path))
            fixed[label] = result["bytes"] - _embedded(path)
        assert len(set(fixed.values())) == 1, (
            f"the page is not run-independent: {fixed}")

    @pytest.mark.parametrize("label,run,bound", COMMITTED_EXPORTS)
    def test_each_committed_run_exports_within_its_stated_bound(
            self, label, run, bound, tmp_path):
        """`UX-287`'s acceptance: the bound is asserted against a run
        whose size is representative, and it is stated *for that run*.

        **The decision the item asked for**, since the 11-element export
        is 288,404 B and the old ceiling was 260,000: the export is not
        too big. A self-contained HTML report at 288 KB - or at 1.04 MB
        for 1,202 elements - is well inside what a ticket or a mail
        client takes, and `tools/bga_view.py`'s own `EXPORT_BUDGET_B` of
        8 MiB is the limit that reflects the use. The old number was not
        a judgement about attachments; it was the size of a four-element
        run at the moment somebody wrote it down.
        """
        from tools.bga_view import export

        path = tmp_path / f"{label}.html"
        result = export(str(run), str(path))
        assert result["bytes"] < bound, (
            f"{label} exports {result['bytes']} B from a "
            f"{len(os.path.abspath(run))}-character run path, over its "
            f"stated {bound} B - see the note above on what the path costs")
        assert result["over_budget"] is False

    def test_the_data_is_the_documents_and_the_schemas(self, exported):
        """The backstop's other half, and the one that actually
        discriminates: every byte of embedded data is a document the
        page renders. A ceiling cannot tell 10 KB of new contract from
        10 KB of embedded font; this can, and it is why raising the
        ceiling above is a measurement rather than an argument."""
        import json

        html = open(exported[0], encoding="utf-8").read()
        blocks = re.findall(
            r"<script[^>]*type=\"application/json\"[^>]*>(.*?)</script>",
            html, flags=re.S)
        assert blocks, "no data blocks - the export stopped embedding"
        for block in blocks:
            # Every one parses as JSON. A blob that is not a document
            # would land here as something else.
            json.loads(block)
        data = sum(len(block) for block in blocks)
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(html) - len(page) - data < 4_000, (
            f"{len(html) - len(page) - data} B of embedded data is not one "
            f"of the JSON documents the page renders")

    def test_a_file_over_budget_is_reported_not_refused(
            self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        monkeypatch.setattr(view, "EXPORT_BUDGET_B", 100)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["over_budget"] is True
        assert os.path.exists(tmp_path / "r.html"), (
            "it refused to write a report the user asked for")


class TestTheCommandLine:
    def test_it_writes_the_file_and_says_where(self, snapshot, tmp_path):
        path = tmp_path / "out.html"
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["view", str(snapshot / "run"), "--export", str(path)],)],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        assert result.returncode == 0, result.stderr
        assert path.exists()
        assert json.loads(result.stdout)["bytes"] == path.stat().st_size
        assert "needs no server" in result.stderr

    def test_it_never_starts_a_server(self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        def refuse(*args, **kwargs):
            raise AssertionError("--export bound a port")

        monkeypatch.setattr(view.http.server, "ThreadingHTTPServer", refuse)
        monkeypatch.setattr(view.webbrowser, "open", refuse)
        assert view.main([str(snapshot / "run"), "--export",
                          str(tmp_path / "r.html")]) == 0


class TestTheCiWiring:
    def test_the_ci_docs_teach_attaching_it(self):
        text = open("docs/guides/ci-comment.md", encoding="utf-8").read()
        assert "--export" in text, (
            "the CI page posts the comment but never mentions the artifact")


_COMMON_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function makeNode(tag) {
  const node = _makeNode(tag);
  return node;
}
function collect(root) {
  const sections = [], classes = new Set(), severities = new Set();
  let text = "";
  (function walk(node) {
    text += " " + node.text;
    if (node.className) String(node.className).split(/\\s+/).forEach(c => c && classes.add(c));
    if (node.attrs["data-section"]) sections.push(node.attrs["data-section"]);
    if (node.attrs["data-severity"]) severities.add(node.attrs["data-severity"]);
    node.children.forEach(walk);
  })(root);
  return { sections, classes: [...classes], severities: [...severities], text };
}
"""

# The export is run the way a browser runs it: its own inline module,
# its own inline JSON blocks, no filesystem beyond the one file.
_EXPORT_HARNESS = _COMMON_SHIM + """
import { readFileSync } from "node:fs";
const html = readFileSync(%s, "utf-8");

const blocks = {};
for (const m of html.matchAll(
    /<script type="application\\/json" id="bga-([a-z]+)">([\\s\\S]*?)<\\/script>/g)) {
  blocks[m[1]] = m[2].replace(/<\\\\\\//g, "</");
}
const nodes = {};
for (const name of Object.keys(blocks)) {
  const node = makeNode("script");
  node.textContent = blocks[name];
  nodes[`bga-${name}`] = node;
}
const root = makeNode("main");
nodes["report"] = root;

globalThis.document = {
  createElement: makeNode,
  getElementById: (id) => nodes[id] ?? makeNode("div"),
};
globalThis.fetch = () => { throw new Error("the export fetched something"); };

const source = html.match(
  /<script type="module">([\\s\\S]*?)<\\/script>/)[1];
const mod = await import(
  "data:text/javascript;base64," + Buffer.from(
    source + "\\nexport { render, inlined, load };").toString("base64"));

// Through `load`, not `inlined`: the first draft rendered
// `inlined("report")` directly, so deleting the inline-first branch
// from `load` entirely left every render guard green - the loading
// path was never on the wire. `fetch` above throws, so anything not
// answered inline fails here.
const payload = await mod.load("report");
const schemas = await mod.load("schemas");
mod.render(payload, schemas[payload.schema], root);
console.log(JSON.stringify(collect(root)));
"""

_SERVED_HARNESS = _COMMON_SHIM + """
const payload = %s, schema = %s;
globalThis.document = { createElement: makeNode, getElementById: () => makeNode("div") };
const mod = await import("./tests/viewer.mjs");
const root = makeNode("main");
mod.render(payload, schema, root);
console.log(JSON.stringify(collect(root)));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
