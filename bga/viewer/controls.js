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
import { el } from "./format.js";

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

// UX-335: a section that throws loses its section, not the page.
//
// `boot()` has one page-wide `try/catch`, so **any** renderer's throw
// replaced the whole report with "Could not load this run". Measured on
// the golden run served with a single `null` row in `store.json` - the
// shape a field capture hit:
//
//     refused: "Could not load this run
//               TypeError: Cannot read properties of null (reading 'elements')"
//     sections rendered: 0
//
// Forty-eight sections' worth of correct analysis thrown away because
// one row of one optional payload was malformed. The page-wide catch
// stays for *load* failures - a report that will not parse is not a
// report - but a renderer's throw is now contained where it happened.
//
// **It also reaches the console on purpose.** The catch is what made
// this class invisible to `UX-334`'s console guard: the page swallowed
// the throw and rendered a banner, so the boot came back with zero
// console errors and a net built for exactly this saw nothing. A
// contained failure that is silent is a failure nobody measures.

/** The card a failed section leaves behind: what broke, and from where. */
export function sectionFailure(doc, name, payload, error) {
  const card = doc.createElement("section");
  card.className = "verdict refused section-failed";
  card.setAttribute("data-section", name);
  card.setAttribute("data-section-failed", "true");
  card.setAttribute("data-payload", payload);
  const head = doc.createElement("h2");
  head.textContent = `This section could not be drawn: ${name}`;
  const why = doc.createElement("p");
  // The payload path, because that is the half a reader can act on:
  // the section is a consequence, the document is the cause.
  why.textContent =
    `Its renderer threw on \`${payload}\`, so this section is missing and `
    + `the rest of this report is not. ${String(error)}`;
  card.append(head, why);
  return card;
}

/**
 * Run `build`, or return the card that says why it could not.
 *
 * `name` is the section, `payload` the document it was drawn from -
 * both appear in the card and in the console line, so a reader and a
 * guard read the same two facts.
 */
export function contained(doc, name, payload, build) {
  try {
    return build();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`bga: section "${name}" failed on ${payload}:`, error);
    return sectionFailure(doc, name, payload, error);
  }
}


/**
 * `UX-429` (§1's command row): one command line, wherever one is drawn.
 *
 * Three sites rendered `next_steps[].argv`: `decision.js` and
 * `views.js` each hand-joined it with a space and hand-rolled a copy
 * button, and the table path did neither - so the same field read as a
 * runnable command in two places and as `bga, blast, elem.bst` in the
 * third. That is the drift a shared control exists to prevent, so all
 * three call this.
 *
 * Returns the **nodes**, not a wrapper: the three callers append into
 * three different parents, and a wrapper element would change the DOM
 * that existing guards read for `.next-command` and `.copy-step`.
 *
 * `copy` is the page's clipboard writer, absent in the export where
 * there is none - and then the line still renders, because a command
 * you can select is worth more than no command. The table path passes
 * none deliberately: inside a table §4c's affordance is the table's
 * own (double-click a cell, or Copy rows), and a fourth copy control
 * per row is the clutter `UX-284` measured rather than a fix.
 */
export function commandLine(argv, { make = el, copy = null, deps = {} } = {}) {
  const text = Array.isArray(argv) ? argv.join(" ") : String(argv ?? "");
  if (!text) return [];
  const code = make("code", { class: "next-command", "data-argv": text });
  code.textContent = text;
  if (!copy) return [code];
  const label = "Copy command";
  const button = make("button", {
    type: "button", class: "copy-step", "data-copies": "command",
    title: "Copy this command to the clipboard, ready to run" });
  button.textContent = label;
  button.addEventListener?.("click", () => {
    copy(text);
    button.textContent = "\u2713 copied";
    (deps.setTimeout ?? setTimeout)(() => { button.textContent = label; }, 1200);
  });
  return [code, button];
}
