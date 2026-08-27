// UX-340: a module written to break the wrong instrument.
//
// Not loaded by the viewer and not part of the page. It exists so the
// guard beside it can show a *difference* rather than assert a number.
// Every trap below is one the regex stripper walked into while deriving
// `UX-337`'s split, and the crossing count it produced was **cleaner**
// than the truth because of them.
//
// The shape that matters is two template literals with an ordinary
// function between them. A pattern written to skip `${…}` matches
// neither template, so the first one's closing backtick pairs with the
// second one's opening backtick and everything between disappears —
// which on `app.js` was 87% of the file, and here is `gamma` whole.
//
// `alpha` is named in this comment and called nowhere.

export const LABEL = "rows";
export const HIDDEN = 3;

export function alpha() {
  return "alpha";
}

export function render(value) {
  return String(value);
}

export function beta(rows) {
  return `${rows.length} counted`;
}

export function gamma(render) {
  // `render` here is this function's parameter. The top-level `render`
  // above is a different thing, and counting this as an edge is the
  // false crossing UX-337 had to spot by reading.
  const url = "https://example.invalid/x";   // `//` inside a string
  return render(url) + LABEL + HIDDEN;
}

/**
 * The second template. This block of prose sits *above* the
 * declaration, which is where a seam is: a carver that cuts at the
 * declaration line leaves it attached to `gamma`, and a move then
 * reads as a rewrite.
 */
export function delta(name) {
  return `<${name}>`;
}
