/**
 * UX-337: the primitives every chapter uses, in one module below them.
 *
 * **Derived, not chosen.** The split of `views.js` began by deriving
 * the dependency graph between its chapters, and the graph was not
 * acyclic:
 *
 * ```text
 * UX-202: the overview  ->  UX-206: two graphs  ->  the element object
 *                       <-------------------------------------------
 * ```
 *
 * Three edges, and each one was a single symbol: the overview reached
 * for `OVERVIEW_SHOWN`, the graphs for `elementAnchor`, the element
 * object for `bar`. None of the three is chapter content - a constant,
 * a pure string function and a DOM row builder - and the cycle was
 * entirely an artefact of where they happened to be written down.
 *
 * They live here with the formatters that were already shared, and the
 * chapters above are a DAG. This module imports **nothing**, which is
 * what makes that true rather than merely tidy: the export inlines
 * modules in dependency order and its whole premise is that what a
 * module imported is declared above it (`UX-199`, where a cycle shipped
 * a report that threw `ReferenceError` in `boot()` and rendered empty).
 */

/** The SVG namespace, and the one place `createElementNS` is called. */
export const SVG = "http://www.w3.org/2000/svg";

export function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(name, String(value));
  }
  return node;
}

// Small local formatters, kept separate from `format.js`'s `duration`
// and `bytes` on purpose rather than by accident. The cycle that used
// to justify the duplication is gone - `format.js` sits directly above
// this module and importing from it would be legal - but the two
// families do not print the same thing: `duration` says `400 ms` and
// `4.2 h` where `seconds` says `0.4 s` and `252.0 min`, so unifying
// them is a rendering change to every axis label and bar, not a
// deletion. `UX-201` folds formatting into one schema-driven place,
// which is where this duplication goes to die.
export function seconds(microseconds) {
  const s = microseconds / 1e6;
  return s < 90 ? `${s.toFixed(1)} s` : `${(s / 60).toFixed(1)} min`;
}

export function mib(value) {
  const units = ["B", "KiB", "MiB", "GiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

/** How many of the chain's elements are drawn before the fold. */
// UX-207: how many attribution bars stay unfolded.
export const OVERVIEW_SHOWN = 4;

/** The element uid an anchor fragment is spelled as. Mirrors
 *  `app.js`'s `cssId` - the two are asserted equal by a guard, because
 *  a link and its target spelling drifting apart is this item. */
export function elementAnchor(uid) {
  return `element-${String(uid).replace(/[^\w-]+/g, "-")}`;
}

export function bar(label, value, total, extra = {}) {
  const row = document.createElement("div");
  row.className = "wf-row";
  for (const [name, attr] of Object.entries(extra)) row.setAttribute(name, attr);
  const name = document.createElement("span");
  name.className = "wf-label";
  name.textContent = label;
  const track = document.createElement("span");
  track.className = "wf-track";
  const fill = document.createElement("span");
  fill.className = "wf-fill";
  // The only division in this file, and it is a *width*, not a number
  // the reader is told: the printed value is `value` itself.
  // CSSOM, never `setAttribute("style", ...)`: the server sends
  // `default-src 'self'` and a *style attribute* is inline style, so
  // Chrome refuses to apply it and the width channel silently dies
  // (`UX-263`). A property assignment is not inline style and is not
  // subject to the policy.
  fill.style.width =
    `${total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0}%`;
  track.append(fill);
  const amount = document.createElement("span");
  amount.className = "wf-value num";
  amount.setAttribute("data-raw", String(value));
  amount.textContent = seconds(value);
  row.append(name, track, amount);
  return row;
}

// UX-199: a served page can ask the server; an export cannot. One
// predicate, so the two modes cannot disagree about which they are.
export function served() {
  // `UX-303`: guarded, because this is now asked while a *table* is
  // being built rather than only during boot. A page always has a
  // `location`; a harness driving `buildTable` directly need not, and
  // a throw here would take the whole render down - `UX-199`'s defect
  // by a new route. No location is not a server.
  if (typeof location === "undefined" || !location) return false;
  return /^https?:$/.test(location.protocol);
}

export function safeStorage() {
  try {
    return window.localStorage;
  } catch (error) {
    // Blocked site data, a private window, a thumbnail renderer.
    return null;
  }
}
