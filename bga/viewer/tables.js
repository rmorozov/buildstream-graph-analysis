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
