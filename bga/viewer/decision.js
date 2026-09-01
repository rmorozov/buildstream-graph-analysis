/**
 * UX-337: the decision panel - `UX-207`'s first screen.
 *
 * The last chapter of the old `views.js`, and the one that sits on top
 * of the element object: the derivation found it reaching for exactly
 * four of that chapter's symbols and for nothing else, so the three
 * files are a chain rather than a web -
 * `views.js -> element.js -> decision.js`, with `primitives.js` under
 * all three.
 *
 * A move, asserted as one: see `element.js`'s header.
 */
import { commandLine, identify, labelFor } from "./controls.js";
import {
  SVG, svg, seconds, mib, bar, OVERVIEW_SHOWN, elementAnchor,
} from "./primitives.js";
import {
  SCALE, GRADE_ANNOTATION, GRADE_EXHIBIT, exhibitAxis, exhibitTwin,
} from "./drawings.js";
import {
  resolvePath, elementFacts, elementHistory, renderElementHistory,
} from "./element.js";

// ------------------------------------------------- UX-207: the decision

/**
 * The first screen, and the only one that is not evidence.
 *
 * **Everything here is read.** The diagnosis, the ratio it came from,
 * the opportunity split and the ranked actions are all fields of the
 * published `headline` block - `UX-207`'s rule, and Direction 7's: a
 * viewer that derives the diagnosis is a second analyzer, free to
 * disagree with the report and the CI gate about the same build.
 *
 * No `headline`, no panel. An older payload renders the page it always
 * did rather than a box explaining what is missing.
 */
/**
 * UX-229: the chain behind one claim, rendered from the published
 * record and nothing else.
 *
 * Every string here is a field of `provenance`: the sentence is
 * `rule.sentence`, the threshold is `rule.threshold`, each row is an
 * `evidence[]` entry's own `path` and `value`. The page does not
 * compare anything, does not format a share, does not decide which
 * rule applies - it draws the object. That is the property the
 * no-derivation guard asserts, and it is why the record carries a
 * sentence at all: wording the comparison here would make the terminal
 * and the page two explanations of one claim.
 *
 * Folded by default. A reader who believes the finding should not have
 * to scroll past the reason they did not ask for - `UX-209`'s rule for
 * evidence, applied one level up.
 */
export function renderProvenance(provenance, options = {}) {
  if (!provenance || !provenance.rule) return null;
  const details = document.createElement("details");
  details.className = "provenance";
  details.setAttribute("data-provenance", provenance.claim ?? "");
  details.setAttribute("data-kind", provenance.kind ?? "");
  if (provenance.trace_query) {
    details.setAttribute("data-query", provenance.trace_query);
  }
  // `UX-448`: the other grains, where the claim reads at more than
  // one. Published only then, so the attribute is absent on the
  // nineteen claims with a single grain rather than repeating
  // `data-query` - which is the shape of the field it draws.
  if (Array.isArray(provenance.trace_queries)
      && provenance.trace_queries.length) {
    details.setAttribute("data-queries", provenance.trace_queries.join(" "));
  }
  // `UX-357` (§3a.1): the fold says how much is behind it. One level -
  // the sentence, the rule, the evidence rows and the unpublished
  // note are all siblings inside it - and the rows are the evidence
  // references, which is the part a reader is deciding whether to
  // open.
  const evidence = Array.isArray(provenance.evidence)
    ? provenance.evidence : [];
  details.setAttribute("data-levels", "1");
  details.setAttribute("data-rows", String(evidence.length));
  const summary = document.createElement("summary");
  // Named by the claim where the caller has twelve of these in one
  // section and "Why" twelve times names nothing.
  const named = options.label ? `${options.label} · ` : "";
  summary.textContent =
    `${named}1 level, ${evidence.length} `
    + `row${evidence.length === 1 ? "" : "s"}`;
  details.append(summary);

  const why = document.createElement("p");
  why.className = "why";
  why.setAttribute("data-field", "provenance.rule.sentence");
  why.textContent = provenance.rule.sentence ?? "";
  details.append(why);

  // `UX-357`: a name **or** a module. Six of `macro_micro`'s twelve
  // records publish a module and a sentence and no named threshold -
  // the claim is computed rather than gated - and the old condition
  // gated the whole paragraph on the name, so those six said where
  // they came from nowhere. "No named rule" is a fact about the claim,
  // not a reason to withhold the file that made it.
  if (provenance.rule.name || provenance.rule.module) {
    const rule = document.createElement("p");
    rule.className = "rule muted";
    rule.setAttribute("data-rule", provenance.rule.name ?? "");
    rule.setAttribute("data-threshold", String(provenance.rule.threshold));
    rule.setAttribute("data-comparison", provenance.rule.comparison ?? "");
    // And the path the rule *observed*, which is the one address that
    // says which published number it compared. It was published from
    // the first and rendered nowhere.
    if (provenance.rule.observed_path) {
      rule.setAttribute("data-observed", provenance.rule.observed_path);
    }
    // `<span>` rather than `createTextNode`: the guards drive these
    // renderers against a hand-built `document` that offers
    // `createElement` and not much else, and a renderer that needs a
    // DOM method thirty test stubs do not have is a renderer nothing
    // can test. The shim exports `createTextNode`; the stubs predate
    // it (`UX-264`'s complaint, still half-true).
    const said = (text) => {
      const span = document.createElement("span");
      span.textContent = text;
      return span;
    };
    if (provenance.rule.name) {
      rule.append(said(`${provenance.rule.name} `));
      const comparison = document.createElement("code");
      comparison.textContent =
        `${provenance.rule.observed_path ?? ""} `
        + `${provenance.rule.comparison ?? "="} ${provenance.rule.threshold}`;
      rule.append(comparison, said(" in "));
    } else if (provenance.rule.observed_path) {
      // A record can publish an observed path and no threshold -
      // `confidence.run_mode present` is a rule with no number in it -
      // and the address is the interesting half either way.
      rule.append(said("No named threshold; "));
      const observed = document.createElement("code");
      observed.textContent =
        `${provenance.rule.observed_path} `
        + `${provenance.rule.comparison ?? ""}`.trim();
      rule.append(observed, said(" read in "));
    } else {
      rule.append(said("No named threshold; computed in "));
    }
    const module = document.createElement("code");
    module.textContent = provenance.rule.module ?? "";
    rule.append(module);
    details.append(rule);
  }

  const refs = evidence;
  if (refs.length) {
    const list = document.createElement("dl");
    list.className = "pairs evidence-refs";
    for (const ref of refs) {
      const term = document.createElement("dt");
      term.setAttribute("data-path", ref.path ?? "");
      const path = document.createElement("code");
      path.textContent = ref.path ?? "";
      term.append(path);
      const value = document.createElement("dd");
      value.setAttribute("data-raw", ref.value === null || ref.value === undefined
        ? "" : String(ref.value));
      value.setAttribute("data-resolved", String(ref.resolved !== false));
      // An unresolved reference says so rather than rendering as a
      // blank cell: "the path is broken" and "the field is null" are
      // different, and the published record already distinguishes them.
      // `UX-483`: a row whose path resolved to a *container* carries
      // its shape and not a copy of it - the record cites this
      // document, and inlining a population would publish it twice.
      // Rendered as what it is rather than as `undefined`, which is
      // what `String(ref.value)` produces for an absent key.
      value.textContent = ref.resolved === false
        ? "unresolved"
        : (ref.elided ? `${ref.elided} - follow the path`
                      : String(ref.value));
      list.append(term, value);
    }
    details.append(list);
  }

  // `UX-357`: the document every path above walks. A record that
  // travels - a `compare/v1` chain read beside an `analyze/v4` one -
  // resolves against a different document, and the schema calls this
  // load-bearing the moment it does.
  if (provenance.document) {
    const against = document.createElement("p");
    against.className = "muted";
    against.setAttribute("data-document", provenance.document);
    const lead = document.createElement("span");
    lead.textContent = "Paths resolve against ";
    const named = document.createElement("code");
    named.textContent = provenance.document;
    against.append(lead, named);
    details.append(against);
  }

  const unpublished = Array.isArray(provenance.unpublished_inputs)
    ? provenance.unpublished_inputs : [];
  if (unpublished.length) {
    const note = document.createElement("p");
    note.className = "muted unpublished";
    note.setAttribute("data-unpublished", String(unpublished.length));
    note.textContent =
      `Also drawn from, and not published in this document: ${unpublished.join(", ")}`;
    details.append(note);
  }
  return details;
}

/**
 * `UX-357`: one provenance block per published claim, under the index.
 *
 * `provenance` renders as a table, because that is what its schema
 * declares - `bga:columns` names `claim` and `kind`, and a table takes
 * the two scalar columns and drops everything nested. Measured on
 * `macro_micro`: the section drew the claim and the numbers, and
 * withheld the four things that make it provenance -
 *
 * ```text
 *   rule.module           0 of 12
 *   rule.name             0 of 5
 *   rule.observed_path    0 of 5
 *   rule.sentence         1 of 12
 *   unpublished_inputs    0 of 3
 *   evidence[].path       7 of 29
 * ```
 *
 * - which is the one section on the page whose whole job it fails by
 * rendering. A provenance section that shows the verdict and hides the
 * rule is an assertion.
 *
 * The shape is the page's own, not a new one: an **index table plus a
 * detail block per row**, which is exactly what `elements` and the
 * element sections are. `UX-338` forbids drawing one population twice
 * as two full renderings; a two-column index over twelve claims and
 * twelve folded records is the relationship that item's own fix left
 * in place.
 */
export function renderProvenanceRecords(payload, root) {
  const section = root?.querySelector?.('[data-section="provenance"]');
  if (!section) return 0;
  const records = Array.isArray(payload?.provenance) ? payload.provenance : [];
  let drawn = 0;
  for (const record of records) {
    const block = renderProvenance(record, { label: record.claim ?? "" });
    if (!block) continue;
    section.append(block);
    drawn += 1;
  }
  return drawn;
}

/**
 * UX-227: why *this* element is ranked first, as one compact answer.
 *
 * The page could already say `openssl.bst` is worth 522 s, sits at
 * 18.6% of the path, has 14 consumers and moved since the last
 * capture - in five different sections. What it could not do was say
 * them together, as the reason. This gathers them under the question.
 *
 * **Gathering, not deriving.** Every row is a value read out of a
 * published field, and carries the `path` it was read from in
 * `data-field` - a path in the grammar `resolvePath` and
 * `bga/provenance.py` both walk, so a reader (or a guard) follows it
 * back into the payload rather than trusting the number. The reason
 * the claim is ranked at all comes from `UX-229`'s provenance record,
 * looked up by the `finding_id` the action carries: the composition
 * this item was filed with is the interim, and the contract is what it
 * reads now. `UX-344` published those records once, at the top level,
 * so this is a lookup by claim rather than a walk down a `see` path
 * into a copy of the record inside the finding.
 */
export function renderWhyRanked(payload, action, options = {}) {
  const uid = action?.element_uid;
  if (!uid) return null;
  const facts = elementFacts(payload).get(uid);
  const record = (payload?.provenance ?? []).find(
    (entry) => entry?.claim === action?.finding_id) ?? null;
  const history = options.store
    ? renderElementHistory(options.store, uid, options.schema ?? null) : null;
  // `elementFacts` touches a record for every uid a source *names*, so
  // a top action alone produces an empty one. The fold needs something
  // to say: no facts, no rule and no history is no block, which is
  // `UX-194`'s dead-control rule applied to an explanation.
  const rows = facts?.rows ?? [];
  const findings = facts?.findings ?? [];
  const ownRule = record && options.ranking !== action?.finding_id;
  if (!rows.length && !findings.length && !ownRule && !history) return null;

  const details = document.createElement("details");
  details.className = "why-ranked";
  details.setAttribute("data-why", uid);
  const summary = document.createElement("summary");
  summary.textContent = options.rank
    ? `Why #${options.rank}` : "Why this one";
  details.append(summary);

  // The rule that ranked it, from the finding's own record - unless
  // every action shares that record, in which case `renderDecision`
  // has already stated it once above the list (`UX-371`).
  if (ownRule) {
    const chain = renderProvenance(record);
    if (chain) {
      chain.setAttribute("open", "");
      details.append(chain);
    }
  }

  // What this run measured about it, each value beside its path.
  if (rows.length) {
    const list = document.createElement("dl");
    list.className = "pairs why-facts";
    for (const row of rows) {
      const term = document.createElement("dt");
      term.textContent = row.label;
      const value = document.createElement("dd");
      value.className = "num";
      value.setAttribute("data-field", row.path);
      value.setAttribute("data-raw", String(row.value));
      value.textContent = factText(row);
      list.append(term, value);
    }
    details.append(list);
  }

  // The findings that name it - references, not restatements.
  for (const finding of findings) {
    const line = document.createElement("p");
    line.className = "muted why-finding";
    line.setAttribute("data-finding", finding.id ?? "");
    line.textContent = finding.title ?? finding.id ?? "";
    details.append(line);
  }

  if (history) details.append(history);
  return details;
}

/** One fact, in the unit the source declared it in. */
function factText(row) {
  if (row.kind === "duration_us") return seconds(row.value);
  if (row.kind === "share") return `${(row.value * 100).toFixed(1)}%`;
  if (row.kind === "kilobytes") return mib(row.value * 1024);
  return String(row.value);
}

/**
 * UX-228: focus is an investigation, not a dimmer.
 *
 * `UX-222` built focus as visual state - one element held, the rest
 * dimmed, the document unharmed - and that is still exactly what it
 * does. What the reader actually wanted was "show me the evidence
 * about *this*", and today that evidence is in four places: the
 * element's own section, its blast, its history, the finding that
 * names it.
 *
 * So focusing also *assembles*: why it matters, what evidence exists,
 * what it is connected to, and what to do. Every value is read from a
 * published field and carries the path it came from, exactly as
 * `UX-227`'s fold does - and the panel carries `data-role`, so
 * unfocusing removes it and the document is byte-identical to
 * never-focused.
 *
 * No pane, no drawer, no overlay: round 24's argument stands, and what
 * cannot survive an export or a print does not enter the page. This is
 * a section prepended to the document and removed again.
 */
export function renderInvestigation(payload, uid, options = {}) {
  if (!payload || !uid) return null;
  const section = document.createElement("section");
  section.className = "investigation";
  section.setAttribute("data-role", "focus-investigation");
  section.setAttribute("data-section", "investigation");
  section.setAttribute("data-element", uid);
  const heading = document.createElement("h2");
  heading.textContent = `Everything about ${uid}`;
  section.append(heading);

  const groups = [
    ["why", "Why it matters", investigationWhy(payload, uid, options)],
    ["evidence", "What evidence exists", investigationEvidence(payload, uid,
                                                               options)],
    ["relationships", "What it is connected to",
     investigationRelations(payload, uid)],
    ["actions", "What to do", investigationActions(payload, uid, options)],
  ];
  let any = false;
  for (const [key, title, rows] of groups) {
    if (!rows.length) continue;
    any = true;
    const group = document.createElement("div");
    group.className = "investigation-group";
    group.setAttribute("data-group", key);
    const label = document.createElement("h3");
    label.textContent = title;
    group.append(label);
    const list = document.createElement("dl");
    list.className = "pairs";
    for (const row of rows) {
      const term = document.createElement("dt");
      term.textContent = row.label;
      const value = document.createElement("dd");
      if (row.path) {
        value.setAttribute("data-field", row.path);
        value.setAttribute("data-raw", String(row.raw));
      }
      if (row.source) {
        value.setAttribute("data-source", row.source);
        value.setAttribute("data-present", String(row.present));
      }
      if (row.href) {
        const link = document.createElement("a");
        link.setAttribute("href", row.href);
        link.textContent = row.text;
        value.append(link);
      } else {
        value.textContent = row.text;
      }
      list.append(term, value);
    }
    group.append(list);
    section.append(group);
  }
  return any ? section : null;
}

/** The measured case for this element, from the same rows UX-227 uses. */
function investigationWhy(payload, uid, options) {
  const facts = elementFacts(payload).get(uid);
  const rows = (facts?.rows ?? []).map((row) => ({
    label: row.label, path: row.path, raw: row.value, text: factText(row),
  }));
  for (const finding of facts?.findings ?? []) {
    rows.push({ label: "Finding", text: finding.title ?? finding.id ?? "" });
  }
  return rows;
}

/**
 * Which published documents actually carry this element - present or
 * absent, both stated.
 *
 * "Plane 2 saw nothing here" and "Plane 2 was not run" are different
 * facts, and a list that only showed what exists would collapse them.
 */
function investigationEvidence(payload, uid, options) {
  const rows = [];
  const sources = [
    ["Critical path", `critical_path_detail[element_uid=${uid}]`],
    ["Optimization horizon",
     `optimization_horizon[element_uid=${uid}]`],
    ["Off-path heavies", `latent_heavies[element_uid=${uid}]`],
    ["Plane 2 (sandbox)", `element_join[element=${uid}]`],
  ];
  for (const [label, path] of sources) {
    const found = resolvePath(payload, path);
    // Presence is not a value *read*, so it does not claim to be one:
    // `data-source` names where it was looked for and `data-present`
    // says what was there. Putting a uid in `data-raw` under a path
    // that resolves to an object would have been a traceability claim
    // this row cannot honour.
    rows.push({
      label, source: path, present: found !== undefined,
      text: found === undefined ? "not in this document" : "yes",
    });
  }
  const named = (payload.findings ?? []).filter(
    (finding) => (finding.elements ?? []).includes(uid));
  rows.push({ label: "Findings naming it", text: String(named.length) });
  if (options.store) {
    const { series, sawASliceAtAll } = elementHistory(options.store, uid);
    rows.push({
      label: "Store history",
      text: series.length ? `${series.length} snapshot(s)`
        : sawASliceAtAll ? "not watched in these runs"
                         : "captured before history existed",
    });
  }
  return rows;
}

/** Its neighbours on the chain, and how much depends on it. */
function investigationRelations(payload, uid) {
  const rows = [];
  // `UX-288`: the chain comes from `critical_path_detail`, which is now
  // the one place the path is published. The evidence `path` each row
  // carries has to name a field that *resolves* in the payload -
  // provenance is checkable or it is decoration (`UX-229`) - so it
  // cites the detail entry rather than the bare list that used to
  // duplicate it.
  const detail = payload?.critical_path_detail;
  const chain = Array.isArray(detail)
    ? detail.map((entry) => entry?.element_uid) : null;
  if (chain) {
    const at = chain.indexOf(uid);
    const cite = (i) => `critical_path_detail[${i}].element_uid`;
    if (at > 0) {
      rows.push({ label: "Waits on (chain)", path: cite(at - 1),
                  raw: chain[at - 1], text: chain[at - 1],
                  href: `#${elementAnchor(chain[at - 1])}` });
    }
    if (at !== -1 && at < chain.length - 1) {
      rows.push({ label: "Blocks (chain)", path: cite(at + 1),
                  raw: chain[at + 1], text: chain[at + 1],
                  href: `#${elementAnchor(chain[at + 1])}` });
    }
  }
  const downstream = resolvePath(
    payload, `elements.blast_radius[${uid}].downstream_count`);
  if (typeof downstream === "number") {
    rows.push({ label: "Rebuilds if changed",
                path: `elements.blast_radius[${uid}].downstream_count`,
                raw: downstream, text: `${downstream} element(s)` });
  }
  return rows;
}

/** The things that already exist to do about it. */
function investigationActions(payload, uid, options) {
  const rows = [
    { label: "Its section", href: `#${elementAnchor(uid)}`,
      text: "open" },
  ];
  const step = (payload.next_steps ?? []).find(
    (entry) => (entry.argv ?? []).includes(uid));
  if (step) {
    rows.push({ label: "Published next step", text: step.argv.join(" ") });
  } else {
    // The command a reader would type anyway, and the one the blast box
    // runs when there is a server. Shown as text rather than as a dead
    // control, which is `UX-194`'s rule.
    rows.push({ label: "What rebuilds if you touch it",
                text: `bga blast ${uid}` });
  }
  return rows;
}

// ------------------------------------------------- UX-372: the reader

/**
 * `UX-372`: **the page had one reader.**
 *
 * It opened "What should I do?" and answered it once, for whoever was
 * looking. Measured on `macro_micro`, the three top actions are the
 * same advice three times - shorten this element, then that one, then
 * the third - which is the right answer for the person who can change
 * `core.bst` and no answer at all for the CI owner, whose lever is
 * `capacity-recommendation`, finding nine of eleven.
 *
 * Nothing here decides anything. `payload.readers` is the producer's
 * index - which reader, their question, and the finding that is their
 * biggest lever on this run - so choosing a reader is a lookup. A page
 * that ranked severities of its own would be a second decision-maker
 * and the CI comment would route differently from the report
 * (Direction 7).
 *
 * **The default answers.** With nobody chosen the chapter is what it
 * was, byte for byte: this must not become a page that says nothing
 * until a form is filled in.
 */
function readerLead(payload, entry) {
  const finding = (payload?.findings ?? [])
    .find((f) => f?.id === entry?.leads_with);
  if (!finding) return null;
  const block = document.createElement("div");
  block.className = "reader-lead";
  block.setAttribute("data-role", "reader-lead");
  block.setAttribute("data-reader", entry.id);
  block.setAttribute("data-finding", finding.id);
  const asked = document.createElement("p");
  asked.className = "muted";
  asked.textContent = entry.question ?? "";
  const said = document.createElement("p");
  const answer = document.createElement("a");
  answer.setAttribute("href", "#findings");
  answer.textContent = finding.title ?? finding.id;
  said.append(answer);
  block.append(asked, said);
  return block;
}

/** The picker, over the readers this run has something for.
 *
 *  Fewer than two is not a choice, so nothing is drawn - `UX-194`'s
 *  dead-control rule. `slot` is where the answer lands. */
function readerPicker(payload, slot) {
  const readers = (Array.isArray(payload?.readers) ? payload.readers : [])
    .filter((entry) => readerLead(payload, entry));
  if (readers.length < 2) return null;
  const wrap = document.createElement("div");
  wrap.className = "reader-picker";
  const select = document.createElement("select");
  select.className = "top-n";
  select.setAttribute("data-role", "reader");
  for (const [value, text] of [["", "anyone"],
                               ...readers.map((e) => [e.id, e.label])]) {
    const option = document.createElement("option");
    option.setAttribute("value", value);
    option.textContent = text;
    select.append(option);
  }
  const label = document.createElement("label");
  label.textContent = "I am ";
  labelFor(label, select, "reader");
  select.addEventListener?.("change", () => applyReader(payload, slot,
                                                        select.value));
  wrap.append(label, select);
  return wrap;
}

/** Put the chosen reader's biggest lever in `slot`, or empty it. */
export function applyReader(payload, slot, reader) {
  const entry = (payload?.readers ?? []).find((e) => e?.id === reader);
  const block = entry ? readerLead(payload, entry) : null;
  slot.replaceChildren(...(block ? [block] : []));
  slot.setAttribute("data-reader", reader || "");
  return block;
}

export function renderDecision(payload, investigate = null, copy = null,
                               options = {}) {
  const headline = payload?.headline;
  if (!headline || !headline.diagnosis) return null;

  const section = document.createElement("section");
  section.className = "decision";
  section.setAttribute("data-section", "decision");
  section.setAttribute("id", "decision");
  section.setAttribute("data-diagnosis", headline.diagnosis);

  const heading = document.createElement("h2");
  heading.textContent = "What to fix first";
  section.append(heading);

  const sentence = document.createElement("p");
  sentence.className = "diagnosis";
  sentence.setAttribute("data-field", "headline.sentence");
  sentence.textContent = headline.sentence ?? "";
  section.append(sentence);

  // `UX-372`: and, for a reader who says who they are, their own
  // biggest lever. Below the diagnosis, which is true for everyone.
  const slot = document.createElement("div");
  slot.setAttribute("data-role", "reader-slot");
  const picker = readerPicker(payload, slot);
  if (picker) section.append(picker, slot);

  // UX-229: and why. Directly under the claim it explains, folded -
  // the panel is a decision, and the chain is what a reader opens
  // after doubting one.
  const chain = renderProvenance(headline.provenance);
  if (chain) section.append(chain);

  // The opportunity split, both halves published. Absent stays absent -
  // a zero here would claim a measurement nobody made.
  const split = document.createElement("dl");
  split.className = "pairs opportunity";
  for (const [label, key, kind] of [
    ["Certified headroom", "certified_headroom_us", "duration_us"],
    ["Beyond the chain", "scheduling_gap_us", "duration_us"],
  ]) {
    const value = headline[key];
    if (typeof value !== "number") continue;
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.className = "num";
    detail.setAttribute("data-field", `headline.${key}`);
    detail.setAttribute("data-raw", String(value));
    detail.textContent = kind === "duration_us" ? seconds(value) : String(value);
    split.append(term, detail);
  }
  if (split.children?.length) section.append(split);

  const actions = Array.isArray(headline.top_actions) ? headline.top_actions : [];
  if (actions.length) {
    // `UX-371`: **the rule that ranked them, once.**
    //
    // `renderWhyRanked` draws the provenance of the finding each
    // action came from, and on every run measured they all come from
    // one finding - so the same record was rendered once per row.
    // Counted on `macro_micro` with everything open: 6 copies of "No
    // named threshold; computed in ..." in this chapter alone, and 3
    // of the finding's title, all of it on the first screen. A reader's
    // first impression of the page was the same two sentences three
    // times.
    //
    // Where the actions come from different findings the rule is not
    // shared and the old per-row placement is right, so this is a
    // branch rather than a move.
    const claim = actions[0]?.finding_id;
    const shared = claim && actions.every((a) => a?.finding_id === claim)
      ? (payload?.provenance ?? []).find((e) => e?.claim === claim)
      : null;
    const list = document.createElement("ol");
    list.className = "actions";
    for (const [index, action] of actions.entries()) {
      // UX-227: the row names the element; the fold under it answers
      // *why this one*, from the same published fields the rest of the
      // document draws.
      list.append(actionRow(action, investigate, renderWhyRanked(
        payload, action,
        { ...options, rank: index + 1, ranking: shared && claim })));
    }
    section.append(list);
    // Below the list it explains, not above it: the reader came for
    // the actions.
    const how = shared ? renderProvenance(shared) : null;
    if (how) {
      const rule = document.createElement("h3");
      rule.textContent = "How these were ranked";
      rule.setAttribute("data-role", "ranking-rule");
      section.append(rule, how);
    }
  }

  // UX-218: and what to run next. Read from `next_steps`, never
  // derived - the branch that chose these lives in the pipeline, so
  // the terminal, CI and this panel give the same answer.
  const steps = Array.isArray(payload?.next_steps) ? payload.next_steps : [];
  if (steps.length) {
    const heading = document.createElement("h3");
    heading.textContent = "Next";
    section.append(heading);
    const list = document.createElement("ol");
    list.className = "next-steps";
    for (const step of steps) list.append(nextStepRow(step, copy));
    section.append(list);
  }
  return section;
}

/**
 * One published next step: why, and the exact command.
 *
 * `copy` is passed in rather than imported so this file keeps having
 * no dependency on `tables.js` - and so a harness can drive the button
 * without a clipboard.
 */
function nextStepRow(step, copy) {
  const row = document.createElement("li");
  row.className = "next-step";
  row.setAttribute("data-step", step.id ?? "");
  row.setAttribute("data-follows-from", step.follows_from ?? "");

  const why = document.createElement("p");
  why.className = "muted";
  why.textContent = step.reason ?? "";
  row.append(why);

  // `UX-429`: through the shared control. `UX-279`'s "Copy command"
  // wording lives there now, with the join and the monospace line, so
  // this site and the two others cannot drift apart again.
  row.append(...commandLine(step.argv, { copy }));
  return row;
}

function actionRow(action, investigate, whyBlock = null) {
  const row = document.createElement("li");
  row.className = "action";
  row.setAttribute("data-element", action.element_uid ?? "");
  row.setAttribute("data-finding", action.finding_id ?? "");

  // UX-216: the decision panel names an element; naming it and not
  // linking it is the gap this item closes.
  const name = document.createElement("a");
  name.setAttribute("href", `#${elementAnchor(action.element_uid ?? "")}`);
  const code = document.createElement("code");
  code.textContent = action.element_uid ?? "";
  name.append(code);
  row.append(name);

  if (typeof action.saving_us === "number") {
    const worth = document.createElement("span");
    worth.className = "worth num";
    worth.setAttribute("data-field", "saving_us");
    worth.setAttribute("data-raw", String(action.saving_us));
    worth.textContent = `saves ${seconds(action.saving_us)}`;
    row.append(worth);
  } else if (typeof action.downstream_count === "number") {
    const reach = document.createElement("span");
    reach.className = "worth num";
    reach.setAttribute("data-field", "downstream_count");
    reach.setAttribute("data-raw", String(action.downstream_count));
    reach.textContent = `${action.downstream_count} downstream`;
    row.append(reach);
  }

  // The reasoning is a section away, not restated here - `finding_id`
  // is a reference for exactly this.
  const why = document.createElement("a");
  why.className = "why";
  why.setAttribute("href", "#findings");
  why.textContent = "why";
  row.append(why);

  // UX-204's transport, where there is a timeline behind it.
  if (investigate) {
    const button = investigate(action);
    if (button) row.append(button);
  }
  if (whyBlock) row.append(whyBlock);
  return row;
}

