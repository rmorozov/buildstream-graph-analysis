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

import { handOff, deepLink } from "./perfetto.js";
import { renderBand, renderCulprits, renderElementHistory, renderHorizon,
         renderTrend, renderBlastSearch,
         renderOverview, renderEvidence,
         renderCriticalPath, renderBlastTree,
         renderDecision, renderElementSections, elementAnchor,
         INCOMPLETE, renderProvenance, renderInvestigation, renderWhatIf } from "./views.js";
import { anchor, collapsible, toc, jumpTargets, matches,
         paletteResults } from "./nav.js";
import { applyView, splitHash, viewLink, wireViewState } from "./viewstate.js";
import { applyFocus, applyMarks, clearFocus, focusedElement, readMarks,
         renderFocusBar, renderMarkSummary } from "./focus.js";
import { copyButton, renderQuestions } from "./questions.js";
import { investigationFor } from "./trace_context.js";
import { parseThreshold, applyFilters, badgeText, rowJson, cellText,
         copy, applyTopN, presetColumns } from "./tables.js";

const QUANTITY = "bga:quantity";
const SEVERITY = "bga:severity";
const COLUMNS = "bga:columns";
const DIRECTION = "bga:direction";
// UX-209: the question a section answers, and which part of the
// argument it belongs to. UX-208: what a column's values *are*.
const QUESTION = "bga:question";
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
    case "count": return String(value);
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
    else if (name.startsWith("data-")) node.setAttribute(name, value);
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
    list.append(
      el("dt", { title: hintsOf(childNode(node, key)).description ?? null },
         title(key)),
      el("dd", { class: typeof value === "number" ? "num" : null,
                 "data-field": key,
                 "data-raw": value === null ? "" : String(value) },
         typeof value === "number" ? quantity(value, kind)
           : value === null ? "—" : String(value)));
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
        ? copyButton(el, finding.copy_text)
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

export function renderTable(key, rows, hint = {}, node = undefined) {
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
  for (const row of rows) {
    const tr = el("tr");
    for (const spec of specs) {
      const column = spec.key;
      const raw = row?.[column];
      const numeric = typeof raw === "number";
      const kind = numeric ? spec.quantity : null;
      tr.append(el("td",
        { class: numeric ? "num" : null,
          "data-column": column,
          "data-raw": raw === undefined || raw === null ? "" : String(raw) },
        Array.isArray(raw) ? raw.join(", ")
          : (raw && typeof raw === "object") ? JSON.stringify(raw)
          : numeric ? quantity(raw, kind) : (raw ?? "—")));
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
  const tools = interrogable(table, specs, rows.length);
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
export function interrogable(table, specs, total) {
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
      input.className = input.value && !parsed
        ? "th-filter unparsed" : "th-filter";
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

  const copyRows = el("button", { type: "button", class: "copy-rows" },
                      "Copy shown rows");
  copyRows.addEventListener("click", () => {
    const columns = specs.map((spec) => spec.key);
    const shown = [...table.querySelectorAll("tbody tr")]
      .filter((tr) => !tr.hidden)
      .map((tr) => rowJson(tr, columns));
    copy(`[${shown.join(",")}]`);
  });

  // Copy one cell's published value. Delegated, so 1,202 rows do not
  // mean 1,202 listeners.
  table.addEventListener("dblclick", (event) => {
    const cell = event.target?.closest?.("td");
    if (cell) copy(cellText(cell));
  });

  return el("div", { class: "table-tools" }, box, badge,
                     state.preset ?? null, copyRows);
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

export function renderPairs(key, object, hint = {}, node = undefined) {
  const direction = hint[DIRECTION];
  const list = el("dl", { class: "pairs" });
  for (const [name, value] of Object.entries(object)) {
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
      cell = renderTable(name, value, hintsOf(child), child);
    } else if (value !== null && typeof value === "object") {
      cell = el("details", {}, el("summary", {}, "object"),
                el("pre", {}, JSON.stringify(value, null, 2)));
    } else if (typeof value === "number" && direction) {
      // A signed change, coloured by what the schema says "better" is,
      // without this file knowing which metric it is looking at.
      const better = direction === "lower_is_better" ? value < 0 : value > 0;
      cell = el("span", {
        class: `num delta ${value === 0 ? "" : better ? "better" : "worse"}`,
        "data-raw": String(value),
      }, `${value > 0 ? "+" : ""}${quantity(value, kind)}`);
    } else if (typeof value === "number") {
      cell = el("span", { class: "num", "data-raw": String(value) },
                quantity(value, kind));
    } else {
      cell = el("span", { "data-raw": value === null ? "" : String(value) },
                value === null ? "—" : String(value));
    }
    // UX-201: the schema's own `description` is the popover - the "why
    // does this number matter" answer sourced from the contract, and
    // thence the spec, rather than from prose written beside the
    // renderer where it would drift.
    const term = el("dt", { "data-key": name,
                            title: described ?? null,
                            "data-described": described ? "true" : null },
                    title(name));
    list.append(term, el("dd", {}, cell));
  }
  return el("section", { "data-section": key, "data-rail": heading(key, hint).rail },
                        sectionHead(key, hint), list);
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
                              investigate = null) {
  if (value === null || value === undefined) return null;
  if (hint[SEVERITY] && Array.isArray(value)) {
    // UX-217: the schema node travels with the value, so the evidence
    // renders in its declared units rather than by name-sniffing.
    return value.length ? renderFindings(value, investigate, node) : null;
  }
  if (Array.isArray(value)) {
    if (!value.length) return null;
    if (value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      return renderTable(key, value, hint, node);
    }
    return el("section", { "data-section": key,
                           "data-rail": heading(key, hint).rail },
                          sectionHead(key, hint),
              el("p", {}, el("code", {}, value.join(", "))));
  }
  if (typeof value === "object") {
    return Object.keys(value).length ? renderPairs(key, value, hint, node) : null;
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
    list.append(
      el("dt", { "data-key": key }, title(key)),
      el("dd", {}, el("span", {
        class: typeof value === "number" ? "num" : null,
        "data-raw": value === null ? "" : String(value),
      }, typeof value === "number" ? quantity(value, kind)
         : value === null ? "—" : String(value))));
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
  for (const name of [QUANTITY, SEVERITY, COLUMNS, DIRECTION, QUESTION, RAIL]) {
    if (name in node) hint[name] = node[name];
  }
  if (node.description) hint.description = node.description;
  return hint;
}

/** The schema node describing `key` inside `node`, or undefined. */
export function childNode(node, key) {
  if (!node || typeof node !== "object") return undefined;
  if (node.properties && key in node.properties) return node.properties[key];
  if (node.items) return node.items;
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
  const summary = renderSummary(payload, hints);
  if (summary) root.append(summary);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "schema") continue;
    const section = renderSection(key, value, hints[key] ?? {}, nodes[key],
                                  investigate);
    if (section) root.append(section);
  }
  root.setAttribute("aria-busy", "false");
  return root;
}


// UX-199: a served page can ask the server; an export cannot. One
// predicate, so the two modes cannot disagree about which they are.
export function served() {
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

  nav.append(box, list);
  return { targets, box, list, render, rowsOf: () => rows };
}

// ------------------------------------------------------------------ boot


export function wireTheHandoff() {
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
  if (fallback && served) {
    fallback.href = deepLink(absolute.href);
    fallback.parentElement.hidden = false;
  }

  button.addEventListener("click", async () => {
    status.textContent = "opening ui.perfetto.dev — sent tab to tab, not uploaded…";
    // `handOff` opens the tab before its first `await` (UX-198), so
    // this must call it without one - no `await` may come first in
    // this handler, or the click's activation is gone before the open.
    try {
      const { bytes } = await handOff(url);
      status.textContent = `sent ${(bytes / 1024).toFixed(1)} KiB`;
    } catch (error) {
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
    if (band) root.prepend(band);
    // UX-221: and above the band, which elements put the candidate
    // where the band says it is. Prepended after it so it ends up
    // first: the band states the verdict, this states the cause.
    const culprits = comparison && renderCulprits(comparison);
    if (culprits) root.prepend(culprits);

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
    if (overview) root.prepend(overview);
    const evidence = renderEvidence(payload);
    if (evidence) root.prepend(evidence);

    // UX-207: **first screen = decision, everything else = evidence.**
    // Prepended last, so it lands above the status line and the
    // overview - which is the whole point of the item: the reader knows
    // what deserves attention before reading anything that justifies it.
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
    // still prepended and the sections are still appended.
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
    if (decision) root.prepend(decision);
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
    if (run.has_timeline) wireTheHandoff();

    // UX-199: navigation, last, over whatever was rendered. Nothing
    // above changes; a reader who ignores all of it sees the same
    // report in the same order.
    anchor(root);
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
      const heading = document.querySelector("header");
      if (heading && typeof heading.after === "function") {
        heading.after(contents);
      } else {
        document.body.insertBefore(contents, document.body.firstChild);
      }
      document.body.setAttribute("data-has-toc", "true");
      foldOnNarrow(contents, document);
    }

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
