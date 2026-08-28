/**
 * UX-337: the vocabulary every renderer speaks, in one module below them.
 *
 * `app.js`'s own first seam was called `format`, and this is that
 * chapter lifted out whole: the nine `bga:` hint keys, the readers that
 * pull them off a schema node (`hintsOf`, `childNode`, `quantityFor`),
 * the formatters that turn a number into a printed value under them,
 * and `el` - the one node constructor everything above builds with.
 *
 * The seam was drawn in prose already; what `UX-337` did before cutting
 * was count the symbols crossing it, with comments and string literals
 * stripped by a scanner rather than a regex - a `//` inside a string is
 * not a comment, and the first cut of that analysis, done with regexes,
 * ate 90% of the file and reported a clean split that was not one.
 *
 * Nothing here reaches upward. The one import is `primitives.js`, which
 * imports nothing itself, so the chain below `app.js` is
 * `primitives -> format -> structured` - and the export inlines modules
 * in exactly that order (`UX-199`, where a cycle shipped a report that
 * threw `ReferenceError` in `boot()` and rendered empty).
 */
import { elementAnchor } from "./primitives.js";

export const QUANTITY = "bga:quantity";

export const SEVERITY = "bga:severity";

export const COLUMNS = "bga:columns";

export const DIRECTION = "bga:direction";

// UX-303: the two hints §2 introduces. A value draws as a shape because
// a schema declared it one, never because it looked numeric.
export const SERIES = "bga:series";

export const DISTRIBUTION = "bga:distribution";

// UX-209: the question a section answers, and which part of the
// argument it belongs to. UX-208: what a column's values *are*.
export const QUESTION = "bga:question";

// UX-289: the named views over a table, declared in the schema.
export const PRESETS = "bga:presets";

// UX-346: where the schema's sentence lives. The default is the `?`
// door - closed, so the page is this run's numbers rather than the
// contract's glossary. Two classes of value keep the sentence beside
// them, and both are declared here rather than decided per call site:
// `"name"`, a label that invites a reading the value does not have,
// and `"caveat"`, a sentence whose absence changes what a reader would
// *do* with the number.
export const INLINE = "bga:inline";

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
    // UX-341 retired these four from the vocabulary a schema may
    // *declare*: the payload is µs, bytes and 0..1. They stay here as
    // renderer cases, because a value can still arrive carrying one -
    // `guessQuantity` below is a fallback with its own history, and an
    // external consumer may hand this function whatever it holds - and
    // rendering a known unit correctly costs five lines.
    //
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

export function el(tag, attrs = {}, ...children) {
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
                      RAIL, PRESETS, SERIES, DISTRIBUTION, INLINE]) {
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
  // UX-343: a map keyed by *data* - an element uid, a resource name -
  // cannot name its keys in `properties`, so the value's schema is
  // declared once under `additionalProperties`. Seven such maps in
  // `signals` alone put 56 leaves in front of the reader with no unit
  // at all, because there was nowhere to say what they were.
  if (node.additionalProperties &&
      typeof node.additionalProperties === "object") {
    return node.additionalProperties;
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
