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

import { handOff, deepLink, tracedSize, openTab, perfettoCanFetch,
         PERFETTO_FRIENDLY_URL } from "./perfetto.js";
import { renderBand, renderCulprits, renderElementHistory, renderHorizon,
         renderTrend, renderBlastSearch,
         renderOverview, renderEvidence,
         renderCriticalPath, renderBlastTree,
         renderDecision, renderElementSections, elementAnchor,
         ensureElementSection, uidForAnchor,
         INCOMPLETE, renderProvenance, renderInvestigation, renderWhatIf } from "./views.js";
import { anchor, collapsible, toc, jumpTargets, matches,
         paletteResults } from "./nav.js";
import { chapters, fileInChapter } from "./chapters.js";
// UX-302: the second of §1's two deliberate raw-JSON sites - the one
// the reader asks for, per section, because pasting a section into an
// issue is what people do with a report.
import { jsonToggles, recordSource } from "./rawjson.js";
import { applyView, splitHash, viewLink, wireViewState } from "./viewstate.js";
import { applyFocus, applyMarks, clearFocus, focusedElement, readMarks,
         renderFocusBar, renderMarkSummary } from "./focus.js";
import { copyButton, renderQuestions } from "./questions.js";
import { investigationFor } from "./trace_context.js";
import { parseThreshold, applyFilters, badgeText, rowJson, cellText,
         copy, applyTopN, presetColumns, applyPreset,
         rowsMarkdown } from "./tables.js";

// UX-302: the style guide's §1 dispatch table, which decides *which*
// control draws a structured value. The controls live here; the choice
// between them lives there, so that "raw JSON unless deliberate" is a
// rule with one enforcement point rather than a habit.
import { CONTROLS, UNMAPPED, classify, noteUnmapped, depthSentence, shapeOf } from "./shapes.js";
// UX-303: §2's two drawings. They import nothing and take their
// formatter, so the quantity table stays here and the geometry stays
// there.
import { sparkline, strip, columnStrip, GRADE_ANNOTATION, GRADE_EXHIBIT }
  from "./drawings.js";
import { enterTableFocus, focusedTable, leaveTableFocus, registerFocusTarget }
  from "./tablefocus.js";

const QUANTITY = "bga:quantity";
const SEVERITY = "bga:severity";
const COLUMNS = "bga:columns";
const DIRECTION = "bga:direction";
// UX-303: the two hints §2 introduces. A value draws as a shape because
// a schema declared it one, never because it looked numeric.
const SERIES = "bga:series";
const DISTRIBUTION = "bga:distribution";
// UX-209: the question a section answers, and which part of the
// argument it belongs to. UX-208: what a column's values *are*.
const QUESTION = "bga:question";
// UX-289: the named views over a table, declared in the schema.
const PRESETS = "bga:presets";
const RAIL = "bga:rail";
const ROLE = "bga:role";

// ---------------------------------------------------------------- format

export function duration(microseconds) {
  if (microseconds === null || microseconds === undefined) return "—";
  const s = microseconds / 1e6;
  if (s < 1) return `${Math.round(microseconds / 1000)} ms`;
  if (s < 90) return `${s.toFixed(1)} s`;
  const m = s / 60;
  if (m < 90) return `${m.toFixed(1)} min`;
  return `${(m / 60).toFixed(1)} h`;
}

export function bytes(value) {
  if (value === null || value === undefined) return "—";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

export function quantity(value, kind) {
  if (value === null || value === undefined) return "—";
  switch (kind) {
    case "duration_us": return duration(value);
    case "bytes": return bytes(value);
    case "share": return `${(value * 100).toFixed(1)}%`;
    // UX-201: already 0..100. Multiplying again is how a 42% cpu_pct
    // rendered as "4200.0%".
    case "percent": return `${value.toFixed(1)}%`;
    // UX-201: and megabytes are not a byte count - `peak_rss_mb: 512`
    // rendered as "512 B" through the `_mb`-means-bytes guess.
    case "megabytes": return bytes(value * 1024 * 1024);
    // UX-215: and a kilobyte count is not a byte count either. Same
    // error one order down, and `peak_rss_kb: 157200` would have read
    // as "154 KB" where the truth is 153 MB.
    case "kilobytes": return bytes(value * 1024);
    case "seconds": return duration(value * 1e6);
    case "ratio": return `${value.toFixed(2)}×`;
    // UX-275: a count is usually whole and renders as itself. The
    // first fractional one published - `cores_busy`, an average over
    // the run - arrived as "1.603977885512677" on the page, fifteen
    // digits of a number measured to two. Whole counts are untouched.
    case "count": return Number.isInteger(value) ? String(value)
      : String(Math.round(value * 100) / 100);
    default:
      return typeof value === "number"
        ? String(Math.round(value * 1000) / 1000) : String(value);
  }
}

// A key with no hint still wants a sensible unit. This is a *fallback*,
// not a second vocabulary: the schema wins wherever it speaks, and this
// only runs for keys nested below the top level, which the schemas
// deliberately do not describe (see bga/schemas.py's docstring).
export function guessQuantity(key) {
  if (/_us$/.test(key)) return "duration_us";
  if (/_bytes$/.test(key) || /_mb$/.test(key)) return "bytes";
  if (/(share|ratio_pct|_pct)$/.test(key)) return "share";
  if (/_seconds$/.test(key)) return "seconds";
  if (/_count$/.test(key)) return "count";
  return null;
}

export function title(key) {
  return key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

/**
 * `UX-209`: the heading is the question the section answers, where the
 * schema declares one - and `title(key)` where it does not.
 *
 * Declared in `bga/schemas.py` rather than here, for the reason every
 * other hint is: the text renderer and the TOC read the same field, so
 * three surfaces cannot name one section three ways.
 */
export function heading(key, hint = {}) {
  return { question: hint[QUESTION] ?? null, label: hint[QUESTION] ?? title(key),
           subtitle: hint[QUESTION] ? key : null,
           rail: hint[RAIL] ?? "raw" };
}

/** `UX-208`: the column that holds element uids, or null. */
/** An element uid as an anchor fragment. Dots are legal in an `id`
 *  but awkward in a selector, so the jump target is normalised once. */
export function cssId(uid) {
  // UX-216: the same spelling `views.js` gives the section it lands
  // on. Delegated rather than duplicated - a link and its target
  // spelling drifting apart *is* the defect this item exists to fix,
  // and two copies of the expression is how that happens again.
  return elementAnchor(uid);
}

export function sectionHead(key, hint = {}) {
  const info = heading(key, hint);
  const node = el("h2", {}, info.label);
  if (info.subtitle) {
    node.append(el("span", { class: "section-key muted" }, info.subtitle));
  }
  return node;
}

export function elementColumn(specs = []) {
  const found = specs.find((spec) => spec.role === "element");
  return found ? found.key : null;
}

// ---------------------------------------------------------------- render

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (name === "class") node.className = value;
    // `UX-317`: **any hyphenated name is an attribute**, not a
    // property. It was `data-` only, so `el("input", {"aria-label": …})`
    // assigned a JS property a browser reflects nowhere - measured in
    // Chromium 141: `node["aria-label"] = "filter rows"` leaves
    // `getAttribute("aria-label")` at `null`, and a
    // `[aria-expanded="true"]` selector matches nothing. Five
    // `aria-label`s in this file had been invisible to assistive
    // technology and to CSS since they were written; the sixth
    // (`UX-317`'s own `aria-expanded`) is what surfaced it, because it
    // is the first one a *guard* reads back.
    else if (name.includes("-")) node.setAttribute(name, value);
    else node[name] = value;
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined) continue;
    node.append(child.nodeType ? child : String(child));
  }
  return node;
}

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
      key, hintsOf(childNode(node, key)).description);
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
  return el("details", { class: "evidence-fold", "data-fold": "evidence" },
            el("summary", {}, `${scalars.length} measurements`), list);
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

/**
 * `bga:columns` v2: an entry is a name, or an object saying what the
 * column *is*.
 *
 * UX-201: `renderTable` decided numeric-ness by sampling row values and
 * the sorter guessed from the same sample, so a column of numeric-
 * looking strings sorted as numbers and a column that should never be
 * sorted was sortable anyway. Declared beats sampled.
 */
export function columnSpecs(hint, rows, node) {
  const declared = hint[COLUMNS];
  const present = (key) => rows.some((r) => key in (r ?? {}));
  const itemNode = node?.items;
  const fallback = () => [...new Set(rows.flatMap((r) => Object.keys(r ?? {})))]
    .map((key) => ({ key }));
  const specs = declared && declared.length
    ? declared.map((c) => (typeof c === "string" ? { key: c } : { ...c }))
              .filter((c) => present(c.key))
    : fallback();
  return specs.map((spec) => {
    const child = childNode(itemNode, spec.key);
    const quantityName = spec.quantity ?? hintsOf(child)[QUANTITY]
      ?? guessQuantity(spec.key);
    return {
      ...spec,
      title: spec.title ?? title(spec.key),
      quantity: quantityName,
      // Numeric-ness is declared by carrying a quantity, or observed
      // only when nothing declared anything.
      numeric: quantityName
        ? true : rows.some((r) => typeof r?.[spec.key] === "number"),
      sortable: spec.sortable !== false,
      description: spec.description ?? hintsOf(child).description ?? null,
    };
  });
}

// UX-267: how a nested value is drawn, chosen by its measured shape.
//
// Every object and every array that was not an array-of-objects used to
// render as `<details><summary>object</summary><pre>{raw JSON}</pre>`.
// One branch, four complaints: a summary that says `object` so a reader
// clicks each one to find out what it is, a wall of `JSON.stringify`
// behind it, arrays read as JSON, and nothing searchable or bounded.
//
// Measured on a served 44-element run: 34 such cells, 32,393 characters
// of `<pre>`, the largest 8,191 - and `signals.blast_radius` scales to
// ~224,000 characters at 1,202 elements behind a label saying `object`.
//
// **The rule is width, not depth.** The document is 7 levels deep and
// three nodes live at level 7; the mass is at 3-4 and the pain is the
// level-2 maps with one key per element (Direction 12).
//
// **The fold is not the defect.** A spike replaced folds with tables
// and took the document from 13.8 screens to 35.5; row-bounding got it
// to 32.3 and a bounded height to 20.8. Keeping the fold and labelling
// it `Blast radius · 44 entries` gives zero raw JSON at 14.9.
export const OBJECT_INLINE_FIELDS = 4;
export const ARRAY_INLINE_ITEMS = 6;

// `UX-277`: how far the rule recurses *inside a cell*.
//
// The rule is width, not depth - but that governs which of the three
// renderings a value gets, not how many tables may nest inside one
// another. A table cell holding a table holding a table is three sets
// of column headers and three sets of tools for one value, and the
// document this page renders is seven levels deep.
//
// Two is where it stops: a cell may hold a table, and that table's
// cells may hold one more. Past that the value is folded as text -
// still labelled, still bounded, still one click from the whole thing,
// which is what `renderText` already does for a long string.
export const CELL_NEST_LIMIT = 2;

/** `{k: v}` as one line - no click, because there is nothing to hide. */
function inlineObject(value, node) {
  const parts = [];
  for (const [name, member] of Object.entries(value)) {
    const kind = quantityFor(childNode(node, name), name);
    parts.push(el("span", { class: "pair" },
      el("span", { class: "pair-key" }, `${title(name)} `),
      el("span", { class: typeof member === "number" ? "num" : null,
                   "data-raw": member === null ? "" : String(member) },
         member === null ? "—" : quantity(member, kind))));
  }
  return el("span", { class: "inline-object" }, ...parts);
}

/**
 * A map as a bounded, searchable table - the table only, never a
 * section (`buildTable`, not `renderTable`).
 */
function mapTable(key, rows, hint, node, nested, depth = 0, path = key) {
  let declared = hint;
  if (!nested) {
    // A `{name: number}` map's value column has to *declare* a
    // quantity: `presetColumns` selects on the declaration, so without
    // this the table gets no `Top N` control and therefore no bound
    // (`UX-262`).
    const measure = hintsOf(node)[QUANTITY] ?? guessQuantity(key) ?? "count";
    declared = { ...hint, [COLUMNS]: [
      { key: "key", title: "name" },
      { key: "value", title: title(key), quantity: measure }] };
  }
  const { table, tools } = buildTable(path, rows, declared, node, depth);
  const box = el("div", { class: "map-table", "data-bounded": "map" },
                 tools, table);
  return box;
}

/**
 * A large value, folded behind a summary that says what it holds.
 *
 * `UX-318` (§3a.1): and **how deep it goes**. "N entries" answered how
 * wide the first level is and said nothing about what is behind it -
 * the field report's unknown rabbit hole. The summary now carries
 * `shapeOf`'s sentence, and the numbers are on the element so a walk
 * can check them against the value rather than against the text.
 */
function folded(label, value, body, path = null) {
  const { levels, rows } = shapeOf(value);
  return el("details", { class: "map",
                         // The payload key this fold holds, so a walk can
                         // check the numbers against the *value* rather
                         // than against the sentence beside them.
                         "data-fold-path": path,
                         "data-levels": String(levels),
                         "data-rows": String(rows) },
            el("summary", {},
               el("span", { class: "map-name" }, label),
               el("span", { class: "map-count muted" },
                  ` · ${depthSentence(value)}`)),
            body);
}

/**
 * The node a table travels as: its box with its own tools, or - for a
 * table that *is* a section - the section.
 *
 * Walked rather than `closest`, so the shim and a browser answer the
 * same thing (`UX-264`'s rule about the instrument).
 */
// `tagName` is upper-case in a browser and whatever `createElement` was
// handed in the shim, so the comparison is folded. The first draft
// compared against `"SECTION"` and every breadcrumb read "the report".
const isSection = (node) =>
  String(node?.tagName ?? "").toLowerCase() === "section"
  && node.getAttribute?.("data-section");

function movableBox(table) {
  let at = table.parentNode;
  let section = null;
  while (at) {
    const klass = at.className || at.getAttribute?.("class") || "";
    if (String(klass).split(" ").includes("map-table")) return at;
    if (!section && isSection(at)) section = at;
    at = at.parentNode;
  }
  return section ?? table.parentNode ?? table;
}

/** The section a table came from, for the breadcrumb's "back to …". */
function breadcrumbFor(table) {
  let at = table.parentNode;
  while (at) {
    if (isSection(at)) return title(at.getAttribute("data-section"));
    at = at.parentNode;
  }
  return "the report";
}

/**
 * `UX-318` (§3a.3): the expand control on a capped or nested table.
 *
 * It registers **at click time**, because that is when the box it has
 * to move is in the document: a table is built before it is placed, and
 * a registry filled at build time would remember a detached parent.
 */
function expandTableControl(table, depth) {
  const path = table.getAttribute?.("data-table") ?? "table";
  const button = el("button", {
    type: "button", class: "expand-table", "data-expand": path,
    title: depth > 0
      ? "Open this nested table full width, with a way back"
      : "Open this table full width, with a way back",
  }, "Expand");
  const notify = (root) => root?.dispatchEvent?.(
    new Event("change", { bubbles: true }));
  button.addEventListener?.("click", () => {
    const root = document.getElementById?.("report");
    if (focusedTable(root) === path) {
      leaveTableFocus(root);
    } else {
      registerFocusTarget(path, {
        label: title(path.split(".").pop() ?? path),
        breadcrumb: breadcrumbFor(table), node: movableBox(table) });
      enterTableFocus(root, path, { onLeave: () => notify(root) });
    }
    notify(root);
  });
  return button;
}

/**
 * `UX-318` (§3a.3): "expand this table" - the user's enlarge
 * affordance, and §3a's route out of a rabbit hole, as one control.
 *
 * The node is rendered **once, here, detached**, and handed to the
 * registry: entering focus moves it into the focus section and leaving
 * puts it back, so the table a reader expands is *the* table with its
 * filter, sort and Top-N exactly as they were left. A second render
 * would be a second answer.
 */
function expandControl(path, label, render, breadcrumb = "the report") {
  const button = el("button", {
    type: "button", class: "expand-table",
    "data-expand": path,
    // `UX-279`: the noun and what it does, before it is pressed.
    title: `Open ${label} full width, with a way back`,
  }, `Expand ${label}`);
  let made = null;
  // The fragment listens for `change` on the report root already, so
  // firing one event rather than writing the hash here keeps `UX-211`
  // the only writer of the URL.
  const notify = (root) => root?.dispatchEvent?.(
    new Event("change", { bubbles: true }));
  button.addEventListener?.("click", () => {
    const root = document.getElementById?.("report");
    if (!made) {
      made = el("div", { class: "focus-body" }, render());
      registerFocusTarget(path, { label, breadcrumb, node: made });
    }
    if (focusedTable(root) === path) leaveTableFocus(root);
    else enterTableFocus(root, path, { onLeave: () => notify(root) });
    notify(root);
  });
  return button;
}

/**
 * `UX-267`'s renderer. Exported so a guard can drive it directly.
 *
 * Returns a **cell**: never a `<section>`, because `nav.js` finds
 * sections at any depth and one inside a table cell becomes a phantom
 * entry in the table of contents.
 */
export function renderStructured(key, value, hint = {}, node = undefined,
                                 depth = 0, path = key) {
  const count = Array.isArray(value)
    ? value.length : Object.keys(value).length;
  if (!count) return el("span", { class: "muted" }, "none");
  // `UX-302`: one dispatch, and it is the style guide's table. Every
  // branch below is a row of §1 - the branch is *chosen* there and
  // *drawn* here, so a shape the guide does not cover cannot quietly
  // acquire a rendering by someone adding an `if` to this function.
  const declared = hintsOf(node);
  const control = classify(value, {
    columns: declared[COLUMNS] ?? null,
    series: declared[SERIES] ?? null,
    distribution: declared[DISTRIBUTION] ?? null,
    depth, nestLimit: CELL_NEST_LIMIT,
    inlineFields: OBJECT_INLINE_FIELDS, inlineItems: ARRAY_INLINE_ITEMS,
  });
  // `UX-303`: a series and a distribution draw as their shape, at any
  // depth - the nesting cap is about tables inside tables, and a
  // sparkline is one element wide however deep it sits.
  //
  // `UX-316` grades them, and the grade is a property of *why the
  // drawing is here* rather than of where it landed: a value the schema
  // declares a series or a distribution renders as that drawing because
  // the drawing **is** the value - it is the answer, not a mark beside
  // one, wherever the nesting puts it. The two annotation-grade
  // drawings in this viewer are the two that annotate something else:
  // `columnStrip` beside a table, and `views.js`'s per-element history
  // beside an element's row. Neither comes through here.
  if (control === CONTROLS.SPARKLINE) {
    return sparkline(value, {
      unit: String(declared[SERIES]), grade: GRADE_EXHIBIT,
      format: (n) => quantity(n, quantityFor(node, key)),
    });
  }
  if (control === CONTROLS.DENSITY_STRIP) {
    return strip(value, {
      countKey: String(declared[DISTRIBUTION]), grade: GRADE_EXHIBIT,
      format: (n) => quantity(n, quantityFor(node, key)),
    });
  }
  // `UX-277`: past the nesting limit a value is folded as text rather
  // than as a third table. Deliberately *not* silent - the fold carries
  // the label and the count, so the reader knows what is behind it.
  //
  // `UX-302` adds the second way in: a shape §1 has no row for. It gets
  // the same fold - the reader is never shown nothing - and a console
  // warning naming the path, because the gap is a design task and an
  // unnoticed one stays open.
  if (control === CONTROLS.FOLD || control === UNMAPPED) {
    if (control === UNMAPPED) noteUnmapped(path, value);
    // `UX-318` (§3a.2): **one nested level renders inline.** Deeper than
    // that the fold does not open in place - it opens in table focus,
    // where the value renders as the tables §1 would have given it, at
    // the content column's full width.
    //
    // Served only, and the export keeps exactly what it had: a fold, its
    // depth, and the whole value one click away. An export is a file
    // somebody scrolls, prints and attaches; a control that rearranges
    // the page has nothing to rearrange there, and `UX-194`'s rule is
    // that an affordance whose precondition is absent is not drawn as a
    // dead one. Nothing about the *meaning* needs the mechanism, which
    // is §3a's own condition on it.
    if (control === CONTROLS.FOLD && served()) {
      return folded(title(key), value,
                    expandControl(path, title(key), () =>
                      renderStructured(key, value, hint, node, 0, path)),
                    path);
    }
    return folded(title(key), value,
                  el("p", { class: "full-text" }, JSON.stringify(value)),
                  path);
  }
  if (Array.isArray(value)) {
    if (control === CONTROLS.INLINE_LIST) {
      return el("span", {}, value.map(String).join(", "));
    }
    if (control === CONTROLS.FOLDED_LIST) {
      const rows = value.map((item, at) => ({ key: String(at), value: item }));
      return folded(title(key), value,
                    mapTable(key, rows, hint, node, false, depth + 1, path),
                    path);
    }
    // `UX-277`: an array of *arrays* - `[["app.bst", 8], …]` - used to
    // reach `Array.prototype.toString` twice and render `app.bst,8,
    // lib-b.bst,4`. It is a table of positional columns, which is what
    // the payload means by it.
    // Positional members get positional names - unless the schema
    // says what they are.
    //
    // `UX-290`: `bga:columns` already declares what an array of
    // *objects* holds; for an array of pairs, entry `i` describes
    // position `i`, which needs no new vocabulary. Where the schema
    // declares them the tuple becomes named columns (and the index
    // column goes, because the element is the identity); where it does
    // not, the fallback stays `#1`/`#2` - honest about being a
    // position, which `C0`/`C1` were not.
    const declared = hintsOf(node)[COLUMNS];
    const tuple = value.every(Array.isArray)
      && Array.isArray(declared)
      && value.every((item) => item.length === declared.length)
      && declared.every((spec) => spec && typeof spec === "object" && spec.key);
    //
    // `UX-302`: three cases, not four. A *mixed* array - some objects,
    // some scalars - used to fall through here and get one row shape
    // per item; §1 has no row for it, so `classify` now returns
    // `UNMAPPED` and it is folded above, with a warning, rather than
    // improvised into a ragged table.
    const rows = value.map((item, at) => (
      tuple
        ? Object.fromEntries(item.map((m, i) => [declared[i].key, m]))
        : Array.isArray(item)
          ? Object.fromEntries([["key", String(at)],
                                ...item.map((m, i) => [`#${i + 1}`, m])])
          : item));
    return folded(title(key), value,
                  mapTable(key, rows, tuple ? { ...hint, [COLUMNS]: declared } : hint,
                           node, true, depth + 1, path),
                  path);
  }
  const entries = Object.entries(value);
  if (control === CONTROLS.INLINE_OBJECT) return inlineObject(value, node);
  const nested = entries.every(([, member]) =>
    member && typeof member === "object" && !Array.isArray(member));
  const rows = entries.map(([name, member]) => (
    nested ? { key: name, ...member } : { key: name, value: member }));
  return folded(title(key), value,
                mapTable(key, rows, hint, node, nested, depth + 1, path),
                path);
}

/**
 * The table and its controls, with **no section around them**.
 *
 * `UX-267`: `renderTable` returns a `<section data-section=…>`, which
 * is right for a top-level view and wrong for a *cell*. A spike that
 * rendered nested maps by calling it put twenty-two sections inside
 * table cells; `nav.js` finds sections with `querySelectorAll` at any
 * depth, so the table of contents listed one of them (`summary`,
 * which is both a map key and the run's own section) twice. Splitting
 * the builder out is the whole fix: a cell gets the table, a view gets
 * the section.
 */
export function buildTable(key, rows, hint = {}, node = undefined,
                           depth = 0) {
  const specs = columnSpecs(hint, rows, node);
  const columns = specs.map((s) => s.key);
  const table = el("table", { "data-table": key });
  const head = el("tr");
  for (const spec of specs) {
    head.append(el("th", {
      class: spec.numeric ? "num" : null,
      scope: "col", "data-column": spec.key,
      "data-sortable": String(spec.sortable),
      title: spec.description ?? null,
    }, spec.title));
  }
  table.append(el("thead", {}, head));
  const body = el("tbody");
  for (const [at, row] of rows.entries()) {
    // UX-292: which row this is, for the view-state key of any table
    // nested inside it. A map table's cells are all in a column called
    // `value`, so the column alone named three tables the same thing.
    // The row's own key is what tells them apart, and it is the name a
    // reader would use for the thing they filtered.
    const rowId = row?.key ?? row?.element_uid ?? String(at);
    const tr = el("tr");
    for (const spec of specs) {
      const column = spec.key;
      const raw = row?.[column];
      const numeric = typeof raw === "number";
      const kind = numeric ? spec.quantity : null;
      // `UX-277`: the leaf every `<td>` in the report goes through.
      //
      // `UX-267` built `renderStructured` and wired it into
      // `renderPairs`, which draws `<dd>` cells. This was never wired
      // to it, so the rule governed one cell type and stopped dead at
      // the other. Measured on the 1,202-element run before the fix:
      // 6 cells of raw JSON, 11 joined arrays over 60 characters, one
      // `[object Object]`, and a widest cell of 14,300 characters -
      // `signals.leaves_detail`, which `CELL_TEXT_CAP` never saw
      // because the cap lives on the path this one bypassed.
      //
      // `data-raw` keeps the *unrendered* value, because sorting,
      // filtering and `Copy shown rows` read it and must never start
      // reading markup.
      const structural = raw !== null && typeof raw === "object";
      // UX-290: a map table's rows are `{key, value}`, so the schema
      // node describing a cell is the one for the *row*, not the one
      // for a column literally called `value`. Resolving by column
      // meant every declaration under an object-valued field was
      // unreachable: the choke-point columns were declared and the page
      // still drew `Element uid` / `Downstream count` from the raw
      // field names, because it looked up `bottleneck.properties.value`.
      const describes = column === "value" && row?.key !== undefined
        ? String(row.key) : column;
      const child = childNode(node, describes);
      tr.append(el("td",
        { class: numeric ? "num" : null,
          "data-column": column,
          "data-raw": raw === undefined || raw === null ? ""
            : structural ? JSON.stringify(raw) : String(raw) },
        structural
          ? renderStructured(describes, raw, hintsOf(child), child, depth,
                             `${key}.${rowId}`)
          : numeric ? quantity(raw, kind)
          : typeof raw === "string" ? renderText(column, raw)
          : (raw ?? "—")));
    }
    body.append(tr);
  }
  table.append(body);
  sortable(table, specs);
  // UX-205: the tools. Sorting alone cannot reduce 1,202 rows to the
  // twelve that matter, and the page renders every row of every array
  // unconditionally - the right default for a viewer, unusable without
  // something to narrow it with.
  // UX-208: a declared element column earns every row a generic
  // Inspect - one affordance, no per-table code, because the *schema*
  // says which values are element uids.
  const uidColumn = elementColumn(specs);
  if (uidColumn) {
    table.setAttribute("data-element-column", uidColumn);
    for (const tr of table.querySelectorAll("tbody tr")) {
      const cell = [...tr.children].find(
        (td) => td.getAttribute("data-column") === uidColumn);
      if (!cell) continue;
      const uid = cell.getAttribute("data-raw") || cell.textContent;
      tr.setAttribute("data-element", uid);
      cell.append(el("a", { class: "inspect", href: `#${cssId(uid)}`,
                            title: `Find ${uid} elsewhere in this report` },
                     "\u2315"));
    }
  }
  const tools = interrogable(table, specs, rows.length, depth);
  return { table, tools };
}

/** One table as its own view: `buildTable`, in a section. */
export function renderTable(key, rows, hint = {}, node = undefined) {
  const { table, tools } = buildTable(key, rows, hint, node);
  return el("section", { "data-section": key,
                         "data-rail": heading(key, hint).rail },
    sectionHead(key, hint), tools, table);
}

/**
 * The filter bar, the per-column thresholds and the copy affordances.
 *
 * Every comparison runs against `data-raw` - the published value - not
 * against the formatted cell text. Comparing "1.2s" to "5s" as strings
 * is the defect this shape exists to prevent, and `UX-201`'s column
 * metadata is what makes `> 5s` parseable: the column declares that it
 * is a `duration_us`, so the suffix has a meaning.
 */
export function interrogable(table, specs, total, depth = 0) {
  const state = { text: "", thresholds: {} };
  const badge = el("span", { class: "badge" }, badgeText(total, total));
  const refresh = () => {
    badge.textContent = badgeText(applyFilters(table, state), total);
  };

  const box = el("input", {
    type: "search", class: "table-filter",
    placeholder: "filter rows…",
    "aria-label": "filter rows",
  });
  box.addEventListener("input", () => { state.text = box.value; refresh(); });

  // A threshold per quantity column, in the header, where the column
  // says what unit it is in.
  table.querySelectorAll("th").forEach((th, index) => {
    const spec = specs[index];
    if (!spec || !spec.quantity) return;
    const input = el("input", {
      type: "text", class: "th-filter", "data-column": spec.key,
      placeholder: PLACEHOLDER[spec.quantity] ?? "> 0",
      "aria-label": `threshold for ${spec.title ?? spec.key}`,
    });
    input.addEventListener("input", () => {
      const parsed = parseThreshold(input.value, spec.quantity);
      // Unparseable is *no filter*, and says so: a threshold nobody can
      // read must not silently hide every row.
      //
      // `UX-304`: and it says so in more than one channel. A red border
      // was the whole signal, which is styleguide §4.3's defect - a
      // status tone alone. The border also goes dashed (a shape), and
      // `aria-invalid` plus a `title` carry it to a reader who is not
      // looking at borders at all.
      const bad = Boolean(input.value) && !parsed;
      input.className = bad ? "th-filter unparsed" : "th-filter";
      input.setAttribute("aria-invalid", String(bad));
      if (bad) {
        input.setAttribute(
          "title", `"${input.value}" is not a threshold this column can `
                   + `read, so no filter is applied`);
      } else {
        input.removeAttribute("title");
      }
      if (parsed) state.thresholds[spec.key] = parsed;
      else delete state.thresholds[spec.key];
      refresh();
    });
    // The header stays clickable for sorting; the input must not
    // forward its clicks there.
    input.addEventListener("click", (event) => event.stopPropagation?.());
    th.append(input);
  });

  // UX-208 item 4: Top-N over any column the schema declares a
  // quantity. `Top 10` is a *preset*, not a cap - the badge still says
  // `10 of 1,202`, because a reader who cannot see the denominator
  // cannot tell a filtered table from a small one.
  const presets = presetColumns(specs);
  if (presets.length) {
    const preset = el("select", { class: "top-n", "aria-label": "Top rows" });
    preset.append(el("option", { value: "" }, "All rows"));
    for (const column of presets) {
      for (const n of [10, 25]) {
        preset.append(el("option", { value: `${n}:${column}` },
                         `Top ${n} by ${column}`));
      }
    }
    preset.addEventListener("change", () => {
      if (!preset.value) { refresh(); return; }
      const [n, column] = preset.value.split(":");
      badge.textContent = badgeText(applyTopN(table, column, Number(n)), total);
    });
    // UX-262: a table longer than this opens bounded.
    //
    // `UX-187` capped the tables that grow with *element count* and
    // this one grows with **critical-path depth**, which nobody had a
    // run deep enough to notice. Measured at 1440x900: a 122-deep path
    // took the `signals` section from 1884px (2.1 screens, 24 rows) to
    // 5539px (6.2 screens, 132 rows) - on a *smaller* run.
    //
    // The control already existed; `All rows` being its default was
    // the defect. The badge still says `25 of 132`, per `UX-208`'s
    // rule that a reader who cannot see the denominator cannot tell a
    // filtered table from a small one - so this bounds the page
    // without hiding the size of what it bounded.
    if (total > TABLE_OPENS_BOUNDED_ABOVE) {
      const [column] = presets;
      preset.value = `25:${column}`;
      badge.textContent = badgeText(applyTopN(table, column, 25), total);
    }
    state.preset = preset;
  }

  // UX-279: the noun, not the verb, and the count rather than a
  // promise. Measured on the served report when this was filed: 43 copy
  // controls, three vocabularies, `Copy` fourteen times over two
  // different payloads, and not one `title` or `aria-label` among them.
  // "Copy shown rows" is a promise; `Copy 12 rows` is a number a reader
  // can check against the badge beside it.
  //
  // UX-280: and in which form. JSON pastes into a ticket as a code
  // block somebody has to read; Markdown pastes as a table. The choice
  // is remembered, because a reader pasting ten tables into one ticket
  // should choose once - `localStorage`, which is where this page
  // already remembers per-reader preferences, and which failing is not
  // allowed to take the report down with it.
  const shownRows = () => [...table.querySelectorAll("tbody tr")]
    .filter((tr) => !tr.hidden);
  const asMarkdown = el("label", { class: "copy-as" },
    el("input", { type: "checkbox", class: "copy-markdown" }),
    " as Markdown");
  const markdownBox = asMarkdown.querySelector("input");
  const remembered = readCopyFormat();
  if (markdownBox && remembered === "markdown") markdownBox.checked = true;
  markdownBox?.addEventListener?.("change", () => {
    writeCopyFormat(markdownBox.checked ? "markdown" : "json");
    label();
  });

  const copyRows = el("button", { type: "button", class: "copy-rows" });
  const label = () => {
    const n = shownRows().length;
    const form = markdownBox?.checked ? "Markdown" : "JSON";
    const rows = `${n.toLocaleString("en-US")} row${n === 1 ? "" : "s"}`;
    copyRows.textContent = `Copy ${rows}`;
    copyRows.title = `Copy the ${rows} shown in this table as ${form}, `
      + `with their published values`;
  };
  label();
  copyRows.addEventListener("click", () => {
    const rows = shownRows();
    copy(markdownBox?.checked
      ? rowsMarkdown(rows, specs)
      : `[${rows.map((tr) => rowJson(tr, specs.map((s) => s.key))).join(",")}]`);
  });
  // The count follows the filter, the threshold, the sort and the
  // bound - all of which go through `refresh` or the preset - so it is
  // recomputed on any input rather than only when the table is built.
  table.parentNode?.addEventListener?.("input", label);

  // Copy one cell's published value. Delegated, so 1,202 rows do not
  // mean 1,202 listeners.
  table.addEventListener("dblclick", (event) => {
    const cell = event.target?.closest?.("td");
    if (cell) copy(cellText(cell));
  });

  // UX-303 (styleguide §2): the shape of the column before its rows.
  //
  // A table longer than the bound is a table nobody reads to the end,
  // and its primary quantity's *distribution* is the thing a reader
  // wants before scrolling - "is the top row an outlier or the top of
  // a ramp" is one glance, or twelve scrolls.
  //
  // Built from the column's own `data-raw` values, which is a reading
  // of published values in the way sorting is. The boundary §2 draws
  // and `columnStrip` keeps: **a self-built strip prints no derived
  // number.** Its labels are the smallest and largest *rows* and a
  // count of rows; the p50 and p95 ticks are positions and nothing
  // else. A percentile worth printing enters the payload first.
  const shape = distributionStrip(table, specs, total, state, refresh);

  // `UX-318` (§3a.3): **every capped or nested table offers focus.** A
  // table that opened bounded is hiding rows behind a Top-N; a nested
  // one is inside a cell that cannot give it room. Both are the
  // reader's "enlarge table to occupy more space", and both enter the
  // same state - one control, not two features.
  //
  // "Nested" is measured in *tables*, not in calls: `renderStructured`
  // hands `mapTable` `depth + 1`, so a section's own fold already
  // arrives here at depth 1. Depth 2 is a table inside another table's
  // cell - the one with no room - and depth 3 does not exist, because
  // `CELL_NEST_LIMIT` turns it into the fold that routes to focus.
  const nested = depth > 1;
  const expand = served() && (nested || total > TABLE_OPENS_BOUNDED_ABOVE)
    ? expandTableControl(table, depth) : null;
  const tools = el("div", { class: "table-tools" }, box, badge,
                            state.preset ?? null, copyRows, asMarkdown,
                            expand, shape);
  // The badge and the count are the same claim; refresh both together.
  tools.addEventListener?.("input", label);
  tools.addEventListener?.("change", label);
  return tools;
}

/**
 * The density strip for a long table's primary quantity column, or
 * `null` when the table is short or has no quantity to have a shape.
 *
 * Clicking it sets that column's threshold to the **nearest actual row
 * value** - a published number, never the position the click landed
 * on, which would be a derived figure entering the page through a
 * mouse. Served only: an export is a file, and `UX-194`'s rule is that
 * an affordance whose precondition is absent is not shown as a dead
 * one. The strip itself renders in both, because the *shape* is the
 * point and the click is a convenience.
 */
function distributionStrip(table, specs, total, state, refresh) {
  if (total <= TABLE_OPENS_BOUNDED_ABOVE) return null;
  const spec = specs.find((s) => s && s.quantity && s.numeric !== false);
  if (!spec) return null;
  // The column key, not `cssId`: that normalises an *element uid* into
  // an anchor, and a column key is already a schema identifier.
  const raw = [...table.querySelectorAll(`td[data-column="${spec.key}"]`)]
    .map((td) => Number(td.getAttribute("data-raw")))
    .filter((n) => Number.isFinite(n));
  if (!raw.length) return null;

  const drawn = columnStrip(raw, {
    grade: GRADE_ANNOTATION,
    format: (n) => quantity(n, spec.quantity),
    label: `${spec.title ?? title(spec.key)} across all ${
      total.toLocaleString("en-US")} rows`,
  });
  drawn.setAttribute("data-column", spec.key);
  drawn.setAttribute("data-interactive", String(served()));
  if (!served()) return drawn;

  const sorted = raw.slice().sort((a, b) => a - b);
  const svg = drawn.querySelector?.("svg");
  svg?.addEventListener?.("click", (event) => {
    // Where in the range the click landed, as a fraction. A shim and a
    // browser both give `offsetX`/`clientWidth`; without them the
    // click simply does nothing rather than guessing a threshold.
    const width = event?.currentTarget?.clientWidth;
    if (!width) return;
    const fraction = Math.min(1, Math.max(0, (event.offsetX ?? 0) / width));
    const low = sorted[0];
    const high = sorted[sorted.length - 1];
    const wanted = low + fraction * (high - low);
    // The nearest value a row actually has, so the threshold is a
    // published number.
    const chosen = sorted.reduce((best, value) =>
      Math.abs(value - wanted) < Math.abs(best - wanted) ? value : best,
      sorted[0]);
    const input = table.querySelector(
      `.th-filter[data-column="${spec.key}"]`);
    if (!input) return;
    // Raw units, no suffix - `parseThreshold` reads a bare number as
    // the published one, so this round-trips exactly rather than
    // through a formatted string.
    input.value = `>= ${chosen}`;
    input.dispatchEvent?.(new Event("input", { bubbles: true }));
    if (!input.listeners?.input?.length) {
      // A shim with no bubbling: set the state directly so the guard
      // measures the filter rather than the event system.
      state.thresholds[spec.key] = { op: ">=", value: chosen };
      refresh();
    }
  });
  return drawn;
}

// UX-280: which form the reader last chose, remembered for them alone.
//
// `localStorage` is the right channel and `UX-211` says why: it
// remembers for *me*, on *this* browser, and it is not part of the link
// anybody pastes. An export opened from `file://` may get no storage at
// all, and a page that threw there would lose the report rather than
// the preference - so both sides are guarded and the default is what
// the page did before.
const COPY_FORMAT_KEY = "bga.copy-format";

export function readCopyFormat() {
  try {
    return safeStorage()?.getItem(COPY_FORMAT_KEY) === "markdown"
      ? "markdown" : "json";
  } catch (error) {
    return "json";
  }
}

export function writeCopyFormat(format) {
  try {
    safeStorage()?.setItem(COPY_FORMAT_KEY, format);
  } catch (error) {
    /* a private window, blocked site data, an export from a folder */
  }
}

// What to type, in the unit the column publishes.
const PLACEHOLDER = {
  duration_us: "> 5s", seconds: "> 5s", bytes: "> 10mb",
  megabytes: "> 512mb", kilobytes: "> 512mb", share: "> 10%", percent: "> 10%",
  count: "> 10", ratio: "> 1",
};

function sortable(table, specs = []) {
  const body = table.querySelector("tbody");
  table.querySelectorAll("th").forEach((th, index) => {
    // UX-201: a column the schema declares unsortable stays unsortable,
    // whatever its values happen to look like.
    if (specs[index] && specs[index].sortable === false) return;
    th.addEventListener("click", () => {
      const ascending = th.getAttribute("aria-sort") !== "ascending";
      table.querySelectorAll("th").forEach((other) =>
        other.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      const rows = [...body.querySelectorAll("tr")];
      rows.sort((a, b) => {
        const x = a.children[index]?.dataset.raw ?? "";
        const y = b.children[index]?.dataset.raw ?? "";
        const nx = Number(x), ny = Number(y);
        const numeric = x !== "" && y !== "" && !Number.isNaN(nx) && !Number.isNaN(ny);
        const order = numeric ? nx - ny : String(x).localeCompare(String(y));
        return ascending ? order : -order;
      });
      rows.forEach((row) => body.append(row));
    });
  });
}

// UX-270: the critical path is a section of its own.
//
// Requested, and `UX-262` is the argument: this is the table that
// grows with **path depth** rather than element count, and on a
// 122-deep path it took the `signals` section from 2.1 screens to 6.2
// on a *smaller* run. `UX-262` bounded its rows, which fixed the
// height; it stayed a row inside a section named after a schema key,
// beside a dozen unrelated quantities.
export const LIFTED_SECTION = "critical_path_detail";

export function liftedCriticalPath(signals, node) {
  const rows = signals?.[LIFTED_SECTION];
  if (!Array.isArray(rows) || !rows.length) return null;
  const child = childNode(node, LIFTED_SECTION);
  return renderTable(LIFTED_SECTION, rows, hintsOf(child), child);
}

// UX-269: a long value is truncated; a long *sentence* is not.
//
// Measured per field on a 44-element run:
//
//   678 chars  findings[].copy_text
//   572 chars  floors.capacity_model_note
//   393 chars  findings[].copy_text
//   293 chars  attribution_hints.resource_wait_us
//
// Two families that want opposite treatment. `copy_text` is a
// paragraph meant to be copied whole (`UX-224`) - truncating the cell
// is right, truncating what the button yields would break it.
// `capacity_model_note` and the `attribution_hints` strings are
// *explanations*: long because they are careful, and hiding them by
// default is how a reader stops seeing the caveat on a number.
//
// So a flat character cap is the wrong instrument, and the split is
// declared rather than sniffed.
export const CELL_TEXT_CAP = 160;

export const EXPLANATIONS = {
  capacity_model_note: "the caveat on the capacity numbers - hiding it "
    + "by default is how a reader stops seeing it",
  resource_wait_us: "attribution_hints prose: it explains what the "
    + "number does and does not include",
  note: "a field named `note` is an explanation by construction",
  sentence: "UX-220's published sentence for a number - the whole "
    + "point is that the reader sees it without asking",
};

function isExplanation(name) {
  return Object.prototype.hasOwnProperty.call(EXPLANATIONS, name)
    || name.endsWith("_note") || name.endsWith("_sentence");
}

/**
 * A long string as a truncated cell with the whole thing one click
 * away. The `…` is visible, never silent, and the full text stays
 * selectable - a reader who cannot select it has not been given it.
 */
export function renderText(name, value) {
  const text = String(value);
  if (text.length <= CELL_TEXT_CAP || isExplanation(name)) {
    return el("span", { "data-raw": text }, text);
  }
  const head = text.slice(0, CELL_TEXT_CAP).replace(/\s+\S*$/, "");
  return el("details", { class: "long-text", "data-raw": text },
            el("summary", {},
               el("span", {}, `${head}…`),
               el("span", { class: "muted" }, ` ${text.length} chars`)),
            el("p", { class: "full-text" }, text));
}

// UX-268: the element-keyed signals are one table, not six.
//
// `signals` carries seven maps that scale with the run. Six are the
// *same element list* seen through different fields - measured on a
// 44-element run, all six carry the identical 44 keys - and the page
// rendered them as six separate folds, so a reader wanting "the
// slowest element with the widest blast radius" had to open two and
// join them by hand.
//
// The seventh is not the same population at all. `wall_clock_share` is
// keyed by **task**:
//
//   element-keyed     app.bst
//   wall_clock_share  app.bst|BUILD|BUILD|0
//   union 88 keys, intersection 0
//
// It shares no keys with the other six, and nothing on the page said
// so. It stays its own table and says what its key is.
//
// Declared rather than sniffed: a new element-keyed signal has to join
// this list or be argued into `NOT_ELEMENT_KEYED`, and a guard fails
// on one that does neither.
export const ELEMENT_KEYED_SIGNALS = [
  "element_durations", "slack", "downstream_count", "unweighted_depth",
  "blast_radius", "criticality_probability",
];

export const NOT_ELEMENT_KEYED = {
  wall_clock_share: "keyed by task (`element|BUILD|BUILD|0`), not by "
    + "element - it shares zero keys with the six and pooling them "
    + "would put two populations in one table",
};

/**
 * One row per element, one column per element-keyed signal.
 *
 * Returns `null` when the run carries none of them, so a payload
 * without the signals renders exactly as it did.
 */
export function elementSignalTable(signals, node) {
  const present = ELEMENT_KEYED_SIGNALS.filter(
    (name) => signals?.[name] && typeof signals[name] === "object");
  if (present.length < 2) return null;
  const byElement = new Map();
  for (const name of present) {
    for (const [uid, value] of Object.entries(signals[name])) {
      const row = byElement.get(uid) ?? { element: uid };
      // A record-valued signal (`blast_radius`) contributes its own
      // fields; a scalar one contributes itself under its name.
      if (value && typeof value === "object" && !Array.isArray(value)) {
        for (const [field, member] of Object.entries(value)) {
          if (member === null || typeof member !== "object") {
            row[field] = member;
          }
        }
      } else {
        row[name] = value;
      }
      byElement.set(uid, row);
    }
  }
  const rows = [...byElement.values()];
  if (!rows.length) return null;
  const columns = [...new Set(rows.flatMap(Object.keys))]
    .filter((name) => name !== "element");
  const hint = {
    [COLUMNS]: [{ key: "element", title: "element" },
                ...columns.map((name) => ({
                  key: name, title: title(name),
                  quantity: quantityFor(childNode(node, name), name)
                    ?? guessQuantity(name) ?? "count" }))],
    [QUESTION]: "Which element should I look at?",
  };
  return { rows, hint, merged: present };
}

/**
 * UX-289: one element table, drawn as the view a reader asked for.
 *
 * The page had bounds and filters and **zero named presets** - measured
 * on the 1,202-element run, no element carried a preset role. So a
 * reader wanting "the critical path" got it as a separate table the
 * payload published separately, and the one table every element is
 * already in had to carry 13 columns because it served every question
 * at once.
 *
 * Each view names its own columns, so the width is a property of the
 * question rather than of the union of all of them. The selector is a
 * `<select>` for the reason `UX-262`'s Top-N is: it is the control the
 * page already teaches, and it round-trips through `UX-211`'s fragment
 * with no new vocabulary.
 *
 * A preset this run cannot support is **not offered** rather than
 * offered empty: "there are no choke points" and "this run does not
 * carry choke points" are different claims, and a view that draws zero
 * rows makes them look alike.
 */
export function presetTable(key, rows, presets, hint, node, payload) {
  const usable = (presets ?? [])
    .map((preset) => ({ preset, view: applyPreset(preset, rows, payload) }))
    .filter((entry) => entry.view);
  if (usable.length < 2) return null;

  const slot = el("div", { class: "preset-table", "data-presets":
                           usable.map((e) => e.preset.name).join("|") });
  const select = el("select", { class: "preset-view",
                                "data-table": key,
                                "aria-label": "View" });
  for (const { preset, view } of usable) {
    select.append(el("option", { value: preset.name, title: preset.question ?? null },
                     `${preset.name} (${view.total})`));
  }
  const body = el("div", { class: "preset-body" });

  const draw = (name) => {
    const entry = usable.find((e) => e.preset.name === name) ?? usable[0];
    const { preset, view } = entry;
    // The columns this view shows, in the order it names them - and
    // only the ones the run actually carries, so a preset naming a
    // column an older payload lacks degrades to the columns it has
    // rather than to a wall of empty cells.
    const present = new Set(rows.flatMap(Object.keys));
    const columns = preset.columns.filter((column) => present.has(column));
    const viewHint = {
      ...hint,
      [COLUMNS]: (hint[COLUMNS] ?? []).filter(
        (spec) => columns.includes(typeof spec === "string" ? spec : spec.key)),
      [QUESTION]: preset.question ?? hint[QUESTION],
    };
    const built = buildTable("elements", view.shown, viewHint, node);
    built.table.setAttribute("data-preset", preset.name);
    body.replaceChildren(
      el("p", { class: "muted" },
         preset.question ? `${preset.question} ` : "",
         `${view.shown.length} of ${rows.length} elements`
         + (view.total > view.shown.length
            ? `, the first ${view.shown.length} of ${view.total}` : "")),
      built.tools, built.table);
  };
  select.addEventListener("change", () => draw(select.value));
  draw(usable[0].preset.name);
  slot.append(el("div", { class: "preset-bar" },
                 el("label", { class: "preset-label" }, "View: "), select),
              body);
  return { node: slot, select, draw, presets: usable.map((e) => e.preset) };
}

export function renderPairs(key, object, hint = {}, node = undefined,
                            payload = undefined) {
  const direction = hint[DIRECTION];
  const list = el("dl", { class: "pairs" });
  // UX-268: the element-keyed signals leave the pair list and become
  // one table, so they are drawn once rather than six times.
  const joined = key === "signals" ? elementSignalTable(object, node) : null;
  const merged = new Set(joined?.merged ?? []);
  for (const [name, value] of Object.entries(object)) {
    if (merged.has(name)) continue;
    // UX-270: the critical path is its own section, not a row inside
    // this one. It is also the one member that rendered a whole
    // `<section>` into a `<dd>` - the nesting UX-267 removed
    // everywhere else.
    if (key === "signals" && name === LIFTED_SECTION) continue;
    // UX-201: each member resolved against *its own* schema node, not
    // guessed from its name. `deltas` was hinted at the top level and
    // still name-sniffed every member inside it.
    const child = childNode(node, name);
    const kind = quantityFor(child, name);
    const described = hintsOf(child).description;
    let cell;
    // UX-208: a nested array of objects is a *table*, not a JSON dump.
    // `signals.critical_path_detail` - the list of elements the whole
    // report is about - rendered as a `<pre>` of raw JSON, which is
    // why nothing in it was sortable, filterable or one click from
    // investigation. Same renderer, same declarations, one level down.
    if (Array.isArray(value) && value.length
        && value.every((item) => item && typeof item === "object"
                                 && !Array.isArray(item))) {
      // `buildTable`, not `renderTable`: a cell must not contain a
      // `<section>`. This was the last of them (`UX-267`) - measured,
      // three sections still lived inside `<dd>` after the rest moved.
      {
        const built = buildTable(name, value, hintsOf(child), child);
        cell = el("div", { class: "map-table", "data-bounded": "map" },
                  built.tools, built.table);
      }
    } else if (value !== null && typeof value === "object") {
      cell = renderStructured(name, value, hintsOf(child), child, 0,
                              `${key}.${name}`);
      // UX-268: a map whose keys are *not* elements says so, because
      // the page draws it identically to the six that are and a reader
      // comparing them would be comparing populations that share no
      // keys at all.
      if (NOT_ELEMENT_KEYED[name]) {
        cell = el("span", {}, cell,
                  el("span", { class: "muted key-note" },
                     ` keyed by task, not by element`));
      }
    } else if (typeof value === "number" && direction) {
      // A signed change, coloured by what the schema says "better" is,
      // without this file knowing which metric it is looking at.
      const better = direction === "lower_is_better" ? value < 0 : value > 0;
      const way = value === 0 ? "" : better ? "better" : "worse";
      // `UX-305` (styleguide §4.4): the *value* stays ink and the tone
      // moves to a marker beside it. Colouring the number was the
      // rule's own example of what not to do, and the marker is also
      // §4.3's non-colour channel - `UX-212`'s triangles, which is the
      // vocabulary the trend and the history already use.
      cell = el("span", {
        class: `num delta ${way}`, "data-raw": String(value),
      }, way ? el("span", { class: "delta-mark", "data-direction": way,
                            "aria-hidden": "true" },
                  better ? "\u25be" : "\u25b4") : null,
         `${value > 0 ? "+" : ""}${quantity(value, kind)}`);
    } else if (typeof value === "number") {
      cell = el("span", { class: "num", "data-raw": String(value) },
                quantity(value, kind));
    } else if (typeof value === "string") {
      cell = renderText(name, value);
    } else {
      cell = el("span", { "data-raw": value === null ? "" : String(value) },
                value === null ? "—" : String(value));
    }
    // UX-201: the schema's own `description` is the sentence - the "why
    // does this number matter" answer sourced from the contract, and
    // thence the spec, rather than from prose written beside the
    // renderer where it would drift.
    //
    // UX-317 (§2b.3): and it has a door a reader can see.
    const { term, describe } = describedTerm(name, described);
    list.append(term, el("dd", {}, cell, describe));
  }
  const parts = [sectionHead(key, hint)];
  if (joined) {
    // One row per element, before the scalars - it is the thing a
    // reader came for, and `UX-261` put the same argument to the
    // decision block.
    //
    // UX-289: as the *view* the reader asked for, where the schema
    // declares views over it. The unfiltered union is still one of
    // them ("All elements"), so nothing became unreachable - it stopped
    // being the only thing on offer.
    const views = presetTable("elements", joined.rows, hint[PRESETS],
                              joined.hint, node, payload);
    if (views) {
      parts.push(el("div", { class: "map-table", "data-bounded": "map",
                             "data-joined": joined.merged.join(",") },
                    el("p", { class: "muted" },
                       `One row per element, joined from `
                       + `${joined.merged.length} signals.`),
                    views.node));
    } else {
      const { table, tools } = buildTable("elements", joined.rows,
                                          joined.hint, node);
      parts.push(el("div", { class: "map-table", "data-bounded": "map",
                             "data-joined": joined.merged.join(",") },
                    el("p", { class: "muted" },
                       `One row per element, joined from `
                       + `${joined.merged.length} signals.`),
                    tools, table));
    }
  }
  parts.push(list);
  return el("section", { "data-section": key, "data-rail": heading(key, hint).rail },
                        ...parts);
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
export function renderSection(key, value, hint = {}, node = undefined,
                              investigate = null, payload = undefined) {
  if (value === null || value === undefined) return null;
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
      // selection published elsewhere in it - `structural.bottleneck`
      // for the choke points. The section renders its own value; the
      // payload is only ever read for a declared `from` path.
      ? renderPairs(key, value, hint, node, payload) : null;
  }
  return null;   // scalars belong in the summary, below
}

/**
 * `UX-317` (styleguide §2b.3): **a described value shows its
 * affordance.**
 *
 * `UX-201` sourced the "why does this number matter" sentence from the
 * schema and put it in a `title`, where discovery is hover archaeology:
 * the reader who does not know to hover never learns what
 * `scheduler_wait` means, and the one who does gets a tooltip they
 * cannot keep open while comparing two values.
 *
 * So the term carries a visible `?`, and the sentence opens **beside
 * the value** - which is why the description node is built here and
 * appended to the `<dd>` rather than to the `<dt>`. The `title` stays:
 * it costs nothing, and it is what a screen reader and a keyboard
 * focus already read.
 *
 * Returns `{ term, describe }` - the `<dt>`, and the node to put in the
 * `<dd>`, or `null` when the schema describes nothing.
 */
function describedTerm(name, description, attrs = {}) {
  const term = el("dt", { ...attrs, "data-key": name,
                          title: description ?? null,
                          "data-described": description ? "true" : null },
                  title(name));
  if (!description) return { term, describe: null };
  const sentence = el("span", { class: "description",
                                "data-role": "description",
                                "data-describes": name, hidden: "" },
                      description);
  sentence.hidden = true;
  const marker = el("button", {
    type: "button", class: "describe", "data-describe": name,
    "aria-expanded": "false",
    // `UX-279`: the control says what it does before it is pressed.
    title: `What ${title(name)} means`,
  }, "?");
  marker.addEventListener?.("click", () => {
    const open = marker.getAttribute("aria-expanded") === "true";
    marker.setAttribute("aria-expanded", open ? "false" : "true");
    sentence.hidden = open;
  });
  term.append(marker);
  return { term, describe: sentence };
}

export function renderSummary(payload, hints) {
  const scalars = Object.entries(payload).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;
  const list = el("dl", { class: "pairs" });
  for (const [key, value] of scalars) {
    const kind = hints[key]?.[QUANTITY] ?? guessQuantity(key);
    const { term, describe } = describedTerm(key, hints[key]?.description);
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

/**
 * The hints on one schema node, plus the node itself so a renderer can
 * keep walking.
 *
 * UX-201: hints used to be read from the *top level only*, and every
 * nested value fell to `guessQuantity(key)` name-sniffing. The two
 * systems demonstrably disagreed - `peak_rss_mb: 512` rendered as
 * "512 B" and a 0-100 `cpu_pct` as "4200.0%", both measured. The schema
 * is the authority now, at every depth; the guess is what happens when
 * the schema says nothing, and that is a schema gap rather than a
 * feature.
 */
export function hintsOf(node) {
  const hint = {};
  if (!node || typeof node !== "object") return hint;
  for (const name of [QUANTITY, SEVERITY, COLUMNS, DIRECTION, QUESTION,
                      RAIL, PRESETS, SERIES, DISTRIBUTION]) {
    if (name in node) hint[name] = node[name];
  }
  if (node.description) hint.description = node.description;
  return hint;
}

/** The schema node describing `key` inside `node`, or undefined. */
export function childNode(node, key) {
  if (!node || typeof node !== "object") return undefined;
  if (node.properties && key in node.properties) return node.properties[key];
  // UX-290: an array's item schema, and then the item's own field if it
  // has one. Returning `items` whole meant a column of a record array
  // resolved to the record rather than to the column, so a declaration
  // on `serialization_point_risks[].pinned_elements` was unreachable
  // while an identical one a level up resolved fine.
  if (node.items) {
    const inside = node.items.properties?.[key];
    return inside ?? node.items;
  }
  return undefined;
}

/**
 * What a value should be rendered as, schema first.
 *
 * The one place the precedence lives, so "declared beats guessed" is a
 * property of the code rather than of every call site remembering.
 */
export function quantityFor(node, key) {
  const declared = hintsOf(node)[QUANTITY];
  if (declared) return declared;
  const guessed = guessQuantity(key);
  if (guessed && typeof console !== "undefined" && globalThis.BGA_STRICT_HINTS) {
    // Dev-mode complaint: an undeclared key the renderer had to guess
    // about is a gap in the published schema, and the schema is what
    // every other consumer reads.
    console.warn(`bga: ${key} has no bga:quantity; guessed ${guessed}`);
  }
  return guessed;
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
    const section = renderSection(key, value, hints[key] ?? {}, nodes[key],
                                  investigate, payload);
    // `UX-302`: what this section was rendered *from*, so the "view as
    // JSON" toggle has a published value to show rather than a
    // re-serialisation of the DOM. Only the schema-driven sections get
    // one; a section the page composes from several places has no
    // single payload slice, and gets no toggle rather than a misleading
    // one.
    if (section) root.append(recordSource(section, value));
    // UX-270: the run's most important list, immediately after the
    // section it used to be a row of. `UX-262` bounded its rows and
    // `UX-208` gave it a badge; this only moves it.
    if (key === "signals") {
      const lifted = liftedCriticalPath(value, nodes[key]);
      if (lifted) root.append(lifted);
    }
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


// UX-199: a served page can ask the server; an export cannot. One
// predicate, so the two modes cannot disagree about which they are.
export function served() {
  // `UX-303`: guarded, because this is now asked while a *table* is
  // being built rather than only during boot. A page always has a
  // `location`; a harness driving `buildTable` directly need not, and
  // a throw here would take the whole render down - `UX-199`'s defect
  // by a new route. No location is not a server.
  if (typeof location === "undefined" || !location) return false;
  return /^https?:$/.test(location.protocol);
}

function safeStorage() {
  try {
    return window.localStorage;
  } catch (error) {
    // Blocked site data, a private window, a thumbnail renderer.
    return null;
  }
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

// UX-262: above this many rows a table opens on its top 25 rather than
// on everything. 40 is chosen against the shapes that occur: the
// 1,202-element run's widest table is 26 rows and stays whole, and a
// 122-deep critical path is 132 and does not. A bound that fired on
// the ordinary case would train readers to reset it every load.
export const TABLE_OPENS_BOUNDED_ABOVE = 40;

export function wireJumpBox(nav, root, payload, context = {}) {
  const targets = jumpTargets(root, payload);
  const box = document.createElement("input");
  box.setAttribute("type", "search");
  box.setAttribute("id", "jump");
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
    const comparison = await load("compare", null).catch(() => null);
    const band = comparison && renderBand(comparison);
    if (band) root.append(band);
    // UX-221: and which elements put the candidate where the band says
    // it is. The band states the verdict, this states the cause, and
    // `chapters.js` is what puts them in that order - see the note on
    // `renderDecision` below.
    const culprits = comparison && renderCulprits(comparison);
    if (culprits) root.append(culprits);

    // UX-202: the overview above the sections, and the evidence header
    // above even that - what the capture can support, before any
    // number is believed. Prepended in reverse so evidence ends up
    // first.
    // UX-206: the chain drawn, hung off the overview's execution
    // segment - the "where did the time go" spine, as a list with
    // widths rather than a graph layout problem.
    const chain = renderCriticalPath(payload);
    if (chain) root.append(chain);

    // UX-219: the horizon as a plan rather than a five-column table.
    // Placed with the chain, because "what is the path" and "what does
    // fixing it buy" are the same question one step apart.
    const horizon = renderHorizon(payload);
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

    const overview = renderOverview(payload);
    if (overview) root.append(overview);
    const evidence = renderEvidence(payload);
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
    const store = await load("store", null).catch(() => null);
    // UX-234: and what the store says about itself as a distribution.
    // A separate document rather than a key of the listing: one row
    // per snapshot and one row per host class are different shapes,
    // and a page with no aggregate simply draws no band.
    const aggregate = await load("store-aggregate", null).catch(() => null);
    const decision = renderDecision(payload,
      run.has_timeline ? (action) => decisionInvestigation(action, payload) : null,
      // UX-218: the clipboard helper, passed in so `views.js` keeps
      // having no dependency on `tables.js`.
      copy,
      // UX-227: the store and the schema, for the history line and the
      // verdict shapes inside each "why this one" fold.
      { store, schema: schemas[store?.schema] });
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
          node.append(renderElementHistory(store, uid, schemas[store.schema]));
        }
      }
      root.append(node);
    }
    // UX-212: the schema, so the trend draws the shape the *contract*
    // assigns each verdict. UX-234: and the distribution the points
    // came from, drawn behind them from published figures only.
    const trend = store && renderTrend(store, schemas[store.schema], aggregate);
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
      const note = el("section", { "data-section": "blast-offline" },
        el("h2", {}, "Blast radius"),
        el("p", { class: "muted" },
          "Not available in an exported report - the search asks the "
          + "server, and there is not one here. Run "),
        el("p", {}, el("code", {}, "bga blast <target> <run>")));
      // UX-286 files it beside `resource_blast` in "What if I change
      // this?", which is where the served page offers to compute it.
      root.append(note);
    }

    // UX-199: the export used to strip the link to the questions page
    // and leave nothing behind it - functionality lost rather than
    // moved. They are inlined here instead, from the same module
    // `sql.html` renders, so the two cannot drift.
    if (!served()) root.append(renderQuestions(el));
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
    chapters(root, document);

    // UX-199: navigation, last, over whatever was rendered. Nothing
    // above changes; a reader who ignores all of it sees the same
    // report in the same order.
    anchor(root);
    // UX-302: before `collapsible`, so the collapse caret ends up first
    // in the heading - `collapsible` prepends and this appends.
    jsonToggles(root, { document });
    const controls = collapsible(root, {
      document, storage: served() ? safeStorage() : null });
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
    window.addEventListener?.("hashchange", () => {
      const built = openElement(splitHash(location.hash).anchor);
      // The browser has already decided there was nothing to scroll to,
      // so the section it just missed has to say where it is.
      built?.scrollIntoView?.();
    });
    openElement(splitHash(location.hash).anchor);

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
    root.replaceChildren(el("div", { class: "verdict refused" },
      el("h2", {}, "Could not load this run"),
      el("p", {}, String(error))));
  }
}

if (typeof document !== "undefined" && document.getElementById("report")) {
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
