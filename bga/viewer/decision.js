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
import { identify, labelFor } from "./controls.js";
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
export function renderProvenance(provenance) {
  if (!provenance || !provenance.rule) return null;
  const details = document.createElement("details");
  details.className = "provenance";
  details.setAttribute("data-provenance", provenance.claim ?? "");
  details.setAttribute("data-kind", provenance.kind ?? "");
  if (provenance.trace_query) {
    details.setAttribute("data-query", provenance.trace_query);
  }
  const summary = document.createElement("summary");
  summary.textContent = "Why";
  details.append(summary);

  const why = document.createElement("p");
  why.className = "why";
  why.setAttribute("data-field", "provenance.rule.sentence");
  why.textContent = provenance.rule.sentence ?? "";
  details.append(why);

  if (provenance.rule.name) {
    const rule = document.createElement("p");
    rule.className = "rule muted";
    rule.setAttribute("data-rule", provenance.rule.name);
    rule.setAttribute("data-threshold", String(provenance.rule.threshold));
    rule.setAttribute("data-comparison", provenance.rule.comparison ?? "");
    rule.textContent =
      `${provenance.rule.name} = ${provenance.rule.threshold}` +
      ` (${provenance.rule.module ?? ""})`;
    details.append(rule);
  }

  const refs = Array.isArray(provenance.evidence) ? provenance.evidence : [];
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
      value.textContent = ref.resolved === false
        ? "unresolved" : String(ref.value);
      list.append(term, value);
    }
    details.append(list);
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
  if (!rows.length && !findings.length && !record && !history) return null;

  const details = document.createElement("details");
  details.className = "why-ranked";
  details.setAttribute("data-why", uid);
  const summary = document.createElement("summary");
  summary.textContent = options.rank
    ? `Why #${options.rank}` : "Why this one";
  details.append(summary);

  // The rule that ranked it, from the finding's own record.
  if (record) {
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
    const list = document.createElement("ol");
    list.className = "actions";
    for (const [index, action] of actions.entries()) {
      // UX-227: the row names the element; the fold under it answers
      // *why this one*, from the same published fields the rest of the
      // document draws.
      list.append(actionRow(action, investigate, renderWhyRanked(
        payload, action, { ...options, rank: index + 1 })));
    }
    section.append(list);
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

  const argv = Array.isArray(step.argv) ? step.argv.join(" ") : "";
  const command = document.createElement("code");
  command.className = "next-command";
  command.setAttribute("data-argv", argv);
  command.textContent = argv;
  row.append(command);

  if (copy && argv) {
    const button = document.createElement("button");
    button.setAttribute("type", "button");
    button.className = "copy-step";
    // UX-279: a command, and it says so - this one pastes into a shell.
    button.textContent = "Copy command";
    button.title = "Copy this command to the clipboard, ready to run";
    button.setAttribute("data-copies", "command");
    button.addEventListener("click", () => {
      copy(argv);
      button.textContent = "\u2713 copied";
      setTimeout(() => { button.textContent = "Copy command"; }, 1200);
    });
    row.append(button);
  }
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

