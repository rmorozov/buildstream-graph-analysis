// `UX-450`: the section walk, split out of `app.js`.
//
// `UX-337` set a 1,500-line ceiling per viewer module and `app.js` sat
// exactly on it, having twice paid for a new line by deleting a
// comment. The seam is the one the file's own header already names:
// **what the page draws** against **what runs it**. Everything here
// turns a payload and a schema into DOM and returns it; nothing here
// touches the document, the URL, storage or an event - that is
// `app.js`, which boots, wires and hands this the payload.
//
// The cut was derived rather than judged (`tools/dev_js_deps.py
// --crossings`). Its first shape was cyclic: `investigateButton` lives
// here and calls `investigate`, which lived there. Moving `investigate`,
// `decisionInvestigation` and `traceUrl` across with it leaves one
// direction only -
//
//     app <- sections    decisionInvestigation investigate
//                        investigateButton render render traceUrl
//
// - which is what `_module_order` needs: a module is inlined after
// everything it imports, so a cycle would make the export's
// concatenation a lie (`UX-199`, which rendered an empty page for
// several rounds).
import { chapters } from "./chapters.js";
import { renderProvenance } from "./decision.js";
import { GRADE_EXHIBIT, decomposition, interval, strip } from "./drawings.js";
import { resolvePath } from "./element.js";
import { COLUMNS, DECOMPOSITION, DISTRIBUTION, INLINE, INTERVAL, QUANTITY, SERIES, SEVERITY, bytes, childNode, cssId, describedTerm, el, guessQuantity, heading, hintsOf, quantity, quantityFor, sectionHead, title } from "./format.js";
import { matches } from "./nav.js";
import { handOff } from "./perfetto.js";
import { served } from "./primitives.js";
import { byId, copyButton } from "./questions.js";
import { recordSource } from "./rawjson.js";
import { CONTROLS, classify } from "./shapes.js";
import { ARRAY_INLINE_ITEMS, CELL_NEST_LIMIT, LIFTED_SECTION, OBJECT_INLINE_FIELDS, TABLE_OPENS_BOUNDED_ABOVE, liftedCriticalPath, renderPairs, renderStructured, renderTable } from "./structured.js";
import { boundCards } from "./tables.js";
import { investigationsFor } from "./trace_context.js";
import { INCOMPLETE, PLANE2_NOT_CAPTURED, renderEvidence }
  from "./views.js";

/**
 * `UX-204`: each finding carries a button that knows *why* it is
 * sending you to Perfetto.
 *
 * `investigate` is passed in rather than reached for, and it is only
 * passed when the run has a timeline behind it - `UX-194`'s dead-button
 * rule. No timeline, no buttons, rather than a row of controls that
 * error.
 */
export const EVIDENCE_SHOWN = 4;

/**
 * `UX-217`: the numbers a finding was drawn from.
 *
 * Every finding has carried a structured `evidence` dict since the
 * findings became data, and `renderFindings` read `id`, `severity`,
 * `title`, `detail` and `elements` and dropped it. So the page showed
 * the conclusion and hid the measurements it rests on.
 *
 * `node` is the schema's `evidence` node, so a key renders in its
 * declared unit and a key nobody declared renders raw - `UX-201`'s
 * rule one level deeper, and the reason a new finding's evidence
 * formats correctly with no change here. A value that is not a scalar
 * (`rows`, `steps`, `constraints` - the arrays a finding builds its
 * sentence from) is a table in its own right and is left to the
 * section that already draws it.
 */
export function renderFindingEvidence(evidence, node = undefined) {
  const scalars = Object.entries(evidence ?? {}).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;

  const list = el("dl", { class: "pairs evidence" });
  for (const [key, value] of scalars) {
    const kind = quantityFor(childNode(node, key), key);
    // UX-317 (§2b.3): the same marker here. The mechanism is generic -
    // any described value, anywhere - and this list is one of the three
    // places a `<dt>` is built.
    const { term, describe } = describedTerm(
      key, hintsOf(childNode(node, key)).description, {},
      hintsOf(childNode(node, key))[INLINE], kind);
    list.append(
      term,
      el("dd", { class: typeof value === "number" ? "num" : null,
                 "data-field": key,
                 "data-raw": value === null ? "" : String(value) },
         typeof value === "number" ? quantity(value, kind)
           : value === null ? "—" : String(value),
         describe));
  }
  if (scalars.length <= EVIDENCE_SHOWN) return list;
  // UX-209's fold, for the same reason: the evidence is the point, and
  // eight rows of it above the next finding is a wall.
  //
  // `UX-359`: and it announces its depth, like every other value fold
  // (§3a.1). It did not, because it is built by hand here rather than
  // by `renderStructured`, and it only appears on a finding with more
  // than `EVIDENCE_SHOWN` scalars - which only the Plane 2 half of
  // `macro_micro` has, and every guard's `copytree` was dropping it.
  const rows = scalars.length;
  return el("details", { class: "evidence-fold", "data-fold": "evidence",
                         "data-levels": "1", "data-rows": String(rows) },
            el("summary", {},
               `${rows} measurements · 1 level, `
               + `${rows} row${rows === 1 ? "" : "s"}`),
            list);
}

export function renderFindings(findings, investigate = null, node = undefined) {
  const section = el("section", { "data-section": "findings" },
    el("h2", {}, `Findings (${findings.length})`));
  const evidenceNode = childNode(node?.items, "evidence");
  for (const finding of findings) {
    const severity = String(finding.severity ?? "info").toLowerCase();
    const detail = Array.isArray(finding.detail)
      ? finding.detail : (finding.detail ? [finding.detail] : []);
    section.append(el("article",
      { class: "finding", "data-severity": severity,
        "data-finding-id": finding.id ?? "" },
      el("p", { class: "title" },
        el("span", { class: "badge" }, severity),
        finding.title ?? finding.id ?? ""),
      ...detail.map((line) => el("p", { class: "detail muted" }, line)),
      // UX-216: a finding names elements; each is a link to that
      // element's own section, and carries `data-element` so the
      // cross-reference finds this finding from the other direction.
      finding.elements && finding.elements.length
        ? el("p", { class: "muted" },
            ...finding.elements.flatMap((uid, index) => [
              index ? ", " : "",
              el("a", { href: `#${cssId(uid)}`, "data-element": uid },
                 el("code", {}, uid)),
            ]))
        : null,
      renderFindingEvidence(finding.evidence, evidenceNode),
      // UX-229: the chain behind this finding, from the published
      // record. `views.js` draws it, so the decision panel and every
      // finding show one shape.
      renderProvenance(finding.provenance),
      investigate ? investigateButton(finding, investigate) : null,
      // UX-224: the finding as something you can paste. The text is
      // `findings[].copy_text`, rendered in the pipeline - this button
      // copies a published string and does not word anything, which is
      // the only way one renderer can serve both a Python CI comment
      // and a JavaScript page. Absent, not empty, on a payload that
      // does not carry it.
      finding.copy_text
        ? copyButton(el, finding.copy_text, {}, "finding")
        : null));
  }
  //: `UX-413`: cards are bounded like rows - see `boundCards`.
  boundCards(section, "article.finding", TABLE_OPENS_BOUNDED_ABOVE, "finding");
  return section;
}

/**
 * The button, and the paste it leaves behind.
 *
 * `UX-204`'s always-works floor: Perfetto's deep-link API takes a trace
 * and a title, and has no documented way to preload the Query pane -
 * so the query is not faked into the URL, it is put one paste away. The
 * button reveals it whether the handoff succeeds or not, because a
 * blocked pop-up is exactly when the reader needs the SQL most.
 */
export function investigateButton(finding, investigate) {
  const contexts = investigationsFor(finding);
  const context = contexts[0];
  if (!context) return null;
  const wrapper = el("div", { class: "investigate",
                              "data-query-id": context.queryId,
                              "data-element": context.element ?? "" });
  const button = el("button", { type: "button" }, "Investigate in Perfetto");
  // `UX-448`: one paste per grain the claim offers, not one button
  // per grain. The handoff opens one trace into one tab whichever
  // question the reader came with, so a second button would send the
  // same trace twice; a second paste is the second question, which is
  // the thing that actually differs. Labelled only where there is more
  // than one - a lone `<pre>` needs no heading saying which of one it
  // is (`UX-371`, the page's repeated text).
  //
  // `hidden` through `el` lands as a *property* (it is not a
  // `data-` attribute), so it is cleared as one: `removeAttribute`
  // would not touch it, and the paste would never appear.
  const pastes = contexts.map((entry) => el(
    "pre", { class: "query", hidden: true, "data-query-id": entry.queryId },
    contexts.length > 1
      ? el("span", { class: "muted query-grain" }, byId(entry.queryId)?.title
                                                   ?? entry.queryId)
      : null,
    el("code", {}, entry.sql)));
  const status = el("span", { class: "muted handoff" });
  button.addEventListener("click", () => {
    // No `await` before the handoff: the click's transient activation
    // is what opens the tab (`UX-198`), and it is gone by the time one
    // resolves.
    for (const node of pastes) node.hidden = false;
    const sent = investigate(context);
    status.textContent = pastes.length > 1
      ? "opening ui.perfetto.dev — the queries are below…"
      : "opening ui.perfetto.dev — the query is below…";
    Promise.resolve(sent).then(
      ({ bytes } = {}) => {
        const noun = pastes.length > 1 ? "queries" : "query";
        status.textContent = bytes
          ? `sent ${(bytes / 1024).toFixed(1)} KiB — paste the ${noun} below`
          : `paste the ${noun} below`;
      },
      (error) => { status.textContent = String(error.message ?? error); });
  });
  wrapper.append(button, status, ...pastes);
  return wrapper;
}

// UX-201: the enum decides, and the prose is a fallback for payloads
// written before `verdict_kind` existed. The viewer used to
// string-match the *sentence* - so rewording "improved" would have
// silently restyled the banner, and a `compare/v1` that changed its
// wording was a rendering change nobody would have called one.
const VERDICT_CLASS = {
  improved: "good",
  regressed: "refused",
  not_comparable: "refused",
  no_significant_change: "",
  within_observed_range: "warn",
};

export function verdictClass(text, kind) {
  if (kind && kind in VERDICT_CLASS) return VERDICT_CLASS[kind];
  const value = String(text).toLowerCase();
  if (value.includes("not comparable") || value.includes("regress")) return "refused";
  if (value.includes("improve")) return "good";
  if (value.includes("no significant")) return "";
  return "warn";
}

export function renderVerdict(payload) {
  // Refusals get visual weight because they are the answer, not an
  // error: `UX-156`/`UX-185`'s incomplete runs and `UX-186`'s
  // cross-host pairs are all "bga will not judge this, and here is
  // why".
  const banner = [];
  if (payload.verdict) {
    banner.push(el("div", {
      class: `verdict ${verdictClass(payload.verdict, payload.verdict_kind)}`,
      "data-verdict": String(payload.verdict),
      "data-verdict-kind": payload.verdict_kind ?? null },
      el("h2", {}, "Verdict"), el("p", {}, String(payload.verdict))));
  }
  const outcome = payload.run_instance?.incomplete_reason
    ?? payload.run_instance?.build_outcome?.incomplete_reason;
  if (outcome) {
    // UX-207: the *one* place a refusal is drawn. `renderEvidence` drew
    // a second banner with the same claim in different words - measured
    // at two `data-incomplete` nodes on an interrupted fixture - and the
    // header is also the part a reader may have collapsed, which is the
    // worst place to keep the one sentence they must not miss.
    //
    // The wording comes from `INCOMPLETE`, which is where UX-202 put the
    // three sentences and where the guard against `RunContext`'s reasons
    // still points.
    banner.push(el("div", { class: "verdict refused",
                            "data-incomplete": outcome },
      el("h2", {}, `This run is ${outcome}`),
      el("p", { class: "muted" },
        INCOMPLETE[outcome] ?? "Durations from a run that did not finish "
                               + "are not measurements.")));
  }
  if (payload.comparability_warning) {
    banner.push(el("div", { class: "verdict warn", "data-warning": "1" },
      el("h2", {}, "Comparability"),
      el("p", {}, String(payload.comparability_warning))));
  }
  return banner;
}

// The generic dispatch. Note there is no `switch (key)` here: what a
// value is rendered as follows from its *shape* and its hints.
//: `UX-338`: sections the page deliberately does not draw on their
//: own, and where their content went instead. Not a blanket "skip
//: list": each entry is a population that is drawn *somewhere*, and
//: saying where is what stops this becoming a place to hide a section
//: nobody wants to fix.
export const DRAWN_ELSEWHERE = {
  element_join: "merged into the one element table (`elements`) and the "
    + "element sections beneath it, which is `UX-289`'s rule applied to "
    + "the columns `UX-215` added - it is the same eleven elements, and "
    + "drawing it twice is what `UX-338` was filed for. Every published "
    + "field arrives at one of those two except "
    + "`recommendations[].id`, which is a slug used as a key and never "
    + "shown, the way `next_steps[].id` is not shown",
  attribution_hints: "drawn on the row of the bucket it explains, which "
    + "`attribution` names through `bga:explained_by` (`UX-390`). The two "
    + "keys are the same eight bucket names, so a section each was one "
    + "population in two chapters - the number in one and the sentence "
    + "explaining it in another - which is `UX-288`'s rule at section "
    + "level. Every hint present before the merge is reachable after it, "
    + "on the row it belongs to",
};

//: `UX-401`: the fourth destination, and the only silent one allowed.
//: A key reaches a reader as its own section, as a `Run` row (every
//: scalar), through `DRAWN_ELSEWHERE`, or declared here with the reason
//: it stops at the terminal. Empty is the *measurement*: every key of
//: `analyze/v4` reaches a reader today, and the slot exists so the next
//: one that cannot is written down rather than left to the next walk -
//: which is what fourteen Plane 2 blocks were for six rounds.
export const TERMINAL_ONLY = {};

/**
 * `UX-388`: **an empty population is a result, and the page says so.**
 *
 * Six sections vanished between a cold capture and the incremental one
 * beside it - the optimization horizon 5 rows -> `[]`, `latent_heavies`
 * 1 -> `[]`, `joint_saving` an object -> `null`, and three more - and
 * the page went 9,316 px to 3,347 px without a word about any of them.
 * Every one of those was `return null` in this function.
 *
 * (The horizon is named in prose rather than by its key here: `UX-219`
 * guards that this file does not special-case it, by grepping for the
 * key. Tenth time a guard in this repository has found itself.)
 *
 * The reader is left unable to tell three facts the *payload* keeps
 * apart: the analysis ran and found nothing (`[]`, or a `null` the
 * emitter writes when its input set was empty); the key is absent
 * because this version of bga does not compute it; and - the one the
 * page did tell them - there is something here. `UX-107` made that
 * distinction law for Plane 2's coverage blocks; nothing had applied
 * it to a population.
 *
 * Absent stays absent: a key the payload does not carry renders
 * nothing, because nothing was computed and inventing a heading for it
 * would be the opposite error.
 */
function declaresACollection(node) {
  if (!node) return false;
  const type = node.type;
  if (type === "array" || type === "object") return true;
  if (Array.isArray(type)) return type.includes("array") || type.includes("object");
  return Boolean(node.items || node.additionalProperties || node.properties);
}

function isEmptyPopulation(value) {
  if (Array.isArray(value)) return !value.length;
  if (value && typeof value === "object") return !Object.keys(value).length;
  return value === null || value === undefined;
}

/** The heading, the sentence, and the one line that says it is empty. */
function renderEmptySection(key, hint, node, sentence = null) {
  const info = heading(key, hint);
  const section = el("section", {
    "data-section": key, "data-rail": info.rail,
    // The mark the rail reads, so the map of the report matches the
    // report on every run rather than only on the full ones.
    "data-empty": "true",
  }, sectionHead(key, hint));
  section.append(el("p", { class: "empty-population" },
                    sentence ?? (`Nothing to report here for this run \u2014 the `
                    + `analysis ran and found none.`)));
  // **No schema sentence here**, though an empty section is exactly
  // where a reader would want one. `UX-346` made the rule that a
  // description renders beside its value only when the contract
  // declares it inline, and `UX-317` that every described value carries
  // a `?` marker; a `<p class="description">` under a heading satisfies
  // neither, and the first version of this reddened four clauses of
  // those two items. The rule is older and better argued than the
  // convenience, so the sentence stays where the rule puts it.
  return section;
}

export function renderSection(key, value, hint = {}, node = undefined,
                              investigate = null, payload = undefined,
                              root = undefined) {
  if (key in DRAWN_ELSEWHERE) return null;
  // `UX-536`: **a join with no Plane 2 in it is not a measurement of
  // zero.** The evidence line already says these words on the same
  // condition; the section presenting the zeros said nothing, under a
  // heading that names two planes.
  if (key === "element_join_coverage" && value
      && Number(value.plane2_elements) === 0) {
    return renderEmptySection(key, hint, node,
      `${PLANE2_NOT_CAPTURED} for this run, so the two planes have `
      + `nothing to agree on \u2014 these are not zeros that were measured.`);
  }
  // `UX-388`: empty is rendered, absent is not - and what tells them
  // apart is the *contract*, not the value. A declared collection with
  // nothing in it (or a `null` its emitter writes for an empty input
  // set, which is what `joint_saving` does) is a population that came
  // back empty; anything else that is null is a scalar with no value
  // and has never been a section.
  if (isEmptyPopulation(value)) {
    return declaresACollection(node) ? renderEmptySection(key, hint, node)
                                     : null;
  }
  if (hint[SEVERITY] && Array.isArray(value)) {
    // UX-217: the schema node travels with the value, so the evidence
    // renders in its declared units rather than by name-sniffing.
    return renderFindings(value, investigate, node);
  }
  if (Array.isArray(value)) {
    // `UX-302`: §1 again, at section level. Three of its rows reach
    // here and each gets its own control; the fourth outcome is a shape
    // §1 does not name, and `renderStructured` folds and warns.
    //
    // The branch this replaces was `value.join(", ")` for *everything*
    // that was not an array of objects - which is right for a short
    // scalar array, unbounded for a long one, and for an array holding
    // an object renders `[object Object]`: strictly less than the JSON
    // it was meant to be better than (`UX-277` found the same leaf in a
    // table cell).
    const control = classify(value, {
      severity: Boolean(hint[SEVERITY]),
      columns: hintsOf(node)[COLUMNS] ?? null,
      series: hintsOf(node)[SERIES] ?? hint[SERIES] ?? null,
      nestLimit: CELL_NEST_LIMIT,
      inlineFields: OBJECT_INLINE_FIELDS, inlineItems: ARRAY_INLINE_ITEMS,
    });
    if (control === CONTROLS.TABLE
        && value.every((item) => item && typeof item === "object"
                                 && !Array.isArray(item))) {
      return renderTable(key, value, hint, node);
    }
    const body = control === CONTROLS.INLINE_LIST
      ? el("p", {}, el("code", {}, value.join(", ")))
      : renderStructured(key, value, hint, node, 0, key);
    return el("section", { "data-section": key,
                           "data-rail": heading(key, hint).rail },
                          sectionHead(key, hint), body);
  }
  if (typeof value === "object") {
    // `UX-303`: a section whose whole value is a published distribution
    // is the strip and its sentence, not a definition list of five
    // percentiles - which is what §2 means by "its shape first".
    if ((hintsOf(node)[DISTRIBUTION] ?? hint[DISTRIBUTION])
        && Object.keys(value).length) {
      return el("section", { "data-section": key,
                             "data-rail": heading(key, hint).rail },
                sectionHead(key, hint),
                strip(value, {
                  countKey: String(hintsOf(node)[DISTRIBUTION]
                                   ?? hint[DISTRIBUTION]),
                  grade: GRADE_EXHIBIT,
                  format: (n) => quantity(n, quantityFor(node, key)),
                }));
    }
    if (!Object.keys(value).length) return null;
    // `UX-361` (§2d): a section whose declaration says its numbers are
    // a *total split into parts*, or *values on one axis*, draws that
    // before it lists them. The declaration names published paths and
    // this resolves them - the page chooses nothing, which is the
    // whole of why the shape could be added without becoming a second
    // analyzer (Direction 7).
    const shaped = declaredDrawing(key, hint, node, payload);
    const body = renderPairs(key, value, hint, node, payload, root);
    if (shaped && body) body.insertBefore(shaped, body.children[1] ?? null);
    // UX-289: the whole document, because a preset's population is a
    // selection published elsewhere in it - `bottleneck`
    // for the choke points. The section renders its own value; the
    // payload is only ever read for a declared `from` path.
    return body;
  }
  return null;   // scalars belong in the summary, below
}

/**
 * `UX-361`: the drawing a section's own declaration asks for, or `null`.
 *
 * Both hints name published paths in the grammar `resolvePath` walks,
 * and every number the drawing gets comes back from one of them. A
 * path that does not resolve drops its part rather than being guessed
 * at, and a drawing left with nothing to say returns its sentence -
 * which is `strip`'s discipline (`UX-226`) in the two new shapes.
 */
function declaredDrawing(key, hint, node, payload) {
  if (!payload) return null;
  const hints = hintsOf(node);
  const split = hints[DECOMPOSITION] ?? hint[DECOMPOSITION];
  const axis = hints[INTERVAL] ?? hint[INTERVAL];
  const at = (path) => (path ? resolvePath(payload, path) : undefined);

  if (split) {
    const parts = (split.parts ?? []).map((part) => ({
      key: part.key, label: part.label, value: at(part.path),
    })).filter((part) => part.value !== undefined && part.value !== null);
    const mark = split.mark && at(split.mark.path) !== undefined
      ? { key: split.mark.key, label: split.mark.label,
          value: at(split.mark.path) }
      : null;
    return decomposition(parts, {
      total: at(split.total), mark, grade: GRADE_EXHIBIT,
      format: (n) => quantity(n, split.quantity ?? quantityFor(node, key)),
    });
  }
  if (axis) {
    const marks = (axis.marks ?? []).map((one) => ({
      key: one.key, label: one.label, value: at(one.path),
    })).filter((one) => one.value !== undefined && one.value !== null);
    return interval(marks, {
      low: axis.low ?? 0, high: axis.high ?? 1,
      threshold: axis.threshold === undefined ? null : at(axis.threshold),
      thresholdLabel: axis.threshold_label ?? "line",
      grade: GRADE_EXHIBIT,
      format: (n) => quantity(n, axis.quantity ?? quantityFor(node, key)),
    });
  }
  return null;
}

export function renderSummary(payload, hints) {
  const scalars = Object.entries(payload).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;
  const list = el("dl", { class: "pairs" });
  for (const [key, value] of scalars) {
    const kind = hints[key]?.[QUANTITY] ?? guessQuantity(key);
    const { term, describe } = describedTerm(key, hints[key]?.description, {},
                                             hints[key]?.[INLINE], kind);
    list.append(
      term,
      el("dd", {}, el("span", {
        class: typeof value === "number" ? "num" : null,
        "data-raw": value === null ? "" : String(value),
      }, typeof value === "number" ? quantity(value, kind)
         : value === null ? "—" : String(value)), describe));
  }
  return el("section", { "data-section": "summary" },
            el("h2", {}, "Run"), list);
}

export function render(payload, schema, root, investigate = null) {
  const hints = {};
  for (const [key, sub] of Object.entries(schema?.properties ?? {})) {
    const hint = hintsOf(sub);
    if (Object.keys(hint).length) hints[key] = hint;
  }
  const nodes = schema?.properties ?? {};

  root.replaceChildren();
  for (const banner of renderVerdict(payload)) root.append(banner);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "schema") continue;
    // UX-270: the critical path is the one table that grows with *path
    // depth* rather than element count, so it folds by the chain's own
    // numbers. `UX-344` made it a key of the document rather than a row
    // of `signals`, which is what it was already drawn as - this is the
    // fold, kept, now that the section arrives on its own.
    const section = key === LIFTED_SECTION
      ? liftedCriticalPath(payload, schema)
      : renderSection(key, value, hints[key] ?? {}, nodes[key],
                      investigate, payload, schema);
    // `UX-302`: what this section was rendered *from*, so the "view as
    // JSON" toggle has a published value to show rather than a
    // re-serialisation of the DOM. Only the schema-driven sections get
    // one; a section the page composes from several places has no
    // single payload slice, and gets no toggle rather than a misleading
    // one.
    if (section) root.append(recordSource(section, value));
  }
  const summary = renderSummary(payload, hints);
  if (summary) {
    root.append(recordSource(summary, Object.fromEntries(
      Object.entries(payload).filter(
        ([, value]) => value === null || typeof value !== "object"))));
  }
  root.setAttribute("aria-busy", "false");
  return root;
}

// The trace is a data: URL in an export and a served path otherwise.
// `handOff` fetches whichever it is given; `fetch` handles data: URLs,
// so the Perfetto button works from `file://` with no server at all.
/**
 * `UX-204`: hand the timeline over with a title that says why.
 *
 * The title is what Perfetto shows in its tab, so a reader with three
 * of these open can tell them apart - which is the whole point of the
 * context travelling.
 */
export function investigate(context) {
  return handOff(traceUrl(), context.title);
}

/**
 * `UX-207` x `UX-204`: an action's investigate button.
 *
 * The action carries `finding_id`, so the context is built from the
 * finding it references rather than invented here - the same linkage
 * `UX-204` asserts in both directions.
 */
export function decisionInvestigation(action, payload) {
  const finding = (payload?.findings ?? []).find(
    (f) => f.id === action.finding_id);
  if (!finding) return null;
  return investigateButton(
    { ...finding, elements: [action.element_uid] }, investigate);
}

export function traceUrl() {
  const node = document.getElementById("bga-trace");
  return node ? node.textContent.trim() : "timeline.json.gz";
}
