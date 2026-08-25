// UX-302: the style guide's §1 dispatch table, as the one function
// every render path asks.
//
// The user's rule, adopted whole by `docs/design/styleguide.md` §1:
// **raw JSON on the page is a defect unless it is deliberate.** What
// replaces it there is a table - published shape (+ hint) on the left,
// the one control that may render it on the right. `UX-267` and
// `UX-277` built the controls; this file is the *dispatch*, so that
// "which control draws this value" is a question with one answer and
// one place to read it.
//
// Two properties follow from classifying by shape rather than by key,
// and both are why the table is worth having as code:
//
//   - a schema addition whose shape is in the table renders correctly
//     with **zero viewer changes** (`UX-193`);
//   - a shape *not* in the table is a **design task, not an
//     improvisation** - it lands in the guide with its control, then
//     in the code. Until it does, `classify` returns `UNMAPPED`, the
//     value renders as the labeled fold (which is honest: a label, a
//     count, and the JSON one click away), and `noteUnmapped` warns on
//     the console so that whoever added the shape finds out.
//
// This module imports nothing. It is a pure classification over a
// value plus its hints, so a guard can drive it without a DOM, and
// `app.js` can import it without a cycle.

/** The controls §1 names. The value is the guide's own wording. */
export const CONTROLS = Object.freeze({
  INLINE_OBJECT: "definition list",
  INLINE_LIST: "inline code list",
  FOLDED_LIST: "count + folded list",
  TABLE: "table",
  TUPLE_TABLE: "table of positional columns",
  MAP_TABLE: "table of key/value rows",
  FINDINGS: "findings blocks",
  FOLD: "the labeled fold",
});

/**
 * What `classify` says when §1 has no row for a value.
 *
 * `null` rather than a string, so that `if (!control)` is the check
 * and a caller cannot accidentally treat "unmapped" as a control name.
 */
export const UNMAPPED = null;

const isScalar = (value) => value === null || typeof value !== "object";
const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

/**
 * The §1 row for one value.
 *
 * `caps` carries the thresholds, which stay declared in `app.js` where
 * `UX-273`'s guard reads them - this file must not become a second
 * place they are written down.
 *
 * `depth` is `UX-277`'s cell nesting, and it wins over everything: past
 * the limit a value is the labeled fold whatever its shape, because
 * the fold is a bound on nesting rather than a reading of the value.
 */
export function classify(value, {
  severity = false, columns = null, depth = 0,
  nestLimit = Infinity, inlineFields = 4, inlineItems = 6,
} = {}) {
  if (isScalar(value)) return UNMAPPED;          // scalars are §1's top rows,
                                                 // drawn by the summary and
                                                 // the cell renderer, not here
  if (severity && Array.isArray(value)) return CONTROLS.FINDINGS;
  if (depth >= nestLimit) return CONTROLS.FOLD;

  if (Array.isArray(value)) {
    if (value.every(isScalar)) {
      return value.length <= inlineItems
        ? CONTROLS.INLINE_LIST : CONTROLS.FOLDED_LIST;
    }
    if (value.every(isPlainObject)) return CONTROLS.TABLE;
    if (value.every(Array.isArray)) {
      // Declared columns make it named columns; undeclared, positional
      // ones. Either way it is §1's "array of objects" row reached by
      // `UX-290`'s tuple rule - one control, not two.
      const declared = Array.isArray(columns)
        && columns.every((spec) => spec && typeof spec === "object" && spec.key)
        && value.every((item) => item.length === columns.length);
      return declared ? CONTROLS.TABLE : CONTROLS.TUPLE_TABLE;
    }
    // A **mixed** array - some scalars, some objects, some arrays. §1
    // has no row for it, and the code that used to reach it improvised
    // one row shape per item (and, at section level,
    // `[object Object], 2`). Unmapped, deliberately.
    return UNMAPPED;
  }

  const entries = Object.entries(value);
  if (!entries.length) return UNMAPPED;          // "none" is a sentence,
                                                 // which §1 draws for absence
  if (entries.length <= inlineFields && entries.every(([, m]) => isScalar(m))) {
    return CONTROLS.INLINE_OBJECT;
  }
  return CONTROLS.MAP_TABLE;
}

// The dev-mode console check. A shape §1 does not cover still renders -
// as the fold, so the reader is never shown nothing - but it must not
// render *quietly*, or the gap becomes permanent by going unnoticed.
const unmappedSeen = [];

/** Every unmapped shape this page met, in order, for a guard to read. */
export function unmappedShapes() {
  return unmappedSeen.slice();
}

/** Forget them. For a guard that renders more than one page. */
export function forgetUnmapped() {
  unmappedSeen.length = 0;
}

/**
 * Record and announce one unmapped shape.
 *
 * `where` is the value's path in the document, which is what makes the
 * warning actionable: it names the payload key to take to the guide.
 */
export function noteUnmapped(where, value, log = undefined) {
  const kind = Array.isArray(value)
    ? `array of ${[...new Set(value.map(
        (item) => Array.isArray(item) ? "array"
          : item === null ? "null" : typeof item))].sort().join("/")}`
    : value === null ? "null" : typeof value;
  const note = { where: String(where), kind };
  unmappedSeen.push(note);
  const sink = log ?? (typeof console !== "undefined" ? console : null);
  sink?.warn?.(
    `bga: no styleguide §1 control for ${note.where} (${kind}); `
    + "rendered as the labeled fold. Add the shape to "
    + "docs/design/styleguide.md §1, then to shapes.js.");
  return note;
}
