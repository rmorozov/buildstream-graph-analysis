// UX-334: a form control the browser can name.
//
// Chrome's Issues panel raises `FormEmptyIdAndNameAttributesForInputError`
// for every `<input>`, `<select>` and `<textarea>` with neither an `id`
// nor a `name`, and `FormLabelHasNeitherForNorNestedInput` for every
// `<label>` that neither wraps its control nor points at one. Measured
// on the golden fixture before this existed: **138 and 6** on the
// exported page, **70 and 10** on the served one - two hundred entries
// in a panel a reader opens to find one real problem.
//
// An `aria-label` does not answer either complaint. Six of them were on
// these very controls (`UX-317` put them there and they are right to be
// there), and the panel still reported all of it: the browser is asking
// for the identity a *form control* has - the thing autofill, a `<label
// for=>` and a restored session all key off - not for its accessible
// name.
//
// This module imports nothing, so `views.js` can use it without the
// cycle back through `app.js` that its own note at the top forbids.

// Document-unique, and stable for the first control that asks for a
// given stem: the ids are what `<label for=>` points at and what a
// bookmarked page would restore by, so a counter on *every* control
// would renumber the page on every render for no gain.
const taken = new Set();

/** A sanitized, document-unique id from `stem`. */
export function uniqueId(stem) {
  const base = `bga-${String(stem)}`.replace(/[^A-Za-z0-9_-]+/g, "-")
                                    .replace(/-+/g, "-")
                                    .replace(/-$/, "");
  if (!taken.has(base)) { taken.add(base); return base; }
  for (let n = 2; ; n += 1) {
    const candidate = `${base}-${n}`;
    if (taken.has(candidate)) continue;
    taken.add(candidate);
    return candidate;
  }
}

/**
 * Give `node` a `name` and a unique `id`, and return the id.
 *
 * `name` is the stem as written - it is scoped to a form, and there is
 * no form here - while the `id` is uniquified, because a document may
 * carry the same table twice (a preset view and the section it came
 * from) and two nodes with one id is its own defect.
 */
export function identify(node, stem) {
  const id = uniqueId(stem);
  node.setAttribute?.("name", String(stem));
  node.setAttribute?.("id", id);
  return id;
}

/** Point `label` at `node`, identifying `node` if it is not already. */
export function labelFor(label, node, stem) {
  const id = node.getAttribute?.("id") || identify(node, stem);
  label.setAttribute?.("for", id);
  return id;
}

// For the guards: a fresh document is a fresh id space. The page never
// calls this - it loads once - but a test file that boots the shim
// twice would otherwise see `-2` suffixes it did not ask for.
export function forgetIds() {
  taken.clear();
}
