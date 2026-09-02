// UX-266: this was an inline `<script type="module">` in
// `perfetto.html`, refused by the page's own `default-src 'self'`.
// The consequence is quieter than `sql.html`'s and worse: the page
// renders, the "Open in Perfetto" button is *there*, and nothing
// is listening to it - so `bga view --perfetto` lands on a button
// that does nothing at all.
import { handOff, deepLink } from "./perfetto.js";
import { renderQuestions } from "./questions.js";
import { elementUids } from "./element.js";

const line = document.getElementById("line");
const deep = document.getElementById("deep");
deep.href = deepLink(new URL("timeline.json.gz", location.href).href);

// UX-198: no `go()` at script load. The previous version called it
// here, so there was never a user gesture and default-settings Chrome
// blocked the pop-up *every time* - the "Try again" button below it was
// the tell that nobody read as a bug report.
document.getElementById("open").addEventListener("click", async () => {
  line.textContent = "Opening ui.perfetto.dev…";
  try {
    const { bytes } = await handOff();
    line.textContent =
      `Sent ${(bytes / 1024).toFixed(1)} KiB to the Perfetto tab. ` +
      `You can close this one — and stop the server with Ctrl-C.`;
  } catch (error) {
    line.textContent = String(error.message ?? error);
  }
});

// ------------------------------------------------- UX-373: and what to ask

/**
 * `UX-373`: the questions, on the page that opened the trace.
 *
 * This was `sql.html`, and `sql.js` was these fourteen lines. Two
 * pages, one errand: how to open the trace, and what to ask it once
 * open. The export has always had them together - `app.js` inlines
 * this same section into the report because `UX-199` found the export
 * dropping the link and leaving nothing behind it - so the one-page
 * arrangement already existed and only the served path was split.
 *
 * `renderQuestions` is the one source. The list was written out in
 * `sql.html` once and drifted from the module the export rendered; a
 * guard compared titles and would not have caught a changed query.
 *
 * **And the run behind it.** `sql.html` had none, so `UX-369`'s
 * element control could not be drawn there and the queries showed the
 * bare token. This page is served beside `report.json`, so it reads
 * the same three facts `app.js` passes - whether there is a timeline,
 * which planes are in it, and this project's own element uids - and
 * the substitution control the item asks for is on the merged page
 * rather than described in it. A fetch that fails changes nothing:
 * the section renders with what it had, which is what `sql.html`
 * always showed.
 */
function make(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    node.setAttribute(name, value);
  }
  for (const child of children) {
    node.append(child?.nodeType ? child : String(child));
  }
  return node;
}

async function questions() {
  let options = {};
  try {
    const [report, run] = await Promise.all([
      fetch("report.json").then((r) => (r.ok ? r.json() : null)),
      fetch("run.json").then((r) => (r.ok ? r.json() : null)),
    ]);
    options = {
      hasTimeline: Boolean(run?.has_timeline),
      tracePlanes: run?.trace_planes,
      flowLosses: run?.trace_flow_losses,
      elements: report ? elementUids(report) : [],
      element: report?.headline?.top_actions?.[0]?.element_uid ?? null,
    };
    // `UX-194`'s dead-control rule, which this page had never applied
    // to its own button - and the merge is what made that visible.
    // Measured on `tests/fixtures/macro_micro`, served: the top of the
    // page offered "Open in Perfetto" and the section below it said
    // "This snapshot carries no build log, so there is no timeline to
    // open here". Both were true of the page and only one was true of
    // the run. `index.html` has gated its own button on this fact
    // since `UX-194`; this is the same gate, one page over.
    if (run && !run.has_timeline) {
      document.querySelector(".handoff")?.remove();
      // `:not(#line)` - `#line` is a `p.muted` too, and removing it
      // detached the very node the sentence below is written to. The
      // page then said nothing at all, which is a worse answer than
      // the contradiction this is fixing.
      document.querySelectorAll("#status p.muted:not(#line)")
        .forEach((node) => node.remove());
      line.textContent =
        "This snapshot carries no timeline, so there is nothing to hand "
        + "over. Capture one with `bga capture`, then `bga timeline`.";
      line.setAttribute("data-handoff", "absent");
    }
  } catch {
    // Served from somewhere that has no documents beside it. The
    // section still renders; it just cannot name this run's elements,
    // and the button stays - an unknown timeline is not an absent one.
  }
  document.getElementById("questions").append(renderQuestions(make, options));
  // `UX-523`, one page over: this page fetches too, and it is the one
  // whose whole state is what the fetch found. Without the flag the
  // sampler falls back to "the markup stopped growing", which a cold
  // start satisfies before `report.json` lands - three clauses of
  // `test_one_page_behind_the_button.py` red under the full suite and
  // green alone.
  if (document.documentElement?.dataset) {
    document.documentElement.dataset.bgaBooted = "1";
  }
}

questions();
