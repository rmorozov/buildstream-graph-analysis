"""UX-921 (styleguide §3j): the findings fold bounds its interactive
descendants too.

A direct render of findings carrying one copy action each measured
1/1, 15/15, 40/40 and 121/120 controls/findings (round 130's design
review, `docs/audits/round-130.md`) - the visible population stayed
bounded at `TABLE_OPENS_BOUNDED_ABOVE` while every hidden card kept its
button. This is `renderFindings` itself, in the shim: the claim is
about the document the renderer produces, not a rendered browser page.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_SCRIPT = r"""
globalThis._makeNode = (await import(process.env.BGA_DOM_SHIM)).makeNode;
const { installDocument } = await import(process.env.BGA_DOM_SHIM);
const document = installDocument();
document.getElementById = (id) => document.body.querySelector(`#${id}`);

const sections = await import(process.env.BGA_REPO + "/bga/viewer/sections.js");
const { findingAnchor } = await import(process.env.BGA_REPO + "/bga/viewer/primitives.js");

const finding = (i) => ({ id: `f${i}`, severity: "info", title: `Finding ${i}`,
  copy_text: `copy ${i}` });

// UX-413's own "Show all N findings" button is the fold's control,
// not a finding's interactive descendant - excluded so the 40/120
// equality below is about the population, not this repository's other
// bound.
const controls = (section) => {
  const all = (n, out = []) => {
    if (n.tagName === "button" && n.getAttribute("class") !== "show-all-cards") {
      out.push(n);
    }
    for (const c of n.children ?? []) all(c, out);
    return out;
  };
  return all(section).length;
};
const order = (section) => [...section.querySelectorAll("article.finding")]
  .map((a) => a.getAttribute("data-finding-id"));

const render = (n) => {
  const section = sections.renderFindings(
    Array.from({ length: n }, (_, i) => finding(i)), null, undefined);
  document.body.append(section);
  return section;
};

const one = render(1);
const forty = render(40);
const oneTwenty = render(120);

const before120 = controls(oneTwenty);
// Direct fragment entry: only finding 100's shell hydrates.
document.getElementById(findingAnchor("f100"))._hydrate();
const afterFragment = controls(oneTwenty);
// Only the shells (index >= 40) matter here - the opening 40 are
// hydrated on render regardless, by contract.
const others = [...oneTwenty.querySelectorAll("article.finding")]
  .slice(40)
  .filter((a) => a.getAttribute("data-finding-id") !== "f100")
  .filter((a) => a.querySelector("button")).length;

const showAll = render(120);
showAll.querySelector('[data-role="card-bound"] button')
  .dispatchEvent({ type: "click" });

process.stdout.write(JSON.stringify({
  one: controls(one), forty: controls(forty), before120, afterFragment,
  others, showAllControls: controls(showAll), showAllOrder: order(showAll),
}) + "\n");
"""


@pytest.fixture(scope="module")
def measured():
    result = subprocess.run(
        [node, "--input-type=module", "-e", _SCRIPT],
        capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ, BGA_REPO=str(REPO),
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@needs_node
class TestTheFoldBoundsControlsToo:
    def test_one_finding_is_never_hidden(self, measured):
        assert measured["one"] == 1

    def test_forty_and_a_hundred_and_twenty_carry_the_same_controls(
            self, measured):
        """The class the item names: at 40 and at 120 findings, the
        interactive descendants materialised before expansion are
        equal - the population past the bound is a shell, not a hidden
        card carrying its own button."""
        assert measured["forty"] == measured["before120"]

    def test_a_direct_fragment_hydrates_only_its_own_card(self, measured):
        assert measured["afterFragment"] == measured["before120"] + 1
        assert measured["others"] == 0

    def test_show_all_hydrates_every_finding_once_in_source_order(
            self, measured):
        assert measured["showAllControls"] == 120
        assert measured["showAllOrder"] == [f"f{i}" for i in range(120)]
