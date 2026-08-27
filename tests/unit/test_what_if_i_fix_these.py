"""UX-219: the horizon as a plan, drawn.

`signals.optimization_horizon` has carried the whole answer per step for
many rounds - the saving, the makespan that remains, and which elements
*enter* the critical path once that step is taken. It rendered as a
five-column table, and the question it answers - *if I fix the top
three, what does this build become?* - is the most product-shaped
question the tool asks.

`entering` is the part a table hides and the part that matters: it is
the honest reason the savings stop adding up, and why this is a plan
rather than a sum.

Every guard here reads `data-` attributes against the payload rather
than computed style, per the acceptance. The committed golden fixture
discriminates the width mutation on its own - at every step the
published `makespan_after_us` differs from the naive
`total - cumulative_saving_us`:

    base.bst    8000 vs 10000
    lib.bst     4000 vs  6000
    extra.bst   3000 vs  5000
    app.bst        0 vs  2000

so a drawing that summed savings would disagree with the payload on
every bar, not just in principle.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")

_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: t,
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const text = (n) => (n.children ?? []).reduce(
  (acc, c) => acc + text(c), n.textContent ?? "");
const href = (n) => n.href ?? n.attrs.href ?? "";
"""


@pytest.fixture(scope="module")
def report():
    """The committed golden fixture, analyzed through the real CLI."""
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", GOLDEN,
         "--format", "json", "--diagnostics"],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def drawn(report):
    script = _SHIM + '''
      const { renderHorizon } = await import("./tests/viewer.mjs");
      const section = renderHorizon(%s);
      if (section === null) { console.log(JSON.stringify(null)); }
      else {
        const rows = all(section, (n) => n.className === "horizon-step").map((li) => {
          const bar = all(li, (n) => n.attrs["data-role"] === "bar")[0];
          const entering = all(li, (n) => n.attrs["data-role"] === "entering")[0];
          return {
            element: li.attrs["data-element"] ?? null,
            makespan: li.attrs["data-makespan-after-us"],
            saving: li.attrs["data-saving-us"] ?? null,
            style: bar.attrs.style,
            entering: entering
              ? all(entering, (n) => n.tagName === "a").map((a) => a.textContent)
              : [],
            enteringHrefs: entering
              ? all(entering, (n) => n.tagName === "a").map(href) : [],
            hrefs: all(li, (n) => n.tagName === "a").map(href),
          };
        });
        const total = all(section, (n) => n.attrs["data-role"] === "horizon-total")[0];
        console.log(JSON.stringify({
          rows,
          section: section.attrs["data-section"],
          total: total ? {
            text: text(total),
            cumulative: total.attrs["data-cumulative-saving-us"],
            of: total.attrs["data-total-us"],
          } : null,
        }));
      }
    ''' % json.dumps(report)
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=REPO, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
class TestEveryWidthIsAPublishedMakespan:

    def test_one_row_per_published_step_plus_now(self, report, drawn):
        steps = report["signals"]["optimization_horizon"]
        assert len(drawn["rows"]) == len(steps) + 1, (
            "one row per step, plus the run as it stands")

    def test_the_first_row_is_the_run_as_it_stands(self, report, drawn):
        now = drawn["rows"][0]
        assert now["element"] is None
        assert now["makespan"] == str(report["total_duration_us"])

    def test_each_bar_carries_the_payloads_own_makespan(self, report, drawn):
        steps = report["signals"]["optimization_horizon"]
        for step, row in zip(steps, drawn["rows"][1:]):
            assert row["element"] == step["element_uid"]
            assert row["makespan"] == str(step["makespan_after_us"]), row

    def test_the_width_is_that_makespan_over_the_total(self, report, drawn):
        """One division of two published durations - UX-202's rule.

        Compared as a number, not as a string: JavaScript renders an
        integral ratio as `100` where Python formats `100.0`, and a
        guard that failed on that would be testing number formatting
        rather than the drawing.
        """
        total = report["total_duration_us"]
        for row in drawn["rows"]:
            width = _decl(row["style"], "--w")
            assert width.endswith("%"), row
            drawn_pct = float(width.rstrip("%"))
            assert drawn_pct == pytest.approx(
                (int(row["makespan"]) / total) * 100), row

    def test_a_width_is_never_a_sum_of_savings(self, report, drawn):
        """The mutation this fixture discriminates: on every step the
        published makespan differs from `total - cumulative_saving`."""
        total = report["total_duration_us"]
        steps = report["signals"]["optimization_horizon"]
        for step, row in zip(steps, drawn["rows"][1:]):
            naive = total - step["cumulative_saving_us"]
            assert step["makespan_after_us"] != naive, (
                "fixture no longer discriminates; pick another")
            assert row["makespan"] != str(naive), row


@needs_node
class TestTheDrawingNamesWhatEntersThePath:

    def test_entering_is_exactly_the_payloads(self, report, drawn):
        steps = report["signals"]["optimization_horizon"]
        for step, row in zip(steps, drawn["rows"][1:]):
            assert row["entering"] == list(step.get("entering") or []), row

    def test_the_fixture_has_a_step_that_enters(self, report):
        """Otherwise the guard above passes over four empty lists."""
        entering = [s for s in report["signals"]["optimization_horizon"]
                    if s.get("entering")]
        assert entering, "the fixture must have at least one entering element"

    def test_entering_elements_link_to_their_sections(self, drawn):
        seen = 0
        for row in drawn["rows"]:
            for target in row["enteringHrefs"]:
                assert target.startswith("#element-"), target
                seen += 1
        assert seen, "no entering links were rendered"

    def test_the_step_element_links_to_its_section(self, drawn):
        for row in drawn["rows"][1:]:
            assert any(h.startswith("#element-") for h in row["hrefs"]), row


@needs_node
class TestTheTotalIsPublishedValuesOnly:

    def test_the_total_reads_the_last_steps_cumulative_saving(self, report, drawn):
        last = report["signals"]["optimization_horizon"][-1]
        assert drawn["total"]["cumulative"] == str(last["cumulative_saving_us"])
        assert drawn["total"]["of"] == str(report["total_duration_us"])

    def test_the_share_is_that_over_the_total(self, report, drawn):
        last = report["signals"]["optimization_horizon"][-1]
        share = last["cumulative_saving_us"] / report["total_duration_us"] * 100
        assert f"{share:.0f}% faster" in drawn["total"]["text"], drawn["total"]

    def test_the_count_is_the_number_of_published_steps(self, report, drawn):
        steps = report["signals"]["optimization_horizon"]
        assert f"{len(steps)} fixes" in drawn["total"]["text"]

    def test_the_total_is_read_and_not_re_added(self):
        """Asserted on a synthetic payload, and the reason is worth saying.

        In every report this analyzer produces, `cumulative_saving_us`
        *is* the running sum of `saving_us` - they agree by
        construction. So the obvious mutation, "re-add the savings
        instead of reading the cumulative", cannot fail against any real
        fixture: it is non-discriminating, and was rejected rather than
        counted.

        The property it was meant to check is real all the same - the
        page must read the published field - so it is checked where the
        two can differ: a payload whose last `cumulative_saving_us`
        disagrees with the sum. The page must report the published one.
        """
        payload = {
            "total_duration_us": 100,
            "signals": {"optimization_horizon": [
                {"element_uid": "a.bst", "saving_us": 10,
                 "makespan_after_us": 90, "cumulative_saving_us": 10,
                 "entering": []},
                {"element_uid": "b.bst", "saving_us": 10,
                 "makespan_after_us": 85, "cumulative_saving_us": 15,
                 "entering": []},
            ]},
        }
        assert sum(s["saving_us"] for s in
                   payload["signals"]["optimization_horizon"]) == 20
        script = _SHIM + '''
          const { renderHorizon } = await import("./tests/viewer.mjs");
          const section = renderHorizon(%s);
          const total = all(section,
            (n) => n.attrs["data-role"] === "horizon-total")[0];
          console.log(JSON.stringify({
            cumulative: total.attrs["data-cumulative-saving-us"],
            text: text(total),
          }));
        ''' % json.dumps(payload)
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True, cwd=REPO,
                                timeout=60)
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout)
        assert out["cumulative"] == "15", out
        assert "15% faster" in out["text"], out


@needs_node
class TestAbsenceStaysAbsent:

    @staticmethod
    def _render(payload):
        script = _SHIM + '''
          const { renderHorizon } = await import("./tests/viewer.mjs");
          console.log(JSON.stringify(renderHorizon(%s) === null));
        ''' % json.dumps(payload)
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True, cwd=REPO, timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_no_horizon_renders_nothing(self):
        assert self._render({"total_duration_us": 1000, "signals": {}}) is True

    def test_no_total_renders_nothing(self):
        """Without a denominator there is no honest width to draw."""
        assert self._render({"signals": {"optimization_horizon": [
            {"element_uid": "a.bst", "makespan_after_us": 5,
             "saving_us": 1, "cumulative_saving_us": 1}]}}) is True

    def test_an_empty_horizon_renders_nothing(self):
        assert self._render(
            {"total_duration_us": 1000,
             "signals": {"optimization_horizon": []}}) is True


def _decl(style, name):
    """The value of one declaration in a browser-serialised `style`.

    A real DOM writes `flex-grow: 428.571;` — with the semicolon, and
    with any other declarations beside it. The `.replace("flex-grow: ",
    "")` this replaced read the shim's semicolon-less form and would
    have broken on the real one, which is `UX-263`'s lesson in the
    guard rather than in the page.
    """
    for part in style.split(";"):
        key, _, value = part.partition(":")
        if key.strip() == name:
            return value.strip()
    raise AssertionError(f"no `{name}` declaration in {style!r}")


class TestTheTableStays:
    """Clause 4: nothing leaves the page or the export."""

    def test_the_horizon_still_declares_its_columns(self):
        from bga import schemas
        signals = schemas.schema(schemas.ANALYZE)["properties"]["signals"]
        horizon = signals["properties"]["optimization_horizon"]
        assert schemas.COLUMNS in horizon, (
            "the table is the fold-out beneath the drawing and must keep "
            "its column declaration")

    def test_the_drawing_did_not_replace_the_payload_section(self):
        source = open(os.path.join(REPO, "bga/viewer/app.js"),
                      encoding="utf-8").read()
        assert "renderHorizon" in source
        # The generic schema dispatch still renders `signals`; the
        # drawing is appended, never substituted for it.
        assert "delete payload.signals" not in source
        assert "optimization_horizon" not in source, (
            "app.js must not special-case the horizon key - the drawing "
            "lives in views.js and the table stays generic")
