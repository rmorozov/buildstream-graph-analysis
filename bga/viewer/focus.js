// UX-222 and UX-225: one element at a time, and where the reader is.
//
// Two features, one mechanism, which is why they share a module.
// `data-element` is already on path boxes, table rows, blast rows, top
// actions, horizon steps, culprit rows and finding element lists - so
// both "show me only this element" and "I have dealt with this element"
// are a predicate over an attribute that is already in the document.
// No new data model, no second render, and nothing here reads or writes
// analysis.
//
// Both are *view state*, so both travel in `UX-211`'s fragment rather
// than `localStorage`: storage remembers for me, on this browser, and an
// exported report opened from `file://` may get none at all. A link is
// the thing a reader already pastes into an issue.

export const MARKS = ["working", "done", "aside"];
export const MARK_LABELS = {
  working: "working", done: "done", aside: "set aside",
};

const elementNodes = (root) => [...(root.querySelectorAll?.("[data-element]") ?? [])];

// ------------------------------------------------------------- focus

/**
 * Focus one element: dim every occurrence of any other, and collapse
 * the sections that mention none.
 *
 * Dimmed and collapsed, never removed. The reader has to be able to see
 * what they are *not* looking at, and the document underneath must stay
 * byte-identical so Ctrl-F and the export remain honest.
 */
export function applyFocus(root, uid) {
  if (!uid) return clearFocus(root);
  root.setAttribute?.("data-focus", uid);
  for (const node of elementNodes(root)) {
    const mine = node.getAttribute("data-element") === uid;
    if (mine) node.removeAttribute?.("data-dimmed");
    else node.setAttribute("data-dimmed", "true");
  }
  for (const section of root.querySelectorAll?.("section[data-section]") ?? []) {
    const mentions = section.getAttribute("data-element") === uid
      || [...(section.querySelectorAll?.("[data-element]") ?? [])]
           .some((n) => n.getAttribute("data-element") === uid);
    if (mentions) section.removeAttribute?.("data-unfocused");
    else section.setAttribute("data-unfocused", "true");
  }
  return uid;
}

export function clearFocus(root) {
  root.removeAttribute?.("data-focus");
  for (const node of elementNodes(root)) node.removeAttribute?.("data-dimmed");
  for (const section of root.querySelectorAll?.("section[data-section]") ?? []) {
    section.removeAttribute?.("data-unfocused");
  }
  return null;
}

export function focusedElement(root) {
  return root.getAttribute?.("data-focus") || null;
}

/** The persistent bar: what is focused, and how to stop. */
export function renderFocusBar(uid, { onClear } = {}) {
  const bar = document.createElement("p");
  bar.className = "focus-bar";
  bar.setAttribute("data-role", "focus-bar");
  bar.setAttribute("data-element", uid);
  const label = document.createElement("span");
  label.textContent = `Focused on ${uid}`;
  const clear = document.createElement("button");
  clear.className = "focus-clear";
  clear.setAttribute("type", "button");
  clear.textContent = "clear";
  if (onClear) clear.addEventListener?.("click", onClear);
  bar.append(label, document.createTextNode(" · "), clear);
  return bar;
}

// ------------------------------------------------------------- marks

/**
 * The reader's own annotation, per element.
 *
 * Never an input to the analysis and never a filter: an element marked
 * `done` stays in the ranking and stays in the horizon, annotated. A
 * ranking that quietly drops what the reader dismissed is one they
 * cannot check.
 */
export function applyMarks(root, marks) {
  for (const node of elementNodes(root)) {
    const mark = marks?.[node.getAttribute("data-element")];
    if (mark && MARKS.includes(mark)) node.setAttribute("data-mark", mark);
    else node.removeAttribute?.("data-mark");
  }
  return marks ?? {};
}

/** Read the marks back off the document, so capture needs no store. */
export function readMarks(root) {
  const marks = {};
  for (const node of elementNodes(root)) {
    const mark = node.getAttribute("data-mark");
    if (mark) marks[node.getAttribute("data-element")] = mark;
  }
  return marks;
}

export function summariseMarks(marks) {
  const counts = new Map(MARKS.map((name) => [name, 0]));
  for (const mark of Object.values(marks ?? {})) {
    if (counts.has(mark)) counts.set(mark, counts.get(mark) + 1);
  }
  const parts = MARKS
    .filter((name) => counts.get(name))
    .map((name) => `${counts.get(name)} ${MARK_LABELS[name]}`);
  return parts.join(" · ");
}

export function renderMarkSummary(marks, { onClear } = {}) {
  const text = summariseMarks(marks);
  if (!text) return null;
  const bar = document.createElement("p");
  bar.className = "mark-summary";
  bar.setAttribute("data-role", "mark-summary");
  const label = document.createElement("span");
  label.textContent = text;
  const clear = document.createElement("button");
  clear.className = "mark-clear";
  clear.setAttribute("type", "button");
  clear.textContent = "clear";
  if (onClear) clear.addEventListener?.("click", onClear);
  bar.append(label, document.createTextNode(" · "), clear);
  return bar;
}

// ------------------------------------------ the fragment's two keys

/** `focus` and `mk` as they appear in `UX-211`'s query. */
export function captureFocusAndMarks(root, params) {
  const uid = focusedElement(root);
  if (uid) params.set("focus", uid);
  const marks = readMarks(root);
  const entries = Object.entries(marks);
  if (entries.length) {
    params.set("mk", entries
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([element, mark]) => `${element}:${mark}`)
      .join(","));
  }
  return params;
}

export function parseMarks(value) {
  const marks = {};
  for (const entry of String(value ?? "").split(",").filter(Boolean)) {
    const at = entry.lastIndexOf(":");
    if (at === -1) continue;
    const element = entry.slice(0, at);
    const mark = entry.slice(at + 1);
    if (element && MARKS.includes(mark)) marks[element] = mark;
  }
  return marks;
}
