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
import { plainValue, served } from "./primitives.js";
import { COPY_FORMAT_MIRROR, readCopyFormat } from "./viewstate.js";
import { BARE_KEY, COMMAND, QUANTITY, COLUMNS, SERIES, DISTRIBUTION, KEYED_BY,
         KEYED_BY_BINARY, KEYED_BY_ELEMENTS, KEYED_BY_TASK_UID, bytes,
         childNode, cssId, dataKeyed, el, elementColumn, guessQuantity, heading,
         hintsOf, itemsAsShown, keyAsShown, quantity, quantityFor, readerLabel,
         sectionHead, tally, taskUid, title } from "./format.js";
import { commandLine, identify, say } from "./controls.js";
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
         distributionStrip, shapeOf } from "./shapes.js";
import { enterTableFocus, focusedTable, leaveTableFocus, registerFocusTarget }
  from "./tablefocus.js";
import { parseQuery, applyFilters, badgeText, rowJson, jsonNames, cellText,
         copy, presetColumns, openingBound, plural, sortable, ownRows,
         ownBody, showAlso, columnCells, rowsMarkdown, showSort, labelSorts, ownHeads, STATED, ALL_ROWS_CEILING, reorder }
  from "./tables.js";
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

// `UX-1029` (styleguide §3k): `boundedList`'s paging step - a reveal
// mounts at most this many names besides the head and tail it keeps,
// whatever number of times it is pressed.
export const REVEAL_STEP = 60;

/** `{k: v}` as one line - no click, because there is nothing to hide. */
function inlineObject(value, node) {
  const parts = [];
  for (const [name, member] of Object.entries(value)) {
    const kind = quantityFor(childNode(node, name), name);
    parts.push(el("span", { class: "pair" },
      el("span", { class: "pair-key", "data-key": name },
        `${readerLabel(title(name, kind, dataKeyed(node, name)))} `),
      el("span", { class: typeof member === "number" ? "num" : null,
                   "data-raw": member === null ? "" : String(member) },
         typeof member === "number" ? quantity(member, kind) : plainValue(member))));
  }
  return el("span", { class: "inline-object" }, ...parts);
}

/**
 * A map as a bounded, searchable table - the table only, never a
 * section (`buildTable`, not `renderTable`).
 *
 * `UX-864` exports this: `renderSection`'s own map routing is its
 * only caller outside this file. The header/noun/task-uid pass a
 * top-level section needs lives there, beside that one call, so this
 * function's body is unchanged from its cell-only years.
 */
export function mapTable(key, rows, hint, node, nested, depth = 0, path = key, list = false, beside = [], titles = null) {
  let declared = hint;
  if (!nested) {
    // A `{name: number}` map's value column has to *declare* a
    // quantity: `presetColumns` selects on the declaration, so without
    // this the table gets no `Top N` control and therefore no bound
    // (`UX-262`).
    //
    // `UX-407`: **unless the node is a record.** A schema that names
    // its members in `properties` is describing one value per member,
    // each with its own unit - `projection` holds three durations and
    // a capacity map - and there is no column quantity to declare. The
    // `?? "count"` fallback invented one anyway, which put `43200000`
    // in a cell whose member is declared `duration_us` and drew a
    // strip reading `19050000 -> 43200000 across 3 rows` over three
    // numbers that are not a distribution. Left undeclared, the cell
    // renders each member in its own unit (`buildTable`) and the strip
    // is not drawn, which is the honest answer for a record.
    const record = Boolean(node?.properties);
    const measure = hintsOf(node)[QUANTITY] ?? guessQuantity(key)
      ?? (record ? null : "count");
    // UX-1173: a list's index is not a name, so a list draws its items alone.
    declared = { ...hint, [COLUMNS]: [
      // `UX-1207`: a top-level map's `titles` name both columns once, for th, cell labels and Copy.
      ...(list ? [] : [{ key: "key", title: titles?.key ?? "Name" }]), ...beside,
      { key: "value", title: titles?.value ?? node?.additionalProperties?.title ?? title(key, measure), quantity: measure }] };
  }
  const { table, tools } = buildTable(path, rows, declared, node, depth);
  // `UX-1163`'s rule: a list left one column says its name in its fold, not a header.
  if (list && table.children[0]?.children[0]?.children.length < 2) table.children[0].remove();
  const box = el("div", { class: "map-table", "data-bounded": "map" },
                 tools, table);
  return box;
}

/**
 * `UX-641`: a scalar list too long for a cell - head and tail, with a count.
 *
 * `UX-319`'s bound, one container down. A table is the wrong shape
 * here: the 102 uids on one level of the 1,202-element run built a
 * 102-row interrogable table inside a `<td>`, and twelve of those took
 * the page to 11,068 DOM elements against a budget of 5,500 - and put
 * a filter input on a 14-row table that did not ask for one.
 *
 * `PATH_HEAD` items, the control, `PATH_TAIL` items - the control
 * where the middle begins, because DOM order is reading order.
 *
 * `UX-1029` (styleguide §3k): the control used to reveal the whole
 * middle in one press - 3,625 names, one 72,703-character run, on the
 * 4,002-element run's `resource_blast` populations. It now pages
 * `REVEAL_STEP` names at a time, **replacing** what the last press
 * showed rather than appending to it, so no number of presses mounts
 * more than `REVEAL_STEP` names besides the head and tail it keeps.
 *
 * Review (#295): a press had no way back. `prev` reuses `interrogable`'s
 * "‹ Prev"/position shape - `page` is a fixed `REVEAL_STEP`-wide window
 * index into `middle` (`-1` at rest), so backward always lands on the
 * same window forward built, even where the last one is a short remainder.
 */
function boundedList(value, noun, item = null) {
  const items = value.map(String);
  const head = items.slice(0, PATH_HEAD);
  const tail = items.slice(items.length - PATH_TAIL);
  const middle = items.slice(head.length, items.length - tail.length);
  const pages = Math.ceil(middle.length / REVEAL_STEP);
  // `item` draws each shown name as a node (a finding's element link); text otherwise.
  const run = (names, lead) => (item
    ? names.flatMap((name, i) => [i || lead ? ", " : "", item(name)])
    : [names.length ? `${lead ? ", " : ""}${names.join(", ")}` : ""]);
  const first = el("span", { class: "list-head" }, ...run(head, false));
  const shownMiddle = el("span", { class: "list-middle" }, "");
  const last = el("span", { class: "list-tail" }, ...run(tail, true));
  const position = el("span", { class: "list-position" }, "");
  const prev = el("button", { type: "button", class: "list-prev",
                              "aria-label": `previous ${noun}` }, "‹ Prev");
  const more = el("button", { type: "button", class: "fold-more", "data-noun": noun });
  let page = -1;
  const render = () => {
    const start = Math.max(0, page) * REVEAL_STEP;
    const chunk = page < 0 ? [] : middle.slice(start, start + REVEAL_STEP);
    shownMiddle.replaceChildren(...run(chunk, true));
    const remaining = middle.length - start - chunk.length;
    prev.hidden = page <= 0;
    more.hidden = remaining <= 0;
    more.setAttribute("data-folded", String(remaining));
    more.title = `Show the next ${Math.min(REVEAL_STEP, remaining)} ${noun} `
      + `of the ${remaining} still between the first ${head.length} and `
      + `the last ${tail.length}`;
    more.textContent = `+${tally(remaining)} More ${noun} (${tally(items.length)} in all)`;
    position.textContent = page < 0 ? "" : `${noun} ${start + 1}-`
      + `${start + chunk.length} of ${middle.length} (page ${page + 1} of `
      + `${pages})`;
  };
  more.addEventListener?.("click", () => {
    page = Math.min(page + 1, pages - 1);
    render();
  });
  prev.addEventListener?.("click", () => {
    page = Math.max(page - 1, -1);
    render();
  });
  render();
  return el("div", { class: "bounded-list", "data-bounded": "list",
                     "data-items": String(items.length),
                     "data-shown": String(head.length + tail.length) },
            first, shownMiddle, el("span", { class: "list-pager" },
                                   prev, position, more), last);
}

/** `UX-1053` (review): a list past the bound whose shown names are `item`'s nodes. */
export function foldedList(key, value, item) {
  return folded(title(key), value,
                boundedList(value, title(key).toLowerCase(), item), key);
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
    columns: declared[COLUMNS] ?? null, series: declared[SERIES] ?? null,
    distribution: declared[DISTRIBUTION] ?? null,
    command: declared[COMMAND] ?? null, depth, nestLimit: CELL_NEST_LIMIT,
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
      unit: String(declared[SERIES]), grade: GRADE_EXHIBIT, marks: hint.marks ?? [],
      format: (n) => quantity(n, quantityFor(node, key)),
    });
  }
  // `UX-429`: one line, monospace, with the copy control beside it.
  // `commandLine` returns `[code, button]` and this branch is a
  // *cell*, so it takes the code alone - the button belongs where
  // there is room for it, which is the two step lists in
  // `decision.js` and `views.js`.
  //
  // Restored by `UX-450`. It was deleted to buy `UX-429` four
  // lines under the 1,500 ceiling, which left one branch of a §1
  // table bare where every branch around it carries a note.
  if (control === CONTROLS.COMMAND) return commandLine(value)[0];
  if (control === CONTROLS.DENSITY_STRIP) {
    return strip(value, {
      countKey: String(declared[DISTRIBUTION]), grade: GRADE_EXHIBIT,
      name: title(key, quantityFor(node, key)),
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
    // `UX-826`: a task-uid array shows `taskUid`'s split, not the raw
    // join key - the same declaration `keyAsShown` reads for a map's
    // keys, read here for a plain array's items.
    const shown = itemsAsShown(value, hint) ?? value;
    if (control === CONTROLS.INLINE_LIST) {
      return el("span", {}, shown.map(readerLabel).join(", "));
    }
    if (control === CONTROLS.FOLDED_LIST) {
      // `UX-641`: **past the row bound a cell's list is bounded too**,
      // and by `UX-319`'s head-and-tail fold rather than by a second
      // table. Nothing bounded a cell before: the 102 uids on one level
      // of the 1,202-element run built a 102-row interrogable table
      // inside one `<td>`, twelve times over - 11,068 DOM elements
      // against the page's budget of 5,500, and a filter input on a
      // 14-row table that did not ask for one.
      //
      // The threshold is `TABLE_OPENS_BOUNDED_ABOVE`'s, so this
      // replaces that bound where it applied rather than adding a
      // second: measured on both committed fixtures, no cell is over
      // it; at 1,202 elements twelve are and all twelve are this key.
      if (shown.length > TABLE_OPENS_BOUNDED_ABOVE) {
        return folded(title(key), value,
                      boundedList(shown, title(key).toLowerCase()), path);
      }
      const rows = shown.map((item, at) => ({ key: String(at), value: item }));
      return folded(title(key), value,
                    mapTable(key, rows, hint, node, false, depth + 1, path, true),
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

/** `UX-1152` (styleguide §3d): one row with no element column is a record, drawn as pairs - an element row keeps its table's Inspect. */
export function oneRecord(rows, hint, node) {
  // A row holding a nested table keeps its table, so the nested one keeps its fold and rail.
  const nested = (v) => Array.isArray(v) && v.some((i) => i && typeof i === "object");
  return rows.length === 1 && !Object.values(rows[0]).some(nested)
    && !elementColumn(columnSpecs(hint, rows, node));
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
  // `UX-1186`: a list's key columns, or a map's `key`.
  const keyed = [hint[KEYED_BY] ?? []].flat();
  const declared = columnSpecs(hint, rows, node).map((spec) => {
    const kind = keyed.includes(spec.key) ? spec.key
      : spec.key === "key" && keyed.length === 1 ? keyed[0] : null;
    return kind && !spec.role ? { ...spec, role: kind } : spec;
  });
  // `UX-1214`: an undrawn list column has no head, cell or Copy column; the box reads it off the row.
  const specs = declared.filter((spec) => spec.drawn !== false);
  const undrawn = declared.filter((spec) => spec.drawn === false);
  const columns = specs.map((s) => s.key);
  // `UX-1199`: a keyed list column names every element its row holds, for Focus.
  const listed = specs.find((spec) => spec.role === KEYED_BY_ELEMENTS)?.key;
  // `UX-526`: how many rows the table *has*. The DOM used to answer
  // that and no longer does - a row past the bound leaves it - so the
  // population is published where a reader and a guard can both read it.
  const table = el("table", { "data-table": key,
                              "data-rows": String(rows.length) });
  const head = el("tr");
  for (const spec of specs) {
    head.append(el("th", {
      class: spec.numeric ? "num" : null,
      scope: "col", "data-column": spec.key,
      "data-sortable": String(spec.sortable),
      // `UX-835`: the declared quantity, not the sampled `num` class
      // above - so a guard can tell "quantity, unfiltered" from
      // "no quantity" without re-deriving `columnSpecs`.
      "data-quantity": spec.quantity ?? null,
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
      // `UX-407`: and the *unit* comes from there too.
      //
      // `mapTable` declares one quantity for the whole `value` column,
      // falling back to `count` - which is right for a homogeneous map
      // (`{element: duration_us}`) and wrong for a **record**, where
      // every member has its own unit. `projection` is a record:
      // `replayed_baseline_us` printed `43200000` on the page beside a
      // terminal saying `43.2s`, two surfaces disagreeing about one
      // number, which is the property this viewer is built on.
      //
      // Only an *explicit* per-member declaration wins, and only where
      // the row key is the thing being described (`UX-290`'s rule,
      // which resolved the schema node here and left the rendering
      // reading the column's). A real table is untouched: there
      // `describes === column`, and `columnSpecs` already consulted
      // the same node.
      const perMember = describes === column ? null : hintsOf(child)[QUANTITY];
      const kind = numeric ? (perMember ?? spec.quantity) : null;
      tr.append(el("td",
        { class: numeric ? "num" : null,
          "data-column": column, "data-label": spec.title,
          "data-raw": raw === undefined || raw === null ? ""
            : structural ? JSON.stringify(raw) : String(raw) },
        structural
          // `UX-407`: the column too, where it is not already the row.
          //
          // `UX-292` keyed a nested table by its row because a map
          // table's cells are all in a column called `value`. A
          // *record* row with several structural columns is the other
          // half of the same problem, and `restructuring`'s one row
          // holds three of them: its elements list, its edge table and
          // its projection all opened and filtered as one state key.
          // Where the row key already names the column (`describes ===
          // rowId`, which is every map table) the path is unchanged.
          ? renderStructured(describes, raw, hintsOf(child), child, depth,
                             String(describes) === String(rowId)
                               ? `${key}.${rowId}`
                               : `${key}.${rowId}.${column}`)
          : numeric ? quantity(raw, kind)
          : typeof raw === "string" ? renderText(column, raw, memberTitle(column, raw, node))
          : plainValue(raw)));
    }
    if (Array.isArray(row?.[listed])) tr.setAttribute("data-elements", row[listed].join(" "));
    for (const spec of undrawn) if (Array.isArray(row?.[spec.key])) tr.setAttribute(`data-list-${spec.key}`, row[spec.key].join(" "));
    body.append(tr);
  }
  table.append(body);
  // `UX-1177`: a fold name two record rows share takes its row, so it reads alone in the rail, the tree and Jump.
  const shared = specs.map(() => []);
  for (const tr of body.children) {
    const first = tr.children[0];
    if (!first || first.getAttribute("data-column") === "key") continue;
    [...tr.children].forEach((td, at) => {
      const fold = at ? [...td.children].find((node) => node.className === "map") : null;
      const name = [...(fold?.children[0]?.children ?? [])].find((node) => node.className === "map-name");
      if (name) shared[at].push([name, first.getAttribute("data-raw") || first.textContent]);
    });
  }
  for (const [name, row] of shared.filter((names) => names.length > 1).flat()) {
    name.textContent += ` \u00b7 ${specs[0].title} ${row}`;
  }
  sortable(table);
  // UX-205: the tools. Sorting alone cannot reduce 1,202 rows to the
  // twelve that matter, and the page renders every row of every array
  // unconditionally - the right default for a viewer, unusable without
  // something to narrow it with.
  // UX-208: a declared element column earns every row a generic
  // Inspect - one affordance, no per-table code, because the *schema*
  // says which values are element uids.
  if (keyed.length) table.setAttribute("data-keyed-by", keyed.join(" "));
  const binaryColumn = specs.find((spec) => spec.role === KEYED_BY_BINARY)?.key;
  const taskColumn = specs.find((spec) => spec.role === KEYED_BY_TASK_UID)?.key;
  const uidColumn = elementColumn(specs) ?? taskColumn;
  for (const tr of binaryColumn ? ownRows(table) : []) {
    const cell = [...tr.children].find((td) => td.getAttribute("data-column") === binaryColumn);
    if (cell) tr.setAttribute("data-binary", cell.getAttribute("data-raw") || cell.textContent);
  }
  if (uidColumn) {
    table.setAttribute("data-element-column", uidColumn);
    for (const tr of ownRows(table)) {
      const cell = [...tr.children].find(
        (td) => td.getAttribute("data-column") === uidColumn);
      if (!cell) continue;
      // `UX-1244`: an empty raw is a row naming no element (a builders step), never the word "none".
      const raw = cell.hasAttribute("data-raw") ? cell.getAttribute("data-raw") : cell.textContent;
      if (!raw) continue;
      const uid = uidColumn === taskColumn ? taskUid(raw).element : raw;
      tr.setAttribute("data-element", uid);
      cell.append(el("a", { class: "inspect", href: `#${cssId(uid)}`,
                            title: `Find ${uid} elsewhere in this report`,
                            "aria-label": `Find ${uid}` },
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
  const { note: uniform, gone } = statedOnce(table, specs, rows.length);
  // `UX-1151`: a column said once above the table ranks nothing - no preset over it.
  const tools = interrogable(table, specs.filter((spec) => !gone.has(spec.key)),
                             rows.length, depth, undrawn);
  // `UX-1055`: after `copy-rows`, not before it - a plain `prepend`
  // put this note ahead of `copy-rows`, undoing its guaranteed first
  // place in the row (styleguide §3l).
  if (uniform) {
    const after = tools.querySelector?.(".copy-rows");
    if (after) after.after(uniform);
    else tools.prepend?.(uniform);
  }
  // `UX-1176`: named once it is placed, since its section is where the name comes from.
  globalThis.queueMicrotask?.(() => nameTable(table));
  return { table, tools };
}

/** `UX-1176`: a table's accessible name - its section's question, then the field and the fold it sits in. */
export function nameTable(table) {
  if (table.getAttribute?.("aria-label") || !table.closest) return;
  const said = (node) => (node?.textContent ?? "").replace(/[\u25b8\u25be]/g, "").trim();
  // Children walked, not `:scope` selectors, so the shim reads what a browser does.
  const child = (node, test) => [...(node?.children ?? [])].find(test) ?? null;
  const tag = (name) => (node) => String(node.tagName).toLowerCase() === name;
  const section = table.closest("section[data-section]");
  const head = child(section, (node) => String(node.className).split(" ").includes("section-head")) ?? section;
  const dd = table.closest("dd");
  const fold = table.closest("details");
  const summary = child(fold, tag("summary"));
  const parts = [said(child(head, (node) => /^h[23]$/i.test(node.tagName))),
    dd?.previousElementSibling && tag("dt")(dd.previousElementSibling) ? said(dd.previousElementSibling) : "",
    fold && (!dd || fold.closest("dd") === dd) ? said(child(summary, (node) => node.className === "map-name")) : ""];
  const name = [...new Set(parts.filter(Boolean))].join(" \u203a ");
  if (name) table.setAttribute("aria-label", name);
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
  const gone = new Set();
  if (total <= SERIES_MIN_POINTS) return { note: null, gone };
  const said = [];
  const stash = {};
  for (const spec of specs) {
    if (!spec || spec.role === "element" || spec.key === elementColumn(specs)) {
      continue;
    }
    const cells = columnCells(table, spec.key);
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
    // `UX-1195`: the box still reads it - a threshold only where the value is a number.
    stash[spec.key] = { raw: raw[0], shown: cells[0].textContent, spec: { ...spec, stated: true,
      quantity: Number.isFinite(Number(raw[0])) && raw[0] !== "" ? spec.quantity : null } };
    gone.add(spec.key);
    for (const cell of cells) cell.remove?.();
    const head = [...table.querySelectorAll("th")].find(
      (th) => th.getAttribute("data-column") === spec.key);
    head?.remove?.();
  }
  if (!said.length) return { note: null, gone };
  STATED.set(table, stash);
  // `UX-1163`: a short table left one column is a list, with no header.
  const head = table.children[0];
  if (total <= TABLE_OPENS_BOUNDED_ABOVE && head.children[0].children.length < 2) head.remove();
  const note = el("p", { class: "muted uniform-columns",
                         "data-role": "uniform-columns",
                         "data-columns": String(said.length) });
  note.textContent = "Every row: "
    + said.map(([name, value]) => `${name} ${value}`).join(", ") + ".";
  return { note, gone };
}

/**
 * Hide a table's middle rows behind one control that says how many.
 *
 * `UX-526`: the middle used to stay in the document, hidden. It does
 * not any more on a table the row bound also reaches - `applyFilters`
 * holds what it does not show out of the DOM - so the control puts them
 * back through `showAlso` rather than flipping `hidden`.
 */
function foldTheMiddle(table, total, { head, tail, noun = "rows" }) {
  if (total <= head + tail + 1) return null;
  const body = ownBody(table);
  const all = ownRows(table);
  const middle = all.slice(head, all.length - tail);
  if (!middle.length) return null;
  // `UX-1196`: marked, so print shows them, Copy takes them and a landing opens the fold.
  for (const row of middle) { row.hidden = true; row.setAttribute("data-fold-middle", ""); }
  const cells = all[0]?.children?.length ?? 1;
  const more = el("button", {
    type: "button", class: "fold-more", "data-folded": String(middle.length),
    // §3a.1: the count is visible before the click, and it names what
    // is behind it rather than promising "more".
    title: `Show the ${middle.length} ${noun} between the first ${head} `
           + `and the last ${tail}`,
  }, `+${tally(middle.length)} More ${noun} (${tally(total)} in all)`);
  const row = el("tr", { class: "fold-row", "data-fold-rows": String(middle.length) },
                 el("td", { colspan: String(cells) }, more));
  more.addEventListener?.("click", () => {
    // `UX-526`: through `showAlso`, because on a table long enough to
    // also open bounded the middle rows are held out of the document
    // rather than merely hidden, and un-hiding a detached row draws
    // nothing.
    showAlso(body, middle);
    row.hidden = true;
  });
  // Where the middle *begins*, not where it ends: the hidden rows
  // collapse to nothing, so this is what a reader sees between the two
  // ends - and DOM order is the order a screen reader and a `Tab` key
  // follow (`UX-254`'s lesson about the rail, one element down).
  body?.insertBefore?.(row, all[head] ?? null);
  return row;
}

/** `UX-1177`: narrow section `id`'s table to `query`, as a reader typing it would. */
export function filterSection(doc, id, query) {
  const box = doc.getElementById(id)?.querySelector("input.table-filter");
  if (!box) return;
  box.value = query;
  box.dispatchEvent(new Event("input", { bubbles: true }));
  return box;
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
 * The filter bar (one grammar: words, `column:value`, thresholds) and the copy affordances.
 *
 * Every comparison runs against `data-raw` - the published value - not
 * against the formatted cell text. Comparing "1.2s" to "5s" as strings
 * is the defect this shape exists to prevent, and `UX-201`'s column
 * metadata is what makes `> 5s` parseable: the column declares that it
 * is a `duration_us`, so the suffix has a meaning.
 */
export function interrogable(table, specs, total, depth = 0, undrawn = []) {
  const state = { text: "", thresholds: {}, exact: [], top: null, sort: null };
  const narrowed = () => Boolean(state.text.trim() || Object.keys(state.thresholds).length || state.exact.length);
  // UX-334: what these controls are called. The table key is the name
  // `viewstate.js` already keys this table's url state by, so the
  // control's `name` and its bookmarked parameter say the same word.
  const key = table.getAttribute?.("data-table") ?? "table";
  // `UX-1162`: each tool's accessible name ends with its table's.
  // `UX-1177`: a phrase - "levels.1.elements" reads "Level 1 elements"; a published name keeps its case.
  const parts = key.split(".");
  // `UX-1197`: the task table's tools are named for its tasks, not for the share it also holds.
  const named = parts.length === 1 && specs.some((spec) => spec?.role === KEYED_BY_TASK_UID) ? "Tasks" : parts.map((part, i) => {
    const said = title(part, guessQuantity(part));
    const word = i && said !== part ? said.toLowerCase() : said;
    return /^\d+$/.test(parts[i + 1] ?? "") ? word.replace(/s$/, "") : word;
  }).join(" ");
  // `UX-1163`: at rest `Copy N rows` is the count; the badge says `N of M`.
  const rest = badgeText(total, total);
  // UX-1169: a live region, so a typist hears the count the filter leaves; `UX-1176`: mounted empty at rest.
  const badge = el("span", { class: "badge", role: "status" });
  // Review (#295), `UX-1028`: `filtered` - the text/threshold
  // population, before `top`'s slice - is what the paging step below
  // measures its position and bounds against, not `total`, which
  // disagrees with the page the moment a filter narrows it.
  let pagerRefresh = null;
  let relabel = null;
  let restart = null;
  let rewind = null;
  let shape = null;
  let rank = null;
  let resting = null;
  const few = total <= FEW_ROWS;
  // `UX-1197`: the window and a sort other than the opening rank are said in the one live region.
  // `UX-1223`: the rank is the resting sort only on a table that opened ranked.
  const view = () => {
    const sort = state.sort && (state.sort.column !== opening?.top.column || state.sort.direction !== "descending")
      ? state.sort : null;
    const head = sort && ownHeads(table).find((th) => th.getAttribute("data-column") === sort.column);
    return { offset: state.top?.offset ?? 0, sorted: sort ? `${head?.textContent.trim() || sort.column}, ${sort.direction}` : "",
             narrowed: narrowed() };
  };
  const refresh = () => {
    // `applyFilters` also writes `state.filtered` and `state.kept` - the pre-`top` population.
    const said = badgeText(applyFilters(table, state), total, state.filtered, view());
    badge.textContent = said === rest ? "" : said;
    // `UX-1224`: paper drops the box; the badge prints its filter.
    const typed = box?.value.trim();
    if (typed) badge.setAttribute("data-filter", typed); else badge.removeAttribute("data-filter");
    pagerRefresh?.();
    relabel?.();
    // UX-1158: the strip draws, and counts, the rows the filter kept; `UX-1170`: none at two or fewer.
    // `UX-1198`: an emptied box gets the strip it opened with back, its route id unchanged.
    shape?.replaceWith?.(shape = (narrowed() ? distributionStrip(table, specs, total, few || state.filtered <= FEW_ROWS,
                                                                 state.kept) : resting) ?? el("span"));
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
  // `UX-1191` (§3d): one box, one grammar - `binary:ld` exact, `> 5s` a threshold, a word a substring.
  const keyed = specs.find((spec) => ["element", "binary", "task_uid"].includes(spec?.role));
  // `UX-349`: a threshold only where the column holds numbers - a boolean guessed `count` takes none.
  const filterable = specs.map((spec) => !worthFiltering || !spec?.quantity || columnCells(table, spec.key)
    .some((td) => Number.isFinite(Number(td.getAttribute("data-raw")))) ? spec : { ...spec, quantity: null });
  const primary = filterable.find((spec) => spec?.quantity && spec.numeric !== false);
  const jumps = Boolean(table.getAttribute?.("data-keyed-by"));
  const box = worthFiltering ? el("input", {
    type: "search", class: "table-filter",
    // `UX-1179`: Jump reaches the rows a bound detaches, in the key hint's place so it fits at 390.
    placeholder: ["filter", !jumps && keyed && `${keyed.role === "task_uid" ? "op" : keyed.role}:\u2026`,
                  primary && (PLACEHOLDER[primary.quantity] ?? "> 0"), jumps && "or Jump\u2026"].filter(Boolean).join(", "),
    // `UX-1198`: born with the state an input writes, so a focus that drives the box and hands it back changes nothing.
    "aria-label": `Filter rows: ${named}`, "aria-invalid": "false",
    title: ["a word matches any cell; column:value that column exactly (value* its start); column > 5s, or a bare > 5s, a threshold",
            ...undrawn.map((spec) => spec.help)].filter(Boolean).join("; "),
  }) : null;
  // `UX-1191`: an unreadable threshold is said on the page, and applies nothing.
  const unread = el("span", { class: "filter-unread", role: "status", hidden: true });
  if (box) {
    identify(box, `filter-${key}`);
    box.addEventListener("input", () => {
      const labels = Object.fromEntries([...table.querySelectorAll("th")].map(
        (th) => [th.getAttribute("data-column"), th.textContent]));
      const share = new Set(ownHeads(table).filter((th) => th.hasAttribute?.("data-share"))
        .map((th) => th.getAttribute("data-column")));
      // `UX-1214`: an undrawn column is read, never named in the sentence below.
      const columns = [...filterable, ...Object.values(STATED.get(table) ?? {}).map((said) => said.spec)];
      const query = parseQuery(box.value, [...columns, ...undrawn].map((spec) => (share.has(spec?.key) ? { ...spec, share: true } : spec)),
                               labels);
      Object.assign(state, { text: query.text, exact: query.exact, thresholds: query.thresholds });
      const bad = query.unread.length > 0;
      box.classList?.toggle?.("unparsed", bad);
      box.setAttribute("aria-invalid", String(bad));
      unread.hidden = !bad;
      const heads = [...columns.map((spec) => labels[spec?.key] ?? spec?.title), ...undrawn.map((spec) => `${spec.key}:\u2026`)]
        .filter(Boolean).join(", ");
      // `UX-1206`: a bare threshold on a table whose only quantity is a share says so, and how to name it.
      const shareOf = (key) => labels[key] ?? columns.find((spec) => spec?.key === key)?.title ?? key;
      unread.textContent = query.unread.map(({ clause, column, share }) => (column
        ? `\u201c${clause}\u201d: no column here is called \u201c${column}\u201d (${heads}), so it is not applied.`
        : share ? `\u201c${clause}\u201d is not applied: ${shareOf(share)} is a share, not a duration - name it, `
          + `as in \u201c${shareOf(share).toLowerCase()} ${clause}\u201d.`
          : `\u201c${clause}\u201d is not a threshold this table can read, so it is not applied.`)).join(" ");
      if (bad && !unread.parentNode) box.after?.(unread);
      rewind?.();
      refresh();
    });
    // The density strip's click (`shapes.js`) writes its threshold here, replacing a bare one.
    table.addEventListener?.("bga:threshold", (event) => {
      box.value = `${box.value.replace(/(^|\s)(>=|<=|>|<|=)\s*\S*/g, "$1").trim()} >= ${event.detail}`.trim();
      box.dispatchEvent?.(new Event("input", { bubbles: true }));
    });
  }

  // UX-208 item 4: Top-N over any column the schema declares a
  // quantity. `Top 10` is a *preset*, not a cap - the badge still says
  // `10 of 1,202`, because a reader who cannot see the denominator
  // cannot tell a filtered table from a small one.
  const presets = presetColumns(specs);
  // `UX-413`: the bound is about *length*, not about rankability -
  // `openingBound` carries why, and a table with nothing to rank by
  // used to get no control and therefore no bound at all.
  const opening = openingBound(presets, total, TABLE_OPENS_BOUNDED_ABOVE);
  rank = presets[0] ?? null;
  // UX-673: a preset that cannot shrink the table is apparatus without
  // effect - skip any `n >= total`, and offer no control at all once
  // even the smallest preset fails that test.
  // `UX-1196`: nor one that hides a single row - `Top 10` of 11 is apparatus too.
  // `UX-1028`: the step past the "All rows" ceiling - built once, set
  // here, appended into `tools` below.
  let pager = null;
  // `UX-1223`: the listing order, and the sort a bound imposed rather than the reader pressed.
  const listed = [...ownRows(table)];
  let imposed = null;
  if ((presets.length && total > 11) || opening) {
    const preset = el("select", { class: "top-n", "aria-label": `Rows shown: ${named}` });
    identify(preset, `top-${key}`);
    // `UX-1028` (styleguide §3k): "All rows" mounts the whole table in
    // one step, so it is offered only under a ceiling the table
    // states - past it the paging step below is the only way to reach
    // the rest.
    if (total <= ALL_ROWS_CEILING) {
      preset.append(el("option", { value: "" }, "All rows"));
    }
    // `UX-1197`: bounds only - the rank is the header's sort, the first quantity's at opening.
    for (const n of presets.length ? [10, 25] : []) {
      if (n < total - 1) preset.append(el("option", { value: `${n}:${rank}` }, `Top ${n} rows`));
    }
    if (!presets.length) {
      preset.append(el("option", { value: `${TABLE_OPENS_BOUNDED_ABOVE}:` },
                       `First ${TABLE_OPENS_BOUNDED_ABOVE} rows`));
    }
    // `UX-1028` (styleguide §3k): past `ALL_ROWS_CEILING` the reader
    // has no "All rows" - the paging step below is the only way to
    // reach the rest, one bound-sized window at a time. `offset` and
    // `paging` are declared here, ahead of the preset's own `change`
    // handler, so choosing a preset can hand the window back in the
    // *same* listener rather than a second one racing the first's
    // `refresh` (Review #295: that race is what left "Top 25 by …"
    // selected while paging showed a plain offset window).
    let offset = 0;
    let paging = false;
    // `UX-1197`: a page is the chosen bound's size, in the table's current sort.
    const size = () => state.top?.n ?? opening?.top.n ?? TABLE_OPENS_BOUNDED_ABOVE;
    let ranking = opening?.top.column ?? null;
    const canPage = total > ALL_ROWS_CEILING;
    const prev = canPage ? el("button", { type: "button", class: "page-prev",
                              "aria-label": `previous rows: ${named}` }, "‹ Prev") : null;
    const next = canPage ? el("button", { type: "button", class: "page-next",
                              "aria-label": `next rows: ${named}` }, "Next ›") : null;
    // Runs from `refresh` itself, so a filter or threshold narrowing
    // the population while paging keeps the position and the buttons'
    // bounds measured against `state.filtered` - the text/threshold
    // population `applyFilters` just computed - never a stale reading
    // of the unfiltered `total` (Review #295, `UX-1028`).
    if (canPage) {
      pagerRefresh = () => {
        if (!paging) { pager?.removeAttribute?.("data-offset"); return; }
        const denom = state.filtered ?? total;
        const lastStart = denom === 0 ? 0 : Math.floor((denom - 1) / size()) * size();
        // The filtered population can shrink under the current window
        // (typing a filter mid-page) - clamp back onto its last real
        // page rather than claim a range past what is now filtered.
        if (offset > lastStart) {
          offset = lastStart;
          state.top = { n: size(), column: ranking, offset };
          const said = badgeText(applyFilters(table, state), total, state.filtered, view());
          badge.textContent = said === rest ? "" : said;
        }
        const end = Math.min(offset + size(), denom);
        prev.disabled = offset <= 0;
        next.disabled = end >= denom;
        // `UX-1185`: the fragment's `p.` - `viewstate.js` reads it here and writes it back through `bga:page`; none on the first rows.
        if (offset) pager?.setAttribute?.("data-offset", String(offset));
        else pager?.removeAttribute?.("data-offset");
      };
      const step = () => {
        paging = true;
        // `UX-1197`: the select keeps its bound - it is every page's size.
        state.top = { n: size(), column: ranking, offset };
        refresh();
      };
      prev.addEventListener("click", () => {
        offset = Math.max(0, offset - size());
        step();
      });
      next.addEventListener("click", () => {
        // `Top 10` then Next is rows 11-20; `pagerRefresh` clamps it.
        offset = paging ? offset + size() : size();
        step();
      });
      // `UX-1185`: a filter edit names a new population, so the pager starts at its front.
      rewind = () => {
        offset = 0;
        if (state.top) state.top = { ...state.top, offset: 0 };
      };
      pager = el("span", { class: "table-pager" }, prev, next);
      pager.addEventListener?.("bga:page", () => {
        offset = Math.max(0, Number(pager.getAttribute("data-offset")) || 0);
        step();
      });
    }

    // `UX-392`: through the same `refresh`, so the preset narrows what
    // the filter left rather than replacing it. Choosing any preset
    // also ends paging and starts back at the front, in this same
    // pass (Review #295) - so the label and the rows agree the
    // instant the reader chooses, not one `refresh` later.
    preset.addEventListener("change", () => {
      const [n, column] = preset.value ? preset.value.split(":") : [];
      // `UX-1028`: an empty *value* reads as "All rows" only when a
      // real `<option value="">` was chosen (`selectedIndex !== -1`).
      // Forced to `""` with no such option present - which is what a
      // stray external write does, not what a reader's own choice ever
      // produces - `selectedIndex` is `-1`, and that must not read as
      // "unbounded" the way `state.top = null` would.
      state.top = preset.value ? { n: Number(n), column: column || null }
        : preset.selectedIndex === -1 ? (opening?.top ?? null) : null;
      // `UX-1197`: a bound keeps the table's sort; with none yet it ranks by the first quantity, shown on its header.
      if (state.top?.column && !state.sort) showSort(table, imposed = state.sort = { column: state.top.column, direction: "descending" });
      // `UX-1223`: All rows drops a sort only a bound imposed, and the rows go back to their listing order.
      if (!state.top && imposed && state.sort === imposed) {
        showSort(table, imposed = state.sort = null);
        reorder(ownBody(table), [...listed]);
      }
      offset = 0;
      paging = false;
      refresh();
    });
    // UX-262: a table longer than this opens bounded. Measured at
    // 1440x900, a 122-deep critical path took `signals` from 1884px
    // (2.1 screens) to 5539px (6.2 screens) on a *smaller* run. The
    // control already existed; `All rows` being its default was the
    // defect. The badge still says `25 of 132`, per `UX-208`, so this
    // bounds the page without hiding the size of what it bounded.
    if (opening) {
      // UX-1158: the opening value, which the link leaves unsaid.
      preset.value = preset.opening = opening.value;
      state.top = opening.top;
      if (opening.top.column) showSort(table, state.sort = { column: opening.top.column, direction: "descending" });
      refresh();
    }
    state.preset = preset;

    // Not paged at build time: at rest the table opens on `opening`'s
    // own bound, and the paging step only takes over once pressed.
    if (prev) prev.disabled = true;
    // `UX-1190`: a header's sort starts the bound at the front; `UX-1197`: the bound stays chosen.
    restart = (sort) => {
      offset = 0;
      ranking = sort.column;
      if (state.top) state.top = { ...state.top, offset: 0 };
    };
  }
  table.addEventListener?.("bga:sort", (event) => {
    state.sort = event.detail;
    restart?.(state.sort);
    // Unbounded and unfiltered, `sortable` reorders every row itself; the live region still says the sort.
    if (!state.top && !narrowed()) {
      const said = badgeText(total, total, total, view());
      badge.textContent = said === rest ? "" : said;
      return;
    }
    event.preventDefault?.();
    refresh();
  });

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
  // `UX-1196`: a head-and-tail fold's held middle is shown rows too; its stub is none.
  const shownRows = () => ownRows(table).filter((tr) => !tr.hidden
    || (tr.hasAttribute?.("data-fold-middle") && tr.parentNode));
  // `UX-1189` (§4c): a filter names a population, and copy takes it - up to `ALL_ROWS_CEILING` - not the page.
  const filtered = narrowed;
  const copied = () => (filtered() ? (state.kept ?? []).slice(0, ALL_ROWS_CEILING) : shownRows());
  const markdown = () => readCopyFormat() === "markdown";
  // `UX-1189`: the format is one page-wide box now (`app.js`); it tells every table.
  document.addEventListener?.(COPY_FORMAT_MIRROR, () => label());

  const copyRows = el("button", { type: "button", class: "copy-rows" });
  const label = () => {
    const n = copied().length;
    const form = markdown() ? "Markdown" : "JSON";
    // `UX-412`: through the shared helper, so this label and the badge
    // beside it agree with the count in one place rather than two.
    const matched = state.filtered ?? 0;
    const rows = !filtered() ? plural(n, "row")
      : n < matched ? `first ${tally(n)} of ${plural(matched, "matched row")}` : plural(n, "matched row");
    // `UX-1165`: nothing shown, nothing to copy or to say of the rows.
    for (const node of [copyRows, copyRows.parentNode?.querySelector?.(".uniform-columns")]) {
      if (node) node.hidden = !n;
    }
    say(copyRows, `Copy ${rows}`, named);
    copyRows.title = `Copy the ${rows} ${filtered() ? "the filter keeps" : "shown in this table"} as ${form}, `
      + `with their published values`;
  };
  // `UX-1185`: every `refresh` - a page step is a click, which no `input` listener hears.
  relabel = label;
  label();
  copyRows.addEventListener("click", () => {
    const rows = copied();
    copy(markdown()
      ? rowsMarkdown(rows, specs)
      : `[${rows.map((tr) => rowJson(tr, specs.map((s) => s.key), jsonNames(specs))).join(",")}]`);
    // `UX-355` (styleguide §4c): and it says so. A clipboard write is
    // invisible by construction, so the control acknowledges the press
    // itself - the same shape `copy-step`, `copy-sql` and `copy-view`
    // already use. This was the most numerous copy control on the page
    // (13 on `golden`, 23 on `macro_micro`) and the only one of the
    // four that reported nothing.
    say(copyRows, "\u2713 copied", named);
    // Back through `label`, not to a captured string: the count follows
    // the filter and the bound, so what it should say on the way back
    // is whatever it would say now.
    setTimeout(label, 1200);
  });

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
  // `UX-1152` (styleguide §3d): at two rows or fewer `Copy N rows` is the one count.
  shape = resting = distributionStrip(table, specs, total, few);

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
  // `UX-1197`: a sort button's name ends with its table's, once the section has relabelled its heads.
  globalThis.queueMicrotask?.(() => { table.sortName = named; labelSorts(table); });
  const nested = depth > 0;
  const expand = served() && (nested || total > TABLE_OPENS_BOUNDED_ABOVE)
    ? expandTableControl(table, depth) : null;
  // `UX-1055` (styleguide §3l): `copyRows` first and `state.preset`
  // (`top-n`) last in the DOM too, not just visually via CSS `order` -
  // a reader tabbing through matches what a sighted reader sees
  // (WCAG 2.4.3/1.3.2); `style.css`'s `margin-left: auto` on `top-n`
  // still carries the "nothing shares its trailing space" guarantee.
  const tools = el("div", { class: "table-tools" }, copyRows, box, few ? null : badge,
                            pager, expand, shape,
                            state.preset ?? null);
  // The badge and the count are the same claim; refresh both together.
  tools.addEventListener?.("input", label);
  tools.addEventListener?.("change", label);
  return tools;
}

// What to type, in the unit the column publishes.
const PLACEHOLDER = {
  duration_us: "> 5s", seconds: "> 5s", bytes: "> 10mb",
  megabytes: "> 512mb", kilobytes: "> 512mb", share: "> 10%", percent: "> 10%",
  count: "> 10", ratio: "> 1",
};

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
  const section = renderTable(LIFTED_SECTION, rows, hintsOf(child), child,
                              { fold: { head: PATH_HEAD, tail: PATH_TAIL,
                                        noun: "elements" } });
  // `UX-1196`: the listing's order is a claim, so its header sorts at any length.
  const table = section.querySelector?.("table");
  if (table) {
    sortable(table, { always: true });
  }
  return section;
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
 * `UX-1141`: a map table's key column names a declared record member
 * by its title, never its key; a data-keyed map's names are data.
 */
function memberTitle(column, raw, node) {
  if (column !== "key" || !node || !BARE_KEY.test(raw)) return null;
  if (readerLabel(raw) !== raw || dataKeyed(node, raw)) return null;
  return title(raw, quantityFor(childNode(node, raw), raw));
}

/**
 * A long string as a truncated cell with the whole thing one click
 * away. The `…` is visible, never silent, and the full text stays
 * selectable - a reader who cannot select it has not been given it.
 */
export function renderText(name, value, shown = null) {
  const text = String(value);
  if (text.length <= CELL_TEXT_CAP || isExplanation(name)) {
    return el("span", { "data-raw": text }, shown ?? readerLabel(text));
  }
  let head = text.slice(0, CELL_TEXT_CAP).replace(/\s+\S*$/, "");
  // A cut inside a backtick span would print the raw backtick.
  if ((head.match(/`/g) ?? []).length % 2) head = head.slice(0, head.lastIndexOf("`")).trimEnd();
  return el("details", { class: "long-text", "data-raw": text },
            // `UX-1152`: the preview hides once open, so the text shows once; a count of chars is no label.
            el("summary", {},
               el("span", { class: "long-text-head" }, `${head}… `),
               el("span", { class: "long-text-more muted" }, "more"),
               el("span", { class: "long-text-less muted" }, "less")),
            el("p", { class: "full-text" }, text));
}

// UX-262: above this many rows a table opens on its top 25 rather than
// on everything. 40 is chosen against the shapes that occur: the
// 1,202-element run's widest table is 26 rows and stays whole, and a
// 122-deep critical path is 132 and does not. A bound that fired on
// the ordinary case would train readers to reset it every load.
export const TABLE_OPENS_BOUNDED_ABOVE = 40;
// `UX-1152`: at or under this many rows a table's tools carry no badge and no strip.
const FEW_ROWS = 2;
