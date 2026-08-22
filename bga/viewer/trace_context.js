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
 * Which library question answers which finding.
 *
 * Keyed by the `id` `findings.py` assigns, so a renamed finding loses
 * its button rather than silently pointing at the wrong question - and
 * the coverage guard asserts both directions: every id here names a
 * real query, and every query a finding references is on the library
 * page.
 */
export const FINDING_QUERIES = {
  // Scheduling: the finding says time was spent waiting; the query
  // shows where the gaps are.
  "wait-category": "stalls",
  "capacity-recommendation": "stalls",
  // Execution: the finding names elements; the query opens them.
  "time-concentration": "element-time",
  "execution-bound": "element-commands",
  "latent-heavies": "element-commands",
  // Dependencies: the finding is about shape, not speed.
  "criticality": "dependency-wait",
  "blast-radius-ranking": "dependency-wait",
  "shared-source-blast": "dependency-wait",
  // Resources: what the processes inside the sandbox cost.
  "memory-envelope": "process-storm",
  "cache-transfer-cost": "sandbox-tax",
};

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
  const query = FINDING_QUERIES[finding?.id];
  if (!query) return null;
  return traceContext({
    element_uid: subjectOf(finding),
    reason: finding.title ?? finding.id,
    query,
  });
}

/** Every query id a finding can reference - the coverage guard's other
 *  direction. */
export function referencedQueries() {
  return [...new Set(Object.values(FINDING_QUERIES))].sort();
}
