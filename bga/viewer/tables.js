// UX-205: tables you can interrogate.
//
// The page renders every row of every array unconditionally - the right
// default for a viewer, and unusable without tools on it: `UX-187`
// capped what the *text* report prints, and a 1,202-row element table
// on this page had sorting and nothing else.
//
// Everything here works on the rendered table, and every number it
// compares is `data-raw` - the published value, not the formatted
// string. Comparing "1.2s" to "5s" as text is the defect this avoids;
// `UX-201`'s column metadata says which columns are quantities and in
// what unit, which is what makes `> 5s` parseable at all.

import { el } from "./format.js";

/** How many microseconds/bytes/… one suffix is worth, per quantity. */
const UNITS = {
  duration_us: { us: 1, ms: 1e3, s: 1e6, m: 60e6, h: 3600e6 },
  // UX-341: one unit per dimension. `seconds`, `megabytes`,
  // `kilobytes` and `percent` were retired from the vocabulary, so a
  // column can no longer be declared in them and these tables no
  // longer have to carry four extra conversion sets to filter one.
  bytes: { b: 1, kb: 1024, k: 1024, mb: 1024 ** 2, m: 1024 ** 2,
           gb: 1024 ** 3, g: 1024 ** 3 },
  share: { "%": 0.01 },
};

/**
 * `"> 5s"` -> `{op: ">", value: 5000000}` for a `duration_us` column.
 *
 * A bare number is the published value as it stands, because that is
 * what the reader sees in `data-raw` and what every other consumer of
 * this JSON compares against. A suffix converts.
 *
 * Returns null for anything it cannot parse, and null is *no filter* -
 * a threshold nobody can read is not a threshold that hides rows.
 */
export function parseThreshold(text, quantity) {
  const match = String(text ?? "").trim().toLowerCase()
    .match(/^(>=|<=|>|<|=)?\s*(-?[\d.]+)\s*(%|[a-z]+)?$/);
  if (!match) return null;
  const [, op = ">=", digits, suffix] = match;
  const value = Number(digits);
  if (!Number.isFinite(value)) return null;
  if (!suffix) return { op, value };
  const scale = (UNITS[quantity] ?? {})[suffix];
  if (scale === undefined) return null;
  return { op, value: value * scale };
}

// `UX-1191` (§3d): `name:value` is exact on any named column; `op` and `element` read a task uid's parts.
const slug = (text) => String(text ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

/** What a reader may call each column: its key, its role, its head's label and each word of it. */
function columnNames(specs, labels = {}) {
  const names = new Map();
  const words = new Map();
  for (const spec of specs) {
    if (!spec) continue;
    const said = [spec.key, spec.role, spec.title, labels[spec.key]].map(slug).filter(Boolean);
    for (const name of said) names.set(name, names.get(name) ?? spec);
    if (spec.role === "task_uid") { names.set("op", spec); names.set("element", names.get("element") ?? spec); }
    for (const word of said.flatMap((name) => name.split("_"))) {
      words.set(word, words.has(word) && words.get(word) !== spec ? null : spec);
    }
  }
  for (const [word, spec] of words) if (spec && !names.has(word)) names.set(word, spec);
  // `UX-1195`: a plural name reads in the singular too - `duration` for Element durations.
  for (const [name, spec] of [...names]) {
    if (/\w{3}s$/.test(name) && !names.has(name.slice(0, -1))) names.set(name.slice(0, -1), spec);
  }
  return names;
}

// `UX-1195`: a column the page says once above the table - `{column: {raw, shown, spec}}` - still answers the box.
export const STATED = new WeakMap();

/**
 * `UX-1191`: the one filter box's grammar. `binary:ld` is exact on a key
 * column (`ld*` a prefix), `duration > 60s` a threshold (bare `> 5s` is
 * the first quantity column's), and what is left matches as a substring.
 * A threshold nobody can read is returned in `unread`, never applied.
 */
export function parseQuery(text, specs = [], labels = {}) {
  const names = columnNames(specs, labels);
  // `UX-1194`: a bare threshold never reads a share column, nor one stated above the table.
  const primary = specs.find((spec) => spec?.quantity && spec.numeric !== false && !spec.share && !spec.stated);
  const exact = [];
  const thresholds = {};
  const unread = [];
  let rest = String(text ?? "").replace(/(^|\s)([a-z_][\w-]*):\s*(\S+)/gi, (whole, lead, name, value) => {
    const spec = names.get(slug(name));
    if (!spec) { unread.push({ clause: whole.slice(lead.length), column: name }); return lead; }
    const part = spec.role !== "task_uid" ? null : slug(name) === "op" ? 1 : slug(name) === "element" ? 0 : null;
    const prefix = value.endsWith("*");
    exact.push({ column: spec.key, part, prefix, value: (prefix ? value.slice(0, -1) : value).toLowerCase() });
    return lead;
  });
  rest = rest.replace(/(^|\s)(?:([a-z_][\w-]*)\s*)?(>=|<=|>|<|=)\s*(\S*)/gi, (whole, lead, name, op, value) => {
    // `UX-1195`: a word that names no column is said back and applies nothing - no substring residue.
    const clause = whole.slice(lead.length);
    if (name && !names.has(slug(name))) { unread.push({ clause, column: name }); return lead; }
    const spec = name ? names.get(slug(name)) : primary;
    const parsed = spec?.quantity ? parseThreshold(`${op} ${value}`, spec.quantity) : null;
    if (parsed) thresholds[spec.key] = parsed;
    else unread.push({ clause, column: null });
    return lead;
  });
  return { text: rest.replace(/\s+/g, " ").trim(), exact, thresholds, unread };
}

/** Does a row's key cell - its published value or the word it shows - equal (or start with) the clause's value? */
function matchesKey(tr, clause, stated = {}) {
  const cell = [...tr.children].find((td) => td.getAttribute("data-column") === clause.column);
  const said = cell ? { raw: cell.getAttribute("data-raw"), shown: cell.textContent } : stated[clause.column];
  const raw = String(said?.raw ?? "");
  const got = [clause.part === null ? raw : raw.split("|")[clause.part] ?? ""];
  if (clause.part === null) got.push(String(said?.shown ?? "").replace("⌕", "").trim());
  return got.some((value) => (clause.prefix ? value.toLowerCase().startsWith(clause.value)
    : value.toLowerCase() === clause.value));
}

/** Does one published number pass a parsed threshold? */
export function passes(raw, threshold) {
  if (!threshold) return true;
  const value = Number(raw);
  if (!Number.isFinite(value)) return false;
  switch (threshold.op) {
    case ">": return value > threshold.value;
    case ">=": return value >= threshold.value;
    case "<": return value < threshold.value;
    case "<=": return value <= threshold.value;
    default: return value === threshold.value;
  }
}

const childrenNamed = (node, tag) => [...(node?.children ?? [])].filter(
  (child) => String(child?.tagName ?? "").toLowerCase() === tag);

/**
 * `UX-532`: the table's **own** body, never a nested table's.
 *
 * A cell can hold a whole table (`UX-318`'s folds), and `<tbody>` inside
 * one is still a descendant of this `<table>`.
 */
export function ownBody(table) {
  return childrenNamed(table, "tbody")[0] ?? null;
}

/**
 * `UX-532`: the table's **own** rows - the one row selector.
 *
 * `body.querySelectorAll("tr")` reads every `<tr>` at any depth, so a
 * table whose cells fold counted the nested tables' rows as its own and
 * every site that re-appends them tore them out of their folds. Measured
 * on 60 shared resources over `macro_micro`: 660 direct `<tr>` in the
 * outer tbody, 60 nested tables left empty, badge `660 of 60`.
 *
 * A child walk rather than `:scope > tr`: `tests/dom_shim.mjs` refuses
 * pseudo-classes by design (`UX-264`), and the claim is the same one.
 *
 * Through `everyRow`, because `UX-526` took the rows past the bound out
 * of the document: children of the tbody are the *shown* own rows, and
 * both claims have to hold at once.
 */
export function ownRows(table) {
  return everyRow(ownBody(table));
}

/** The text a row matches on: every cell's rendered text, joined. */
export function rowText(tr) {
  return [...tr.children].map((td) => td.textContent).join(" ").toLowerCase();
}

// `UX-526`: a row the bound does not show leaves the document.
//
// Measured on the seeded 4,002-element run: 4,800 `<tr>` in the DOM and
// 293 rendered. A row past the bound was `hidden`, which costs no pixels
// and every node - and `nodes` is the one volume measure that sees a
// table (`UX-366`). The rows are held here instead, in the order the
// table holds them, and re-attached by the same control that used to
// flip `hidden`. Nothing is lost: the payload holds them once already,
// and the export ships the payload rather than the rendered DOM.
const HELD = new WeakMap();

/**
 * Every **own** row of `body`, shown or held out, in the table's order.
 *
 * `childrenNamed` and not `querySelectorAll("tr")`: `UX-532`'s claim -
 * a cell can hold a whole table, and its rows are not these.
 */
export function everyRow(body) {
  const state = HELD.get(body);
  if (state?.out.size) return state.order;
  const order = childrenNamed(body, "tr");
  if (body) HELD.set(body, { order, out: new Set() });
  return order;
}

/** Attach exactly `shown`, in that order; the rest leave the document. */
function showOnly(body, order, shown) {
  const wanted = new Set(shown);
  const out = new Set();
  for (const tr of order) {
    if (wanted.has(tr)) continue;
    tr.hidden = true;
    tr.remove?.();
    out.add(tr);
  }
  for (const tr of shown) { tr.hidden = false; body.append?.(tr); }
  HELD.set(body, { order, out });
}

/** Record a new order for the table, leaving the held rows held. */
function reorder(body, order) {
  const out = HELD.get(body)?.out ?? new Set();
  for (const tr of order) if (!out.has(tr)) body.append?.(tr);
  HELD.set(body, { order, out });
}

/**
 * Put `rows` back, keeping whatever else is already shown.
 *
 * The other door onto the same held set: a fold's own "+N more" control
 * asks for its middle rows by name rather than through a filter pass.
 */
export function showAlso(body, rows) {
  const state = HELD.get(body);
  for (const tr of rows) tr.hidden = false;
  if (!state) return;
  for (const tr of rows) state.out.delete(tr);
  for (const tr of state.order) if (!state.out.has(tr)) body.append?.(tr);
}

/**
 * One column's cells, over every row the table has - held or shown.
 *
 * `UX-526`: `querySelectorAll("td[data-column=…]")` used to be the same
 * thing and stopped being it. A strip labelled "across all 1,202 rows"
 * drawn from the 25 the bound shows is the wrong-population defect the
 * fixing guide's §5 names, arriving through a change of mechanism.
 */
export function columnCells(table, key, rows = everyRow(ownBody(table))) {
  // `ownBody`, not `querySelector("tbody")`: `UX-532` again.
  return rows
    .map((tr) => [...(tr.children ?? [])].find(
      (td) => td.getAttribute?.("data-column") === key))
    .filter(Boolean);
}

/**
 * Apply the text box and the per-column thresholds to a rendered table.
 * Returns how many rows survived, which is what the badge shows.
 *
 * Review (#295), `UX-1028`: also writes `options.filtered` - the
 * text/threshold population, before `top`'s slice - back onto the
 * caller's own state object. A paging step's position and bounds have
 * to be measured against that population, not the table's unfiltered
 * row count, which disagrees with the page the moment a filter narrows
 * it; a second field on the state already passed in, not a second
 * return shape every caller has to unpack.
 */
export function applyFilters(table, options = {}) {
  const { text = "", thresholds = {}, exact = [], top = null, sort = null } = options;
  const needle = String(text).trim().toLowerCase();
  const body = ownBody(table);
  const rows = everyRow(body);
  const kept = [];
  const stated = STATED.get(table) ?? {};
  const statedText = Object.values(stated).map((said) => said.shown).join(" ").toLowerCase();
  for (const tr of rows) {
    let keep = (!needle || rowText(tr).includes(needle) || statedText.includes(needle))
      && exact.every((clause) => matchesKey(tr, clause, stated));
    if (keep) {
      // Over the *thresholds*, not over the row's cells: walking the
      // cells means a threshold naming a column this row does not carry
      // is never checked, and every row passes a filter that should
      // have emptied the table. "No value" does not pass "> 5s".
      for (const [column, threshold] of Object.entries(thresholds)) {
        const cell = [...tr.children].find(
          (td) => td.getAttribute("data-column") === column);
        if (!passes(cell ? cell.getAttribute("data-raw") : stated[column]?.raw ?? null, threshold)) {
          keep = false;
          break;
        }
      }
    }
    if (keep) kept.push(tr);
  }
  // `UX-392`: **and the preset, over what the filter left.**
  //
  // The Top-N menu used to be a second, separate pass: choosing one
  // re-showed rows the filter had hidden, so a reader whose filter box
  // still said `mod023` was looking at ten rows that had nothing to do
  // with it. Measured on the 1,202-element run - filter to 12 rows,
  // choose `Top 10`, and the table shows 10 rows drawn from all 1,202.
  //
  // Two controls answering different questions (`UX-392`'s own Out of
  // Scope keeps both) must compose, and "the ten biggest **of the ones
  // I asked for**" is what a reader typing in both means. One pass, so
  // there is one place the shown-count comes from and the badge cannot
  // describe a state the table is not in.
  //
  // `UX-413`: **and a column is optional.** `{n, column: null}` is "the
  // first n, in the order the payload published them" - the bound for a
  // population with nothing numeric to rank by, which used to get no
  // bound at all because the caller had no column to name. Everything
  // else about it is the same pass, so the badge, the filter and the
  // copy control cannot tell the two apart.
  let shown = kept;
  // `UX-1190`: a header's sort ranks the population, before any bound slices it.
  if (sort?.column) kept.sort(byColumn(sort.column, sort.direction));
  if (top && Number.isFinite(Number(top.n))) {
    if (top.column && !sort?.column) {
      const value = (tr) => {
        const cell = [...tr.children].find(
          (td) => td.getAttribute("data-column") === top.column);
        const raw = Number(cell ? cell.getAttribute("data-raw") : NaN);
        return Number.isFinite(raw) ? raw : -Infinity;
      };
      kept.sort((a, b) => value(b) - value(a));
    }
    // `UX-1028`: an optional window past the first `n`, for the paging
    // step - the same slice, offset rather than always from zero, so
    // paging and Top-N share one mechanism and one bound.
    const offset = Number.isFinite(Number(top.offset)) ? Number(top.offset) : 0;
    shown = kept.slice(offset, offset + Number(top.n));
  }
  // `UX-526`: one place decides which rows exist, so the count the badge
  // shows and the rows the document holds cannot disagree.
  showOnly(body, rows, shown);
  options.filtered = kept.length;
  options.kept = kept;
  return shown.length;
}

/**
 * `UX-413`: what a table this long should *open* at, if anything.
 *
 * `UX-367` set the volume budget and `UX-262` made a long table open
 * bounded, and both were enforced from inside `if (presets.length)` -
 * the list of numeric columns worth ranking by. A table with none got
 * no preset control, so `[column]` was `undefined` and the bound was
 * never applied. The bound was therefore a *side effect of having
 * something to rank by*, which is not what either filing meant.
 *
 * Measured by `UX-400`'s sweep at 120 rows: five populations opened at
 * `25 of 120` and four drew every one of their 121 rows - `readers`,
 * `next_steps`, `restructuring`, `provenance`, which are exactly the
 * four with nothing numeric in them. `restructuring` is the one that
 * made it urgent: a list of never-read dependency edges, published by
 * `UX-407`, and the population most likely to be long on a real
 * monorepo.
 *
 * With no column the head is the bound and the order is the payload's,
 * which `UX-413`'s Out of Scope keeps as the emitter's decision rather
 * than reopening it here.
 */
/**
 * `UX-1028` (styleguide §3k): the ceiling under which "All rows" may be
 * offered at all - past it the reader gets the paging step instead,
 * never the whole population in one mount. `UX-1032`'s census reads
 * "no table ever mounts more than `MOUNTED_ROWS_MAX` rows" as one bound
 * over the whole page, so this ceiling has to sit under that number
 * too, not only under `TABLE_OPENS_BOUNDED_ABOVE`.
 */
export const ALL_ROWS_CEILING = 200;

// `UX-1185` (D1): two pages or fewer open whole.
export const UNROLL_AT = 80;

export function openingBound(presets, total, bound) {
  if (total <= Math.max(bound, UNROLL_AT)) return null;
  const [column] = presets;
  return column
    ? { value: `25:${column}`, top: { n: 25, column } }
    : { value: `${bound}:`, top: { n: bound, column: null } };
}

/**
 * `UX-412`: a count and a noun that agrees with it.
 *
 * `1 rows` was written in two places and read on every run small
 * enough to have one of something - one finding, one next step, one
 * heavy element, which is the shape of somebody's first run.
 * `UX-400`'s sweep at a single row found nine badges saying it.
 *
 * Pluralised where the count is written rather than at each call site,
 * which is the fix `UX-365` asked for the first time this class of bug
 * appeared: a sentence written for a population and read over one row.
 */
export function plural(count, noun) {
  return `${count.toLocaleString("en-US")} ${noun}${count === 1 ? "" : "s"}`;
}

/** `12 of 1,202` - and just the total when nothing is filtered. */
export function badgeText(shown, total, matched = total) {
  const n = (value) => value.toLocaleString("en-US");
  // The `N of M` form needs no agreement: a denominator is always a
  // population, and `1 of 12` is right as it stands.
  // UX-1158: an emptied table says why beside the box that emptied it.
  // `UX-1195`: a bound over a filter states one population, the matched one.
  return shown === total ? plural(total, "row")
    : !shown ? `none of ${n(total)} match`
      : shown < matched && matched < total ? `${n(shown)} of ${n(matched)} matched`
        : `${n(shown)} of ${n(total)}`;
}

/**
 * `UX-413`: the same bound, over cards instead of rows.
 *
 * `renderFindings` draws one `<article>` per finding rather than a
 * table, so the row bound cannot see it at all - `UX-400`'s sweep at
 * 120 measured **120 cards drawn**, on a page whose every table
 * stopped at 25.
 *
 * The cards past the bound are *hidden*, not removed: an `#anchor` into
 * a finding has to land somewhere, and a card is not a row a bound
 * re-materialises (`UX-526` moved the rows and left these). One control says how
 * many there are and shows them, and the badge beside it carries the
 * denominator so a bounded list cannot be mistaken for a short one.
 */
export function boundCards(section, selector, bound, noun = "item") {
  const note = boundGroups(
    [...(section.querySelectorAll?.(selector) ?? [])].map((c) => [c]),
    bound, noun);
  if (note) section.append(note);
  return note;
}

/**
 * The same bound over anything drawn as repeated groups of nodes.
 *
 * `groups[i]` is every node belonging to the i-th thing - one card, or
 * a `<dt>` and its `<dd>`. Past `bound` they are hidden, not removed,
 * for the reason `boundCards` gives. Returns the control, or `null`
 * when there was nothing to bound.
 */
export function boundGroups(groups, bound, noun = "item", detach = false) {
  if (groups.length <= bound) return null;
  // `UX-526`: `detach` is the pair list's answer - `wall_clock_share_us`
  // is one pair per element, and at 4,002 elements the hidden ones were
  // 24,020 DOM nodes and 96,065 words of the page's 107,352.
  const parent = groups[0]?.[0]?.parentElement
                 ?? groups[0]?.[0]?.parentNode ?? null;
  for (const [index, group] of groups.entries()) {
    for (const node of group) {
      node.hidden = index >= bound;
      if (detach && node.hidden) node.remove?.();
    }
  }
  const badge = el("span", { class: "badge" },
                   badgeText(bound, groups.length));
  const more = el("button", { type: "button", class: "show-all-cards" },
                  `Show all ${plural(groups.length, noun)}`);
  more.addEventListener("click", () => {
    // Every group re-appended, not only the detached ones: appending a
    // node already in place is a no-op that keeps the pairs in order.
    for (const group of groups) for (const node of group) {
      node.hidden = false;
      if (detach) parent?.append?.(node);
    }
    badge.textContent = badgeText(groups.length, groups.length);
    more.hidden = true;
  });
  return el("p", { class: "muted card-bound", "data-role": "card-bound" },
            badge, " ", more);
}

/**
 * `UX-419`: the same bound over a pair list.
 *
 * `UX-413` bounded tables and `boundCards` bounded the cards
 * `renderFindings` draws, and both missed the third shape the page has:
 * a section whose payload is a **map** - one measure per key - is drawn
 * by `renderPairs`, which had no bound at all. Measured at 120 keys,
 * `by_binary` and `wall_clock_share_us` drew every pair, no table, no
 * badge and no control.
 *
 * The sizes are not hypothetical: `wall_clock_share_us` is one duration
 * *per task uid*, so it is the element population by another name -
 * 1,202 keys on the scale run.
 *
 * A `<dt>` and its `<dd>` are one thing to a reader, so they are one
 * group here; hiding the term and leaving the value is the shape of bug
 * this file exists to avoid.
 */
export function boundPairs(list, bound, noun = "row") {
  const groups = [];
  for (const node of list.children ?? []) {
    if (String(node.tagName).toLowerCase() === "dt") groups.push([node]);
    else if (groups.length) groups[groups.length - 1].push(node);
  }
  // `UX-526`: detached, unlike the cards - a pair carries no `#anchor`
  // and this is the page's largest hidden population.
  return boundGroups(groups, bound, noun, true);
}

/** What "copy row" puts on the clipboard: the published values, keyed
 *  by column - so it pastes into an issue as JSON that parses. */
export function rowJson(tr, columns) {
  const out = {};
  for (const td of tr.children) {
    const column = td.getAttribute("data-column");
    if (!columns.includes(column)) continue;
    const raw = td.getAttribute("data-raw");
    // The published value, not the rendering: `data-raw` is a string
    // because attributes are, and a number that went in comes back out
    // as one.
    const number = Number(raw);
    // `UX-1189`: and a boolean as one.
    out[column] = raw === "true" || raw === "false" ? raw === "true"
      : raw !== "" && !Number.isNaN(number) ? number : raw;
  }
  return JSON.stringify(out);
}

/** What "copy cell" puts on the clipboard: the published value. */
export function cellText(td) {
  const raw = td.getAttribute("data-raw");
  return raw === "" || raw === null ? td.textContent : raw;
}

/** Best-effort clipboard write. A page served over http on a
 *  non-localhost origin has no `navigator.clipboard`, and a viewer that
 *  throws there would lose the report, not just the copy. */
export function copy(value, deps = {}) {
  const clipboard = deps.clipboard
    ?? (typeof navigator !== "undefined" ? navigator.clipboard : null);
  try {
    const result = clipboard?.writeText?.(value);
    return result ? Promise.resolve(result).then(() => true, () => false)
                  : Promise.resolve(false);
  } catch (error) {
    return Promise.resolve(false);
  }
}

/** The quantity columns a Top-N preset can sort by, declared not
 *  sampled - `UX-201`'s rule, reused. */
export function presetColumns(specs = []) {
  return specs.filter((spec) => spec.quantity).map((spec) => spec.key);
}

// ---------------------------------------------------------------- UX-289

/**
 * The elements a published *selection* names, in the order it names them.
 *
 * `UX-288` left every selection published exactly once and in one shape:
 * an ordered list of records that name an element each
 * (`critical_path_detail`, `choke_points`), or a map keyed by element
 * (`leaves_detail`). This reads either, and the order it returns is the
 * order the payload published - which is how "the critical path" is
 * drawn in path order without the page knowing what a critical path is.
 *
 * Returns `null` for a path the payload does not carry, so a preset over
 * an absent selection can be dropped rather than drawn empty.
 */
export function selectionAt(payload, path) {
  let at = payload;
  for (const step of String(path).split(".")) {
    if (!at || typeof at !== "object") return null;
    at = at[step];
  }
  if (Array.isArray(at)) {
    const uids = at
      .map((entry) => (entry && typeof entry === "object"
                       ? entry.element_uid : entry))
      .filter((uid) => typeof uid === "string");
    return uids.length === at.length && uids.length ? uids : null;
  }
  if (at && typeof at === "object") {
    const keys = Object.keys(at);
    return keys.length ? keys : null;
  }
  return null;
}

/**
 * One preset resolved against a run: which rows, in which order.
 *
 * Returns `null` when this run cannot support the preset - an absent
 * selection, or a filter nothing matches. A named view that draws no
 * rows is worse than one that is not offered: it reads as "there are
 * none of these" when the truth is "this run does not carry that".
 */
export function applyPreset(preset, rows, payload, key = "element") {
  if (!preset) return null;
  let chosen;
  if (preset.from) {
    const order = selectionAt(payload, preset.from);
    if (!order) return null;
    const byUid = new Map(rows.map((row) => [row[key], row]));
    chosen = order.map((uid) => byUid.get(uid)).filter(Boolean);
  } else if (preset.where) {
    chosen = rows.filter((row) => row[preset.where.column]
                                  === preset.where.equals);
  } else {
    chosen = [...rows];
  }
  if (!chosen.length) return null;
  // A `from` preset is already in the order the payload published it in,
  // and re-sorting it would throw that away - so `sort` only applies
  // where the rows had no order of their own.
  const sort = preset.sort;
  if (sort && !preset.from) {
    const sign = (sort.direction ?? "desc") === "asc" ? 1 : -1;
    const of = (row) => {
      const value = row?.[sort.column];
      return typeof value === "number" ? value : -Infinity;
    };
    chosen.sort((a, b) => sign * (of(a) - of(b)));
  }
  return { rows: chosen, total: chosen.length,
           shown: preset.bound ? chosen.slice(0, preset.bound) : chosen };
}

// ---------------------------------------------------------------- UX-280

const RAW_UNIT = { duration_us: "\u00b5s", bytes: "B", seconds: "s", kilobytes: "KB", megabytes: "MB", percent: "%" };

/**
 * The shown rows as a GitHub-flavoured Markdown table.
 *
 * `UX-280`: JSON pastes into a ticket as a code block a reader has to
 * read; a table pastes as a table. Same rows, same order, same
 * `data-raw` values - this is a second *rendering* of what
 * `rowJson` already copies, not a second selection, so the two can
 * never disagree about which rows were shown.
 *
 * Cells are escaped for the one character that would break the shape: a
 * `|` inside a value ends the cell. Newlines cannot appear in a
 * `data-raw` attribute value the page writes, but are collapsed anyway
 * rather than trusted.
 */
export function rowsMarkdown(rows, specs) {
  const columns = specs.map((spec) => spec.key);
  // UX-1172: the cells are raw, so the header names their unit.
  const titles = specs.map((spec) => (spec.title ?? spec.key)
    + (RAW_UNIT[spec.quantity] ? ` (${RAW_UNIT[spec.quantity]})` : ""));
  const cell = (value) => String(value ?? "")
    .replace(/\|/g, "\\|").replace(/\s*\n\s*/g, " ");
  const lines = [
    `| ${titles.map(cell).join(" | ")} |`,
    `| ${specs.map((spec) => (spec.numeric ? "---:" : "---")).join(" | ")} |`,
  ];
  for (const tr of rows) {
    const values = columns.map((column) => {
      const td = [...(tr.children ?? [])].find(
        (node) => node.getAttribute?.("data-column") === column);
      return cell(td ? (td.getAttribute("data-raw") || td.textContent) : "");
    });
    lines.push(`| ${values.join(" | ")} |`);
  }
  return lines.join("\n");
}

// `UX-450`: moved here from `structured.js`. This file is the
// table's *behaviour* - filters, bounds, presets, copy - and sorting
// is behaviour. It was in the DOM builder only because that is where
// it was first written.
// `UX-1190`: a table this short is read whole, so its header stays text.
export const SORTABLE_ABOVE = 10;

/** Rows in `column`'s order: numbers as numbers, anything else as text. */
export function byColumn(column, direction) {
  const sign = direction === "ascending" ? 1 : -1;
  const raws = new Map();
  const raw = (tr) => {
    if (!raws.has(tr)) {
      raws.set(tr, [...(tr.children ?? [])].find(
        (td) => td.getAttribute?.("data-column") === column)?.getAttribute?.("data-raw") ?? "");
    }
    return raws.get(tr);
  };
  return (a, b) => {
    const x = raw(a), y = raw(b);
    const nx = Number(x), ny = Number(y);
    const numeric = x !== "" && y !== "" && !Number.isNaN(nx) && !Number.isNaN(ny);
    return sign * (numeric ? nx - ny : String(x).localeCompare(String(y)));
  };
}

/** The table's own header cells - not a nested table's. */
export function ownHeads(table) {
  return childrenNamed(childrenNamed(childrenNamed(table, "thead")[0], "tr")[0], "th");
}

/** Mark `sort` on the table's own header, and only there. */
export function showSort(table, sort) {
  for (const th of ownHeads(table)) {
    if (sort && th.getAttribute("data-column") === sort.column) th.setAttribute("aria-sort", sort.direction);
    else th.removeAttribute("aria-sort");
  }
}

// `UX-450`: moved here from `structured.js`. This file is the
// table's *behaviour* - filters, bounds, presets, copy - and sorting
// is behaviour. It was in the DOM builder only because that is where
// it was first written.
export function sortable(table, specs = []) {
  const body = ownBody(table);
  if (everyRow(body).length <= SORTABLE_ABOVE) return;
  ownHeads(table).forEach((th, index) => {
    // UX-201: a column the schema declares unsortable stays unsortable,
    // whatever its values happen to look like.
    if (specs[index] && specs[index].sortable === false) return;
    // `UX-1190` (styleguide §6e.8): a button, so the sort is in the tab order.
    const label = th.textContent;
    th.textContent = "";
    th.append(el("button", { type: "button", class: "th-sort" }, label));
    th.addEventListener("click", () => {
      const was = th.getAttribute("aria-sort");
      // The first press on a quantity puts its largest first.
      const direction = was ? (was === "ascending" ? "descending" : "ascending")
        : specs[index]?.quantity ? "descending" : "ascending";
      const sort = { column: th.getAttribute("data-column"), direction };
      showSort(table, sort);
      // A head-and-tail fold is about the listing's order, which a sort replaces: open it first.
      childrenNamed(body, "tr").find((tr) => tr.className === "fold-row" && !tr.hidden)
        ?.querySelector?.("button")?.click?.();
      // The table's own tools re-rank past a bound; with none, every row is shown and reordered here.
      const event = new CustomEvent("bga:sort", { cancelable: true, detail: sort });
      table.dispatchEvent?.(event);
      if (event.defaultPrevented) return;
      // `UX-526`: over every row, held or shown.
      reorder(body, [...everyRow(body)].sort(byColumn(sort.column, direction)));
    });
  });
}
