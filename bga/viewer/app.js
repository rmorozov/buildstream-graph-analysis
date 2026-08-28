// UX-193: render the schema, not the report.
//
// The load-bearing property is that this file contains no list of the
// report's fields. It asks the schema what a key *is* - a duration, a
// share, a findings array, a table with these columns - and renders
// accordingly. A field added to `analyze/v1` therefore appears here
// with no edit to this file, and a field the schema does not describe
// still renders, generically, rather than vanishing.
//
// The corollary is the constraint Direction 7 wanted: anything the
// viewer should show has to enter the published schema first, where the
// text renderer, CI and every external consumer get it too.

// UX-337: `app.js` keeps the seam it was named for - boot, the handoff,
// the findings block, the section router - and hands the other two to
// modules below it. Each is named symbol by symbol rather than
// re-exported through one file: the export's `_module_order` walks
// `import` lines, and a re-export is a module it would never inline
// (`UX-199`).
import { served, safeStorage } from "./primitives.js";
import { QUANTITY, SEVERITY, COLUMNS, SERIES, DISTRIBUTION, INLINE, bytes,
         childNode, cssId, el, guessQuantity, heading, hintsOf, quantity,
         quantityFor, sectionHead, title } from "./format.js";
import { ARRAY_INLINE_ITEMS, CELL_NEST_LIMIT, OBJECT_INLINE_FIELDS,
         LIFTED_SECTION, describedTerm, liftedCriticalPath, renderPairs,
         renderStructured,
         renderTable } from "./structured.js";
import { handOff, deepLink, tracedSize, openTab, perfettoCanFetch,
         PERFETTO_FRIENDLY_URL } from "./perfetto.js";
// `renderBlastTree` is *not* imported here: `views.js` draws the tree
// inside `renderBlastSearch`, and the name sat in this list unused
// until UX-337 counted what each half of the file actually reaches for.
import { renderBand, renderTrend, renderBlastSearch, renderBlastOffline,
         renderOverview, renderEvidence,
         renderCriticalPath, INCOMPLETE } from "./views.js";
// `UX-337`: the two chapters that moved out of `views.js`. Named
// directly, one import per file - `views.js` could re-export them, but
// the export's `_module_order` walks `import` lines and a re-export is
// a module it would never inline (`UX-199`).
import { renderCulprits, renderElementHistory, renderHorizon,
         renderElementSections, ensureElementSection, uidForAnchor,
         renderWhatIf } from "./element.js";
import { renderDecision, renderProvenance,
         renderInvestigation } from "./decision.js";
import { anchor, collapsible, toc, jumpTargets, matches,
         paletteResults } from "./nav.js";
import { chapters, fileInChapter, revealChapter,
         setAllOpen } from "./chapters.js";
// UX-302: the second of §1's two deliberate raw-JSON sites - the one
// the reader asks for, per section, because pasting a section into an
// issue is what people do with a report.
import { jsonToggles, recordSource } from "./rawjson.js";
// UX-334: `name` and `id` on every control the page builds - see the
// measured counts in the module.
import { contained } from "./controls.js";
import { applyView, splitHash, viewLink, wireViewState } from "./viewstate.js";
import { applyFocus, applyMarks, clearFocus, focusedElement, readMarks,
         renderFocusBar, renderMarkSummary } from "./focus.js";
import { copyButton, renderQuestions } from "./questions.js";
import { investigationFor } from "./trace_context.js";
import { copy } from "./tables.js";
import { CONTROLS, classify } from "./shapes.js";
import { strip, GRADE_EXHIBIT } from "./drawings.js";

/**
 * `UX-204`: each finding carries a button that knows *why* it is
 * sending you to Perfetto.
 *
 * `investigate` is passed in rather than reached for, and it is only
 * passed when the run has a timeline behind it - `UX-194`'s dead-button
 * rule. No timeline, no buttons, rather than a row of controls that
 * error.
 */
export const EVIDENCE_SHOWN = 4;

/**
 * `UX-217`: the numbers a finding was drawn from.
 *
 * Every finding has carried a structured `evidence` dict since the
 * findings became data, and `renderFindings` read `id`, `severity`,
 * `title`, `detail` and `elements` and dropped it. So the page showed
 * the conclusion and hid the measurements it rests on.
 *
 * `node` is the schema's `evidence` node, so a key renders in its
 * declared unit and a key nobody declared renders raw - `UX-201`'s
 * rule one level deeper, and the reason a new finding's evidence
 * formats correctly with no change here. A value that is not a scalar
 * (`rows`, `steps`, `constraints` - the arrays a finding builds its
 * sentence from) is a table in its own right and is left to the
 * section that already draws it.
 */
export function renderFindingEvidence(evidence, node = undefined) {
  const scalars = Object.entries(evidence ?? {}).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;

  const list = el("dl", { class: "pairs evidence" });
  for (const [key, value] of scalars) {
    const kind = quantityFor(childNode(node, key), key);
    // UX-317 (§2b.3): the same marker here. The mechanism is generic -
    // any described value, anywhere - and this list is one of the three
    // places a `<dt>` is built.
    const { term, describe } = describedTerm(
      key, hintsOf(childNode(node, key)).description, {},
      hintsOf(childNode(node, key))[INLINE], kind);
    list.append(
      term,
      el("dd", { class: typeof value === "number" ? "num" : null,
                 "data-field": key,
                 "data-raw": value === null ? "" : String(value) },
         typeof value === "number" ? quantity(value, kind)
           : value === null ? "—" : String(value),
         describe));
  }
  if (scalars.length <= EVIDENCE_SHOWN) return list;
  // UX-209's fold, for the same reason: the evidence is the point, and
  // eight rows of it above the next finding is a wall.
  //
  // `UX-359`: and it announces its depth, like every other value fold
  // (§3a.1). It did not, for the same reason `evidence-detail` did not
  // until `UX-320` - it is built by hand here rather than by
  // `renderStructured`. What kept it hidden this time is that it only
  // appears on a finding with more than `EVIDENCE_SHOWN` scalars, and
  // the only fixture that has one is the Plane 2 half of `macro_micro`
  // that every guard's `copytree` was dropping. One level, N rows.
  const rows = scalars.length;
  return el("details", { class: "evidence-fold", "data-fold": "evidence",
                         "data-levels": "1", "data-rows": String(rows) },
            el("summary", {},
               `${rows} measurements · 1 level, `
               + `${rows} row${rows === 1 ? "" : "s"}`),
            list);
}

export function renderFindings(findings, investigate = null, node = undefined) {
  const section = el("section", { "data-section": "findings" },
    el("h2", {}, `Findings (${findings.length})`));
  const evidenceNode = childNode(node?.items, "evidence");
  for (const finding of findings) {
    const severity = String(finding.severity ?? "info").toLowerCase();
    const detail = Array.isArray(finding.detail)
      ? finding.detail : (finding.detail ? [finding.detail] : []);
    section.append(el("article",
      { class: "finding", "data-severity": severity,
        "data-finding-id": finding.id ?? "" },
      el("p", { class: "title" },
        el("span", { class: "badge" }, severity),
        finding.title ?? finding.id ?? ""),
      ...detail.map((line) => el("p", { class: "detail muted" }, line)),
      // UX-216: a finding names elements; each is a link to that
      // element's own section, and carries `data-element` so the
      // cross-reference finds this finding from the other direction.
      finding.elements && finding.elements.length
        ? el("p", { class: "muted" },
            ...finding.elements.flatMap((uid, index) => [
              index ? ", " : "",
              el("a", { href: `#${cssId(uid)}`, "data-element": uid },
                 el("code", {}, uid)),
            ]))
        : null,
      renderFindingEvidence(finding.evidence, evidenceNode),
      // UX-229: the chain behind this finding, from the published
      // record. `views.js` draws it, so the decision panel and every
      // finding show one shape.
      renderProvenance(finding.provenance),
      investigate ? investigateButton(finding, investigate) : null,
      // UX-224: the finding as something you can paste. The text is
      // `findings[].copy_text`, rendered in the pipeline - this button
      // copies a published string and does not word anything, which is
      // the only way one renderer can serve both a Python CI comment
      // and a JavaScript page. Absent, not empty, on a payload that
      // does not carry it.
      finding.copy_text
        ? copyButton(el, finding.copy_text, {}, "finding")
        : null));
  }
  return section;
}

/**
 * The button, and the paste it leaves behind.
 *
 * `UX-204`'s always-works floor: Perfetto's deep-link API takes a trace
 * and a title, and has no documented way to preload the Query pane -
 * so the query is not faked into the URL, it is put one paste away. The
 * button reveals it whether the handoff succeeds or not, because a
 * blocked pop-up is exactly when the reader needs the SQL most.
 */
export function investigateButton(finding, investigate) {
  const context = investigationFor(finding);
  if (!context) return null;
  const wrapper = el("div", { class: "investigate",
                              "data-query-id": context.queryId,
                              "data-element": context.element ?? "" });
  const button = el("button", { type: "button" }, "Investigate in Perfetto");
  // `hidden` through `el` lands as a *property* (it is not a
  // `data-` attribute), so it is cleared as one: `removeAttribute`
  // would not touch it, and the paste would never appear.
  const paste = el("pre", { class: "query", hidden: true },
                   el("code", {}, context.sql));
  const status = el("span", { class: "muted handoff" });
  button.addEventListener("click", () => {
    // No `await` before the handoff: the click's transient activation
    // is what opens the tab (`UX-198`), and it is gone by the time one
    // resolves.
    paste.hidden = false;
    const sent = investigate(context);
    status.textContent = "opening ui.perfetto.dev — the query is below…";
    Promise.resolve(sent).then(
      ({ bytes } = {}) => {
        status.textContent = bytes
          ? `sent ${(bytes / 1024).toFixed(1)} KiB — paste the query below`
          : "paste the query below";
      },
      (error) => { status.textContent = String(error.message ?? error); });
  });
  wrapper.append(button, status, paste);
  return wrapper;
}

// UX-201: the enum decides, and the prose is a fallback for payloads
// written before `verdict_kind` existed. The viewer used to
// string-match the *sentence* - so rewording "improved" would have
// silently restyled the banner, and a `compare/v1` that changed its
// wording was a rendering change nobody would have called one.
const VERDICT_CLASS = {
  improved: "good",
  regressed: "refused",
  not_comparable: "refused",
  no_significant_change: "",
  within_observed_range: "warn",
};

export function verdictClass(text, kind) {
  if (kind && kind in VERDICT_CLASS) return VERDICT_CLASS[kind];
  const value = String(text).toLowerCase();
  if (value.includes("not comparable") || value.includes("regress")) return "refused";
  if (value.includes("improve")) return "good";
  if (value.includes("no significant")) return "";
  return "warn";
}

export function renderVerdict(payload) {
  // Refusals get visual weight because they are the answer, not an
  // error: `UX-156`/`UX-185`'s incomplete runs and `UX-186`'s
  // cross-host pairs are all "bga will not judge this, and here is
  // why".
  const banner = [];
  if (payload.verdict) {
    banner.push(el("div", {
      class: `verdict ${verdictClass(payload.verdict, payload.verdict_kind)}`,
      "data-verdict": String(payload.verdict),
      "data-verdict-kind": payload.verdict_kind ?? null },
      el("h2", {}, "Verdict"), el("p", {}, String(payload.verdict))));
  }
  const outcome = payload.run_instance?.incomplete_reason
    ?? payload.run_instance?.build_outcome?.incomplete_reason;
  if (outcome) {
    // UX-207: the *one* place a refusal is drawn. `renderEvidence` drew
    // a second banner with the same claim in different words - measured
    // at two `data-incomplete` nodes on an interrupted fixture - and the
    // header is also the part a reader may have collapsed, which is the
    // worst place to keep the one sentence they must not miss.
    //
    // The wording comes from `INCOMPLETE`, which is where UX-202 put the
    // three sentences and where the guard against `RunContext`'s reasons
    // still points.
    banner.push(el("div", { class: "verdict refused",
                            "data-incomplete": outcome },
      el("h2", {}, `This run is ${outcome}`),
      el("p", { class: "muted" },
        INCOMPLETE[outcome] ?? "Durations from a run that did not finish "
                               + "are not measurements.")));
  }
  if (payload.comparability_warning) {
    banner.push(el("div", { class: "verdict warn", "data-warning": "1" },
      el("h2", {}, "Comparability"),
      el("p", {}, String(payload.comparability_warning))));
  }
  return banner;
}

// The generic dispatch. Note there is no `switch (key)` here: what a
// value is rendered as follows from its *shape* and its hints.
//: `UX-338`: sections the page deliberately does not draw on their
//: own, and where their content went instead. Not a blanket "skip
//: list": each entry is a population that is drawn *somewhere*, and
//: saying where is what stops this becoming a place to hide a section
//: nobody wants to fix.
export const DRAWN_ELSEWHERE = {
  element_join: "merged into the one element table (`elements`) and the "
    + "element sections beneath it, which is `UX-289`'s rule applied to "
    + "the columns `UX-215` added - it is the same eleven elements, and "
    + "drawing it twice is what `UX-338` was filed for. Every published "
    + "field arrives at one of those two except "
    + "`recommendations[].id`, which is a slug used as a key and never "
    + "shown, the way `next_steps[].id` is not shown",
};

export function renderSection(key, value, hint = {}, node = undefined,
                              investigate = null, payload = undefined,
                              root = undefined) {
  if (value === null || value === undefined) return null;
  if (key in DRAWN_ELSEWHERE) return null;
  if (hint[SEVERITY] && Array.isArray(value)) {
    // UX-217: the schema node travels with the value, so the evidence
    // renders in its declared units rather than by name-sniffing.
    return value.length ? renderFindings(value, investigate, node) : null;
  }
  if (Array.isArray(value)) {
    if (!value.length) return null;
    // `UX-302`: §1 again, at section level. Three of its rows reach
    // here and each gets its own control; the fourth outcome is a shape
    // §1 does not name, and `renderStructured` folds and warns.
    //
    // The branch this replaces was `value.join(", ")` for *everything*
    // that was not an array of objects - which is right for a short
    // scalar array, unbounded for a long one, and for an array holding
    // an object renders `[object Object]`: strictly less than the JSON
    // it was meant to be better than (`UX-277` found the same leaf in a
    // table cell).
    const control = classify(value, {
      severity: Boolean(hint[SEVERITY]),
      columns: hintsOf(node)[COLUMNS] ?? null,
      series: hintsOf(node)[SERIES] ?? hint[SERIES] ?? null,
      nestLimit: CELL_NEST_LIMIT,
      inlineFields: OBJECT_INLINE_FIELDS, inlineItems: ARRAY_INLINE_ITEMS,
    });
    if (control === CONTROLS.TABLE
        && value.every((item) => item && typeof item === "object"
                                 && !Array.isArray(item))) {
      return renderTable(key, value, hint, node);
    }
    const body = control === CONTROLS.INLINE_LIST
      ? el("p", {}, el("code", {}, value.join(", ")))
      : renderStructured(key, value, hint, node, 0, key);
    return el("section", { "data-section": key,
                           "data-rail": heading(key, hint).rail },
                          sectionHead(key, hint), body);
  }
  if (typeof value === "object") {
    // `UX-303`: a section whose whole value is a published distribution
    // is the strip and its sentence, not a definition list of five
    // percentiles - which is what §2 means by "its shape first".
    if ((hintsOf(node)[DISTRIBUTION] ?? hint[DISTRIBUTION])
        && Object.keys(value).length) {
      return el("section", { "data-section": key,
                             "data-rail": heading(key, hint).rail },
                sectionHead(key, hint),
                strip(value, {
                  countKey: String(hintsOf(node)[DISTRIBUTION]
                                   ?? hint[DISTRIBUTION]),
                  grade: GRADE_EXHIBIT,
                  format: (n) => quantity(n, quantityFor(node, key)),
                }));
    }
    return Object.keys(value).length
      // UX-289: the whole document, because a preset's population is a
      // selection published elsewhere in it - `bottleneck`
      // for the choke points. The section renders its own value; the
      // payload is only ever read for a declared `from` path.
      ? renderPairs(key, value, hint, node, payload, root) : null;
  }
  return null;   // scalars belong in the summary, below
}

export function renderSummary(payload, hints) {
  const scalars = Object.entries(payload).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;
  const list = el("dl", { class: "pairs" });
  for (const [key, value] of scalars) {
    const kind = hints[key]?.[QUANTITY] ?? guessQuantity(key);
    const { term, describe } = describedTerm(key, hints[key]?.description, {},
                                             hints[key]?.[INLINE], kind);
    list.append(
      term,
      el("dd", {}, el("span", {
        class: typeof value === "number" ? "num" : null,
        "data-raw": value === null ? "" : String(value),
      }, typeof value === "number" ? quantity(value, kind)
         : value === null ? "—" : String(value)), describe));
  }
  return el("section", { "data-section": "summary" },
            el("h2", {}, "Run"), list);
}

export function render(payload, schema, root, investigate = null) {
  const hints = {};
  for (const [key, sub] of Object.entries(schema?.properties ?? {})) {
    const hint = hintsOf(sub);
    if (Object.keys(hint).length) hints[key] = hint;
  }
  const nodes = schema?.properties ?? {};

  root.replaceChildren();
  for (const banner of renderVerdict(payload)) root.append(banner);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "schema") continue;
    // UX-270: the critical path is the one table that grows with *path
    // depth* rather than element count, so it folds by the chain's own
    // numbers. `UX-344` made it a key of the document rather than a row
    // of `signals`, which is what it was already drawn as - this is the
    // fold, kept, now that the section arrives on its own.
    const section = key === LIFTED_SECTION
      ? liftedCriticalPath(payload, schema)
      : renderSection(key, value, hints[key] ?? {}, nodes[key],
                      investigate, payload, schema);
    // `UX-302`: what this section was rendered *from*, so the "view as
    // JSON" toggle has a published value to show rather than a
    // re-serialisation of the DOM. Only the schema-driven sections get
    // one; a section the page composes from several places has no
    // single payload slice, and gets no toggle rather than a misleading
    // one.
    if (section) root.append(recordSource(section, value));
  }
  const summary = renderSummary(payload, hints);
  if (summary) {
    root.append(recordSource(summary, Object.fromEntries(
      Object.entries(payload).filter(
        ([, value]) => value === null || typeof value !== "object"))));
  }
  root.setAttribute("aria-busy", "false");
  return root;
}

/** Type-ahead over section names and element uids. Scrolls; never filters. */
/**
 * UX-255: the heading says which build measured this run.
 *
 * `UX-249`'s producer stamp, rendered where a reader who screenshots
 * the top of the page captures it. Deliberately one line: a heading
 * that grows into a second report is `UX-254`'s defect moved upward.
 *
 * An unstamped run - every artifact written before `UX-249` - says so,
 * because "we do not know which build wrote this" and "this build"
 * must not look alike.
 */
export function stampHeader(doc, payload) {
  const slot = doc.getElementById("run-producer");
  if (!slot) return;
  const stamp = payload?.producer;
  const version = typeof stamp?.version === "string" ? stamp.version : null;
  const tool = typeof stamp?.tool === "string" ? stamp.tool : "bga";
  slot.textContent = version
    ? `measured by ${tool} ${version}`
    : "measured by an unrecorded build (written before bga stamped its version)";
  slot.hidden = false;
}

/**
 * UX-254: on a narrow viewport the rail folds to its title.
 *
 * The stylesheet does the hiding - this only owns the state and the
 * click, so a browser that never matches the media query never sees a
 * folded rail. Folded by *default* below the breakpoint, because a
 * phone opening on a table of contents is the same defect this item is
 * about at a different width; expanded above it, because `UX-199`'s
 * point stands when there is room.
 *
 * Guarded rather than assumed: `matchMedia` is absent in the node
 * harness the viewer guards boot the page in, and a missing browser
 * API must not stop the page rendering.
 */
export function foldOnNarrow(nav, doc) {
  const title = nav.querySelector?.(".toc-title");
  if (!title) return;
  const narrow = doc.defaultView?.matchMedia?.("(max-width: 60rem)");
  const apply = (isNarrow) => {
    nav.setAttribute("data-folded", isNarrow ? "true" : "false");
  };
  apply(Boolean(narrow?.matches));
  title.addEventListener?.("click", () => {
    apply(nav.getAttribute("data-folded") !== "true");
  });
  // `addEventListener` on a MediaQueryList is the modern spelling and
  // the only one worth carrying; a browser without it keeps whatever
  // the first `apply` decided, which is correct for its width.
  narrow?.addEventListener?.("change", (event) => apply(event.matches));
}

export function wireJumpBox(nav, root, payload, context = {}) {
  const targets = jumpTargets(root, payload);
  const box = document.createElement("input");
  box.setAttribute("type", "search");
  box.setAttribute("id", "jump");
  // UX-334: an `id` alone satisfies the browser here; the `name` is
  // set anyway so every control this page builds carries both and the
  // guard can say so without an exception list.
  box.setAttribute("name", "jump");
  box.setAttribute("placeholder", "Jump to…");
  box.setAttribute("aria-label", "Jump to a section or element");
  const list = document.createElement("ul");
  list.className = "jump-hits";

  const go = (target) => {
    const node = target.kind === "section"
      ? document.getElementById(target.key)
      : root.querySelector(`[data-element="${CSS?.escape?.(target.key)
          ?? target.key}"]`);
    if (!node) return;
    // UX-347: a folded chapter is not a wall. Every way in opens it
    // first - here, on a rail link, and on a pasted `#anchor` - so the
    // fold costs the interaction §3b already budgets and never a
    // section a reader cannot reach.
    revealChapter(node);
    node.scrollIntoView?.({ behavior: "smooth", block: "start" });
    node.setAttribute("data-jumped", "true");
    setTimeout(() => node.removeAttribute("data-jumped"), 1600);
  };

  // UX-223: the same box, offering what the page can already do with
  // the thing being typed. `rows` is the flat keyboard order over the
  // grouped display, so `ArrowDown` moves through what a reader sees.
  let rows = [];
  let active = -1;
  const clear = () => { box.value = ""; list.replaceChildren(); rows = []; active = -1; };
  const highlight = () => {
    rows.forEach((row, i) => {
      if (i === active) row.node.setAttribute("data-active", "true");
      else row.node.removeAttribute("data-active");
    });
  };
  const run = (row) => {
    if (!row) return;
    if (row.target) go(row.target);
    else if (row.action) act(row.action);
    clear();
  };
  const act = (action) => {
    if (action.focus) {
      applyFocus(root, action.element);
      root.dispatchEvent?.(new Event("change", { bubbles: true }));
      return;
    }
    // Everything else is a place in the document; the affordance the
    // action names already exists there, and this navigates to it.
    go({ kind: "element", key: action.element });
  };

  const render = () => {
    const groups = paletteResults(targets, box.value, payload, context);
    list.replaceChildren();
    rows = [];
    active = -1;
    for (const [name, entries] of [["ELEMENT", groups.elements],
                                   ["ACTIONS", groups.actions],
                                   ["SECTIONS", groups.sections]]) {
      if (!entries.length) continue;
      const heading = document.createElement("li");
      heading.className = "palette-group";
      heading.setAttribute("data-group", name);
      heading.textContent = name;
      list.append(heading);
      for (const entry of entries) {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.setAttribute("type", "button");
        if (entry.kind) {
          button.textContent = entry.text;
          button.setAttribute("data-jump", entry.key);
          if (entry.facts) {
            // UX-223 clause 4: read, never recomputed.
            const facts = document.createElement("span");
            facts.className = "palette-facts";
            facts.setAttribute("data-duration-us",
                               String(entry.facts.duration_us ?? ""));
            facts.textContent = [
              entry.facts.duration_us !== null
                ? quantity(entry.facts.duration_us, "duration_us") : null,
              entry.facts.share_of_path !== null
                ? `${(entry.facts.share_of_path * 100).toFixed(1)}% path` : null,
              entry.facts.saving_us !== null
                ? `saves ${quantity(entry.facts.saving_us, "duration_us")}` : null,
            ].filter(Boolean).join(" · ");
            button.append(facts);
          }
          rows.push({ node: item, target: entry });
        } else {
          button.textContent = entry.label;
          button.setAttribute("data-action", entry.id);
          button.setAttribute("data-element", entry.element);
          rows.push({ node: item, action: entry });
        }
        const row = rows[rows.length - 1];
        button.addEventListener("click", () => run(row));
        item.append(button);
        list.append(item);
      }
    }
  };

  box.addEventListener("input", render);
  box.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!rows.length) return;
      event.preventDefault?.();
      const step = event.key === "ArrowDown" ? 1 : -1;
      active = (active + step + rows.length + (active < 0 ? 1 : 0)) % rows.length;
      highlight();
      return;
    }
    if (event.key === "Escape") { clear(); return; }
    if (event.key !== "Enter") return;
    run(active >= 0 ? rows[active] : rows[0]);
  });

  // UX-284 item 3: at the top of the rail, not after the section list.
  // The jump box is the page's *coarse* navigation - the control a
  // reader reaches for before they know which section they want - and
  // appending it put it below thirty-odd entries, measured at y=1236 on
  // an 18.8-screen report whose first screen ends at 900.
  const title = nav.querySelector?.(".toc-title");
  if (title && typeof title.after === "function") title.after(box, list);
  else nav.prepend?.(list) ?? nav.append(box, list);
  if (!box.parentNode) nav.prepend(box, list);
  return { targets, box, list, render, rowsOf: () => rows };
}

// ------------------------------------------------------------------ boot

/**
 * `run` is the `run.json` payload: `UX-299` publishes the size
 * threshold in it, so the page applies the server's number rather than
 * keeping a second copy of it.
 */
export function wireTheHandoff(run = {}) {
  const actions = document.getElementById("actions");
  const button = document.getElementById("perfetto");
  const status = document.getElementById("handoff");
  const fallback = document.getElementById("perfetto-link");
  if (!actions || !button) return;
  actions.hidden = false;

  // UX-198: the deep link only works when something is serving the
  // trace over http for Perfetto to fetch. An export is a `file://`
  // document with the trace inlined as a data: URL, and nothing can
  // fetch that cross-origin - so the link is shown in served mode and
  // stays hidden in an export, rather than shipping a link that 404s
  // for exactly the readers least able to debug it.
  const url = traceUrl();
  const absolute = new URL(url, location.href);
  const served = absolute.protocol === "http:" || absolute.protocol === "https:";
  // `UX-314`: served is not enough. The deep link makes *Perfetto*
  // fetch this URL, so it is Perfetto's own `connect-src` that decides
  // - and over plain http that allows two origins, neither of which is
  // the ephemeral port `bga view` binds by default. A link that is
  // always refused is worse than no link: it fails in a console the
  // reader has no reason to open.
  const fetchable = served && perfettoCanFetch(absolute.href);
  if (fallback && fetchable) {
    fallback.href = deepLink(absolute.href);
    fallback.parentElement.hidden = false;
  }
  // `UX-314`: the route that needs nobody's permission. Shown whenever
  // there is a server behind the trace, because both other transports
  // can be refused - the deep link by Perfetto's CSP, the tab-to-tab
  // post by the size threshold - and Perfetto's drag-and-drop is
  // refused by neither.
  const download = document.getElementById("trace-download");
  if (download && served) {
    download.href = absolute.href;
    download.parentElement.hidden = false;
  }

  // UX-299: the threshold above which the trace is fetched by Perfetto
  // rather than copied through this page. Published by the server so
  // there is one number with one explanation, not two copies of it.
  const inlineMax = Number(run?.trace_inline_max_bytes ?? Infinity);

  button.addEventListener("click", async () => {
    status.textContent = "opening ui.perfetto.dev — sent tab to tab, not uploaded…";
    // `handOff` opens the tab before its first `await` (UX-198), so
    // this must call it without one - no `await` may come first in
    // this handler, or the click's activation is gone before the open.
    // The same rule applies to the deep-link path below: the tab is
    // opened here, synchronously, and only then is the size asked for.
    const tab = served ? openTab({}) : null;
    try {
      if (tab) {
        // UX-299: a `HEAD`, which reads no trace bytes at all. Over the
        // threshold, the deep link is the transport: Perfetto fetches
        // from this server itself, so nothing is materialised in this
        // page and nothing is structured-cloned across the boundary.
        const size = await tracedSize(url, {});
        if (size !== null && size > inlineMax) {
          // `UX-314`: only when Perfetto is actually allowed to fetch
          // it. Navigating the tab to a link its CSP will refuse loses
          // the trace into an empty Perfetto and says nothing - which
          // is the failure this whole path existed to avoid.
          if (fetchable) {
            tab.location = deepLink(absolute.href);
            status.textContent =
              `${(size / 1048576).toFixed(1)} MiB — over the ` +
              `${(inlineMax / 1048576).toFixed(0)} MiB this page will copy, ` +
              `so Perfetto is fetching it from here directly.`;
            return;
          }
          tab.close?.();
          status.textContent =
            `${(size / 1048576).toFixed(1)} MiB — over the ` +
            `${(inlineMax / 1048576).toFixed(0)} MiB this page will copy, ` +
            `and ui.perfetto.dev may not fetch ${absolute.origin} ` +
            `(its own connect-src allows https, 127.0.0.1:9001 and ` +
            `localhost:8080 only). Re-run with --port 8080 and open ` +
            `${PERFETTO_FRIENDLY_URL} — or save the trace below and drag ` +
            `it into ui.perfetto.dev.`;
          return;
        }
      }
      // The tab opened above is handed over rather than closed and
      // reopened: a second `window.open` after an `await` is the
      // pop-up a browser blocks (`UX-198`).
      const { bytes } = await handOff(url, "bga timeline",
                                      tab ? { tab } : {});
      status.textContent = `sent ${(bytes / 1024).toFixed(1)} KiB`;
    } catch (error) {
      tab?.close?.();
      status.textContent = String(error.message ?? error);
    }
  });
}

// UX-195: inline first, fetch second - one code path, so the exported
// file and the served page cannot render differently. `bga view
// --export` writes the same payloads into `<script
// type="application/json">` blocks; everything below is identical
// either way, which is the point.
export function inlined(name) {
  const node = document.getElementById(`bga-${name}`);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent);
  } catch (error) {
    return null;
  }
}

/**
 * `UX-334`: does this page have that payload, without asking for it.
 *
 * `compare`, `store` and `store-aggregate` are optional by design -
 * a first run has no predecessor, a run outside a project has no
 * store - and the page used to discover that by fetching each one and
 * catching the 404. Three console errors on every boot of every served
 * report, which is three lines of noise that a real error has to be
 * noticed among. The manifest is published by `bga view` on both sides
 * (`_offered` in `bga_view.py`), so the question is answerable locally.
 *
 * A run document with no `payloads` key predates this and gets the old
 * behaviour: probe, and treat a failure as absence. An export made by
 * an older `bga view` and opened in a newer page still renders.
 */
export function offered(run, name) {
  if (inlined(name) !== null) return true;
  const listed = run?.payloads;
  if (!Array.isArray(listed)) return true;
  return listed.includes(name);
}

/**
 * An optional payload: null when the manifest says it is not here, and
 * null when it is here but will not parse. Never a thrown error and
 * never a request the manifest already answered.
 */
export async function optional(run, name) {
  if (!offered(run, name)) return null;
  return load(name, null).catch(() => null);
}

export async function load(name, fallback = null) {
  const here = inlined(name);
  if (here !== null) return here;
  try {
    const response = await fetch(`${name}.json`);
    if (!response.ok) throw new Error(String(response.status));
    return await response.json();
  } catch (error) {
    if (fallback !== null) return fallback;
    throw error;
  }
}

// The trace is a data: URL in an export and a served path otherwise.
// `handOff` fetches whichever it is given; `fetch` handles data: URLs,
// so the Perfetto button works from `file://` with no server at all.
/**
 * `UX-204`: hand the timeline over with a title that says why.
 *
 * The title is what Perfetto shows in its tab, so a reader with three
 * of these open can tell them apart - which is the whole point of the
 * context travelling.
 */
export function investigate(context) {
  return handOff(traceUrl(), context.title);
}

/**
 * `UX-207` x `UX-204`: an action's investigate button.
 *
 * The action carries `finding_id`, so the context is built from the
 * finding it references rather than invented here - the same linkage
 * `UX-204` asserts in both directions.
 */
export function decisionInvestigation(action, payload) {
  const finding = (payload?.findings ?? []).find(
    (f) => f.id === action.finding_id);
  if (!finding) return null;
  return investigateButton(
    { ...finding, elements: [action.element_uid] }, investigate);
}

export function traceUrl() {
  const node = document.getElementById("bga-trace");
  return node ? node.textContent.trim() : "timeline.json.gz";
}

async function boot() {
  const root = document.getElementById("report");
  try {
    const [payload, schemas, run] = await Promise.all([
      load("report"),
      load("schemas"),
      load("run", {}),
    ]);
    document.getElementById("run-name").textContent = run.name ?? "bga";
    document.getElementById("run-path").textContent = run.run ?? "";
    // UX-255: what qualifies the run, beside what names it. A report is
    // usually read by someone it was sent to, and "which bga measured
    // this" (UX-249) is the first thing that decides whether the rest
    // is worth reading. Absent on a run written before the stamp
    // existed, and absent is shown as absent rather than guessed.
    stampHeader(document, payload);
    document.title = `bga — ${run.name ?? "report"}`;
    // UX-204: the investigate buttons exist only when there is a
    // timeline to investigate - `UX-194`'s dead-button rule, applied to
    // ten more buttons than it was written for. Passed in rather than
    // reached for, so `render` stays a pure function of what it is
    // given.
    render(payload, schemas[payload.schema], root,
           run.has_timeline ? investigate : null);
    // UX-196: the three views, each only when its payload is there.
    //
    // UX-203: from the *compare* document, which is what `renderBand`
    // has always needed - it reads `baseline_band` and
    // `candidate.total_duration_us`, neither of which an analyze
    // document has. Handing it `payload` meant it returned null every
    // time, so the band had never rendered for any user. `bga view`
    // now serves the comparison against the run before this one.
    const comparison = await optional(run, "compare");
    const band = comparison && contained(
      document, "band", "compare.json", () => renderBand(comparison));
    if (band) root.append(band);
    // UX-221: and which elements put the candidate where the band says
    // it is. The band states the verdict, this states the cause, and
    // `chapters.js` is what puts them in that order - see the note on
    // `renderDecision` below.
    const culprits = comparison && contained(
      document, "culprits", "compare.json",
      () => renderCulprits(comparison));
    if (culprits) root.append(culprits);

    // UX-202: the overview above the sections, and the evidence header
    // above even that - what the capture can support, before any
    // number is believed. Prepended in reverse so evidence ends up
    // first.
    // UX-206: the chain drawn, hung off the overview's execution
    // segment - the "where did the time go" spine, as a list with
    // widths rather than a graph layout problem.
    const chain = contained(document, "critical_path", "report.json",
                            () => renderCriticalPath(payload));
    if (chain) root.append(chain);

    // UX-219: the horizon as a plan rather than a five-column table.
    // Placed with the chain, because "what is the path" and "what does
    // fixing it buy" are the same question one step apart.
    const horizon = contained(document, "horizon", "report.json",
                              () => renderHorizon(payload));
    if (horizon) root.append(horizon);

    // UX-230: and the same plan with checkboxes. A prefix of the
    // published sequence is read from the payload; anything else is
    // asked of the server, which runs the projection `bga whatif`
    // runs. Offline there is no server, so `ask` is null and the
    // section shows the command instead of a control that cannot
    // answer - `UX-199`'s shape for the blast box.
    const whatif = renderWhatIf(payload, served() ? async (elements) => {
      const response = await fetch(
        `whatif.json?elements=${encodeURIComponent(elements.join(","))}`);
      const answer = await response.json();
      if (!response.ok) throw new Error(answer.error ?? response.status);
      return answer;
    } : null, { run: run.name ?? "RUN" });
    if (whatif) root.append(whatif);

    const overview = contained(document, "overview", "report.json",
                               () => renderOverview(payload));
    if (overview) root.append(overview);
    const evidence = contained(document, "evidence", "report.json",
                               () => renderEvidence(payload));
    if (evidence) root.append(evidence);

    // UX-207: **first screen = decision, everything else = evidence.**
    // The reader knows what deserves attention before reading anything
    // that justifies it.
    //
    // **`chapters.js` is the ordering authority** (`UX-286`, and
    // `UX-301` for why this comment exists). It re-sorts the document
    // after everything here has rendered: a section goes in the chapter
    // that names it, and within a chapter in the order the chapter's
    // own list declares. So the calls in this function are plain
    // appends in source order and decide nothing about where a section
    // lands - five of them used to be `prepend`, and mutating one to
    // `append` changed the booted page not at all, which is how round
    // 40 found this. To move a section, edit `CHAPTERS`; a second
    // ordering mechanism here would be a mechanism nothing reads.
    //
    // The refusal banners `renderVerdict` produced are still above even
    // this; a run that is not a measurement says so before it offers a
    // decision drawn from it.
    // UX-226: the store is loaded before the decision panel now,
    // because `UX-227`'s "why this one" fold ends with what happened
    // to that element across the snapshots - and the element sections
    // below need it for the same reason. A run with no store simply
    // gets no history block, which is the same absence a store with no
    // slices produces. Loading earlier moves no DOM: the panel is
    // still placed by `chapters.js` and the sections still appended.
    const store = await optional(run, "store");
    // UX-234: and what the store says about itself as a distribution.
    // A separate document rather than a key of the listing: one row
    // per snapshot and one row per host class are different shapes,
    // and a page with no aggregate simply draws no band.
    const aggregate = await optional(run, "store-aggregate");
    const decision = contained(document, "decision", "report.json", () =>
      renderDecision(payload,
      run.has_timeline ? (action) => decisionInvestigation(action, payload) : null,
      // UX-218: the clipboard helper, passed in so `views.js` keeps
      // having no dependency on `tables.js`.
      copy,
      // UX-227: the store and the schema, for the history line and the
      // verdict shapes inside each "why this one" fold.
      { store, schema: schemas[store?.schema] }));
    if (decision) root.append(decision);
    // UX-216: one section per element the report discusses, appended
    // after everything that names an element has been drawn - the
    // cross-reference is read off the rendered document, so a section
    // added later joins it with no edit here.
    for (const node of renderElementSections(payload, root, {
      quantity,
      investigate: run.has_timeline
        ? (uid) => investigateButton({ title: `bga: ${uid}`, element: uid },
                                     investigate)
        : null,
    })) {
      if (store) {
        const uid = node.getAttribute?.("data-element");
        if (uid) {
          // Per element, so one element's malformed history costs that
          // element's line rather than every element's section.
          node.append(contained(
            document, `element_history:${uid}`, "store.json",
            () => renderElementHistory(store, uid, schemas[store.schema])));
        }
      }
      root.append(node);
    }
    // UX-212: the schema, so the trend draws the shape the *contract*
    // assigns each verdict. UX-234: and the distribution the points
    // came from, drawn behind them from published figures only.
    const trend = store && contained(
      document, "store_trend", "store.json",
      () => renderTrend(store, schemas[store.schema], aggregate));
    if (trend) root.append(trend);
    // UX-199: the blast box is a *transport* - it asks the server. An
    // export is a `file://` document with no server, so the box could
    // never answer there and shipped as a control that always errors.
    // Hidden in that mode, with the command to run instead.
    // UX-285: and placed beside `resource_blast`/`findings` rather than
    // appended, so the control sits where the question is asked.
    if (served()) {
      root.append(renderBlastSearch(async (target) => {
        const response = await fetch(
          `blast.json?target=${encodeURIComponent(target)}`);
        const answer = await response.json();
        if (!response.ok) throw new Error(answer.error ?? response.status);
        return answer;
      }));
    } else {
      // `UX-348`: the same capability as a command this run can run,
      // read from the published `next_steps` - not `<target> <run>`
      // under a rail entry reading "Blast offline". `UX-286` files it
      // beside `resource_blast` in "What if I change this?", which is
      // where the served page offers to compute it.
      root.append(renderBlastOffline(payload, copy, el));
    }

    // UX-199: the export used to strip the link to the questions page
    // and leave nothing behind it - functionality lost rather than
    // moved. They are inlined here instead, from the same module
    // `sql.html` renders, so the two cannot drift.
    if (!served()) {
      // `UX-348`: the section says how to open the timeline, so it has
      // to know whether there is one - the same fact `UX-194`'s
      // dead-control rule gates the header button on.
      root.append(renderQuestions(el, { hasTimeline: Boolean(run.has_timeline) }));
    }
    // UX-194: only when there is a timeline behind it. A dead button is
    // worse than no button - the run that has no Plane 2 log is exactly
    // the run whose user would spend a minute wondering what broke.
    if (run.has_timeline) wireTheHandoff(run);

    // UX-286: the chapters, over everything that has been appended -
    // the element sections (`UX-216`), the trend, the inlined
    // questions. Grouping is the last thing done to the document and
    // the first thing the rail reads, so the `toc` below lists
    // chapters rather than thirty-one fragments.
    //
    // This is also what puts `UX-285`'s identity blocks at the foot and
    // the blast control beside `resource_blast`: they are chapters
    // ("Which run is this?", "What if I change this?") and the table
    // declares their order. That item shipped `placeIdentityLast` and
    // `placeBlast` a day earlier; both are gone, because two mechanisms
    // deciding one order is how a page ends up with an order nobody can
    // predict.
    chapters(root, document, payload);

    // UX-199: navigation, last, over whatever was rendered. Nothing
    // above changes; a reader who ignores all of it sees the same
    // report in the same order.
    anchor(root);
    // UX-302: before `collapsible`, so the collapse caret ends up first
    // in the heading - `collapsible` prepends and this appends.
    jsonToggles(root, { document });
    // `UX-355`: the rail's pair drives both fold layers. It used to
    // drive only the sections, which are default-open - so "Expand all"
    // did nothing at all from a fresh load, and "Collapse all" shut the
    // sections of the one open chapter and left the rest folded.
    const controls = collapsible(root, {
      document, storage: served() ? safeStorage() : null,
      enclosing: (open) => setAllOpen(root, open) });
    const contents = toc(root, { document, controls });
    if (contents) {
      // UX-223: which actions this run can honestly offer. UX-194's
      // rule - an affordance whose precondition is absent is not shown
      // at all, rather than shown and dead.
      wireJumpBox(contents, root, payload, {
        hasTimeline: Boolean(run.has_timeline),
        hasBlast: location.protocol === "http:"
               || location.protocol === "https:",
      });
      // UX-211: the link that shows what I was looking at. Beside the
      // contents, because that is where the reader already goes to
      // reach for a section anchor.
      const share = el("button", { type: "button", class: "copy-view" },
                       "Copy link to this view");
      share.addEventListener("click", () => {
        copy(viewLink(root, location));
        share.textContent = "\u2713 copied";
        setTimeout(() => { share.textContent = "Copy link to this view"; }, 1200);
      });
      contents.append(el("p", { class: "toc-controls" }, share));
      // UX-254/UX-255: after the heading, not before it. This used to
      // be `insertBefore(contents, document.body.firstChild)`, which
      // put 573px of navigation above the run's own name - so the page
      // opened on a table of contents and the reader scrolled to find
      // out which build they were looking at. DOM order is the reading
      // order a screen reader and a `Tab` key follow, so it is fixed
      // here rather than only in the grid.
      // `UX-317`: after the actions group, which is now its own block
      // below the header - so the reading order a screen reader and a
      // `Tab` key follow is identity, then how to open the timeline,
      // then the rail, then the report. That is the order this had
      // before the group moved out of the header, kept deliberately.
      const heading = document.querySelector("#actions-group")
        ?? document.querySelector("header");
      if (heading && typeof heading.after === "function") {
        heading.after(contents);
      } else {
        document.body.insertBefore(contents, document.body.firstChild);
      }
      document.body.setAttribute("data-has-toc", "true");
      foldOnNarrow(contents, document);
    }

    // UX-278: any element the page can name can be inspected.
    //
    // The detail sections above are capped (`UX-187`), and the cap is
    // right - rendering 1,202 blocks eagerly is what it exists to
    // prevent. What was wrong is that an Inspect anchor pointing past
    // the cap resolved to nothing: measured on the 1,202-element run,
    // 24 blocks for 1,202 elements and two anchors that consumed the
    // click and did nothing. A missing magnifier says "not here"; a
    // dead one says the page is broken.
    //
    // So the block is built when the anchor is followed, from the
    // payload the page already holds - no request, no second analyzer,
    // and Direction 7's boundary untouched, because it renders
    // published values rather than deriving any.
    //
    // Two ways in, because a reader arrives both ways: a click on an
    // Inspect anchor inside the report, and a pasted `#element-…` on a
    // fresh load or a `hashchange`.
    const elementOptions = {
      quantity,
      investigate: run.has_timeline
        ? (uid) => investigateButton({ title: `bga: ${uid}`, element: uid },
                                     investigate)
        : null,
    };
    const openElement = (id) => {
      if (!id || !id.startsWith("element-")) return null;
      if (root.querySelector(`[data-section="${id}"]`)) return null;
      const uid = uidForAnchor(payload, id);
      if (!uid) return null;
      const built = ensureElementSection(payload, root, uid, elementOptions);
      // UX-286: into its chapter, not onto the end of the document.
      // `UX-278` builds this block when the anchor is followed, which
      // is long after `boot` grouped everything - appended to the root
      // it would land below the chapter that closes the page.
      return built ? fileInChapter(root, built, document) : built;
    };
    root.addEventListener("click", (event) => {
      const link = event?.target?.closest?.("a.inspect");
      const href = link?.getAttribute?.("href") ?? "";
      if (href.startsWith("#")) openElement(href.slice(1));
    });

    // UX-347: an anchor into a folded chapter opens it. One delegated
    // listener on the document rather than a handler per link: the
    // rail is one source of `#section` links, the palette another, the
    // findings' own "next step" a third, and a pasted link is a fourth
    // with no click at all. What they share is the target.
    const revealAnchor = (id) => {
      if (!id) return null;
      const node = document.getElementById(id)
        ?? root.querySelector?.(`[data-section="${id}"]`);
      return node ? revealChapter(node) : null;
    };
    document.addEventListener?.("click", (event) => {
      const href = event?.target?.closest?.("a[href^=\"#\"]")
        ?.getAttribute?.("href");
      if (href && href.length > 1) revealAnchor(href.slice(1));
    });
    window.addEventListener?.("hashchange", () => {
      const built = openElement(splitHash(location.hash).anchor);
      revealAnchor(splitHash(location.hash).anchor);
      // The browser has already decided there was nothing to scroll to,
      // so the section it just missed has to say where it is.
      built?.scrollIntoView?.();
    });
    openElement(splitHash(location.hash).anchor);
    // A pasted `#confidence` lands on a document whose chapters are
    // folded, and the browser has already tried to scroll before this
    // runs - so the reveal is followed by the scroll it could not do.
    revealAnchor(splitHash(location.hash).anchor)
      && document.getElementById(splitHash(location.hash).anchor)
        ?.scrollIntoView?.();

    // UX-211: the fragment last, over the finished document - it drives
    // the controls the way a reader would, so there is no second path
    // that can disagree with the first. A hash-free load does nothing
    // at all here.
    // UX-222 and UX-225 before the fragment, so a link carrying a
    // focus or a set of marks lands on a document whose controls are
    // already live.
    // UX-228: the payload and the store go in, because focusing an
    // element now assembles the evidence about it rather than only
    // dimming the rest. A served page with neither still focuses -
    // the panel is absent, not broken.
    wireFocusAndMarks(root, document, { payload, store, schema: schemas[store?.schema] });
    applyView(root, splitHash(location.hash).query);
    wireViewState(root, { location, history: window.history });
  } catch (error) {
    // UX-335: this is the *load* failure - a report that will not parse
    // is not a report, and there is nothing to render around. It is
    // marked as such because a section's contained failure wears the
    // same refusal styling: both say "this did not work", and only one
    // of them means the page is empty. A reader's stylesheet and a
    // guard both need to tell them apart, and `.verdict.refused` alone
    // could not.
    root.replaceChildren(el("div", { class: "verdict refused",
                                     "data-page-failed": "true" },
      el("h2", {}, "Could not load this run"),
      el("p", {}, String(error))));
  }
}

// `UX-337`: `?.` rather than a bare call. This is the module's only
// top-level statement, and a harness that imports `app.js` for one
// function - which is now every test reaching the formatters and
// the table machinery through one namespace - shims the `document`
// its own assertions need and no more. `served()` is guarded for
// the same reason and says so; a throw here happens at *import*, so
// it takes the test with it rather than one assertion.
if (typeof document !== "undefined" && document.getElementById?.("report")) {
  boot();
}

/**
 * UX-222 and UX-225: one delegated listener for both.
 *
 * Every control is a button carrying the element it acts on, so a view
 * that renders element rows later earns the same behaviour with no
 * second handler - the same reason `data-element` was worth putting
 * everywhere in UX-216.
 *
 * Neither of these filters or re-renders anything. Focus adds
 * `data-dimmed` and `data-unfocused`; marks add `data-mark`. The
 * document underneath is unchanged, which is what keeps Ctrl-F, the
 * export and the anchors honest.
 */
export function wireFocusAndMarks(root, doc, options = {}) {
  const refresh = () => {
    // UX-228 added a third transient node, and it joins the same
    // removal set on purpose: everything focus adds is keyed by
    // `data-role`, so unfocusing leaves the document byte-identical to
    // never-focused. That property is asserted, not assumed.
    for (const stale of [...(root.querySelectorAll?.(
        "[data-role=focus-bar],[data-role=mark-summary],"
        + "[data-role=focus-investigation]") ?? [])]) {
      stale.parentNode?.removeChild?.(stale);
    }
    const uid = focusedElement(root);
    if (uid && options.payload) {
      // UX-228: the evidence about this element, assembled from
      // published objects. Prepended *under* the bar, so the reader
      // sees what they focused and then what is known about it.
      const investigation = renderInvestigation(options.payload, uid, options);
      if (investigation) root.prepend?.(investigation);
    }
    if (uid) root.prepend?.(renderFocusBar(uid, { onClear: () => {
      clearFocus(root); refresh(); notify();
    }}));
    const summary = renderMarkSummary(readMarks(root), { onClear: () => {
      applyMarks(root, {}); refresh(); notify();
    }});
    if (summary) root.prepend?.(summary);
  };
  // The fragment listens for these already; firing one event rather
  // than writing the hash here keeps UX-211 the only writer.
  const notify = () => root.dispatchEvent?.(
    new Event("change", { bubbles: true }));

  root.addEventListener?.("click", (event) => {
    const node = event.target?.closest?.("[data-focus-element],[data-mark-element]");
    if (!node) return;
    const focusUid = node.getAttribute("data-focus-element");
    if (focusUid) {
      applyFocus(root, focusedElement(root) === focusUid ? null : focusUid);
      refresh();
      notify();
      return;
    }
    const markUid = node.getAttribute("data-mark-element");
    const value = node.getAttribute("data-mark-value");
    const marks = readMarks(root);
    if (marks[markUid] === value) delete marks[markUid];
    else marks[markUid] = value;
    applyMarks(root, marks);
    refresh();
    notify();
  });

  // Escape clears the focus - and only the focus. The marks are a
  // decision the reader made; a stray keystroke must not discard them.
  doc?.addEventListener?.("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!focusedElement(root)) return;
    clearFocus(root);
    refresh();
    notify();
  });
  return refresh;
}
