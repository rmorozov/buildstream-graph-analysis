// UX-211: a link that shows what I was looking at.
//
// `nav.js` sells the section ids as something that "can be pasted into
// an issue", and the promise stopped at the anchor: the filter that cut
// 1,202 rows to nine, the `> 5s` threshold, the sort, the Top-10, the
// sections the reader collapsed - all of it lived in DOM state and
// `localStorage`, so the pasted `#floors` opened the unfiltered wall
// for whoever clicked it.
//
// `localStorage` is the wrong channel for this and stays where it
// belongs: it remembers for *me*, on *this browser*, and an exported
// report opened from `file://` may get no storage at all. The fragment
// travels with the link, needs no server, and works from a downloaded
// file. So: **the hash wins where it speaks, storage remains the
// default where it is silent.**
//
// Nothing here reads or writes analysis. Every value is a control's own
// value, captured from the DOM and put back into it.

// The anchor and the state share the fragment, separated by a `~` - a
// character no section key contains. `#floors` keeps meaning exactly
// what it meant, so every link already pasted into an issue still
// works, and the browser's own scroll-to-id still fires for it.
export const SEPARATOR = "~";

// UX-222 and UX-225 are view state too, and the same rule applies: the
// fragment carries them, so "here is the report, focused on the element
// I want you to look at" and "here is where I got to" are both links.
import { applyFocus, applyMarks, captureFocusAndMarks, clearFocus,
         parseMarks } from "./focus.js";

export function splitHash(hash = "") {
  const text = String(hash).replace(/^#/, "");
  const at = text.indexOf(SEPARATOR);
  if (at === -1) return { anchor: text, query: "" };
  return { anchor: text.slice(0, at), query: text.slice(at + 1) };
}

export function joinHash(anchor, query) {
  if (!query) return anchor ? `#${anchor}` : "";
  return `#${anchor ?? ""}${SEPARATOR}${query}`;
}

/**
 * The view, read off the document.
 *
 * Keys are short because they end up in a URL somebody pastes: `c` for
 * the collapsed set, then one entry per table for its filter (`f.`),
 * per-column thresholds (`t.`), sort (`s.`) and preset (`n.`), and `o`
 * for the disclosures a reader opened.
 */
export function captureView(root) {
  const params = new URLSearchParams();
  const sections = [...(root.querySelectorAll?.("section[data-section]") ?? [])];

  const collapsed = sections
    .filter((s) => s.getAttribute("data-collapsed") === "true")
    .map((s) => s.getAttribute("data-section"));
  if (collapsed.length) params.set("c", collapsed.join(","));

  for (const table of root.querySelectorAll?.("table[data-table]") ?? []) {
    const key = table.getAttribute("data-table");
    const tools = table.parentNode?.querySelector?.(".table-tools");
    const filter = tools?.querySelector?.("input.table-filter");
    if (filter?.value) params.set(`f.${key}`, filter.value);
    for (const input of table.querySelectorAll?.("input.th-filter") ?? []) {
      if (input.value) {
        params.set(`t.${key}.${input.getAttribute("data-column")}`, input.value);
      }
    }
    const preset = tools?.querySelector?.("select.top-n");
    if (preset?.value) params.set(`n.${key}`, preset.value);
    for (const th of table.querySelectorAll?.("th") ?? []) {
      const sorted = th.getAttribute("aria-sort");
      if (sorted) params.set(`s.${key}`, `${th.getAttribute("data-column")}:${sorted}`);
    }
  }

  const open = [...(root.querySelectorAll?.("details[data-fold]") ?? [])]
    .filter((node) => node.open)
    .map((node) => node.getAttribute("data-fold"));
  if (open.length) params.set("o", open.join(","));

  captureFocusAndMarks(root, params);

  // Once the view says anything, it says what is collapsed - including
  // "nothing". Without this, a reader who expanded everything and then
  // filtered would hand over a link whose collapse set was silent, and
  // silence means "use your own storage": the recipient would open the
  // filtered table inside the sections *they* had collapsed.
  if ([...params.keys()].length && !params.has("c")) params.set("c", "");

  return params.toString();
}

/**
 * Put a captured view back.
 *
 * Every control is driven the way a reader would drive it - set the
 * value, dispatch the event the control already listens for - so there
 * is no second code path that can disagree with the first. A key that
 * names something this document does not have is dropped in silence:
 * a hash from one run opening another run's report applies what it can,
 * which is what the item asks for.
 */
export function applyView(root, query, { dispatch } = {}) {
  const params = new URLSearchParams(query ?? "");
  const fire = dispatch ?? ((node, name) => {
    if (typeof node.dispatchEvent !== "function") return;
    node.dispatchEvent(new Event(name, { bubbles: true }));
  });
  const applied = [];

  // `c` is authoritative only when the fragment carries it. A hash-free
  // load - and a hash that says nothing about collapse - leaves the
  // reader's own remembered state exactly as it was, which is the whole
  // "the hash wins where it speaks" rule.
  if (params.has("c")) {
    const collapsed = new Set((params.get("c") ?? "").split(",").filter(Boolean));
    for (const section of root.querySelectorAll?.("section[data-section]") ?? []) {
      const key = section.getAttribute("data-section");
      const shut = collapsed.has(key);
      const button = section.querySelector?.("button[data-collapse]");
      const isShut = section.getAttribute("data-collapsed") === "true";
      if (button && shut !== isShut) { fire(button, "click"); applied.push(`c:${key}`); }
    }
  }

  for (const table of root.querySelectorAll?.("table[data-table]") ?? []) {
    const key = table.getAttribute("data-table");
    const tools = table.parentNode?.querySelector?.(".table-tools");
    const filter = params.get(`f.${key}`);
    const box = tools?.querySelector?.("input.table-filter");
    if (filter && box) { box.value = filter; fire(box, "input"); applied.push(`f:${key}`); }
    for (const input of table.querySelectorAll?.("input.th-filter") ?? []) {
      const value = params.get(`t.${key}.${input.getAttribute("data-column")}`);
      if (value) { input.value = value; fire(input, "input"); applied.push(`t:${key}`); }
    }
    const sort = params.get(`s.${key}`);
    if (sort) {
      const [column, direction] = sort.split(":");
      for (const th of table.querySelectorAll?.("th") ?? []) {
        if (th.getAttribute("data-column") !== column) continue;
        // One click sorts ascending; a second reverses it. Driving the
        // control rather than setting `aria-sort` directly is what keeps
        // the rows in the order the attribute claims.
        fire(th, "click");
        if (th.getAttribute("aria-sort") !== direction) fire(th, "click");
        applied.push(`s:${key}`);
      }
    }
    const preset = params.get(`n.${key}`);
    const select = tools?.querySelector?.("select.top-n");
    if (preset && select) {
      select.value = preset;
      fire(select, "change");
      applied.push(`n:${key}`);
    }
  }

  const open = new Set((params.get("o") ?? "").split(",").filter(Boolean));
  for (const node of root.querySelectorAll?.("details[data-fold]") ?? []) {
    if (open.has(node.getAttribute("data-fold"))) {
      node.open = true;
      applied.push(`o:${node.getAttribute("data-fold")}`);
    }
  }

  // The marks first, then the focus: focus dims by element and the
  // marks annotate by element, and applying them the other way round
  // would have the dimming pass walk a document the marks then change.
  if (params.has("mk")) {
    applyMarks(root, parseMarks(params.get("mk")));
    applied.push("mk");
  }
  if (params.has("focus")) {
    const uid = params.get("focus");
    if (uid) { applyFocus(root, uid); applied.push(`focus:${uid}`); }
    else { clearFocus(root); }
  }
  return applied;
}

/**
 * Keep the fragment in step with the document.
 *
 * Every control this touches already fires an event; one delegated
 * listener at the root writes the hash after it. `replaceState` rather
 * than assigning `location.hash`, so investigating a report does not
 * fill the back button with twenty entries - and a plain assignment as
 * the fallback where there is no history object (an export opened as a
 * bare file in some browsers).
 */
export function wireViewState(root, { location: where, history: past } = {}) {
  const write = () => {
    const query = captureView(root);
    const { anchor } = splitHash(where?.hash ?? "");
    const next = joinHash(anchor, query);
    if ((where?.hash ?? "") === next) return next;
    if (past?.replaceState) past.replaceState(null, "", next || " ");
    else if (where) where.hash = next;
    return next;
  };
  for (const name of ["input", "change", "click", "toggle"]) {
    root.addEventListener?.(name, write);
  }
  return write;
}

/** The link to hand somebody: this document, at this view. */
export function viewLink(root, where) {
  const base = String(where?.href ?? "").split("#")[0];
  const { anchor } = splitHash(where?.hash ?? "");
  return base + joinHash(anchor, captureView(root));
}
