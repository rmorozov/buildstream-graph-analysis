/**
 * UX-268: a map drawn as a pair list, and the element-keyed signals
 * lifted out of it into one table with its presets.
 * Points down at `structured.js` for the table factory; nothing there
 * points back.
 */
import { served } from "./primitives.js";
import { COLUMNS, DIRECTION, QUESTION, PRESETS, INLINE, attachBlockDoor,
         childNode, dataKeyed, describedTerm, el, guessQuantity, heading,
         hintsOf, adviceFor, keyAsShown, quantity, quantityFor, sectionHead,
         title } from "./format.js";
import { identify, labelFor } from "./controls.js";
import { applyPreset, boundPairs, sortable } from "./tables.js";
import { TABLE_OPENS_BOUNDED_ABOVE, buildTable, renderStructured, renderText }
  from "./structured.js";

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
                  // `UX-835`: no blanket "count" here - `mapTable`'s
                  // record branch above already learned this default
                  // invents a unit a boolean or categorical join column
                  // never declared, which is what left it unfiltered
                  // and unflagged as exempt.
                  const measure = quantityFor(origin.get(name)
                                              ?? childNode(node, name), name)
                    ?? guessQuantity(name);
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
  const doors = [];
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
    // `critical_path_detail` rendered as a `<pre>` of raw JSON, so
    // nothing in it was sortable, filterable or one click from
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
    // `UX-391`: a task uid is an identity, not a label - the map says
    // which it is, `data-key` keeps the composite, and the reader sees
    // the element with a muted qualifier.
    const shown = keyAsShown(name, hint);
    const { term, describe } = describedTerm(
      shown ? shown.element : name, described, {}, hintsOf(child)[INLINE],
      kind, shown ? true : dataKeyed(node, name));
    doors.push(describe);
    if (shown) {
      term.setAttribute?.("data-key", name);
      if (shown.qualifier) term.append(
        el("span", { class: "task-qualifier muted" }, ` ${shown.qualifier}`));
    }
    // `UX-390`: and the run's own advice for this bucket, on its row,
    // beside the schema's sentence rather than instead of it.
    const advice = adviceFor(payload, hint, name);
    list.append(term, el("dd", {}, cell, describe,
                         advice ? el("p", { class: "run-advice" }, advice)
                                : null));
  }
  attachBlockDoor(list, doors);
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
    // `UX-829` (styleguide §1b): `fan_in[uid].direct` is a joined field
    // this table deliberately does not draw a column for - a capped
    // name list is a card fact, not a cell (§3c) - so the lead names
    // where it went, the same clause `DRAWN_ELSEWHERE` states for a
    // whole section.
    const leadText = `One row per element, joined from `
      + `${joined.merged.length} signals. Each element's direct `
      + `dependencies are listed on its own card, not here.`;
    if (views) {
      parts.push(el("div", { class: "map-table", "data-bounded": "map",
                             "data-joined": joined.merged.join(",") },
                    el("p", { class: "muted" }, leadText),
                    views.node));
    } else {
      const { table, tools } = buildTable("elements", joined.rows,
                                          joined.hint, node);
      parts.push(el("div", { class: "map-table", "data-bounded": "map",
                             "data-joined": joined.merged.join(",") },
                    el("p", { class: "muted" }, leadText),
                    tools, table));
    }
  }
  // `UX-419`: a map grows with the payload too, and had no bound at all.
  parts.push(list, boundPairs(list, TABLE_OPENS_BOUNDED_ABOVE));
  return el("section", { "data-section": key, "data-rail": heading(key, hint).rail },
                        ...parts);
}
