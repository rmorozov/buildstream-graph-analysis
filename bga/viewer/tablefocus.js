// UX-318 (styleguide §3a): table focus, and the depth a fold announces.
//
// The field report, in three sentences that turned out to be one
// mechanism: tables nest several levels deep and "it is unknown for
// user how deep rabbit hole is"; the resource blast table "became
// scrollable, but nested doesn't work if I try to look through all
// rows"; and "a separate button to enlarge table to occupy more space".
//
// §3a answers all three at once. Depth is *announced* - a fold states
// what is behind it before any click. One nested level renders inline;
// deeper than that the fold does not open in place, it opens **here**:
// the table takes the content column's full width as a plain in-flow
// section with a breadcrumb back, and the rest of the report collapses
// behind it. The enlarge affordance enters the same state, which is why
// it is one mechanism rather than three features.
//
// **Deliberately not an overlay** - round 24 declined the element
// drawer for the same reason and the argument still stands: overlay
// machinery is the one part of this page that does not survive an
// export, a print, `filter: grayscale` or a pasted anchor. Focus is a
// section; the document underneath is unchanged.
//
// **The node is moved, not re-rendered.** A second render is a second
// answer: the table a reader expands has to be *the* table, with its
// filter, its sort and its Top-N exactly as they were left. So this
// module remembers where a node came from and puts it back.
//
// This module imports nothing. It is DOM plumbing over nodes the page
// hands it, so a guard can drive it with the shim and `app.js` can
// import it without a cycle.

/** Where a focusable node lives when it is not focused. */
const targets = new Map();

/** `UX-638`: where the reader was before focus hid the document. */
let cameFrom = null;

/** Forget every target. For a guard that renders more than one page. */
export function forgetFocusTargets() {
  targets.clear();
  cameFrom = null;
}

/** The scrolling view, or `null` under a harness that has no layout. */
function view() {
  return typeof window === "undefined" ? null : window;
}

/**
 * `UX-638`: the control says which of its two states it is in.
 *
 * The label is parked on the button, not in this module: the page can
 * rebuild a table under a registered path, and a remembered node would
 * put the label back on a button that is gone.
 */
function markControls(root, path, pressed) {
  const selector = `[data-expand="${String(path)}"]`;
  for (const button of root?.querySelectorAll?.(selector) ?? []) {
    if (pressed) {
      if (button.getAttribute("data-expand-label") === null) {
        button.setAttribute("data-expand-label", button.textContent ?? "");
        button.setAttribute("data-expand-title",
                            button.getAttribute("title") ?? "");
      }
      button.setAttribute("aria-pressed", "true");
      button.textContent = String(button.getAttribute("data-expand-label"))
        .replace(/^Expand/, "Collapse");
      button.setAttribute("title", "Close this table and go back");
      continue;
    }
    const label = button.getAttribute("data-expand-label");
    if (label !== null) {
      button.textContent = label;
      button.setAttribute("title",
                          button.getAttribute("data-expand-title") ?? "");
      button.removeAttribute?.("data-expand-label");
      button.removeAttribute?.("data-expand-title");
    }
    // Removed rather than `false`: going back restores the document
    // byte for byte, which is what this module already promises.
    button.removeAttribute?.("aria-pressed");
  }
}

/** What a `path` would open, for a guard and for `applyView`. */
export function focusTargets() {
  return [...targets.keys()];
}

/**
 * Declare that `node` can be opened full width.
 *
 * `breadcrumb` is what the way back is called - the section or table the
 * reader came from - and `label` names the thing they are looking at.
 */
export function registerFocusTarget(path, { label, breadcrumb, node }) {
  if (!path || !node) return null;
  targets.set(String(path), { label: label ?? String(path),
                              breadcrumb: breadcrumb ?? "the report",
                              node, home: null });
  return String(path);
}

/** Is `node` within `ancestor`? Walked, because the shim has no `contains`. */
function inside(node, ancestor) {
  let at = node?.parentNode;
  while (at) {
    if (at === ancestor) return true;
    at = at.parentNode;
  }
  return false;
}

export function focusedTable(root) {
  return root?.getAttribute?.("data-table-focused") || null;
}

/**
 * Open one table full width.
 *
 * Returns the path actually opened, or `null` for a path this document
 * does not have - a fragment from one run opening another run's report
 * applies what it can, which is `UX-211`'s rule.
 */
export function enterTableFocus(root, path, { onLeave } = {}) {
  const target = targets.get(String(path ?? ""));
  if (!root || !target) return null;
  if (focusedTable(root) === String(path)) return String(path);
  leaveTableFocus(root);
  // `UX-638`: read after the leave above, which restores its own, and
  // before anything is hidden - the collapse clamps the offset.
  cameFrom = view()?.scrollY ?? null;

  // Where it came back to. A marker rather than a remembered index: the
  // page can rebuild rows underneath (a preset view replaces a table)
  // and an index would put the node back in the wrong place.
  const parent = target.node.parentNode;
  if (parent) {
    const mark = document.createElement("span");
    mark.className = "focus-home";
    mark.setAttribute("data-focus-home", String(path));
    mark.hidden = true;
    parent.insertBefore(mark, target.node);
    target.home = mark;
  }

  const section = document.createElement("section");
  section.className = "table-focus";
  section.setAttribute("data-table-focus", String(path));
  // Not `data-section`: `nav.js` builds the rail from those, and a
  // transient view must not put an entry in the table of contents that
  // disappears when the reader goes back.
  const crumb = document.createElement("p");
  crumb.className = "focus-crumb";
  crumb.setAttribute("data-role", "focus-crumb");
  const back = document.createElement("button");
  back.type = "button";
  back.className = "focus-back";
  back.setAttribute("data-focus-back", String(path));
  back.title = `Close this table and go back to ${target.breadcrumb}`;
  back.textContent = `← ${target.breadcrumb}`;
  back.addEventListener("click", () => {
    leaveTableFocus(root);
    onLeave?.();
  });
  crumb.append(back);
  const heading = document.createElement("h2");
  heading.textContent = target.label;
  section.append(crumb, heading, target.node);

  root.append(section);
  root.setAttribute("data-table-focused", String(path));
  // Behind, not gone: the document keeps every section so Ctrl-F, the
  // export and a pasted anchor still find what they always found.
  //
  // Except the one that is *inside* the focus - a whole section can be
  // the thing expanded (a capped top-level table is one), and hiding it
  // would put the reader in front of an empty page.
  for (const other of root.querySelectorAll?.("section[data-section]") ?? []) {
    if (inside(other, section)) other.removeAttribute?.("data-behind-focus");
    else other.setAttribute("data-behind-focus", "true");
  }
  markControls(root, path, true);
  // `UX-638`: focus starts where the reader is looking, not wherever the
  // collapse clamped them.
  section.scrollIntoView?.();
  return String(path);
}

/** Put the table back where it was, and the report back in front. */
export function leaveTableFocus(root) {
  if (!root) return null;
  const open = focusedTable(root);
  root.removeAttribute?.("data-table-focused");
  for (const other of root.querySelectorAll?.("section[data-section]") ?? []) {
    other.removeAttribute?.("data-behind-focus");
  }
  if (!open) return null;
  markControls(root, open, false);
  const target = targets.get(open);
  if (target?.home) {
    target.home.parentNode?.insertBefore?.(target.node, target.home);
    target.home.parentNode?.removeChild?.(target.home);
    target.home = null;
  }
  const section = root.querySelector?.(`section[data-table-focus]`);
  if (section) section.parentNode?.removeChild?.(section);
  // `UX-638`: last, after the sections are back - the document has to
  // be its full height again before the offset means anything.
  if (cameFrom !== null) view()?.scrollTo?.(0, cameFrom);
  cameFrom = null;
  return null;
}

/** `UX-211`'s fragment: which table is open, if any. */
export function captureTableFocus(root, params) {
  const open = focusedTable(root);
  if (open) params.set("tf", open);
  return params;
}

export function applyTableFocus(root, params, options) {
  const want = params.get?.("tf");
  if (!want) {
    if (focusedTable(root)) leaveTableFocus(root);
    return null;
  }
  return enterTableFocus(root, want, options);
}
