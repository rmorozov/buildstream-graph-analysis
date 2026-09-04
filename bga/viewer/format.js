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

// `UX-361` (§2d): the two shapes the vocabulary did not have. Both name
// **published paths**, resolved against the document, so the page lays
// out numbers it was handed rather than choosing parts or an axis.
export const DECOMPOSITION = "bga:decomposition";

export const INTERVAL = "bga:interval";

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

// `UX-391`: what a map's own keys *are*, where they are not names.
//
// `UX-374` made a published key render verbatim, which is right for an
// element uid and a binary name and wrong for a **task** uid:
// `codegen.bst|BUILD|BUILD|0` went to the reader as a row label, so a
// reader searching the page for `codegen.bst` did not match the row and
// a reader reading it had to know the tool's key format to see that
// three of the four fields are `BUILD`, `BUILD`, `0`.
//
// The composite is right as identity - a retry and a fetch of one
// element are different rows - so it stays as the row's `data-key` and
// what changes is only what is shown.
export const KEYED_BY = "bga:keyed_by";

/**
 * `UX-390`: the payload key holding this map's per-key advice.
 *
 * Declared, never sniffed. A page that looked for `<key>_hints` would
 * be the name-guessing `UX-201` removed, and the two sentences a bucket
 * carries are different things: the schema's `description` says what
 * the bucket is, this says what to do about it **on this run**.
 */
export const EXPLAINED_BY = "bga:explained_by";

/**
 * `UX-429`: this scalar array is one command line, not a list.
 *
 * `["bga", "blast", "x.bst"]` and `["cmake", "ninja"]` are the same
 * measured shape and §1 draws the second as an inline code list, which
 * is right. Only the schema knows the first is argv - so it says so,
 * and `classify` reads it rather than sniffing for a verb.
 */
export const COMMAND = "bga:command";

/**
 * `UX-390`: the run's advice about one key of an explained map.
 *
 * `attribution` and `attribution_hints` were the same eight bucket
 * names in two `<h2>` sections - a number in one chapter, the sentence
 * explaining it in another, and nothing in either saying they were the
 * same eight things (`UX-288`'s rule at section level). The contract
 * names where the advice lives, so the renderer draws it without
 * knowing which map it is looking at, and the hints key is
 * `DRAWN_ELSEWHERE`: one section rather than two.
 *
 * `""` for anything else, so a caller can test it directly.
 */
export function adviceFor(payload, hint, name) {
  const said = (payload?.[hint?.[EXPLAINED_BY]] ?? {})[name];
  return typeof said === "string" ? said : "";
}
export const KEYED_BY_TASK_UID = "task_uid";

/**
 * What a map's key should *show*, given the map's own declaration.
 *
 * `null` where the key is a name already, which is every map but one -
 * so the call site is one branch rather than a rule restated there.
 */
export function keyAsShown(name, hint = {}) {
  return hint[KEYED_BY] === KEYED_BY_TASK_UID ? taskUid(name) : null;
}

/** `element|kind|phase|attempt` split into a name and a qualifier. */
export function taskUid(key) {
  const parts = String(key).split("|");
  if (parts.length < 4) return { element: String(key), qualifier: null };
  const [element, kind, phase, attempt] = parts;
  // The qualifier says what is *not* the element, and drops what would
  // be noise: `BUILD|BUILD|0` is one BUILD task, first attempt, and
  // printing all three tells the reader nothing they did not have.
  const said = [];
  if (phase && phase !== kind) said.push(phase);
  said.push(kind);
  if (attempt && attempt !== "0") said.push(`attempt ${attempt}`);
  return { element, qualifier: said.join(", ") };
}

const RAIL = "bga:rail";

// `UX-643`: the `R1`-`R5` ids this section serves, declared by the
// producer. Absent is the common case and means no role, not none.
const READERS_SERVED = "bga:readers";

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
    // UX-613: a rate names its time base in the quantity, so the
    // rendering spells the same base the contract does.
    case "rate_per_day": return `${Math.round(value * 100) / 100}/day`;
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

/**
 * `UX-351`: the suffix a quantity already accounts for, per quantity.
 *
 * Keyed by the *quantity*, not by the suffix, which is the property
 * the item is about: `_us` comes off a `duration_us` and stays on
 * anything else, so a key named like a duration and declared as
 * something else looks as odd as it is instead of being quietly
 * tidied. The retired spellings (`quantity` above keeps rendering
 * them) are here for the same reason they are there - a value can
 * still arrive carrying one.
 *
 * Only the quantities whose *rendered value* spells the unit are
 * listed. A `count` renders as a bare number and a `ratio` as
 * `1.5x`, so "Process count" and "Inefficiency ratio" are telling a
 * reader something the value beside them does not.
 */
const UNIT_SUFFIX = {
  duration_us: /_us$/,
  seconds: /_seconds$/,
  bytes: /_bytes$/,
  megabytes: /_mb$/,
  kilobytes: /_kb$/,
  share: /_share$/,
  percent: /_pct$/,
  rate_per_day: /_per_day$/,
};

/**
 * A payload key as a label.
 *
 * `UX-341` made every duration key end `_us` and every memory key end
 * `_bytes`, so the reader met "Execution on chain us  43.2 s" - the
 * suffix answering, in a spelling that is not English, a question the
 * value beside it had already answered. The suffix is for the
 * contract; this is for the reader, and `kind` is what tells the two
 * apart.
 *
 * `kind` is the quantity the *value* is being rendered under - pass
 * what `quantityFor` returned, so declared beats guessed here for the
 * same reason it does there. Without one nothing is trimmed: a label
 * whose value is rendered as a bare number keeps every token it has.
 */
export function title(key, kind = null, published = false) {
  // `UX-374`: a key that is **data** is rendered as it was published.
  //
  // Everything below this line is right for a *schema* key and wrong
  // for a name the tool was given. Measured on `macro_micro`, before:
  //
  // ```text
  //   published                       rendered
  //   codegen.bst|BUILD|BUILD|0       Codegen.bst|BUILD|BUILD|0
  //   cmake                           Cmake
  //   cc1plus                         Cc1plus
  // ```
  //
  // Twenty-two of them, every one renamed. A reader searching the page
  // for `cmake` did not find the row, and a reader copying one pasted
  // a name their project does not have - `UX-326`'s rule about the
  // tool's sentences, applied to the one class of string the tool must
  // never author.
  //
  // The underscore and the unit trim are as wrong as the capital:
  // `a_b.bst` is not "A b.bst", and a binary called `x_us` would lose
  // its tail. So this returns before all three rather than skipping
  // one.
  if (published) return key;
  const suffix = UNIT_SUFFIX[kind];
  // Never trim a key down to nothing: `_us` alone is not a label.
  const trimmed = suffix ? key.replace(suffix, "") : key;
  const named = trimmed || key;
  return named.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

/**
 * `UX-374`: is `key` a name the *payload* chose, rather than the
 * contract?
 *
 * The schema already draws this line and no new hint is needed:
 * `childNode` has resolved a declared member through `properties` and
 * a data-keyed one through `additionalProperties` since `UX-343` - a
 * map whose keys are element uids or binary names cannot name them in
 * `properties`, so it declares the *value* once underneath. That is
 * the predicate, read off the same node.
 *
 * **False where there is no schema**, which is the status quo rather
 * than a judgement: an undeclared node says nothing about its keys,
 * and guessing that a key is data would rename contract keys the other
 * way. The keys this item is about are all declared.
 */
export function dataKeyed(node, key) {
  if (!node || typeof node !== "object") return false;
  if (node.properties && key in node.properties) return false;
  // An array's items are positional; `childNode` resolves through
  // `items`, and neither branch is a data-keyed map.
  if (node.items) return false;
  return Boolean(node.additionalProperties
                 && typeof node.additionalProperties === "object");
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
  const served = hint[READERS_SERVED];
  return { question: hint[QUESTION] ?? null, label: hint[QUESTION] ?? title(key),
           subtitle: hint[QUESTION] ? key : null,
           rail: hint[RAIL] ?? "raw",
           readers: Array.isArray(served) ? served.map(String) : [] };
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
  // `UX-643`: the tag a promoted block wears, built here because this
  // is the one place a section's head is made - and built **empty**,
  // because `UX-305`'s budget is spent on the sections one chosen role
  // owns, not on all of them. `applyRole` fills it and the stylesheet
  // shows it only while the section is promoted. The declared roles
  // ride on it so nothing has to re-read the schema at click time.
  if (info.readers.length) {
    node.append(el("span", { class: "reader-tag", "data-reader-tag": "",
                             "data-readers": info.readers.join(" ") }));
  }
  return node;
}

// `UX-391` moved this here from `structured.js`. It is a *label* -
// the term, its sentence and the `?` door - and every other label
// mechanism (`title`, `heading`, `sectionHead`) already lives in this
// module; `structured.js` was at `UX-337`'s 1,500-line ceiling and a
// label branch was the wrong thing to spend the last lines on. Nothing
// about the function changed, and `el`/`title` are both local here, so
// the move adds no import edge (`bga/viewer` stays acyclic).
/**
 * `UX-317` (styleguide §2b.3): **a described value shows its
 * affordance.**
 *
 * `UX-201` sourced the "why does this number matter" sentence from the
 * schema and put it in a `title`, where discovery is hover archaeology:
 * the reader who does not know to hover never learns what
 * `scheduler_wait` means, and the one who does gets a tooltip they
 * cannot keep open while comparing two values.
 *
 * So the term carries a visible `?`, and the sentence opens **beside
 * the value** - which is why the description node is built here and
 * appended to the `<dd>` rather than to the `<dt>`. The `title` stays:
 * it costs nothing, and it is what a screen reader and a keyboard
 * focus already read.
 *
 * `UX-346`: **and the door has to close.** It did not - `.description`
 * sets `display`, which beats `[hidden]`'s UA rule, so the sentence
 * rendered whatever the marker said, and 43% of the golden page's
 * words were the contract's glossary. The CSS closes it; `inline` is the declared
 * exception (`bga:inline`, `name` or `caveat`), which keeps its
 * sentence beside the value and draws no marker at all.
 *
 * Returns `{ term, describe }` - the `<dt>`, and the node to put in the
 * `<dd>`, or `null` when the schema describes nothing.
 */
export function describedTerm(name, description, attrs = {}, inline = null,
                              kind = null, published = false) {
  // `UX-374`: `published` -> the label *is* `data-key`, verbatim.
  const term = el("dt", { ...attrs, "data-key": name,
                          title: description ?? null,
                          "data-described": description ? "true" : null,
                          "data-inline": inline ?? null },
                  title(name, kind, published));
  if (!description) return { term, describe: null };
  // UX-346: a declared exception is not behind a door at all. There is
  // no marker for it either - a `?` beside a sentence already on screen
  // is the duplication this item was filed on.
  if (inline) {
    return { term, describe: el("span", { class: "description",
                                          "data-role": "description",
                                          "data-inline": inline,
                                          "data-describes": name },
                                description) };
  }
  const sentence = el("span", { class: "description",
                                "data-role": "description",
                                "data-describes": name, hidden: "" },
                      description);
  sentence.hidden = true;
  const marker = el("button", {
    type: "button", class: "describe", "data-describe": name,
    "aria-expanded": "false",
    // `UX-279`: the control says what it does before it is pressed.
    title: `What ${title(name, kind, published)} means`,
  }, "?");
  marker.addEventListener?.("click", () => {
    const open = marker.getAttribute("aria-expanded") === "true";
    marker.setAttribute("aria-expanded", open ? "false" : "true");
    sentence.hidden = open;
  });
  term.append(marker);
  return { term, describe: sentence };
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
                      RAIL, READERS_SERVED, PRESETS, SERIES, DISTRIBUTION,
                      INLINE, DECOMPOSITION, INTERVAL, KEYED_BY,
                      EXPLAINED_BY, COMMAND]) {
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
