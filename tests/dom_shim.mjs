// UX-264: one DOM shim, imported by every viewer harness.
//
// The viewer's guards boot the shipped ES modules in node against a
// hand-written DOM. That shim used to be copy-pasted into each test
// file - twenty-five of them - and every fidelity defect it carried
// had to be found in the page first and then fixed twenty-five times:
//
//   round 27  `prepend` implemented as `append`   -> every order guard
//             read a reversed document (`UX-235`)
//   round 32  `append` copied an already-parented node instead of
//             moving it -> a 4,000-row table read as 8,000 (`UX-262`)
//   round 33  `style: {}` swallowed every write   -> four drawings
//             refused by the page's own CSP, invisible here (`UX-263`)
//
// Each of those is a place where the instrument disagreed with a
// browser and the guards believed the instrument. So the rule for this
// file is narrow and absolute: **every behaviour here is what a real
// browser does, measured rather than assumed**, and where it cannot be
// (there is no layout engine) it does not pretend - see the bottom of
// this file for what is deliberately absent.
//
// `tests/unit/test_the_dom_shim_is_one_instrument.py` checks the
// measurable half against Chrome and censuses the harnesses that
// import this.

/** Serialised the way a browser serialises `style`: `x: v;`, space-joined. */
function styleFor(node) {
  const decls = new Map();
  const kebab = (k) => String(k).startsWith("--")
    ? String(k) : String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
  const flush = () => {
    if (decls.size === 0) { delete node.attrs.style; return; }
    node.attrs.style = [...decls].map(([k, v]) => `${k}: ${v};`).join(" ");
  };
  return new Proxy({
    setProperty(name, value) { decls.set(String(name), String(value)); flush(); },
    getPropertyValue(name) { return decls.get(String(name)) ?? ""; },
    removeProperty(name) { decls.delete(String(name)); flush(); },
  }, {
    set(_target, prop, value) {
      decls.set(kebab(prop), String(value)); flush(); return true;
    },
    get(target, prop) {
      if (prop in target) return target[prop];
      return decls.get(kebab(prop)) ?? "";
    },
  });
}

// Attributes a browser reflects into a same-named property.
const REFLECTED = {href: "href", id: "id", value: "value", title: "title"};

/** Detach `child` from whatever currently parents it. */
function unparent(child) {
  const parent = child && child._parent;
  if (!parent) return;
  const at = parent.children.indexOf(child);
  if (at !== -1) parent.children.splice(at, 1);
}

function adopt(node, item) {
  // A real DOM **moves** an already-parented node rather than copying
  // it. `applyTopN` reorders a table by re-appending its rows, and a
  // shim that copied turned 4,000 rows into 8,000 (`UX-262`).
  unparent(item);
  item._parent = node;
  item.parentElement = node;
  // Some harnesses read `parentNode` and some `parentElement`; a real
  // DOM has both and they agree for element parents.
  item.parentNode = node;
}

export function makeNode(tag) {
  const node = {
    // `nodeType` is what `app.js`'s `el()` checks to tell a node from a
    // string. Without it every child stringifies to "[object Object]".
    nodeType: 1,
    tagName: tag,
    attrs: {},
    children: [],
    listeners: {},
    dataset: {},
    _text: "",
    // A real DOM's `textContent` is the concatenation of every
    // descendant's text, and setting it replaces the children. The
    // per-file shims mostly carried a plain string, which reads the
    // same for a leaf and wrongly for anything with children.
    get textContent() {
      // No separator: measured in Chrome 141, a `<div>` holding
      // `"a"` and `<b>x</b>` reads `"ax"`. The per-file shim this
      // came from joined with a space.
      return this.children.length
        ? this._text + this.children.map((child) => child.textContent).join("")
        : this._text;
    },
    set textContent(value) {
      this._text = String(value);
      for (const child of this.children) {
        child._parent = null; child.parentElement = null; child.parentNode = null;
      }
      this.children = [];
    },
    _className: "",
    get className() { return this._className; },
    set className(value) {
      this._className = String(value);
      this.attrs.class = this._className;
    },
    hidden: false,
    // A browser reflects these *both* ways: writing the property writes
    // the content attribute. The shim reflected only attribute ->
    // property, so a node built by setting `.href` or `.value` read
    // `getAttribute(...) === null` here and the URL in a browser.
    //
    // Measured in the Chromium this repository drives (`UX-289`, which
    // is where two reads returned null against a page a browser
    // answers):
    //
    //   option.value = "Critical path"  ->  getAttribute("value")  "Critical path"
    //   a.href       = "#element-x"     ->  getAttribute("href")   "#element-x"
    //   div.id       = "an-id"          ->  getAttribute("id")     "an-id"
    //   input.value  = "typed"          ->  getAttribute("value")  null
    //
    // `<input>` is the exception and it is not an accident: its `value`
    // is the *current* value, which is why a form reset restores the
    // attribute rather than the property. `<option>` reflects. Pinning
    // both in `test_the_dom_shim_is_one_instrument.py`, because a shim
    // that reflected `<input>` too would be wrong in the other
    // direction.
    _href: "",
    get href() { return this._href; },
    set href(value) { this._href = String(value); this.attrs.href = this._href; },
    _id: "",
    get id() { return this._id; },
    set id(value) { this._id = String(value); this.attrs.id = this._id; },
    _value: "",
    get value() { return this._value; },
    set value(value) {
      this._value = String(value);
      if (this.tagName === "option") this.attrs.value = this._value;
    },
    _parent: null,
    parentElement: null,
    parentNode: null,

    get style() { return this._style ??= styleFor(this); },

    setAttribute(name, value) {
      this.attrs[name] = String(value);
      // A real DOM reflects these attributes into properties of the
      // same name, and the page sets some by attribute and reads
      // others by property. A shim that reflected neither made
      // `a.href` read `""` where a browser reads the URL.
      if (name in REFLECTED) this[REFLECTED[name]] = this.attrs[name];
    },
    getAttribute(name) { return this.attrs[name] ?? null; },
    removeAttribute(name) { delete this.attrs[name]; },
    hasAttribute(name) { return name in this.attrs; },

    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    dispatchEvent(event) {
      for (const fn of this.listeners[event?.type] ?? []) fn(event);
      return true;
    },
    removeEventListener(name, fn) {
      this.listeners[name] = (this.listeners[name] ?? []).filter((f) => f !== fn);
    },

    append(...items) {
      for (const item of items) {
        if (item === null || item === undefined) continue;
        if (typeof item === "string") { this._text += item; continue; }
        adopt(this, item);
        this.children.push(item);
      }
    },
    // A real prepend, in document order. This was `append` once, and
    // every order guard in the repository read a reversed document
    // without failing (`UX-235`).
    prepend(...items) {
      for (const item of [...items].reverse()) {
        if (item === null || item === undefined) continue;
        if (typeof item === "string") { this._text = item + this._text; continue; }
        adopt(this, item);
        this.children.unshift(item);
      }
    },
    insertBefore(item, reference) {
      adopt(this, item);
      const at = this.children.indexOf(reference);
      if (at === -1) this.children.push(item);
      else this.children.splice(at, 0, item);
      return item;
    },
    after(...items) {
      const parent = this._parent;
      if (!parent) return;
      let at = parent.children.indexOf(this);
      for (const item of items) {
        if (item === null || item === undefined) continue;
        adopt(parent, item);
        parent.children.splice(++at, 0, item);
      }
    },
    replaceChildren(...items) {
      for (const child of this.children.slice()) {
        child._parent = null;
        child.parentElement = null;
        child.parentNode = null;
      }
      this.children = [];
      this._text = "";
      this.append(...items);
    },
    remove() {
      unparent(this);
      this._parent = null; this.parentElement = null; this.parentNode = null;
    },

    matches(selector) { return matchesSelector(this, selector); },
    closest(selector) {
      let at = this;
      while (at) {
        if (matchesSelector(at, selector)) return at;
        at = at._parent;
      }
      return null;
    },
    querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; },
    querySelectorAll(selector) {
      const found = [];
      const walk = (n) => {
        for (const child of n.children ?? []) {
          if (matchesSelector(child, selector)) found.push(child);
          walk(child);
        }
      };
      walk(this);
      return found;
    },

    // Present so a page that calls them does not throw. They move
    // nothing a guard can read, and that is the point: see the note at
    // the bottom of this file.
    focus() {},
    click() { for (const fn of this.listeners.click ?? []) fn({}); },
    scrollIntoView() {},
  };
  return node;
}

/**
 * Enough of a selector engine for what the viewer and its guards use:
 * `tag`, `.class`, `#id`, `[attr]`, `[attr="value"]`, compounds of
 * those, descendant combinators (`tbody tr`), and comma-separated
 * lists. No child/sibling combinators and no pseudo-classes: the page
 * uses neither, and a half-working one would be worse than none - a
 * selector this cannot parse must not silently match nothing, so it
 * throws.
 */
function matchesSelector(node, selector) {
  for (const alternative of String(selector).split(",")) {
    if (matchesSequence(node, alternative.trim())) return true;
  }
  return false;
}

function matchesSequence(node, selector) {
  // Sibling combinators and pseudo-classes are still refused rather
  // than quietly matching nothing. The child combinator is
  // implemented: `nav.js` uses `details.map > summary` (`UX-271`), and
  // the shim told us so by throwing - which is the instrument doing
  // its job, and the message asking to be taught.
  if (/[+~]|::?[a-z-]+\(?/.test(selector)) {
    throw new Error(
      `tests/dom_shim.mjs cannot parse the selector ${JSON.stringify(selector)}`
      + " - sibling combinators and pseudo-classes are not implemented."
      + " Teach it rather than letting it quietly match nothing"
      + " (UX-264).");
  }
  // `["div", ">", "p"]` -> steps carrying whether each is a *direct*
  // child of the one before it.
  const raw = selector.replace(/\s*>\s*/g, " > ").split(/\s+/).filter(Boolean);
  const steps = [];
  for (const part of raw) {
    if (part === ">") {
      if (!steps.length) return false;
      steps[steps.length - 1].childOf = true;
      continue;
    }
    steps.push({ compound: part, childOf: false });
  }
  if (!steps.length) return false;
  const last = steps[steps.length - 1];
  if (!matchesCompound(node, last.compound)) return false;
  let at = node._parent;
  for (let i = steps.length - 2; i >= 0; i--) {
    const direct = steps[i].childOf;
    if (direct) {
      // Exactly the parent, not any ancestor.
      if (!at || !matchesCompound(at, steps[i].compound)) return false;
    } else {
      while (at && !matchesCompound(at, steps[i].compound)) at = at._parent;
      if (!at) return false;
    }
    at = at._parent;
  }
  return true;
}

function matchesCompound(node, selector) {
  const parts = String(selector).trim().match(
    /[a-zA-Z][\w-]*|\.[\w-]+|#[\w-]+|\[[^\]]+\]|\*/g) ?? [];
  if (!parts.length) return false;
  if (parts.join("") !== String(selector).trim()) {
    throw new Error(
      `tests/dom_shim.mjs cannot parse the selector ${JSON.stringify(selector)} - `
      + "teach it rather than letting it quietly match nothing");
  }
  const classes = String(node.className).split(/\s+/).filter(Boolean);
  for (const part of parts) {
    if (part.startsWith(".")) {
      if (!classes.includes(part.slice(1))) return false;
    } else if (part.startsWith("#")) {
      if ((node.id ?? "") !== part.slice(1)
          && node.attrs.id !== part.slice(1)) return false;
    } else if (part.startsWith("[")) {
      const inner = part.slice(1, -1);
      const [name, raw] = inner.split("=");
      if (raw === undefined) {
        if (!(name in node.attrs)) return false;
      } else if (node.attrs[name] !== raw.replace(/^["']|["']$/g, "")) {
        return false;
      }
    } else if (part === "*") {
      continue;
    } else if (String(node.tagName).toLowerCase() !== part.toLowerCase()) {
      return false;
    }
  }
  return true;
}

export function makeTextNode(text) {
  return { nodeType: 3, textContent: text, attrs: {}, children: [] };
}

/**
 * Install `globalThis.document`. `overrides` is merged last, so a
 * harness can keep its own `getElementById` policy - which legitimately
 * differs (some want `null`, some a fresh node, some a fixed map).
 */
export function installDocument(overrides = {}) {
  const body = makeNode("body");
  const document = {
    body,
    documentElement: makeNode("html"),
    createElement: makeNode,
    createElementNS: (_ns, tag) => makeNode(tag),
    createTextNode: makeTextNode,
    getElementById: () => null,
    querySelector: (selector) => body.querySelector(selector),
    querySelectorAll: (selector) => body.querySelectorAll(selector),
    addEventListener() {},
    ...overrides,
  };
  globalThis.document = document;
  return document;
}

// ---------------------------------------------------------------------
// What this deliberately does NOT do.
//
// There is no layout: no `getBoundingClientRect`, no box model, no
// cascade, no computed style. Every geometric claim about the viewer -
// "nothing overlaps", "the first content is above the fold", "the
// section is 2.5 screens" - is outside what any guard built on this
// file can hold, and pretending otherwise by returning zeroes would be
// worse than the absence. `UX-257` owns the instrument that can, and
// `tests/unit/test_the_page_has_geometry.py` is where those claims are
// checked against a real browser when one is present.
// ---------------------------------------------------------------------
