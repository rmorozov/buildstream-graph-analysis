// UX-204: where to look, and why.
//
// The viewer's job is not to draw the timeline - Perfetto draws it far
// better - but to say *where to look and why*. "Open timeline in
// Perfetto" is correct and context-free: the findings know an element
// uid and a question, and none of it travelled.
//
// A link-builder, not a layer. Everything here is a pure function of
// data the page already has; nothing fetches, nothing renders. What
// Perfetto's deep-link API verifiably supports is used - the trace and
// a title - and what it does not is not faked: there is no documented
// way to preload a query into the Query pane, so the always-works floor
// is "open the trace, and put the right query one paste away".
import { byId } from "./questions.js";

/**
 * `UX-229` retired this file's own finding -> query table.
 *
 * It lived here, which made the page the only place that knew which
 * question deepens which finding: the text report could not print it
 * and the CI comment could not cite it. It is `bga/provenance.py`'s
 * `TRACE_QUERIES` now, published per claim as
 * `provenance.trace_query`, and this module reads that field - the
 * same move `UX-207` made for the diagnosis.
 *
 * The consequence is deliberate: a payload written before `UX-229` has
 * no provenance and gets no button, which is `UX-194`'s dead-button
 * rule. A guessed query would be worse than none.
 */
export function queryFor(finding) {
  const query = finding?.provenance?.trace_query;
  return typeof query === "string" && query ? query : null;
}

/** The element a finding is about, or null. First one: the button is
 *  one question, and a question about eleven elements is none. */
export function subjectOf(finding) {
  const elements = finding?.elements;
  return Array.isArray(elements) && elements.length ? String(elements[0]) : null;
}

/**
 * `{element_uid?, reason, query?}` -> the handoff invocation.
 *
 * `title` is what Perfetto shows in its tab, so it carries the reason
 * rather than the file name. `sql` is the query with the element
 * substituted - the paste, ready.
 */
export function traceContext({ element_uid = null, reason, query = null } = {}) {
  if (!reason) return null;
  const entry = query ? byId(query) : null;
  if (query && !entry) return null;
  const title = element_uid ? `${reason} — ${element_uid}` : reason;
  return {
    title,
    element: element_uid,
    queryId: entry ? entry.id : null,
    sql: entry ? withElement(entry, element_uid) : null,
  };
}

/** The library entry's SQL, aimed at one element where it takes one. */
export function withElement(entry, element_uid) {
  const target = element_uid ?? entry.example ?? "";
  return entry.sql.split("{element}").join(target);
}

/** The context a finding earns, or null when no query answers it. */
export function investigationFor(finding) {
  const query = queryFor(finding);
  if (!query) return null;
  return traceContext({
    element_uid: subjectOf(finding),
    reason: finding.title ?? finding.id,
    query,
  });
}
