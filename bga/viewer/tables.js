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
 */
export function ownRows(table) {
  return childrenNamed(ownBody(table), "tr");
}

/** `UX-532`: one column's cells, over this table's own rows only. */
export function ownCells(table, column) {
  return ownRows(table).flatMap((tr) => [...(tr.children ?? [])].filter(
    (td) => td.getAttribute?.("data-column") === column));
}

/** The text a row matches on: every cell's rendered text, joined. */
export function rowText(tr) {
  return [...tr.children].map((td) => td.textContent).join(" ").toLowerCase();
}

/**
 * Apply the text box and the per-column thresholds to a rendered table.
 * Returns how many rows survived, which is what the badge shows.
 */
export function applyFilters(table, { text = "", thresholds = {},
                                     top = null } = {}) {
  const needle = String(text).trim().toLowerCase();
  const body = ownBody(table);
  const rows = ownRows(table);
  const kept = [];
  let shown = 0;
  for (const tr of rows) {
    let keep = !needle || rowText(tr).includes(needle);
    if (keep) {
      // Over the *thresholds*, not over the row's cells: walking the
      // cells means a threshold naming a column this row does not carry
      // is never checked, and every row passes a filter that should
      // have emptied the table. "No value" does not pass "> 5s".
      for (const [column, threshold] of Object.entries(thresholds)) {
        const cell = [...tr.children].find(
          (td) => td.getAttribute("data-column") === column);
        if (!passes(cell ? cell.getAttribute("data-raw") : null, threshold)) {
          keep = false;
          break;
        }
      }
    }
    tr.hidden = !keep;
    if (keep) { shown += 1; kept.push(tr); }
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
  if (top && Number.isFinite(Number(top.n))) {
    if (top.column) {
      const value = (tr) => {
        const cell = [...tr.children].find(
          (td) => td.getAttribute("data-column") === top.column);
        const raw = Number(cell ? cell.getAttribute("data-raw") : NaN);
        return Number.isFinite(raw) ? raw : -Infinity;
      };
      kept.sort((a, b) => value(b) - value(a));
    }
    kept.forEach((tr, index) => {
      tr.hidden = index >= Number(top.n);
      body.append(tr);
    });
    shown = Math.min(Number(top.n), kept.length);
  }
  return shown;
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
export function openingBound(presets, total, bound) {
  if (total <= bound) return null;
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
export function badgeText(shown, total) {
  const n = (value) => value.toLocaleString("en-US");
  // The `N of M` form needs no agreement: a denominator is always a
  // population, and `1 of 12` is right as it stands.
  return shown === total ? plural(total, "row") : `${n(shown)} of ${n(total)}`;
}

/**
 * `UX-413`: the same bound, over cards instead of rows.
 *
 * `renderFindings` draws one `<article>` per finding rather than a
 * table, so the row bound cannot see it at all - `UX-400`'s sweep at
 * 120 measured **120 cards drawn**, on a page whose every table
 * stopped at 25.
 *
 * The cards past the bound are *hidden*, not removed, for the reason
 * `foldTheMiddle` hides rather than removes: Ctrl-F, the export and
 * every `#anchor` into a finding keep working. One control says how
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
 * for the reason `foldTheMiddle` hides rather than removes: Ctrl-F, the
 * export and every anchor keep working. Returns the control, or `null`
 * when there was nothing to bound.
 */
export function boundGroups(groups, bound, noun = "item") {
  if (groups.length <= bound) return null;
  for (const [index, group] of groups.entries()) {
    for (const node of group) node.hidden = index >= bound;
  }
  const badge = el("span", { class: "badge" },
                   badgeText(bound, groups.length));
  const more = el("button", { type: "button", class: "show-all-cards" },
                  `Show all ${plural(groups.length, noun)}`);
  more.addEventListener("click", () => {
    for (const group of groups) for (const node of group) node.hidden = false;
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
  return boundGroups(groups, bound, noun);
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
    out[column] = raw !== "" && !Number.isNaN(number) ? number : raw;
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

/**
 * `UX-208` item 4: a Top-N preset over a declared quantity column.
 *
 * Sorts by the published value and shows the first N. The badge keeps
 * reporting the truth - `10 of 1,202` - because the preset narrows what
 * is *shown*, it does not pretend the rest are gone.
 */
export function applyTopN(table, column, n) {
  const body = ownBody(table);
  const rows = ownRows(table);
  const value = (tr) => {
    const cell = [...tr.children].find(
      (td) => td.getAttribute("data-column") === column);
    const raw = Number(cell ? cell.getAttribute("data-raw") : NaN);
    return Number.isFinite(raw) ? raw : -Infinity;
  };
  rows.sort((a, b) => value(b) - value(a));
  rows.forEach((tr, index) => {
    tr.hidden = index >= n;
    body.append(tr);
  });
  return Math.min(n, rows.length);
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
  const titles = specs.map((spec) => spec.title ?? spec.key);
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
export function sortable(table, specs = []) {
  const body = ownBody(table);
  table.querySelectorAll("th").forEach((th, index) => {
    // UX-201: a column the schema declares unsortable stays unsortable,
    // whatever its values happen to look like.
    if (specs[index] && specs[index].sortable === false) return;
    th.addEventListener("click", () => {
      const ascending = th.getAttribute("aria-sort") !== "ascending";
      table.querySelectorAll("th").forEach((other) =>
        other.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      const rows = ownRows(table);
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

