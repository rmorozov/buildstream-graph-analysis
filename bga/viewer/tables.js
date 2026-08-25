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

/** How many microseconds/bytes/… one suffix is worth, per quantity. */
const UNITS = {
  duration_us: { us: 1, ms: 1e3, s: 1e6, m: 60e6, h: 3600e6 },
  seconds: { us: 1e-6, ms: 1e-3, s: 1, m: 60, h: 3600 },
  bytes: { b: 1, kb: 1024, k: 1024, mb: 1024 ** 2, m: 1024 ** 2,
           gb: 1024 ** 3, g: 1024 ** 3 },
  megabytes: { b: 1 / 1024 ** 2, kb: 1 / 1024, mb: 1, m: 1,
               gb: 1024, g: 1024 },
  // UX-215: `peak_rss_kb`. A threshold typed as `> 512mb` on a
  // kilobyte column has to mean 524,288, not 512.
  kilobytes: { b: 1 / 1024, kb: 1, k: 1, mb: 1024, m: 1024,
               gb: 1024 ** 2, g: 1024 ** 2 },
  share: { "%": 0.01 },
  percent: { "%": 1 },
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

/** The text a row matches on: every cell's rendered text, joined. */
export function rowText(tr) {
  return [...tr.children].map((td) => td.textContent).join(" ").toLowerCase();
}

/**
 * Apply the text box and the per-column thresholds to a rendered table.
 * Returns how many rows survived, which is what the badge shows.
 */
export function applyFilters(table, { text = "", thresholds = {} } = {}) {
  const needle = String(text).trim().toLowerCase();
  const body = table.querySelector("tbody");
  const rows = [...body.querySelectorAll("tr")];
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
    if (keep) shown += 1;
  }
  return shown;
}

/** `12 of 1,202` - and just the total when nothing is filtered. */
export function badgeText(shown, total) {
  const n = (value) => value.toLocaleString("en-US");
  return shown === total ? `${n(total)} rows` : `${n(shown)} of ${n(total)}`;
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
  const body = table.querySelector("tbody");
  const rows = [...body.querySelectorAll("tr")];
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
