"""UX-401: no key is terminal-only in silence.

`UX-389` counted the damage - fourteen of twenty-five Plane 2 blocks
reached no browser - and `UX-385`'s `commands_not_observed` became the
fifteenth *one round after being added*. That is the shape of a
treadmill, not of a backlog item: a new block defaults to terminal-only
and nothing says so, so the next walk finds it.

`bga/plane2.py` fixed the capture side by making every block declare a
destination. This file is the other half, and the join between them:

- **the census**, over the analyze document the page is handed. Every
  top-level key reaches a reader one of four ways - its own section,
  a row of the `Run` block (where `renderSummary` puts every scalar),
  a `DRAWN_ELSEWHERE` entry, or `TERMINAL_ONLY` with a reason. Keys
  are read off a real payload and destinations off the *booted page*,
  so a key that reaches none of the four reddens here.
- **the binding**, over `plane2.DESTINATIONS`. `UX-389`'s guard proves
  a declared destination resolves in the payload; that is not the same
  claim as reaching a browser, and reaching a browser is what the
  filing was about. Every `PAYLOAD` destination is resolved against
  the rendered document instead - the section exists, and the member's
  own label is inside it.
- **the anti-rot clause**. A declaration the page has outgrown is a
  lie of the same kind: anything declared unreachable that the page
  does render is RED, so a declaration cannot quietly rot into a
  section that exists.

The page is booted from an export rather than a served run, because an
export is the shape with the fewest documents - anything reachable
there is reachable served, and the reverse is what `UX-203` was filed
for.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2                                        # noqa: E402

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is required")

#: Two planes, so the census sees the keys a single-plane run does not
#: publish - which is the half `UX-389` was about.
RUN = REPO / "tests/fixtures/macro_micro/run"
PLANE2 = REPO / "tests/fixtures/macro_micro/plane2.json"

#: `renderSummary`'s block: every scalar of the document, as a `Run`
#: pair. It is a real destination and the reason most of the document
#: needs no entry anywhere - said here once rather than assumed.
SCALAR_HOME = "summary"

# What the booted page reports back: the sections it drew, the text
# inside each, and the two declaration tables read from the modules the
# page itself loaded, so no clause reads a second copy of either.
_TAIL = r"""
const txt = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(txt).join("") : (n._text ?? ""));
const root = globalThis.document.getElementById("report");
const rendered = {};
const keyed = {};
for (const s of root.querySelectorAll("[data-section]")) {
  const name = s.getAttribute("data-section");
  rendered[name] = txt(s);
  // `UX-374`: every drawn term carries the published key it was drawn
  // from, so a member's arrival can be read exactly rather than by
  // looking for its name in the section's prose - which the schema
  // puts there whether the value arrived or not.
  keyed[name] = s.querySelectorAll("[data-key]")
    .map((n) => n.getAttribute("data-key"));
}
// The two declaration tables, out of the modules the *page* loaded -
// `tests/viewer.mjs` re-exports the same source, so no clause here
// reads a second copy of either.
const viewer = await import(process.env.BGA_VIEWER);
console.log("CENSUS " + JSON.stringify({
  rendered, keyed,
  drawn_elsewhere: viewer.DRAWN_ELSEWHERE ?? null,
  terminal_only: viewer.TERMINAL_ONLY ?? null,
}));
"""


def _declarations(name):
    """A declaration table read out of `app.js`, as {key: reason}."""
    source = (REPO / "bga/viewer/app.js").read_text(encoding="utf-8")
    found = re.search(rf"export const {name} = \{{(.*?)\}};", source, re.S)
    assert found, f"app.js no longer declares {name}"
    body = found.group(1)
    return {key: body for key in re.findall(r"^  (\w+):", body, re.M)}


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("census")
    page = into / "report.html"
    view.export(str(RUN), str(page))
    html = page.read_text(encoding="utf-8")
    (into / "inline.mjs").write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    # The same boot every navigation guard uses, so this census reads
    # the document a reader gets rather than one assembled here.
    probe = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text(
        encoding="utf-8").split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]
    (into / "probe.mjs").write_text(probe + _TAIL, encoding="utf-8")
    done = subprocess.run(
        [node, str(into / "probe.mjs")],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env=dict(os.environ, PAGE=str(page), MOD=str(into / "inline.mjs"),
                 PROTOCOL="file:",
                 BGA_VIEWER=str(REPO / "tests/viewer.mjs"),
                 BGA_DOM_SHIM=str(REPO / "tests/dom_shim.mjs")))
    assert done.returncode == 0, done.stderr[-2500:]
    line = [ln for ln in done.stdout.splitlines()
            if ln.startswith("CENSUS ")][-1]
    return json.loads(line[len("CENSUS "):])


@pytest.fixture(scope="module")
def written():
    """The Plane 2 report `macro_micro` was captured with."""
    return json.loads(PLANE2.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


def _homes(key, value, booted):
    """Every destination this key actually reaches, as names."""
    where = []
    if key in booted["rendered"]:
        where.append("section")
    if value is None or not isinstance(value, (dict, list)):
        where.append(SCALAR_HOME)
    if key in (booted["drawn_elsewhere"] or {}):
        where.append("drawn elsewhere")
    if key in (booted["terminal_only"] or {}):
        where.append("terminal only")
    return where


@needs_node
class TestTheCensusIsExhaustive:
    def test_the_page_drew_something_to_census(self, booted):
        assert len(booted["rendered"]) > 40, sorted(booted["rendered"])
        assert SCALAR_HOME in booted["rendered"], (
            f"the `{SCALAR_HOME}` block is gone; every scalar of the "
            f"document just lost its destination")

    def test_every_key_of_the_document_reaches_a_reader(self, payload, booted):
        """Read off the payload, not off a list.

        A census that only knows the keys it was told about cannot
        catch the next one, which is exactly how the count went from
        fourteen to fifteen inside a single round.
        """
        silent = {key: value.__class__.__name__
                  for key, value in payload.items()
                  if not _homes(key, value, booted)}
        assert silent == {}, (
            f"{len(silent)} key(s) of the analyze document reach no "
            f"reader: {silent}. Draw it, or declare it in "
            f"`TERMINAL_ONLY` with the reason it stops at the terminal")

    def test_a_declaration_carries_a_reason(self):
        """Silence is what produced fourteen. A wildcard entry would
        pass every other clause here and give a reader nothing."""
        for name in ("DRAWN_ELSEWHERE", "TERMINAL_ONLY"):
            for key, reason in _declarations(name).items():
                assert len(reason.split()) >= 12, (name, key, reason)

    def test_nothing_declared_unreachable_is_drawn(self, booted):
        """The anti-rot direction. A declaration the page has outgrown
        is a lie of the same kind as no declaration at all."""
        rotted = [key for key in (booted["terminal_only"] or {})
                  if key in booted["rendered"]]
        assert rotted == [], (
            f"declared terminal-only and drawn as a section: {rotted}")
        misplaced = [key for key in (booted["drawn_elsewhere"] or {})
                     if key in booted["rendered"]]
        assert misplaced == [], (
            f"declared drawn elsewhere and drawn here too: {misplaced}")

    def test_the_declarations_do_not_overlap(self, booted):
        both = set(booted["drawn_elsewhere"] or {}) & set(
            booted["terminal_only"] or {})
        assert both == set(), both

    def test_the_slot_is_empty_because_nothing_needs_it(self, booted):
        """The measurement, stated: every key of `analyze/v4` reaches a
        reader today, so `TERMINAL_ONLY` is empty. Filling it is a
        deliberate act with a reason, and this is where that act is
        noticed rather than absorbed."""
        assert booted["terminal_only"] == {}, (
            f"a key was declared terminal-only: {booted['terminal_only']}. "
            f"That is allowed - update this clause and say which round "
            f"decided it, so the entry is a decision and not a default")


@needs_node
class TestThePlaneTwoDestinationsReachTheBrowser:
    """`UX-389` declared them and proved they resolve in the payload.
    Resolving in the payload is not reaching a reader."""

    def test_every_payload_destination_is_drawn(self, booted, written):
        unreached = []
        for block, (kind, where, _why) in plane2.DESTINATIONS.items():
            if kind != plane2.PAYLOAD or written.get(block) is None:
                continue
            if where.split(".")[0] not in booted["rendered"]:
                unreached.append(f"{block} -> {where}")
        assert unreached == [], (
            f"declared to reach the payload, and the page draws no "
            f"section for it: {unreached}")

    def test_every_carried_member_is_drawn_where_it_landed(
            self, booted, written):
        """A member carried into a section that does not draw it is the
        same silence one level down: the block resolves in the payload,
        the section exists, and the number still reaches nobody.

        Read off `data-key`, which `UX-374` puts on every term the page
        draws - not off the section's prose, which carries the member's
        *schema description* whether or not the value arrived, and so
        cannot tell a drawn member from a declared one.
        """
        undrawn = []
        for block, (kind, where, _why) in plane2.DESTINATIONS.items():
            if kind != plane2.PAYLOAD or written.get(block) is None:
                continue
            root, _, member = where.partition(".")
            if not member:
                continue
            if member not in (booted["keyed"].get(root) or []):
                undrawn.append(f"{where} (no term drawn in `{root}`)")
        assert undrawn == [], undrawn

    def test_a_join_destination_lands_where_the_page_declares_it(
            self, booted):
        """`element_join` is `DRAWN_ELSEWHERE`, and its fields are
        `UX-356`'s guard. What this asserts is the cross-reference: a
        block declared to land on a join field lands on a population
        the page has a written destination for."""
        joins = [where for kind, where, _why in plane2.DESTINATIONS.values()
                 if kind == plane2.JOIN]
        if not joins:
            pytest.skip("no block declares a join destination")
        assert "element_join" in (booted["drawn_elsewhere"] or {}), (
            "blocks are declared to land on `element_join` rows, and the "
            "page has no written destination for that population")
