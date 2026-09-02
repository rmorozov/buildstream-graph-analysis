/**
 * UX-337: the element object - one element, everything known about it.
 *
 * Split out of `views.js`, which was 2,531 lines and where every edit
 * paid a long read. The cut is the chapter rule `views.js` already
 * carried as a comment; what was *derived* rather than assumed is that
 * the chapters are acyclic once `primitives.js` exists, and that this
 * chapter needs exactly three symbols from the one above it.
 *
 * This is a **move**. No rendering behaviour changed with it, and the
 * exported page is asserted byte-for-byte and section-for-section
 * against a capture taken before the split - because `UX-199` is on
 * file for exactly this inlining shipping a report that threw
 * `ReferenceError` in `boot()` and rendered empty for several rounds.
 */
import { identify, labelFor } from "./controls.js";
import {
  SVG, svg, seconds, mib, bar, OVERVIEW_SHOWN, elementAnchor,
} from "./primitives.js";
import {
  SCALE, GRADE_ANNOTATION, GRADE_EXHIBIT, exhibitAxis, exhibitTwin,
} from "./drawings.js";
// The three the derivation named, and the whole of what this chapter
// takes from the one above it.
import { renderBand, verdictMarker, verdictMarkers } from "./views.js";

// -------------------------------------------------- the element object
//
// UX-216. An element uid appears in findings, the critical path, three
// signals tables, the blast tree, the top actions and (since UX-215)
// the two-plane join. A reader who wants "everything about core.bst"
// reads six sections and joins them by hand.
//
// And UX-208 shipped the affordance for exactly this and pointed it at
// nothing: every row's Inspect anchored at `#element-<uid>`, an id
// nothing in the page ever set. Measured on examples/06 before this
// landed: 19 links, 11 distinct targets, 11 of 11 unresolvable. This
// is what they land on, which is why the fix and the object are one
// change rather than two.
//
// Deliberately a *section*, not a drawer. Overlay machinery is the one
// part of this page that would not survive an export opened from a
// downloads folder, a print, `filter: grayscale`, or a pasted anchor -
// and a section is linkable, printable, collapsible and foldable by
// machinery that already exists.

// How many element sections a report renders. The set below is already
// bounded by the analysis (a path, a top-N, a findings list), but a
// 4,000-element report can still produce a long path, and UX-187's rule
// is that an elision names its own count.
export const ELEMENTS_SHOWN = 24;


/**
 * The uid an anchor was spelled from, or `null`.
 *
 * `elementAnchor` is lossy - `layer00/mod051.bst` and
 * `layer00-mod051-bst` sanitise alike - so the way back is to ask which
 * uid the payload names that spells to this anchor, rather than to try
 * to invert the spelling. Every uid the run has is a key of
 * `element_durations`, with the other element-keyed maps as the
 * fallback for a run that carries no durations.
 */
export function uidForAnchor(payload, id) {
  if (!id || !String(id).startsWith("element-")) return null;
  const seen = new Set();
  const maps = ["elements.element_durations", "elements.blast_radius",
                "elements.criticality_probability",
                "leaf_analysis.leaves_detail"];
  for (const path of maps) {
    const map = path.split(".").reduce((node, key) => node?.[key], payload);
    for (const uid of Object.keys(map ?? {})) {
      if (seen.has(uid)) continue;
      seen.add(uid);
      if (elementAnchor(uid) === id) return uid;
    }
  }
  return null;
}

/**
 * Everything the payload says about each element it discusses.
 *
 * Published fields only, and no arithmetic: a value that is not in the
 * document does not appear here. The order is the report's own ranking
 * - top actions first, then the path, then the horizon - so the
 * sections a reader meets first are the ones the decision named.
 */
/**
 * UX-227: walk a published path, the same grammar `bga/provenance.py`
 * resolves.
 *
 * Dotted keys, `[i]` for a list index, `[key=value]` for the one list
 * entry matching it. Two implementations of one grammar is a risk, and
 * the guard takes it seriously: it resolves every path this page emits
 * through *both* and compares, so a divergence is a failing test rather
 * than a wrong number in a tooltip.
 */
export function resolvePath(document, path) {
  let node = document;
  // Scanned rather than split on ".": element uids contain dots, so
  // `[element_uid=core.bst]` is nonsense the moment the separator is
  // taken literally. `bga/provenance.py` had the same bug and this
  // page is what found it.
  for (const segment of pathSegments(String(path))) {
    if (typeof segment === "string") {
      if (node === null || typeof node !== "object" || !(segment in node)) {
        return undefined;
      }
      node = node[segment];
    } else if (segment.bracket !== undefined) {
      // One bracket, two containers: a list takes it as an index, an
      // object as a key. Maps keyed by element uid are why - a uid
      // contains dots, so the dotted form cannot address one.
      if (Array.isArray(node)) node = node[Number(segment.bracket)];
      else if (node && typeof node === "object") node = node[segment.bracket];
      else return undefined;
    } else {
      if (!Array.isArray(node)) return undefined;
      node = node.find((entry) => entry
        && String(entry[segment.key]) === segment.value);
    }
    if (node === undefined) return undefined;
  }
  return node;
}

function pathSegments(path) {
  const segments = [];
  let name = "", inside = null;
  for (const char of path) {
    if (inside === null && char === ".") {
      if (name) segments.push(name);
      name = "";
    } else if (inside === null && char === "[") {
      if (name) segments.push(name);
      name = ""; inside = "";
    } else if (inside !== null && char === "]") {
      const equals = inside.indexOf("=");
      segments.push(equals === -1
        ? { bracket: inside }
        : { key: inside.slice(0, equals), value: inside.slice(equals + 1) });
      inside = null;
    } else if (inside !== null) {
      inside += char;
    } else {
      name += char;
    }
  }
  if (name) segments.push(name);
  return segments;
}

/**
 * `UX-356`: the join's advice and its nested evidence, onto a record.
 *
 * `recommendations[].text` is the sentence the analyzer wrote for this
 * reader - *"holds 44% of the critical path … remove `notparallel` /
 * raise its job count before touching its sources"* - and the page
 * rendered its `severity` and dropped it. Twenty-three of them on
 * `macro_micro`, reaching no node outside the embedded payload. §1b's
 * second clause: where the payload publishes prose written for this
 * reader, the page prints the prose.
 */
function joinDetail(record, entry) {
  for (const advice of entry.recommendations ?? []) {
    if (!advice?.text) continue;
    record.advice.push({
      id: advice.id ?? "",
      severity: String(advice.severity ?? "info").toLowerCase(),
      text: advice.text,
      path: `element_join[element=${entry.element}].recommendations`,
    });
  }
  for (const [key, label, fields] of JOIN_EVIDENCE) {
    const held = entry[key];
    if (!held) continue;
    const rows = [];
    const already = new Set();
    for (const [field, name, kind] of fields) {
      const value = held[field];
      if (value === null || value === undefined || value === "") continue;
      // `UX-349`'s rule, inside a block: a value identical to one
      // already in it is a fact about the block, not a second row.
      // `worst_redundancy.example_cmd` is the case - it equals
      // `signature` unless the normalisation changed something, and
      // where it does differ it is the concrete command and worth its
      // line.
      if (already.has(String(value))) continue;
      already.add(String(value));
      rows.push({ label: name, value, kind, field,
                  path: `element_join[element=${entry.element}].${key}.${field}` });
    }
    if (rows.length) record.evidence.push({ key, label, rows });
  }
  // The two lists the join publishes as bare strings. Not a table:
  // they are names, and `UX-302`'s mapping says a short scalar array
  // is an inline list.
  for (const [key, label] of [["native_findings", "Plane 2 flagged"],
                              ["unused_dependencies", "Depends on, unused"]]) {
    const held = entry[key];
    if (Array.isArray(held) && held.length) {
      record.lists.push({ key, label, items: held.map(String) });
    }
  }
}

export function elementFacts(payload) {
  const facts = new Map();
  const touch = (uid) => {
    if (!uid) return null;
    if (!facts.has(uid)) {
      facts.set(uid, { element: uid, rows: [], findings: [], entering: [],
                       advice: [], evidence: [], lists: [] });
    }
    return facts.get(uid);
  };

  // Where each fact comes from, declared rather than repeated: the
  // published array, the key that names the element in it, and the
  // fields worth showing with the quantity each is in. Adding a field
  // is a line here, and no new code.
  for (const [array, idKey, fields] of SOURCES) {
    const rows = array.split(".").reduce((node, key) => node?.[key], payload);
    for (const entry of rows ?? []) {
      const record = facts.has(entry[idKey]) || array !== "element_join"
        ? touch(entry[idKey]) : null;      // the join follows, never leads
      if (!record) continue;
      for (const [field, label, kind] of fields) {
        const value = entry[field];
        if (value !== null && value !== undefined) {
          // UX-227: and *where it came from*, as a path a reader (or a
          // guard) can walk back into the payload. Built from the
          // source declaration rather than written per field, so a new
          // entry in SOURCES is still one line.
          record.rows.push({
            label, value, kind, field,
            path: `${array}[${idKey}=${entry[idKey]}].${field}`,
          });
        }
      }
      if (Array.isArray(entry.entering) && entry.entering.length) {
        record.entering = entry.entering;
      }
      if (array === "element_join") joinDetail(record, entry);
    }
  }
  for (const finding of payload?.findings ?? []) {
    for (const uid of finding.elements ?? []) {
      const record = facts.get(uid);
      if (record) record.findings.push(finding);
    }
  }
  return facts;
}


// UX-278: what the payload knows about an element the ranked sources
// above never mention.
//
// `SOURCES` is the report's own ranking - what the decision named, the
// path, the horizon - so it covers the elements the report *discusses*.
// A reader who clicks Inspect on a choke point, a leaf, or row 900 of
// the element table is asking about an element the ranking never
// reached. Measured on the 1,202-element run before this landed: 24
// detail blocks for 1,202 elements, and two Inspect anchors that
// resolved to nothing at all.
//
// These are the element-keyed maps every run carries. Declared the same
// way `SOURCES` is - published path, field, label, quantity - so adding
// one is a line and no new code, and nothing here derives: a value that
// is not in the document does not appear.
const ELEMENT_MAPS = [
  ["elements.element_durations", null, "Duration", "duration_us"],
  ["elements.slack", null, "Slack", "duration_us"],
  ["elements.downstream_count", null, "Rebuilds", "count"],
  ["elements.unweighted_depth", null, "Depth", "count"],
  ["elements.blast_radius", "weighted_duration_us", "Blast radius", "duration_us"],
  ["elements.blast_radius", "risk_score", "Risk score", "count"],
  ["elements.blast_radius", "element_kind", "Kind", null],
  ["elements.blast_radius", "is_leaf", "Is a leaf", null],
  ["elements.criticality_probability", "probability", "On the path", "share"],
  ["elements.criticality_probability", "observed_critical", "Observed critical", null],
  ["leaf_analysis.leaves_detail", "deferral_risk", "Deferral risk", null],
  ["leaf_analysis.leaves_detail", "is_potentially_deferrable",
   "Could be deferred", null],
];

/**
 * One element's record, whether or not the report's ranking reached it.
 *
 * Returns a record with no rows when the run says nothing about this
 * element - which is a different answer from "there is no such
 * element", and the section built from it says so rather than being
 * absent.
 */
/**
 * `UX-369`: every element uid this payload knows, sorted.
 *
 * **The whole population, not `elementFacts`.** The first draft read
 * the facts map, and measuring the synthetic 1,202-element run gave a
 * picker with 26 entries beside a sentence reading "26 in this run":
 * `elementFacts` is built from the *published top-N arrays*, so it
 * knows the elements the report chose to talk about. That is the right
 * population for the element sections and the wrong one for a query
 * picker, whose whole purpose is reaching an element the report did
 * **not** rank - and it is `UX-366`'s defect committed again one
 * control over.
 *
 * `elements.element_durations` is the run's full element list, so it
 * leads; the facts map is unioned in so an element named only by a
 * finding is still reachable. Sorted, because this one is read as an
 * alphabet by someone hunting a name.
 */
export function elementUids(payload) {
  const uids = new Set(
    Object.keys(payload?.elements?.element_durations ?? {}));
  for (const uid of elementFacts(payload).keys()) uids.add(uid);
  return [...uids].filter(Boolean).sort();
}

/**
 * `UX-382`: **the one resolved element record.** Both shapes of the
 * entity, joined on the one key, for every element - which is what a
 * new view asks for instead of discovering where its columns live.
 *
 * The entity has two shapes and `analyze/v5` publishes both: six maps
 * under `elements`, keyed by uid, on every capture; and a wide
 * `element_join` row, present only where Plane 2 supplied a report.
 * `SOURCES` above reads the ranked arrays including the join;
 * `ELEMENT_MAPS` reads the column maps.
 *
 * This function used to return the `SOURCES` record when the report's
 * ranking had reached an element and build from the maps only when it
 * had not - so **no element ever had both**. Measured on the synthetic
 * 1,202-element run before this landed: a ranked element's record
 * carried one field and an unranked one carried ten, so the report's
 * own top twenty-six elements were the ones the page knew least about,
 * and no record on either run could answer "at depth 3, on the
 * critical path, and peaked above a gigabyte".
 *
 * The maps are merged **under** the ranked rows, and a field already
 * present is not written twice - the ranked arrays are the report's
 * own framing of a value and win where both name one. `blast_radius`
 * is the single name in both shapes and is dropped from the join's
 * `SOURCES` line rather than deduplicated here: it is an int where the
 * map's is a record, and the same number `elements.downstream_count`
 * already carries under the label "Rebuilds".
 */
export function elementFactsFor(payload, uid) {
  const known = elementFacts(payload).get(uid);
  const record = known ?? { element: uid, rows: [], findings: [],
                            entering: [], advice: [], evidence: [],
                            lists: [], onDemand: true };
  const held = new Set(record.rows.map((row) => row.field));
  for (const [path, field, label, kind] of ELEMENT_MAPS) {
    const map = path.split(".").reduce((node, key) => node?.[key], payload);
    const entry = map?.[uid];
    if (entry === null || entry === undefined) continue;
    const value = field === null ? entry : entry?.[field];
    if (value === null || value === undefined) continue;
    const name = field ?? path.split(".").pop();
    if (held.has(name)) continue;
    held.add(name);
    record.rows.push({
      label, value, kind, field: name,
      // The same walk-back grammar `UX-227` established, and a uid
      // contains dots - so the bracket form, which `resolvePath` reads
      // as a key on an object.
      path: `${path}[${uid}]${field === null ? "" : `.${field}`}`,
    });
  }
  if (known) return record;
  for (const finding of payload?.findings ?? []) {
    if ((finding.elements ?? []).includes(uid)) record.findings.push(finding);
  }
  return record;
}

/**
 * The detail section for `uid`, built on demand if the cap excluded it.
 *
 * Idempotent: an element that already has a section keeps the one it
 * has, so following the same anchor twice is not two blocks. Appended
 * at the end of the report, where every other element section is.
 */
export function ensureElementSection(payload, root, uid, options = {}) {
  if (!uid || !root) return null;
  const id = elementAnchor(uid);
  const existing = root.querySelector?.(`[data-section="${id}"]`)
    ?? root.querySelector?.(`#${id}`);
  if (existing) return existing;
  const { investigate = null, quantity: format = (v) => String(v) } = options;
  const record = elementFactsFor(payload, uid);
  const places = new Set();
  for (const node of root.querySelectorAll?.("[data-element]") ?? []) {
    if (node.getAttribute("data-element") !== uid) continue;
    let owner = node.parentNode;
    while (owner && !owner.getAttribute?.("data-section")) {
      owner = owner.parentNode;
    }
    const key = owner?.getAttribute?.("data-section");
    if (key && !key.startsWith("element-")) places.add(key);
  }
  const section = elementSection(record, places, investigate, format);
  section.setAttribute("data-on-demand", "true");
  if (!record.rows.length && !record.findings.length) {
    // UX-278 item 2: an anchor that resolves to a block saying the run
    // knows nothing about this element, rather than to nothing at all.
    const note = document.createElement("p");
    note.className = "muted";
    note.setAttribute("data-empty-element", uid);
    note.textContent =
      "This run names this element but records no measurements for it.";
    section.append(note);
  }
  root.append(section);
  return section;
}

// The report's own ranking decides the order: what the decision named
// first, then the path, then the horizon. `element_join` (UX-215) is
// last and never introduces an element - it is the Plane 2 half of
// elements Plane 1 already put in play, which is what lets the section
// answer "compute-bound, or badly built".
const SOURCES = [
  ["headline.top_actions", "element_uid", [
    ["saving_us", "Worth fixing", "duration_us"],
    ["downstream_count", "Rebuilds", "count"]]],
  ["critical_path_detail", "element_uid", [
    ["share_of_path", "Share of path", "share"],
    ["duration_us", "Duration", "duration_us"],
    ["realizable_saving_us", "Realizable", "duration_us"],
    ["element_kind", "Kind", null]]],
  ["optimization_horizon", "element_uid", [
    ["makespan_after_us", "Makespan after", "duration_us"]]],
  ["latent_heavies", "element_uid", [
    ["duration_us", "Duration", "duration_us"]]],
  ["element_join", "element", [
    ["cores_busy", "Cores busy", "ratio"],
    ["requested_jobs", "Jobs asked for", "count"],
    ["peak_rss_bytes", "Peak RSS", "bytes"],
    // `UX-382`: `blast_radius` was here and is gone. The join's field
    // is an int where `elements.blast_radius[uid]` is a record - it is
    // that record's own `downstream_count`, denormalised so the join
    // table can sort on it, and `elements.downstream_count` publishes
    // the same number under the label "Rebuilds" below. Two rows
    // labelled "Blast radius" in one record, one a count and one a
    // duration, is what merging the shapes made visible.
    // `UX-356`: two scalars the projection dropped. `cpu_coverage` is
    // the caveat on `cores_busy` beside it - a low coverage makes that
    // number a sample rather than a measurement - and `saving_share`
    // is `potential_saving_us` as a share of the run, which is the
    // form the decision ranks in.
    ["cpu_coverage", "Plane 2 coverage", "share"],
    ["saving_share", "Worth, as a share of the run", "share"],
    // `UX-383`: the quantity beside `cores_busy`'s rate, and `UX-379`'s
    // three pressure axes. `cores_busy` says an element was busy and
    // this says what that cost; the three below say *why* it was slow
    // when it was not busy - it read from the disk, it faulted, or the
    // run queue kept taking its turn away.
    //
    // Summed over the element's processes, unlike `peak_rss_bytes`
    // above, which is a maximum. Each field's own schema sentence says
    // which it is, because that is the door a reader opens before
    // adding two of them.
    ["cpu_us", "CPU burned", "duration_us"],
    ["read_bytes", "Read from disk", "bytes"],
    ["major_faults", "Major faults", "count"],
    ["involuntary_switches", "Preempted", "count"]]],
];

// `UX-356` (styleguide §1b): the join's **nested** evidence, declared
// the same way its scalars are.
//
// `app.js`'s `DRAWN_ELSEWHERE` said `element_join` was "merged into the
// one element table", and the merge kept four of twenty-eight fields.
// Thirteen reached no rendered node at all - among them the three
// objects below, which are the Plane 2 half of *why* an element is
// slow: which binary took the CPU, which one ran alone, and what work
// was repeated. A projection is allowed; a projection that does not
// say what it dropped is not (§1b).
//
// Adding a field is a line here, exactly as it is in `SOURCES`.
const JOIN_EVIDENCE = [
  ["dominant_binary", "Dominant binary", [
    ["binary", "Binary", null],
    ["count", "Processes", "count"],
    ["cpu_us", "CPU time", "duration_us"],
    ["wall_us", "Wall-clock", "duration_us"],
    ["cpu_share", "Share of this element's CPU", "share"]]],
  ["serial_binary", "Ran one process at a time", [
    ["binary", "Binary", null],
    ["cpu_us", "CPU time", "duration_us"],
    ["wall_us", "Wall-clock", "duration_us"]]],
  ["worst_redundancy", "Repeated work", [
    ["signature", "Command", null],
    // Only where it differs from the signature - which is exactly
    // where the normalisation did something (`cmTC_<id>` against
    // `cmTC_0df0f`), and the concrete one is then the command a reader
    // can go and look for. Where they are identical it is the same
    // string twice, which `UX-349` calls a fact about the block rather
    // than a row; `joinDetail` drops it there.
    ["example_cmd", "One occurrence", null],
    ["occurrence_count", "Times run", "count"],
    ["total_duration_us", "Cost, all occurrences", "duration_us"],
    ["max_element_duration_us", "Worst single element", "duration_us"],
    ["worst_element", "Worst element", null]]],
];

/**
 * One section per element the report discusses.
 *
 * `where` is the cross-reference and it is read off the *rendered
 * document* rather than from the payload: whatever else the page drew
 * with a `data-element`, the section links back to the part of the page
 * that drew it. So a section added later joins this list with no edit
 * here - the property `UX-193` bought for the sections themselves.
 */
export function renderElementSections(payload, root, options = {}) {
  const { investigate = null, quantity: format = (v) => String(v) } = options;
  const facts = elementFacts(payload);
  if (!facts.size) return [];

  const places = new Map();
  for (const node of root?.querySelectorAll?.("[data-element]") ?? []) {
    const uid = node.getAttribute("data-element");
    if (!uid || !facts.has(uid)) continue;
    let owner = node.parentNode;
    while (owner && !owner.getAttribute?.("data-section")) {
      owner = owner.parentNode;
    }
    const key = owner?.getAttribute?.("data-section");
    if (!key || key.startsWith("element-")) continue;
    if (!places.has(uid)) places.set(uid, new Set());
    places.get(uid).add(key);
  }

  const sections = [];
  const all = [...facts.values()];
  for (const record of all.slice(0, ELEMENTS_SHOWN)) {
    sections.push(elementSection(record, places.get(record.element),
                                 investigate, format));
  }
  if (all.length > ELEMENTS_SHOWN) {
    // UX-187: an elision names its count and never pretends to be the
    // whole list.
    const note = document.createElement("p");
    note.className = "muted";
    note.setAttribute("data-elided", String(all.length - ELEMENTS_SHOWN));
    note.textContent =
      `${all.length - ELEMENTS_SHOWN} more elements are named in the tables `
      + `above and do not have their own section.`;
    sections.push(note);
  }
  return sections;
}

function elementSection(record, places, investigate, format) {
  const uid = record.element;
  const section = document.createElement("section");
  // `UX-199`'s invariant is that a section's id *is* its key, and this
  // one is the sanitised spelling because a dot in an id is legal and
  // awkward in a selector - so the key is the sanitised spelling too,
  // rather than the two being nearly the same and drifting.
  section.setAttribute("data-section", elementAnchor(uid));
  section.setAttribute("data-element", uid);
  // The id UX-208's anchors have been pointing at since round 23.
  section.setAttribute("id", elementAnchor(uid));
  // ...and the uid is what the contents should say, not the sanitised
  // key mechanically de-hyphenated into "Element core bst".
  section.setAttribute("data-toc-label", uid);
  section.setAttribute("data-rail", "investigate");

  const heading = document.createElement("h2");
  heading.textContent = uid;
  section.append(heading);

  // UX-222 and UX-225: the two controls that act on *this* element.
  // Plain buttons carrying the element and the intent - `app.js` wires
  // one delegated listener at the root, so a control added to a view
  // later needs no second handler.
  const controls = document.createElement("p");
  controls.className = "element-controls";
  controls.setAttribute("data-role", "element-controls");
  const focusButton = document.createElement("button");
  focusButton.setAttribute("type", "button");
  focusButton.className = "focus-this";
  // `UX-534`: born with the state, so an unfocus leaves the document
  // byte-identical to never-focused (`UX-228`'s invariant).
  focusButton.setAttribute("aria-pressed", "false");
  focusButton.setAttribute("data-focus-element", uid);
  focusButton.textContent = "Focus";
  controls.append(focusButton);
  for (const mark of ELEMENT_MARKS) {
    const button = document.createElement("button");
    button.setAttribute("type", "button");
    button.className = "mark-this";
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("data-mark-element", uid);
    button.setAttribute("data-mark-value", mark);
    button.textContent = ELEMENT_MARK_LABELS[mark];
    controls.append(button);
  }
  section.append(controls);

  if (record.rows.length) {
    const list = document.createElement("dl");
    list.className = "pairs";
    for (const row of record.rows) {
      const term = document.createElement("dt");
      term.textContent = row.label;
      const detail = document.createElement("dd");
      detail.setAttribute("data-field", row.field);
      detail.setAttribute("data-raw", String(row.value));
      detail.className = typeof row.value === "number" ? "num" : "";
      detail.textContent = typeof row.value === "number"
        ? format(row.value, row.kind) : String(row.value);
      list.append(term, detail);
    }
    section.append(list);
  }

  // `UX-356` (§1b): the sentence the analyzer wrote for this reader,
  // above the evidence it rests on and above the findings that name
  // the element. It is the finished advice, so it reads at the grade
  // `headline.top_actions` does rather than behind a fold.
  for (const advice of record.advice ?? []) {
    const line = document.createElement("p");
    line.className = "advice";
    line.setAttribute("data-severity", advice.severity);
    line.setAttribute("data-advice", advice.id);
    line.setAttribute("data-path", advice.path);
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = advice.severity;
    line.append(badge, document.createTextNode(` ${advice.text}`));
    section.append(line);
  }

  // The Plane 2 evidence behind those sentences. Folded, because it is
  // the *why* under an answer already given - and the fold announces
  // its depth (§3a.1), like every other value fold on the page.
  const evidenceRows = (record.evidence ?? [])
    .reduce((total, block) => total + block.rows.length, 0);
  if (evidenceRows) {
    const fold = document.createElement("details");
    fold.className = "join-evidence";
    fold.setAttribute("data-fold", "join-evidence");
    fold.setAttribute("data-levels", "1");
    fold.setAttribute("data-rows", String(evidenceRows));
    const summary = document.createElement("summary");
    summary.textContent =
      `What Plane 2 saw · 1 level, ${evidenceRows} `
      + `row${evidenceRows === 1 ? "" : "s"}`;
    fold.append(summary);
    for (const block of record.evidence) {
      const name = document.createElement("p");
      name.className = "muted";
      name.setAttribute("data-evidence", block.key);
      name.textContent = block.label;
      const list = document.createElement("dl");
      list.className = "pairs";
      for (const row of block.rows) {
        const term = document.createElement("dt");
        term.textContent = row.label;
        const detail = document.createElement("dd");
        detail.setAttribute("data-field", row.field);
        detail.setAttribute("data-raw", String(row.value));
        detail.setAttribute("data-path", row.path);
        detail.className = typeof row.value === "number" ? "num" : "";
        detail.textContent = typeof row.value === "number"
          ? format(row.value, row.kind) : String(row.value);
        list.append(term, detail);
      }
      fold.append(name, list);
    }
    section.append(fold);
  }

  // `UX-302`'s mapping: a short scalar array is an inline list, not a
  // table and not a `<pre>`.
  for (const named of record.lists ?? []) {
    const line = document.createElement("p");
    line.className = "muted";
    line.setAttribute("data-list", named.key);
    line.append(document.createTextNode(`${named.label}: `));
    named.items.forEach((item, index) => {
      const code = document.createElement("code");
      code.textContent = item;
      line.append(code);
      if (index < named.items.length - 1) {
        line.append(document.createTextNode(", "));
      }
    });
    section.append(line);
  }

  if (record.entering.length) {
    const enters = document.createElement("p");
    enters.className = "muted";
    enters.setAttribute("data-entering", record.entering.join(","));
    enters.textContent =
      `Fixing this puts ${record.entering.join(", ")} on the critical path.`;
    section.append(enters);
  }

  for (const finding of record.findings) {
    const line = document.createElement("p");
    line.className = `finding-ref sev-${String(finding.severity ?? "info")
      .toLowerCase()}`;
    line.setAttribute("data-finding", finding.id ?? "");
    line.textContent = finding.title ?? finding.id ?? "";
    section.append(line);
  }

  if (places && places.size) {
    const where = document.createElement("p");
    where.className = "where muted";
    where.append(document.createTextNode("Also in: "));
    for (const key of [...places].sort()) {
      const link = document.createElement("a");
      link.setAttribute("href", `#${key}`);
      link.setAttribute("data-where", key);
      link.textContent = key.replace(/[-_]/g, " ");
      where.append(link, document.createTextNode(" "));
    }
    section.append(where);
  }

  if (investigate) {
    const button = investigate(uid);
    if (button) section.append(button);
  }
  return section;
}

// UX-221: the strip that answers "because of what?".
//
// `renderBand` says the candidate is outside the noise band. It cannot
// say which elements put it there, because until UX-221 the payload had
// no per-element deltas to say it with - `compare/v1` carried whole-run
// floors and per-*category* attribution, and the only elements in it at
// all were the ones a change added or removed.
//
// Read straight off `element_deltas.rows`, in the order the payload
// ranked them. A viewer sorting these itself would be a second
// comparison, disagreeing with `bga compare` the moment either changed -
// UX-214's failure, and the reason this was a payload item first.
export const CULPRITS_SHOWN = 4;

// UX-225's vocabulary, spelled here so `views.js` keeps importing
// nothing. A guard asserts it is the same closed set `focus.js`
// declares, so the two cannot drift apart in silence.
export const ELEMENT_MARKS = ["working", "done", "aside"];
export const ELEMENT_MARK_LABELS = {
  working: "Working", done: "Done", aside: "Set aside",
};

export function renderCulprits(compare) {
  const deltas = compare?.element_deltas;
  const rows = deltas?.rows ?? [];
  if (!rows.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "culprits");
  section.setAttribute("data-toc-label", "Which elements changed");
  const heading = document.createElement("h2");
  heading.textContent = "Which elements changed";
  section.append(heading);

  // Improvements and regressions each on their own, rather than one
  // list ordered by magnitude: a reader looking for what cost them time
  // should not have to skip past what saved it.
  const measurable = rows.filter((row) => row.delta_us !== null
                                       && row.delta_us !== undefined);
  const worse = measurable.filter((row) => row.delta_us > 0)
                          .slice(0, CULPRITS_SHOWN);
  const better = measurable.filter((row) => row.delta_us < 0)
                           .slice(0, CULPRITS_SHOWN);
  const absent = rows.filter((row) => row.presence !== "both");

  for (const [label, group] of [["Cost time", worse], ["Saved time", better]]) {
    if (!group.length) continue;
    const list = document.createElement("ul");
    list.className = "culprit-list";
    list.setAttribute("data-group", label === "Cost time" ? "worse" : "better");
    for (const row of group) list.append(culpritRow(row));
    const title = document.createElement("h3");
    title.textContent = label;
    section.append(title, list);
  }

  if (absent.length) {
    const list = document.createElement("ul");
    list.className = "culprit-list";
    list.setAttribute("data-group", "absent");
    for (const row of absent.slice(0, CULPRITS_SHOWN)) list.append(culpritRow(row));
    const title = document.createElement("h3");
    title.textContent = "Only in one run";
    section.append(title, list);
  }

  // The honesty line. A per-element delta is not judged against a noise
  // band - there isn't one - and a strip that coloured rows without
  // saying so would be claiming a verdict it cannot support.
  const caveat = document.createElement("p");
  caveat.className = "muted";
  caveat.setAttribute("data-role", "not-banded");
  caveat.textContent = deltas.banded
    ? "Each row is judged against its own noise band."
    : "These are raw changes, not judged against a noise band - only the "
      + "run as a whole is.";
  section.append(caveat);
  return section;
}

function culpritRow(row) {
  const item = document.createElement("li");
  item.setAttribute("data-element", row.element_uid);
  item.setAttribute("data-verdict-kind", row.verdict_kind);
  item.setAttribute("data-presence", row.presence);
  if (row.delta_us !== null && row.delta_us !== undefined) {
    item.setAttribute("data-delta-us", String(row.delta_us));
  }
  const name = document.createElement("a");
  name.className = "element";
  name.setAttribute("href", `#${elementAnchor(row.element_uid ?? "")}`);
  name.textContent = row.element_uid;
  const change = document.createElement("span");
  change.className = "culprit-change";
  // The values are the payload's. Nothing here subtracts anything: a
  // page computing its own delta is a second comparison.
  change.textContent = (row.delta_us === null || row.delta_us === undefined)
    ? `${row.presence} - no delta to compare`
    : `${row.delta_us > 0 ? "+" : ""}${seconds(row.delta_us)}`
      + ` (${seconds(row.baseline_us)} → ${seconds(row.candidate_us)})`;
  item.append(name, document.createTextNode(" "), change);
  return item;
}

// UX-219: the horizon, drawn.
//
// `optimization_horizon` has carried the whole answer, per step,
// since long before this: the saving, the makespan that remains, and -
// the part a table hides - which elements *enter* the critical path once
// that step is taken. That is the honest reason the savings stop adding
// up, and it is what makes this a plan rather than a sum.
//
// Every width is one published `makespan_after_us` over one published
// total. Nothing here adds savings together or projects anything: if the
// payload publishes three steps, the plan has three rows.
/**
 * UX-230: choose the fixes, and see the projected build.
 *
 * The interaction R8 brings to a prioritisation meeting, under the
 * review's own warning: **this must not pretend to simulate.** A page
 * that summed per-element savings would be wrong the moment two fixes
 * share a chain, and `UX-219` measured exactly that on the golden
 * fixture. So:
 *
 * - A **prefix of the published sequence** is already answered by the
 *   payload: `optimization_horizon[i].makespan_after_us` is the
 *   makespan after the first `i+1` fixes, published. That subset is
 *   read, not computed.
 * - **Any other subset** goes to the server, which calls the same
 *   `bga.whatif.project` the CLI does - the transport `bga blast`
 *   established. The page adds nothing.
 * - **Offline** (an export, `file://`) there is no server, so the
 *   command that answers it is shown instead of a control that cannot.
 *   `UX-199`'s honesty shape for the blast box, applied again.
 *
 * There is no third path. A subset the page cannot read and cannot ask
 * about renders the question, never a guess.
 */
export function renderWhatIf(payload, ask = null, options = {}) {
  const steps = payload?.optimization_horizon ?? [];
  if (!steps.length) return null;
  const run = options.run ?? "RUN";

  const section = document.createElement("section");
  section.className = "whatif";
  section.setAttribute("data-section", "whatif");
  section.setAttribute("data-toc-label", "Choose the fixes");
  const heading = document.createElement("h2");
  heading.textContent = "Choose the fixes";
  section.append(heading);

  const list = document.createElement("ul");
  list.className = "whatif-choices";
  const chosen = new Set();
  const boxes = [];
  for (const step of steps) {
    const row = document.createElement("li");
    row.className = "whatif-choice";
    row.setAttribute("data-element", step.element_uid);
    const box = document.createElement("input");
    box.setAttribute("type", "checkbox");
    box.setAttribute("data-whatif-element", step.element_uid);
    const label = document.createElement("label");
    label.textContent = step.element_uid;
    // UX-334: the label points at its box. It sat *beside* it with no
    // `for`, which is a label that names nothing - the element name is
    // not clickable and the checkbox has no accessible name at all.
    labelFor(label, box, `whatif-${step.element_uid}`);
    row.append(box, label);
    list.append(row);
    boxes.push([box, step.element_uid]);
  }
  section.append(list);

  const answer = document.createElement("p");
  answer.className = "whatif-answer";
  answer.setAttribute("data-role", "whatif-answer");
  section.append(answer);

  const show = () => {
    const selected = steps.map((step) => step.element_uid)
                          .filter((uid) => chosen.has(uid));
    if (!selected.length) {
      answer.setAttribute("data-source", "none");
      answer.removeAttribute("data-makespan-us");
      answer.textContent = "Nothing selected.";
      return;
    }
    const published = publishedPrefix(payload, selected);
    if (published !== null) {
      answer.setAttribute("data-source", "published");
      answer.setAttribute("data-field",
        `optimization_horizon[${selected.length - 1}].makespan_after_us`);
      answer.setAttribute("data-makespan-us", String(published));
      answer.textContent =
        `The build drops to ${seconds(published)} — published, the first `
        + `${selected.length} step(s) of the plan.`;
      return;
    }
    if (!ask) {
      // No server: the command, not a control that cannot answer.
      answer.setAttribute("data-source", "command");
      answer.removeAttribute("data-makespan-us");
      answer.textContent = whatIfCommand(run, selected);
      return;
    }
    answer.setAttribute("data-source", "asking");
    answer.textContent = "Asking bga…";
    Promise.resolve(ask(selected)).then(
      (document_) => {
        const projected = document_?.projected;
        if (!projected) {
          answer.setAttribute("data-source", "refused");
          answer.removeAttribute("data-makespan-us");
          answer.textContent = (document_?.refusals ?? [])
            .map((refusal) => refusal.sentence).join(" ")
            || "bga declined to project this selection.";
          return;
        }
        answer.setAttribute("data-source", "server");
        answer.setAttribute("data-makespan-us",
                            String(projected.makespan_after_us));
        answer.textContent =
          `The build drops to ${seconds(projected.makespan_after_us)} — `
          + `computed by bga for this selection.`;
      },
      (error) => {
        answer.setAttribute("data-source", "error");
        answer.textContent = String(error?.message ?? error);
      });
  };

  for (const [box, uid] of boxes) {
    box.addEventListener?.("change", () => {
      if (chosen.has(uid)) chosen.delete(uid);
      else chosen.add(uid);
      show();
    });
  }
  show();
  return section;
}

/**
 * The published makespan for this selection, or null when the payload
 * does not already answer it.
 *
 * Only a *prefix* of the sequence is published: the horizon is greedy,
 * so step `i`'s makespan assumes steps `0..i-1` were taken. A selection
 * that skips one is a different question and the payload does not hold
 * its answer.
 */
export function publishedPrefix(payload, selected) {
  const steps = payload?.optimization_horizon ?? [];
  if (!selected.length || selected.length > steps.length) return null;
  for (let i = 0; i < selected.length; i += 1) {
    if (steps[i].element_uid !== selected[i]) return null;
  }
  const makespan = steps[selected.length - 1].makespan_after_us;
  return typeof makespan === "number" ? makespan : null;
}

/** The command that answers a selection the page cannot. */
export function whatIfCommand(run, selected) {
  return `bga whatif ${run} `
    + selected.map((uid) => `--element ${uid}`).join(" ");
}

export function renderHorizon(payload) {
  const steps = payload?.optimization_horizon ?? [];
  const total = payload?.total_duration_us;
  if (!steps.length || !total) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "horizon");
  section.setAttribute("data-toc-label", "What if I fix these");
  section.setAttribute("data-total-us", String(total));
  const heading = document.createElement("h2");
  heading.textContent = "What if I fix these";
  section.append(heading);

  const list = document.createElement("ol");
  list.className = "horizon";

  // The run as it stands, so the bars below have something to shorten.
  list.append(horizonRow({
    label: "now", makespanUs: total, total,
    element: null, saving: null, entering: [],
  }));

  let taken = [];
  for (const step of steps) {
    taken = taken.concat([step.element_uid]);
    list.append(horizonRow({
      label: taken.length === 1
        ? `fix ${step.element_uid}`
        : `+ fix ${step.element_uid}`,
      makespanUs: step.makespan_after_us,
      total,
      element: step.element_uid,
      saving: step.saving_us,
      entering: step.entering ?? [],
    }));
  }
  section.append(list);

  // The total, from the last step's own published cumulative saving.
  // Not a sum computed here - the payload already decided what the
  // sequence is worth, and re-adding it would be a second answer.
  const last = steps[steps.length - 1];
  const cumulative = last?.cumulative_saving_us;
  if (cumulative !== null && cumulative !== undefined) {
    const summary = document.createElement("p");
    summary.className = "horizon-total";
    summary.setAttribute("data-role", "horizon-total");
    summary.setAttribute("data-cumulative-saving-us", String(cumulative));
    summary.setAttribute("data-total-us", String(total));
    const share = (cumulative / total) * 100;
    summary.textContent =
      `${steps.length} ${steps.length === 1 ? "fix" : "fixes"}`
      + ` → ${share.toFixed(0)}% faster (${seconds(cumulative)} off ${seconds(total)})`;
    section.append(summary);
  }
  return section;
}

function horizonRow({ label, makespanUs, total, element, saving, entering }) {
  const row = document.createElement("li");
  row.className = "horizon-step";
  // The published value, on the element, so a guard can check the
  // drawing against the payload without reading computed style.
  row.setAttribute("data-makespan-after-us", String(makespanUs));
  if (element) row.setAttribute("data-element", element);
  if (saving !== null && saving !== undefined) {
    row.setAttribute("data-saving-us", String(saving));
  }

  const name = document.createElement("span");
  name.className = "horizon-label";
  if (element) {
    const link = document.createElement("a");
    link.className = "element";
    link.setAttribute("href", `#${elementAnchor(element)}`);
    link.textContent = element;
    name.append(document.createTextNode(label.startsWith("+") ? "+ fix " : "fix "),
                link);
  } else {
    name.textContent = label;
  }

  const bar = document.createElement("span");
  bar.className = "horizon-bar";
  bar.setAttribute("data-role", "bar");
  // One division, UX-202's rule: a proportion of a published total, not
  // a quantity derived in the page.
  // A custom property has no CSSOM alias, so `setProperty` is the
  // only route that is not a style attribute (`UX-263`).
  bar.style.setProperty("--w", `${(makespanUs / total) * 100}%`);

  const value = document.createElement("span");
  value.className = "horizon-value";
  value.textContent = seconds(makespanUs);

  row.append(name, bar, value);

  // What joins the critical path once this step is taken. The reason
  // the savings stop adding up, and the reason this is a plan.
  if (entering.length) {
    const note = document.createElement("span");
    note.className = "horizon-entering muted";
    note.setAttribute("data-role", "entering");
    note.append(document.createTextNode("→ "));
    entering.forEach((uid, i) => {
      if (i) note.append(document.createTextNode(", "));
      const link = document.createElement("a");
      link.className = "element";
      link.setAttribute("href", `#${elementAnchor(uid)}`);
      link.textContent = uid;
      note.append(link);
    });
    note.append(document.createTextNode(
      entering.length === 1 ? " enters the path" : " enter the path"));
    row.append(note);
  }
  return row;
}

// UX-226: what happened to this element since last time.
//
// The loop ends on a question the tool could not answer: *I spent an
// afternoon on core.bst - did it work?* Everything needed was on disk;
// nothing was per element. `store/v1` carried whole-run durations, so
// the trend was a whole-run trend because that is all the store
// published.
//
// It publishes a bounded slice now, and this draws it. Points come
// straight from `snapshots[].elements` - nothing here recomputes a
// duration or infers one from a neighbour.
export const HISTORY_POINTS_MAX = 12;

export function elementHistory(store, uid) {
  const snapshots = store?.snapshots ?? [];
  const series = [];
  let sawASliceAtAll = false;
  let unreadable = 0;
  for (const snapshot of snapshots) {
    // UX-335: the row itself, before its fields. A `null` here read
    // `snapshot.elements` and threw; the throw reached `boot()`'s
    // page-wide catch, and every section in the report was replaced by
    // one sentence about a `TypeError`.
    if (!snapshot || typeof snapshot !== "object") { unreadable += 1; continue; }
    // `null` means "captured before UX-226"; `[]` means "analyzed, and
    // this element was not worth watching in that run". The two are
    // different facts and the drawing must not merge them.
    if (!Array.isArray(snapshot.elements)) continue;
    sawASliceAtAll = true;
    const row = snapshot.elements.find((e) => e.element_uid === uid);
    if (!row) continue;
    series.push({
      stamp: snapshot.stamp,
      duration_us: row.duration_us,
      on_critical_path: row.on_critical_path === true,
      verdict_kind: snapshot.verdict_kind ?? null,
    });
  }
  return { series: series.slice(-HISTORY_POINTS_MAX), sawASliceAtAll,
           unreadable };
}

/**
 * The sparkline and its one sentence, or the absence stated.
 *
 * A single point is not a trend and is drawn as a point, not a line: a
 * line through one value is a claim about change that the data does not
 * make.
 */
export function renderElementHistory(store, uid, schema = null) {
  const { series, sawASliceAtAll, unreadable } = elementHistory(store, uid);
  const block = document.createElement("p");
  block.className = "element-history";
  block.setAttribute("data-role", "element-history");
  block.setAttribute("data-element", uid);
  block.setAttribute("data-points", String(series.length));

  if (unreadable) block.setAttribute("data-unreadable-rows", String(unreadable));
  if (!series.length) {
    block.setAttribute("data-history", "none");
    block.className += " muted";
    // UX-335: three absences, not two. A store whose rows will not read
    // is a different fact from a store that recorded nothing for this
    // element, and telling a reader "it has not been on the critical
    // path" when the truth is "this store is damaged" sends them to
    // look at the wrong thing.
    block.textContent = unreadable && !sawASliceAtAll
      ? `No history for this element: ${unreadable} row`
        + `${unreadable === 1 ? "" : "s"} in this store could not be read, `
        + `and no other snapshot carries per-element history.`
      : sawASliceAtAll
      ? "No history for this element: it has not been on the critical path "
        + "or in the top actions of an earlier run."
      : "No history for this element: the snapshots in this store were "
        + "captured before per-element history was recorded.";
    return block;
  }

  block.setAttribute("data-history", "present");
  const values = series.map((point) => point.duration_us)
                       .filter((v) => typeof v === "number");
  if (values.length) {
    const high = Math.max(...values, 1);
    // UX-316: **annotation** grade - this sparkline sits beside an
    // element's row and annotates it; it is not the section's answer.
    // Its box used to be written out here as `0 0 100 20`, which is the
    // per-drawing constant §2a's scale replaces: the same numbers, from
    // the one place that holds them, so a guard can hold every drawing
    // to the scale instead of to a grep.
    const size = SCALE[GRADE_ANNOTATION];
    const inset = size.spark / 10;
    const line = svg("svg", {
      viewBox: `0 0 ${size.width} ${size.spark}`, class: "sparkline",
      preserveAspectRatio: "none",
      role: "img", "data-role": "sparkline", "data-grade": GRADE_ANNOTATION,
      "data-values": values.join(","),
    });
    series.forEach((point, i) => {
      if (typeof point.duration_us !== "number") return;
      const x = series.length === 1
        ? size.width / 2 : (i / (series.length - 1)) * size.width;
      const y = (size.spark - inset)
                - (point.duration_us / high) * (size.spark - inset * 2);
      line.append(svg("circle", {
        cx: x.toFixed(2), cy: y.toFixed(2), r: 1.6,
        class: "spark-point",
        // UX-212's closed shape vocabulary, so a snapshot's verdict
        // reads the same here as it does in the trend.
        // UX-212's rule, and the first draft of this broke it: the
        // shape comes from the *schema*, so the sparkline draws what
        // the contract assigns each verdict rather than a second map
        // this page keeps. `verdictMarker` falls back to a circle for
        // a snapshot with no verdict at all.
        "data-marker": verdictMarker(point.verdict_kind,
                                     verdictMarkers(schema)),
        "data-stamp": point.stamp,
        "data-value": String(point.duration_us),
        "data-on-path": String(point.on_critical_path),
      }));
    });
    block.append(line);
  }

  // One sentence, from the first and last published values. No
  // percentage: two points from two different builds are not a rate.
  const sentence = document.createElement("span");
  sentence.className = "history-sentence";
  sentence.setAttribute("data-role", "history-sentence");
  const first = series[0];
  const last = series[series.length - 1];
  if (series.length === 1) {
    sentence.textContent = `${seconds(last.duration_us)} in one recorded run.`;
  } else {
    sentence.textContent =
      `${seconds(first.duration_us)} → ${seconds(last.duration_us)}`
      + ` over ${series.length} runs.`;
  }
  // The run it left the chain, when it did: that is usually the answer
  // somebody optimising was actually looking for.
  const left = series.find((point, i) =>
    i > 0 && series[i - 1].on_critical_path && !point.on_critical_path);
  if (left) {
    sentence.textContent += ` Off the critical path since ${left.stamp}.`;
  }
  block.append(sentence);
  return block;
}
