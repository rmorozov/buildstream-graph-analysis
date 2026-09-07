// UX-747: a module whose only job is a *partial* grouping's two homes.
//
// `crossings()` keyed a crossing by (the referencing declaration's
// group, the referenced one's group), and an unplaced declaration put
// `None` in the first half. One key with a group and one with `None`
// sorted against each other raised `TypeError` — on exactly the partial
// grouping the `derive` skill documents.
//
// `interpolated.js` cannot produce both at once: `gamma` is its only
// declaration that references another, so a grouping either places it
// (one key, a group) or leaves it out (one key, `None`). Two referencing
// declarations is the whole point of this file, and it is separate so
// that fixture's measured counts — `LABEL` twice, `alpha` once, one
// crossing — stay exactly what they were built to be.

export const SHARED = "shared";

export function placed() {
  return SHARED;
}

export function unplaced() {
  return SHARED;
}
