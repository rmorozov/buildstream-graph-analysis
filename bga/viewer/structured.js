/**
 * UX-337: a value becomes a table, and the table becomes interrogable.
 *
 * `app.js`'s `render` seam ran to nearly two thousand lines, and the
 * larger half of it was one subject: `UX-201`'s rule that a value is
 * drawn as what the schema says it is, and the apparatus `UX-277`,
 * `UX-284` and `UX-289` built around the result - filters, sort, Top-N,
 * presets, folds, the density strip, the copy control.
 *
 * Everything this module needs points *down*, at `format.js` and
 * `primitives.js`; `app.js` sits above it and is not reached for. The
 * one apparent edge upward - `expandControl(path, label, render, ...)`
 * - is a parameter, which is why the crossing count was taken with
 * comments and strings stripped and then read, rather than trusted.
 */
import { served, safeStorage } from "./primitives.js";
import { QUANTITY, COLUMNS, DIRECTION, SERIES, DISTRIBUTION, QUESTION,
         PRESETS, INLINE, bytes, childNode, cssId, el, elementColumn,
         guessQuantity, heading, hintsOf, quantity, quantityFor, sectionHead,
         title } from "./format.js";
import { identify, labelFor } from "./controls.js";
// UX-303: §2's two drawings. They import nothing and take their
// formatter, so the quantity table stays here and the geometry stays
// there.
import { sparkline, strip, columnStrip, SERIES_MIN_POINTS,
         GRADE_ANNOTATION, GRADE_EXHIBIT } from "./drawings.js";
// UX-302: the style guide's §1 dispatch table, which decides *which*
// control draws a structured value. The controls live here; the choice
// between them lives there, so that "raw JSON unless deliberate" is a
// rule with one enforcement point rather than a habit.
import { CONTROLS, UNMAPPED, classify, noteUnmapped, depthSentence,
         shapeOf } from "./shapes.js";
import { enterTableFocus, focusedTable, leaveTableFocus, registerFocusTarget }
  from "./tablefocus.js";
import { parseThreshold, applyFilters, badgeText, rowJson, cellText,
         copy, applyTopN, presetColumns, applyPreset,
         rowsMarkdown } from "./tables.js";
import { PATH_HEAD, PATH_TAIL } from "./views.js";

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
      title: spec.title ?? title(spec.key, quantityName),
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
// of `<pre>`, the largest 8,191 - and `elements.blast_radius` scales to
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
      el("span", { class: "pair-key" }, `${title(name, kind)} `),
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
      { key: "value", title: title(key, measure), quantity: measure }] };
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
                           depth = 0, options = {}) {
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
  // `UX-319` (styleguide §3a.1 + `UX-187`): an **ordered** listing folds
  // head-and-tail, not top-N.
  //
  // `UX-262`'s Top-N is a *rank* bound - "the 25 biggest" - and that is
  // the right bound for a population. A path is not a population: its
  // meaning is its order, and the 25 longest steps of a 122-step chain
  // are not the chain. `UX-187` taught the text report to fold the
  // chain's middle and `UX-196` taught the drawing to; this is the
  // third surface, folded by the same two numbers.
  if (options.fold) foldTheMiddle(table, rows.length, options.fold);
  const uniform = statedOnce(table, specs, rows.length);
  const tools = interrogable(table, specs, rows.length, depth);
  if (uniform) tools.prepend?.(uniform);
  return { table, tools };
}

/**
 * `UX-349`: a column that never varies is a **fact about the table**.
 *
 * Measured when this was filed: fourteen columns across the signals
 * tables had exactly one distinct value over more than three rows. On
 * the eleven-row element table that is `false` printed eleven times
 * under `Is leaf`, spending a sixth of the width to repeat itself.
 *
 * So it is said once, above the table, and the column goes. Where the
 * value is *not* uniform nothing changes - this only ever removes a
 * column whose every cell was the same.
 *
 * **Three rows is the floor**, and it is `UX-226`'s: two rows that
 * happen to agree are a coincidence, not a fact about a population.
 * The rows stay in the document either way; it is the *column* that
 * goes, so `Copy 12 rows` and Ctrl-F still see what the payload had.
 */
function statedOnce(table, specs, total) {
  if (total <= SERIES_MIN_POINTS) return null;
  const said = [];
  for (const spec of specs) {
    if (!spec || spec.role === "element" || spec.key === elementColumn(specs)) {
      continue;
    }
    const cells = [...table.querySelectorAll(
      `td[data-column="${spec.key}"]`)];
    if (cells.length !== total) continue;
    // The **published** value, not the rendered one. Found by a
    // synthetic case: forty-eight durations from 1000 to 1047 µs all
    // format as `1 ms`, and keying on the text removed a column the
    // payload varies in - taking its sort key with it. A formatter
    // rounding a column flat is a fact about the formatter; this rule
    // is about a column that never varies.
    const raw = cells.map(
      (td) => td.getAttribute?.("data-raw") ?? td.textContent);
    if (new Set(raw).size !== 1) continue;
    said.push([spec.title ?? title(spec.key, spec.quantity),
               cells[0].textContent]);
    for (const cell of cells) cell.remove?.();
    const head = [...table.querySelectorAll("th")].find(
      (th) => th.getAttribute("data-column") === spec.key);
    head?.remove?.();
  }
  if (!said.length) return null;
  const note = el("p", { class: "muted uniform-columns",
                         "data-role": "uniform-columns",
                         "data-columns": String(said.length) });
  note.textContent = `All ${total.toLocaleString("en-US")} rows: `
    + said.map(([name, value]) => `${name} ${value}`).join(", ") + ".";
  return note;
}

/**
 * Hide a table's middle rows behind one control that says how many.
 *
 * The rows stay in the document - hidden, not removed - so Ctrl-F, the
 * export and `Copy shown rows` all see what they saw before, and
 * opening the fold is a `hidden` flip rather than a render.
 */
function foldTheMiddle(table, total, { head, tail, noun = "rows" }) {
  if (total <= head + tail + 1) return null;
  const body = table.querySelector?.("tbody");
  const all = [...(body?.querySelectorAll?.("tr") ?? [])];
  const middle = all.slice(head, all.length - tail);
  if (!middle.length) return null;
  for (const row of middle) row.hidden = true;
  const cells = all[0]?.children?.length ?? 1;
  const more = el("button", {
    type: "button", class: "fold-more", "data-folded": String(middle.length),
    // §3a.1: the count is visible before the click, and it names what
    // is behind it rather than promising "more".
    title: `Show the ${middle.length} ${noun} between the first ${head} `
           + `and the last ${tail}`,
  }, `+${middle.length} more ${noun} (${total} in all)`);
  const row = el("tr", { class: "fold-row", "data-fold-rows": String(middle.length) },
                 el("td", { colspan: String(cells) }, more));
  more.addEventListener?.("click", () => {
    for (const hidden of middle) hidden.hidden = false;
    row.hidden = true;
  });
  // Where the middle *begins*, not where it ends: the hidden rows
  // collapse to nothing, so this is what a reader sees between the two
  // ends - and DOM order is the order a screen reader and a `Tab` key
  // follow (`UX-254`'s lesson about the rail, one element down).
  body?.insertBefore?.(row, all[head] ?? null);
  return row;
}

/** One table as its own view: `buildTable`, in a section. */
export function renderTable(key, rows, hint = {}, node = undefined,
                            options = {}) {
  const { table, tools } = buildTable(key, rows, hint, node, 0, options);
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
  // UX-334: what these controls are called. The table key is the name
  // `viewstate.js` already keys this table's url state by, so the
  // control's `name` and its bookmarked parameter say the same word.
  const key = table.getAttribute?.("data-table") ?? "table";
  const badge = el("span", { class: "badge" }, badgeText(total, total));
  const refresh = () => {
    badge.textContent = badgeText(applyFilters(table, state), total);
  };

  // `UX-349`: **filters appear when the table is long enough to need
  // them.** The bound is the row cap §3 already sets - below it the
  // reader scans, at or above it the tools appear - and it is the same
  // number that decides whether a table opens bounded, because it is
  // the same question: is this a table somebody reads to the end.
  //
  // Measured before this: 12 of golden's 13 tables and 21 of
  // `macro_micro`'s 22 carried a filter row, and every one of them was
  // short enough to read at a glance. On the eleven-row element table
  // that was five inputs above eleven rows.
  const worthFiltering = total > TABLE_OPENS_BOUNDED_ABOVE;
  const box = worthFiltering ? el("input", {
    type: "search", class: "table-filter",
    placeholder: "filter rows…",
    "aria-label": "filter rows",
  }) : null;
  if (box) {
    identify(box, `filter-${key}`);
    box.addEventListener("input", () => { state.text = box.value; refresh(); });
  }

  // A threshold per quantity column, in the header, where the column
  // says what unit it is in.
  table.querySelectorAll("th").forEach((th, index) => {
    const spec = specs[index];
    if (!worthFiltering || !spec || !spec.quantity) return;
    // `UX-349`: and only where the column holds numbers. `> 10` under a
    // boolean was the tell - a column whose quantity was *guessed*
    // `count` by the fallback in `columnSpecs`, never declared, and
    // then given a numeric threshold box. Read off the rendered cells
    // rather than off the guess, which is where the truth is.
    // A column key is a schema identifier, so it needs no escaping -
    // the same reading `distributionStrip` makes two hundred lines
    // down, and `CSS.escape` is a browser global the guards' shim does
    // not have.
    const numeric = [...table.querySelectorAll(
      `td[data-column="${spec.key}"]`)]
      .some((td) => Number.isFinite(Number(td.getAttribute("data-raw"))));
    if (!numeric) return;
    const input = el("input", {
      type: "text", class: "th-filter", "data-column": spec.key,
      placeholder: PLACEHOLDER[spec.quantity] ?? "> 0",
      "aria-label": `threshold for ${spec.title ?? spec.key}`,
    });
    identify(input, `threshold-${key}-${spec.key}`);
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
    identify(preset, `top-${key}`);
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
  if (markdownBox) identify(markdownBox, `copy-markdown-${key}`);
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
    // `UX-355` (styleguide §4c): and it says so. A clipboard write is
    // invisible by construction, so the control acknowledges the press
    // itself - the same shape `copy-step`, `copy-sql` and `copy-view`
    // already use. This was the most numerous copy control on the page
    // (13 on `golden`, 23 on `macro_micro`) and the only one of the
    // four that reported nothing.
    copyRows.textContent = "\u2713 copied";
    // Back through `label`, not to a captured string: the count follows
    // the filter and the bound, so what it should say on the way back
    // is whatever it would say now.
    setTimeout(label, 1200);
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
  // "Nested" is measured in *tables*, not in calls: a section's own
  // table and a table `renderPairs` puts straight into a cell both
  // arrive at depth 0, and `renderStructured` hands `mapTable`
  // `depth + 1` for every level it descends - so depth 1 is a table
  // inside a value inside a cell, the one with no room.
  //
  // `UX-344` moved this bound by one. The threshold was `depth > 1`
  // because `signals.leaf_analysis.leaves_detail` sat two levels inside
  // its section; lifting the namespaces made `leaf_analysis` a section
  // of its own and the same cramped table one level nearer the top. The
  // rule is unchanged - a table inside a cell offers the way out - and
  // the number it is spelled with followed the document.
  const nested = depth > 0;
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
  // `UX-350`: **at any length.** The row cap decides whether a table is
  // *paged*, not whether its shape is worth showing - and gating the
  // strip on it meant the report's central table, eleven rows on one
  // fixture and four on the other, never drew the one §2 names.
  // Measured before this: one sparkline and zero strips on golden, in
  // a twenty-screen document. `columnStrip` already states rather than
  // draws below `SERIES_MIN_POINTS`, so a two-row table is still a
  // sentence.
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
    label: `${spec.title ?? title(spec.key, spec.quantity)} across all ${
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

export function liftedCriticalPath(document, node) {
  const rows = document?.[LIFTED_SECTION];
  if (!Array.isArray(rows) || !rows.length) return null;
  const child = childNode(node, LIFTED_SECTION);
  // `UX-319`: the chain's listing, folded by the chain's own numbers -
  // the same `PATH_HEAD`/`PATH_TAIL` the drawing uses, so the two
  // surfaces show the same chain rather than two elisions of it.
  return renderTable(LIFTED_SECTION, rows, hintsOf(child), child,
                     { fold: { head: PATH_HEAD, tail: PATH_TAIL,
                               noun: "elements" } });
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
// The seventh is not the same population at all. `wall_clock_share_us` is
// keyed by **task**:
//
//   element-keyed     app.bst
//   wall_clock_share_us  app.bst|BUILD|BUILD|0
//   union 88 keys, intersection 0
//
// It shares no keys with the other six, and nothing on the page said
// so. It stays its own table and says what its key is.
//
// `UX-344`: **the document says which six.** This file kept its own
// list of the element-keyed signals - and a note arguing the seventh
// out of it - because `signals` mixed the element population with
// tables that were not it. `elements` *is* that population: every map
// in it is keyed by element uid, and `wall_clock_share_us` is a key of
// the document beside it, drawn as its own section, saying in its own
// description that its keys are tasks. `top_blast_radius` is a ranking
// over the same population, so it is a member and an array - which is
// why the filter asks for a plain object rather than for an object.
/**
 * One row per element, one column per element-keyed signal.
 *
 * Returns `null` when the run carries none of them, so a payload
 * without the signals renders exactly as it did.
 */
export function elementSignalTable(elements, node, join = null,
                                   joinNode = undefined) {
  const present = Object.keys(elements ?? {}).filter(
    (name) => elements[name] && typeof elements[name] === "object"
              && !Array.isArray(elements[name]));
  if (present.length < 2) return null;
  const byElement = new Map();
  // UX-343: a merged column's unit is declared where the field came
  // *from*, not under `signals` - `weighted_duration_us` is declared on
  // `elements.blast_radius`'s value schema and `slack_us` on
  // `element_join`'s item. Resolving every column against the signals
  // node alone found neither, so three columns of the report's central
  // table were rendered from `guessQuantity`'s name-sniff. Found by the
  // console reader, on a real boot, not by reading the payload.
  const origin = new Map();
  for (const name of present) {
    const signalNode = childNode(node, name);
    for (const [uid, value] of Object.entries(elements[name])) {
      const row = byElement.get(uid) ?? { element: uid };
      // A record-valued signal (`blast_radius`) contributes its own
      // fields; a scalar one contributes itself under its name.
      if (value && typeof value === "object" && !Array.isArray(value)) {
        for (const [field, member] of Object.entries(value)) {
          if (member === null || typeof member !== "object") {
            row[field] = member;
            if (!origin.has(field)) {
              origin.set(field, childNode(childNode(signalNode, uid), field));
            }
          }
        }
      } else {
        row[name] = value;
        if (!origin.has(name)) origin.set(name, signalNode);
      }
      byElement.set(uid, row);
    }
  }
  // UX-338: `element_join` is the same population under a second
  // heading. `UX-215` published the two-plane join keyed by `element`,
  // and the page drew it as a table of its own - so every viewer of a
  // two-plane snapshot has seen all eleven elements twice since then.
  // `UX-289` had already settled the rule ("one element table, many
  // presets"); this applies it to the columns `UX-215` added, by
  // merging them into the row that element already has.
  //
  // Only onto rows Plane 1 put in play: the join "never introduces an
  // element" is `views.js`'s own statement of what it is, and a join
  // row for an element the schedule does not carry would be a
  // population this table does not claim to be.
  const joinedIn = [];
  for (const row of Array.isArray(join) ? join : []) {
    const uid = row?.element;
    const existing = uid && byElement.get(uid);
    if (!existing) continue;
    for (const [field, value] of Object.entries(row)) {
      if (field === "element" || value === null
          || typeof value === "object") continue;
      // Plane 1 wins a name collision: this table's other columns are
      // its own, and a join field that shadowed one would change what
      // a column means without changing its heading.
      if (field in existing) continue;
      existing[field] = value;
      if (!origin.has(field)) origin.set(field, childNode(joinNode, field));
      if (!joinedIn.includes(field)) joinedIn.push(field);
    }
  }

  const rows = [...byElement.values()];
  if (!rows.length) return null;
  const columns = [...new Set(rows.flatMap(Object.keys))]
    .filter((name) => name !== "element");
  const hint = {
    [COLUMNS]: [{ key: "element", title: "element" },
                ...columns.map((name) => {
                  const measure = quantityFor(origin.get(name)
                                              ?? childNode(node, name), name)
                    ?? guessQuantity(name) ?? "count";
                  return { key: name, title: title(name, measure),
                           quantity: measure };
                })],
    [QUESTION]: "Which element should I look at?",
  };
  return { rows, hint, merged: present, joined: joinedIn };
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
 *
 * `UX-338` extends that from rows to **columns**. `Plane 2 (sandbox)`
 * asks a question only a two-plane run can answer, and on a run with
 * no Plane 2 report every column it names but `element` is absent - so
 * the view rendered as two columns under a heading promising five.
 * Measured on `macro_micro` served without its `plane2.json`, which is
 * how this was found: a control that is present and answers nothing is
 * the dead-button defect `UX-194` removed everywhere else.
 *
 * The preset declares its subject (`requires`), because "which of my
 * columns make me this view" is a question only its author can
 * answer. Inferring it was tried and is wrong: `Plane 2 (sandbox)`
 * also names `element_durations`, which every run carries, so any
 * "some column is present" rule keeps offering it.
 */
export function presetTable(key, rows, presets, hint, node, payload) {
  const carried = new Set(rows.flatMap(Object.keys));
  // Every column the preset declares as its subject, or it is not
  // offered. A preset with no `requires` is unaffected, which is all of
  // them but one.
  const answerable = (preset) =>
    (preset?.requires ?? []).every((name) => carried.has(name));
  const usable = (presets ?? [])
    .filter(answerable)
    .map((preset) => ({ preset, view: applyPreset(preset, rows, payload) }))
    .filter((entry) => entry.view);
  if (usable.length < 2) return null;

  const slot = el("div", { class: "preset-table", "data-presets":
                           usable.map((e) => e.preset.name).join("|") });
  const select = el("select", { class: "preset-view",
                                "data-table": key,
                                "aria-label": "View" });
  identify(select, `view-${key}`);
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
    // `UX-366`: **the caption says how big this view is; the badge
    // says how much of it is shown** - one fact each, and the only
    // pair that cannot go stale, because the limit moves the
    // shown-count and this is drawn once. See
    // `test_all_rows_means_all_rows.py`.
    body.replaceChildren(
      el("p", { class: "muted" },
         preset.question ? `${preset.question} ` : "",
         view.total >= rows.length
           ? `all ${rows.length} elements`
           : `${view.total} of ${rows.length} elements`),
      built.tools, built.table);
  };
  select.addEventListener("change", () => draw(select.value));
  draw(usable[0].preset.name);
  // UX-334: the label points at the select rather than floating beside
  // it - `<label>` with neither `for` nor a nested control is the
  // second complaint the Issues panel raised on this page.
  const presetLabel = el("label", { class: "preset-label" }, "View: ");
  labelFor(presetLabel, select, `view-${key}`);
  slot.append(el("div", { class: "preset-bar" }, presetLabel, select), body);
  return { node: slot, select, draw, presets: usable.map((e) => e.preset) };
}

export function renderPairs(key, object, hint = {}, node = undefined,
                            payload = undefined, root = undefined) {
  const direction = hint[DIRECTION];
  const list = el("dl", { class: "pairs" });
  // UX-268: the element-keyed signals leave the pair list and become
  // one table, so they are drawn once rather than six times.
  const joined = key === "elements"
    ? elementSignalTable(object, node, payload?.element_join,
                         childNode(root, "element_join"))
    : null;
  const merged = new Set(joined?.merged ?? []);
  for (const [name, value] of Object.entries(object)) {
    if (merged.has(name)) continue;
    // UX-270: the critical path is its own section, not a row inside
    // this one. It is also the one member that rendered a whole
    // `<section>` into a `<dd>` - the nesting UX-267 removed
    // everywhere else.
    // UX-201: each member resolved against *its own* schema node, not
    // guessed from its name. `deltas` was hinted at the top level and
    // still name-sniffed every member inside it.
    const child = childNode(node, name);
    // UX-343: asked only of a number. `quantityFor` complains under
    // `BGA_STRICT_HINTS` when it had to name-sniff, and asking it about
    // `attribution_hints.idle_us` - a *sentence*, keyed by the metric
    // it explains - produced eight complaints per boot about units no
    // number here needs. A guess nothing renders from is noise in the
    // one channel that is supposed to name real gaps.
    const kind = typeof value === "number" ? quantityFor(child, name) : null;
    const described = hintsOf(child).description;
    let cell;
    // UX-208: a nested array of objects is a *table*, not a JSON dump.
    // `critical_path_detail` - the list of elements the whole
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
    const { term, describe } = describedTerm(name, described, {},
                                             hintsOf(child)[INLINE], kind);
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
 * `UX-346`: **and the door has to close.** It did not - `.description`
 * sets `display`, which beats `[hidden]`'s UA rule, so the sentence
 * rendered whatever the marker said, and 43% of the golden page's
 * words were the contract's glossary. The CSS closes it; `inline` is the declared
 * exception (`bga:inline`, `name` or `caveat`), which keeps its
 * sentence beside the value and draws no marker at all.
 *
 * Returns `{ term, describe }` - the `<dt>`, and the node to put in the
 * `<dd>`, or `null` when the schema describes nothing.
 */
export function describedTerm(name, description, attrs = {}, inline = null,
                              kind = null) {
  const term = el("dt", { ...attrs, "data-key": name,
                          title: description ?? null,
                          "data-described": description ? "true" : null,
                          "data-inline": inline ?? null },
                  title(name, kind));
  if (!description) return { term, describe: null };
  // UX-346: a declared exception is not behind a door at all. There is
  // no marker for it either - a `?` beside a sentence already on screen
  // is the duplication this item was filed on.
  if (inline) {
    return { term, describe: el("span", { class: "description",
                                          "data-role": "description",
                                          "data-inline": inline,
                                          "data-describes": name },
                                description) };
  }
  const sentence = el("span", { class: "description",
                                "data-role": "description",
                                "data-describes": name, hidden: "" },
                      description);
  sentence.hidden = true;
  const marker = el("button", {
    type: "button", class: "describe", "data-describe": name,
    "aria-expanded": "false",
    // `UX-279`: the control says what it does before it is pressed.
    title: `What ${title(name, kind)} means`,
  }, "?");
  marker.addEventListener?.("click", () => {
    const open = marker.getAttribute("aria-expanded") === "true";
    marker.setAttribute("aria-expanded", open ? "false" : "true");
    sentence.hidden = open;
  });
  term.append(marker);
  return { term, describe: sentence };
}

// UX-262: above this many rows a table opens on its top 25 rather than
// on everything. 40 is chosen against the shapes that occur: the
// 1,202-element run's widest table is 26 rows and stays whole, and a
// 122-deep critical path is 132 and does not. A bound that fired on
// the ordinary case would train readers to reset it every load.
export const TABLE_OPENS_BOUNDED_ABOVE = 40;
