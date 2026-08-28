// UX-303 (styleguide §2): a value that *is* a shape renders as its
// shape first and its numbers second.
//
// Two drawings live here, and the file imports nothing so that either
// can be driven by a guard with no DOM but the shim and no formatter
// but a stub. Formatting is **injected**: the quantity table lives in
// `app.js`, and a drawing that reached for it would make this module
// depend on the page it is drawn on.
//
// What §2 asks of both, and what the code owes:
//
//   - **geometry from the scale, no axes, no grid.** §2 said "fixed
//     small geometry"; `UX-316` split that into §2a's two grades after
//     the field pass found one size doing two jobs. An *annotation* is
//     the word-sized picture §2 described - beside a table cell, a
//     legend away from being a chart §6 would rather have as a
//     sentence. An *exhibit* is the section's whole answer: container
//     width, the scale's taller box, tick labels, and its table twin.
//     Both come from `SCALE`; neither invents a number.
//   - **one sentence beside it, from published values only.** The
//     drawing says the shape; the sentence says what the shape means,
//     in numbers the payload actually carries.
//   - **fewer than three points is a sentence, not a drawing**
//     (`UX-226`'s rule, now global). Two points joined by a line make
//     a claim about a trend that two points cannot support.
//   - **`n` is always printed beside a distribution.** A strip without
//     its population is a picture of an opinion.
//
// And the boundary that decides what a *self-built* strip may say. A
// strip built from a table column's own `data-raw` values is a reading
// of published values, like sorting - allowed. But it **prints no
// derived number**: its labels are actual row values (the smallest and
// largest rows are rows), and the percentile ticks are geometry only.
// The moment a derived percentile deserves printing it enters the
// payload first, and `strip()` draws it from there.

/** Below this a series is a sentence. Mirrors `schemas.SERIES_MIN_POINTS`. */
export const SERIES_MIN_POINTS = 3;

// UX-316 (styleguide §2a): **two grades, and no third size.**
//
// One geometry used to serve both jobs, and the field pass measured
// what that costs: the blast-radius distribution, the element-duration
// distribution and the graph shape all drew at 20 viewBox units
// because that is what a sparkline beside a table cell wants, and all
// three are the answer their section exists to give. "Very small and I
// don't see anything there" is a size complaint about a drawing that
// was never sized for the job it was doing.
//
// The grade is an **argument**, never a guess from the data (§2a's last
// rule): the renderer knows whether the drawing is the section's
// answer or a mark beside something else, and the data cannot know it.
// Passing neither is an error rather than a default, so a new call site
// has to decide - which is the whole mechanism, because the defect was
// a call site that never chose.
export const GRADE_ANNOTATION = "annotation";
export const GRADE_EXHIBIT = "exhibit";

/**
 * The size scale, in viewBox units.
 *
 * The *rendered* size is CSS (`--draw-*` in `style.css`) - an exhibit
 * takes its container's width, which no constant here can express. What
 * lives here is the drawing's internal coordinate space, and it is a
 * scale rather than a set of per-drawing numbers: a guard holds every
 * drawing in the viewer to it, and the constant that hid in `views.js`
 * (`viewBox: "0 0 100 20"`, written out by hand) is what that guard
 * exists to catch.
 */
export const SCALE = Object.freeze({
  [GRADE_ANNOTATION]: Object.freeze({ width: 100, spark: 20, strip: 8 }),
  // Three times the height, and the room is spent on the same marks
  // drawn further apart rather than on new ones: §2a asks for a size a
  // reader can see, not for a chart with apparatus (§2 still forbids
  // grids and legends). Tick *labels* are the one addition, and they
  // are HTML beside the drawing rather than SVG text - the drawings
  // stretch with `preserveAspectRatio="none"`, which would stretch
  // their letters with them.
  //
  // `figure` is the third **kind**, not a third grade: a composed
  // drawing with lanes (the compare band's strip, extent and marker
  // stacked) is a different shape from a line over an order, the same
  // way a strip is. §2a's "no third size" governs the grades - a
  // drawing is annotation or exhibit and nothing else - and within a
  // grade every height still comes from here rather than from a `const
  // H` beside the drawing, which is the constant this replaces.
  [GRADE_EXHIBIT]: Object.freeze({ width: 100, spark: 60, strip: 26,
                                   figure: 74 }),
});

function scaleFor(grade) {
  const found = SCALE[grade];
  if (!found) {
    throw new Error(
      `bga: a drawing must declare its grade (styleguide §2a): `
      + `"${GRADE_ANNOTATION}" or "${GRADE_EXHIBIT}", got "${String(grade)}"`);
  }
  return found;
}

/** The annotation box, kept as named constants for the §2 geometry guards. */
export const SPARK_WIDTH = SCALE[GRADE_ANNOTATION].width;
export const SPARK_HEIGHT = SCALE[GRADE_ANNOTATION].spark;
export const STRIP_HEIGHT = SCALE[GRADE_ANNOTATION].strip;

const SVG_NS = "http://www.w3.org/2000/svg";

function make(doc, tag, attrs = {}, ...children) {
  const node = doc.createElementNS
    ? doc.createElementNS(SVG_NS, tag) : doc.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(name, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

function box(doc, tag, attrs = {}, ...children) {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (name === "class") node.className = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(child);
  }
  return node;
}

const numeric = (v) => typeof v === "number" && Number.isFinite(v);

// UX-316: an exhibit's tick labels, and its table twin.
//
// Both are HTML rather than SVG, and both are exhibit-only. §2 forbids
// axes and grids on an annotation because a word-sized picture that
// needs a legend is a chart in the wrong place; an exhibit *is* the
// chart, so its extremes get read rather than hovered.

/**
 * A row of labels under an exhibit, each at the fraction its value sits
 * at. Percent positions, because the drawing above stretches to its
 * container and a viewBox unit is not a pixel.
 */
/**
 * `UX-350`: two marks at one position are one label.
 *
 * On an eleven-element population the 95th percentile **is** the
 * largest value, and the axis printed both at the same offset:
 *
 * ```text
 * 0 ms (min)      3.1 s (p50)                    19.1 s19.1 s (p95)
 *                                                      max
 * ```
 *
 * The sparkline had it too, and on the *smaller* fixture: `golden`'s
 * width series peaks at level 1, so `first` and `peak` shared an
 * offset and their labels overlapped by 42 px. A small `n` is the
 * first run a new reader has, so this is the case the page has to
 * handle rather than the exotic one - which is why the merge lives
 * here, over every exhibit axis, rather than in the strip that
 * happened to be measured first.
 *
 * Which marks landed together is the interesting part, so the merged
 * label names them: identical labels become `19.1 s (p95, max)`, and
 * different ones `level 1 (peak 2)`.
 */
function mergeTicks(ticks) {
  const out = [];
  for (const tick of ticks) {
    if (!tick) continue;
    const at = Number(tick.at.toFixed(2));
    const already = out.find((seen) => Number(seen.at.toFixed(2)) === at);
    if (!already) {
      out.push({ ...tick, names: [tick.name], labels: [tick.label] });
      continue;
    }
    already.names.push(tick.name);
    already.labels.push(tick.label);
  }
  return out.map((tick) => {
    if (tick.names.length === 1) return tick;
    const same = tick.labels.every((one) => one === tick.labels[0]);
    const rest = same
      ? tick.names.slice(1).join(", ")
      : tick.names.slice(1).map((name, i) => `${name} ${tick.labels[i + 1]}`)
                  .join(", ");
    return { ...tick, name: tick.names.join(" "),
             label: `${tick.labels[0]} (${same ? tick.names.join(", ") : rest})` };
  });
}

export function exhibitAxis(doc, ticks) {
  const row = box(doc, "div", { class: "draw-axis", "data-role": "draw-axis" });
  for (const tick of mergeTicks(ticks)) {
    if (!tick) continue;
    const at = tick.at.toFixed(2);
    const label = box(doc, "span", {
      class: "draw-tick", "data-mark": tick.name, "data-at": at,
    }, tick.label);
    // `left` is a position, not a colour or a size (§4.5's tokens
    // govern those); a per-mark percentage cannot be a class.
    //
    // UX-334: through the CSSOM, never `style: ...`, which `box` would
    // set as an *attribute*. The server sends `default-src 'self'` with
    // no `style-src`, so a style attribute is inline style and Chrome
    // **refuses to apply it** - measured at 11 `style-src-attr`
    // violations per macro-page boot, with every tick computing
    // `left: 0px` and piling at the exhibit's left edge on served
    // pages. The export has no CSP, so it looked right there and the
    // served page was the broken one. `UX-263` learned this in
    // `views.js:566` and this module reintroduced it; a property
    // assignment is not inline style and is not subject to the policy.
    if (label.style) label.style.left = `${at}%`;
    row.append(label);
  }
  return row;
}

/**
 * The table twin §2a requires of every exhibit.
 *
 * "The drawing never hoards data a reader wants as rows" - so the twin
 * renders **the same published values the drawing was handed**, and
 * nothing else. It is built here rather than through `app.js`'s table
 * machinery for the reason this module states at the top: a drawing
 * that reached for the page it is drawn on could not be driven by a
 * guard with no page. Sorting and filtering are absent on purpose - a
 * twin is four to twelve rows, and §3's machinery is for the tables
 * that need it.
 */
export function exhibitTwin(doc, headers, rows) {
  const wrap = box(doc, "div", { class: "draw-twin" });
  const table = box(doc, "table", { class: "twin-table",
                                    "data-role": "drawing-twin" });
  const head = box(doc, "tr");
  for (const name of headers) head.append(box(doc, "th", {}, name));
  table.append(box(doc, "thead", {}, head));
  const body = box(doc, "tbody");
  for (const cells of rows) {
    const tr = box(doc, "tr");
    for (const cell of cells) tr.append(box(doc, "td", {}, String(cell)));
    body.append(tr);
  }
  table.append(body);
  table.hidden = true;
  const button = box(doc, "button", {
    type: "button", class: "twin-toggle", "data-drawing-twin": "closed",
    // `UX-279`'s rule: a control says what it does before it is
    // pressed, and it says it in a title a reader can reach.
    title: "Show the values this drawing was made from, as a table",
  }, "as table");
  button.addEventListener("click", () => {
    const open = button.getAttribute("data-drawing-twin") === "open";
    button.setAttribute("data-drawing-twin", open ? "closed" : "open");
    button.textContent = open ? "as table" : "as drawing";
    table.hidden = open;
  });
  wrap.append(button);
  wrap.append(table);
  return wrap;
}

/**
 * An ordered numeric series as a sparkline plus its one sentence.
 *
 * `unit` is what one step along the order *is*, and it comes from the
 * schema's `bga:series` value - the sentence has to name it and a
 * viewer must not invent one.
 */
export function sparkline(values, {
  unit = "step", format = String, doc = document, label = null,
  grade = undefined,
} = {}) {
  const size = scaleFor(grade);
  const points = (values ?? []).filter(numeric);
  const wrap = box(doc, "div", {
    class: grade === GRADE_EXHIBIT ? "series exhibit" : "series",
    "data-role": "series", "data-grade": grade,
    "data-points": String(points.length),
    "data-unit": unit,
  });
  if (label) {
    wrap.append(box(doc, "span", { class: "series-label" }, label));
  }
  if (!points.length) {
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "series-sentence muted",
                                   "data-role": "series-sentence" },
                    `No ${unit} values recorded.`));
    return wrap;
  }
  if (points.length < SERIES_MIN_POINTS) {
    // The `UX-226` rule, global: state it, do not draw it.
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "series-sentence",
                                   "data-role": "series-sentence" },
                    points.length === 1
                      ? `${format(points[0])} at one ${unit}.`
                      : `${format(points[0])} → `
                        + `${format(points[points.length - 1])}`
                        + `, over ${points.length} ${unit}s — too few to`
                        + ` draw a trend.`));
    return wrap;
  }

  wrap.setAttribute("data-drawn", "true");
  const high = Math.max(...points);
  const low = Math.min(...points);
  const span = high - low;
  const x = (i) => (i / (points.length - 1)) * size.width;
  // Flat series sit on the middle line rather than on the floor: a
  // series of identical values is not "all at zero".
  //
  // The inset is a tenth of the height at either grade rather than the
  // two units it was written as, so an exhibit's line is not pinned to
  // its edges - the same drawing, scaled, which is what §2a's "one
  // scale" means.
  const inset = size.spark / 10;
  const y = (v) => span === 0
    ? size.spark / 2
    : (size.spark - inset) - ((v - low) / span) * (size.spark - inset * 2);

  const line = make(doc, "svg", {
    viewBox: `0 0 ${size.width} ${size.spark}`,
    class: "sparkline", preserveAspectRatio: "none",
    role: "img", "data-role": "sparkline",
    // The published values, so a guard asserts the geometry against
    // what was drawn rather than against a second computation of it
    // (`UX-213`'s lesson, applied at birth).
    "data-values": points.join(","),
  });
  line.append(make(doc, "polyline", {
    class: "spark-line", fill: "none",
    points: points.map((v, i) => `${x(i).toFixed(2)},${y(v).toFixed(2)}`)
                  .join(" "),
  }));
  // The endpoints and the extremum, which are the three the reader
  // hovers. Nothing else is marked: a dot per point turns a sparkline
  // into a scatter plot.
  const peak = points.indexOf(high);
  for (const [at, role] of [[0, "first"], [points.length - 1, "last"],
                            [peak, "peak"]]) {
    line.append(make(doc, "circle", {
      cx: x(at).toFixed(2), cy: y(points[at]).toFixed(2),
      r: (1.6 * size.spark / SPARK_HEIGHT).toFixed(2),
      class: "spark-point", "data-mark": role,
      "data-value": String(points[at]), "data-at": String(at),
    }));
  }
  wrap.append(line);
  if (grade === GRADE_EXHIBIT) {
    wrap.append(exhibitAxis(doc, [
      { name: "first", at: 0, label: `${unit} 1` },
      { name: "peak", at: (peak / (points.length - 1)) * 100,
        label: format(high) },
      { name: "last", at: 100, label: `${unit} ${points.length}` },
    ]));
  }
  wrap.append(box(doc, "span", { class: "series-sentence",
                                 "data-role": "series-sentence" },
                  `${points.length} ${unit}s, ${format(points[0])} → `
                  + `${format(points[points.length - 1])}`
                  + `, peak ${format(high)} at ${unit} ${peak + 1}.`));
  if (grade === GRADE_EXHIBIT) {
    wrap.append(exhibitTwin(doc, [unit, "value"],
                     points.map((v, i) => [i + 1, format(v)])));
  }
  return wrap;
}

/**
 * Which keys a published distribution keeps its marks in.
 *
 * Two shapes publish one in this repository - `store-aggregate/v1`'s
 * `{samples, min, median, p95, max}` and `analyze/v2`'s
 * `{n, min, max, deciles: {p50…}, p95}` - and the `bga:distribution`
 * hint names where *this* one counts, which is the only thing the two
 * disagree on that a reader would notice.
 */
export function marksOf(distribution, countKey = "n") {
  if (!distribution || typeof distribution !== "object") return null;
  const deciles = distribution.deciles ?? {};
  const median = numeric(distribution.median) ? distribution.median
    : numeric(deciles.p50) ? deciles.p50 : null;
  const marks = {
    n: numeric(distribution[countKey]) ? distribution[countKey] : null,
    min: numeric(distribution.min) ? distribution.min : null,
    p50: median,
    p95: numeric(distribution.p95) ? distribution.p95 : null,
    max: numeric(distribution.max) ? distribution.max : null,
  };
  if (marks.min === null || marks.max === null) return null;
  return marks;
}

function stripSvg(doc, marks, { printed, size }) {
  const span = marks.max - marks.min;
  const at = (v) => span === 0 ? 50 : ((v - marks.min) / span) * 100;
  const strip = make(doc, "svg", {
    viewBox: `0 0 ${size.width} ${size.strip}`, class: "density-strip",
    preserveAspectRatio: "none", role: "img", "data-role": "density-strip",
    "data-min": String(marks.min), "data-max": String(marks.max),
    "data-p50": marks.p50 === null ? "" : String(marks.p50),
    "data-p95": marks.p95 === null ? "" : String(marks.p95),
    // Whether the numbers beside it were published or read off the
    // rows. A self-built strip prints no derived number, and this is
    // what lets a guard tell the two apart on the page.
    "data-printed": printed,
  });
  // The range bar is an eighth of the strip's height at either grade,
  // centred - the same drawing, scaled (§2a).
  const bar = size.strip / 4;
  strip.append(make(doc, "rect", {
    class: "density-range", x: "0", y: String(size.strip / 2 - bar / 2),
    width: "100", height: String(bar),
  }));
  for (const [name, value] of [["p50", marks.p50], ["p95", marks.p95]]) {
    if (value === null) continue;
    strip.append(make(doc, "line", {
      class: `density-tick density-${name}`,
      x1: at(value).toFixed(2), x2: at(value).toFixed(2),
      y1: "0", y2: String(size.strip),
      "data-mark": name, "data-value": String(value),
    }));
  }
  for (const [name, value] of [["min", marks.min], ["max", marks.max]]) {
    strip.append(make(doc, "line", {
      class: "density-end", x1: at(value).toFixed(2), x2: at(value).toFixed(2),
      y1: String(size.strip / 8), y2: String(size.strip - size.strip / 8),
      "data-mark": name, "data-value": String(value),
    }));
  }
  return strip;
}

/**
 * A **published** distribution as a density strip: min → p50 → p95 →
 * max, with `n` printed beside it.
 *
 * Every number this prints came out of the payload, so it prints them
 * all.
 */
export function strip(distribution, {
  countKey = "n", format = String, doc = document, label = null,
  grade = undefined,
} = {}) {
  const size = scaleFor(grade);
  const marks = marksOf(distribution, countKey);
  const wrap = box(doc, "div", {
    class: grade === GRADE_EXHIBIT ? "density exhibit" : "density",
    "data-role": "density", "data-grade": grade });
  if (label) wrap.append(box(doc, "span", { class: "density-label" }, label));
  if (!marks) {
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence muted",
                                   "data-role": "density-sentence" },
                    "No distribution published for this population."));
    return wrap;
  }
  // `UX-350`: the `UX-226` rule reaches the published strip too. It
  // was global for a *series* and enforced in `sparkline` and in
  // `columnStrip`, and a payload's own distribution walked past it -
  // so a two-element build drew a range bar and two ticks over a
  // population that cannot have a shape. The sentence still prints
  // every number the payload published; only the drawing goes.
  if (marks.n !== null && marks.n < SERIES_MIN_POINTS) {
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence",
                                   "data-role": "density-sentence" },
                    `${format(marks.min)} → ${format(marks.max)}`
                    + ` over ${marks.n} value${marks.n === 1 ? "" : "s"}`
                    + " — too few to have a shape."));
    return wrap;
  }
  wrap.setAttribute("data-drawn", "true");
  wrap.setAttribute("data-n", marks.n === null ? "" : String(marks.n));
  wrap.append(stripSvg(doc, marks, { printed: "published", size }));
  const parts = [`${format(marks.min)} → ${format(marks.max)}`];
  if (marks.p50 !== null) parts.push(`median ${format(marks.p50)}`);
  if (marks.p95 !== null) parts.push(`p95 ${format(marks.p95)}`);
  if (grade === GRADE_EXHIBIT) wrap.append(exhibitAxis(doc, stripTicks(marks, format)));
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  `${parts.join(", ")}`
                  + (marks.n === null ? "." : ` — n=${marks.n}.`)));
  if (grade === GRADE_EXHIBIT) {
    wrap.append(exhibitTwin(doc, ["mark", "value"], [
      ["min", format(marks.min)],
      ...(marks.p50 === null ? [] : [["median", format(marks.p50)]]),
      ...(marks.p95 === null ? [] : [["p95", format(marks.p95)]]),
      ["max", format(marks.max)],
      ...(marks.n === null ? [] : [["n", String(marks.n)]]),
    ]));
  }
  return wrap;
}

/** Where an exhibit strip's four marks sit, as percentages. */
function stripTicks(marks, format) {
  const span = marks.max - marks.min;
  const at = (v) => span === 0 ? 50 : ((v - marks.min) / span) * 100;
  return [
    { name: "min", at: at(marks.min), label: format(marks.min) },
    marks.p50 === null ? null
      : { name: "p50", at: at(marks.p50), label: format(marks.p50) },
    marks.p95 === null ? null
      : { name: "p95", at: at(marks.p95), label: format(marks.p95) },
    { name: "max", at: at(marks.max), label: format(marks.max) },
  ];
}

/**
 * A strip built from a table column's own `data-raw` values.
 *
 * §2's boundary, and the whole reason this is a second function rather
 * than a flag: **it prints no derived number.** The smallest and
 * largest values are *rows*, so they may be named; `n` is a count of
 * rows, so it may be named; the p50 and p95 ticks are positions and
 * nothing else. A percentile worth printing enters the payload first
 * and comes back through `strip()`.
 */
/**
 * `UX-361` (styleguide §2d): a published total, split into its
 * published parts.
 *
 * The third shape, and the argument for a third shape at all: a strip
 * shows a **distribution** and a sparkline shows an **ordered series**,
 * and neither can show a total decomposed. `floors` is the tool's
 * central claim - how much of this build is irreducible and how much
 * is yours to take - and it rendered as eleven labelled durations in a
 * definition list, on both fixtures, with the subtraction left to the
 * reader.
 *
 * **Every segment is a published field and so is the total.** The page
 * does not compute a remainder, does not scale to a maximum it chose,
 * and does not decide what the parts are - `parts` arrive named and
 * measured, and Direction 7's rule is why: a viewer that worked out
 * what was left over would be a second analyzer.
 *
 * A `mark` is an optional published bound drawn as a rule across the
 * bar - `t_infinity_observed` over a wall clock, which is the shape of
 * "this much of it could not have been shorter".
 */
export function decomposition(parts, {
  total = null, format = String, doc = document, label = null,
  grade = undefined, mark = null,
} = {}) {
  const size = scaleFor(grade);
  const wrap = box(doc, "div", {
    class: grade === GRADE_EXHIBIT ? "decomposition exhibit" : "decomposition",
    "data-role": "decomposition", "data-grade": grade });
  if (label) wrap.append(box(doc, "span", { class: "density-label" }, label));

  const named = (parts ?? []).filter(
    (part) => part && Number.isFinite(Number(part.value)));
  const whole = Number(total);
  if (!named.length || !Number.isFinite(whole) || whole <= 0) {
    // `UX-226`'s floor, in this shape's own terms: with no total there
    // is nothing to be a share *of*, and a bar scaled to its own parts
    // would be a picture of an opinion.
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence muted",
                                   "data-role": "density-sentence" },
                    "No total published for this split, so there is "
                    + "nothing to draw the parts against."));
    return wrap;
  }
  wrap.setAttribute("data-drawn", "true");
  wrap.setAttribute("data-total", String(whole));

  const drawing = make(doc, "svg", {
    viewBox: `0 0 ${size.width} ${size.strip}`,
    preserveAspectRatio: "none", class: "draw decomposition-bar",
    role: "img", "aria-label": `${format(whole)} split into `
      + named.map((part) => part.label).join(", "),
  });
  let at = 0;
  for (const part of named) {
    const width = (Number(part.value) / whole) * size.width;
    drawing.append(make(doc, "rect", {
      x: at.toFixed(3), y: "0", width: Math.max(width, 0).toFixed(3),
      height: String(size.strip), class: `decomposition-part part-${part.key}`,
      "data-part": part.key, "data-raw": String(part.value),
    }));
    at += width;
  }
  if (mark && Number.isFinite(Number(mark.value))) {
    const x = (Number(mark.value) / whole) * size.width;
    drawing.append(make(doc, "line", {
      x1: x.toFixed(3), x2: x.toFixed(3), y1: "0", y2: String(size.strip),
      class: "decomposition-mark", "data-mark": mark.key,
      "data-raw": String(mark.value),
    }));
  }
  wrap.append(drawing);

  const ticks = named.map((part, index) => ({
    name: part.key, label: `${part.label} ${format(part.value)}`,
    at: (named.slice(0, index).reduce(
      (sum, before) => sum + Number(before.value), 0) / whole) * 100,
  }));
  wrap.append(exhibitAxis(doc, ticks));
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  `${format(whole)} in total: `
                  + named.map((part) => `${format(part.value)} ${part.label}`)
                    .join(", ")
                  + (mark ? `. ${mark.label} ${format(mark.value)}.` : ".")));
  // §2a: the exhibit never hoards data a reader wants as rows.
  if (grade === GRADE_EXHIBIT) {
    wrap.append(exhibitTwin(doc, ["Part", "Value"],
                            named.map((part) => [part.label,
                                                 format(part.value)])));
  }
  return wrap;
}

/**
 * `UX-361` (styleguide §2d): published values on one axis, against a
 * published threshold.
 *
 * The fourth shape, and the same argument: `confidence` publishes a
 * headline score and five component scores, all in 0..1, and rendered
 * as 28 numbers over 561 px on both fixtures. What a reader wants is
 * whether they agree and where the weak one is - a comparison neither
 * a strip nor a sparkline can make, because these are not a sample of
 * one population and not an order.
 *
 * `marks` are published `(key, label, value)` and `threshold` is a
 * published value or `null`. The axis is `low`..`high`, published or
 * defaulted to 0..1 for a share - the page picks no bounds of its own
 * from the data, so a mark cannot move because another one did.
 */
export function interval(marks, {
  low = 0, high = 1, threshold = null, thresholdLabel = "line",
  format = String, doc = document, label = null, grade = undefined,
} = {}) {
  const size = scaleFor(grade);
  const wrap = box(doc, "div", {
    class: grade === GRADE_EXHIBIT ? "interval exhibit" : "interval",
    "data-role": "interval", "data-grade": grade });
  if (label) wrap.append(box(doc, "span", { class: "density-label" }, label));

  const named = (marks ?? []).filter(
    (one) => one && Number.isFinite(Number(one.value)));
  const span = Number(high) - Number(low);
  if (named.length < 2 || !Number.isFinite(span) || span <= 0) {
    // One value on an axis is a value, not a comparison. `UX-226`'s
    // floor again: below two marks the sentence says what the numbers
    // are and the drawing goes.
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence muted",
                                   "data-role": "density-sentence" },
                    named.length
                      ? named.map((one) => `${one.label} ${format(one.value)}`)
                        .join(", ") + " — one value is not a comparison."
                      : "No comparable values published here."));
    return wrap;
  }
  wrap.setAttribute("data-drawn", "true");
  wrap.setAttribute("data-n", String(named.length));

  const place = (value) => ((Number(value) - Number(low)) / span) * size.width;
  const drawing = make(doc, "svg", {
    viewBox: `0 0 ${size.width} ${size.strip}`,
    preserveAspectRatio: "none", class: "draw interval-axis",
    role: "img", "aria-label": named.map(
      (one) => `${one.label} ${format(one.value)}`).join(", "),
  });
  drawing.append(make(doc, "line", {
    x1: "0", x2: String(size.width),
    y1: String(size.strip / 2), y2: String(size.strip / 2),
    class: "interval-rule",
  }));
  if (threshold !== null && Number.isFinite(Number(threshold))) {
    const x = place(threshold);
    drawing.append(make(doc, "line", {
      x1: x.toFixed(3), x2: x.toFixed(3), y1: "0", y2: String(size.strip),
      class: "interval-threshold", "data-mark": "threshold",
      "data-raw": String(threshold),
    }));
  }
  for (const one of named) {
    const mark = make(doc, "circle", {
      cx: place(one.value).toFixed(3), cy: String(size.strip / 2),
      r: String(Math.max(size.strip / 6, 1)),
      class: `interval-mark mark-${one.key}`,
      "data-mark": one.key, "data-raw": String(one.value),
    });
    // The mark names itself. `<title>` rather than a tick label,
    // deliberately: five scores that agree land within a few percent of
    // each other, and a tick row of five labels three percent apart is
    // five labels on top of each other - which is what `UX-350`'s
    // overlap guard is for, and it caught exactly that here. The
    // reading a tick row would have carried is in the sentence below
    // and in the table twin, both of which name every mark.
    const names = make(doc, "title", {});
    names.textContent = `${one.label} ${format(one.value)}`;
    mark.append(names);
    drawing.append(mark);
  }
  wrap.append(drawing);
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  named.map((one) => `${one.label} ${format(one.value)}`)
                    .join(", ")
                  + (threshold !== null && Number.isFinite(Number(threshold))
                     ? `, against ${thresholdLabel} ${format(threshold)}.`
                     : ".")));
  if (grade === GRADE_EXHIBIT) {
    wrap.append(exhibitTwin(doc, ["Measure", "Value"],
                            named.map((one) => [one.label,
                                                format(one.value)])));
  }
  return wrap;
}

export function columnStrip(values, { format = String, doc = document,
                                      label = null,
                                      grade = GRADE_ANNOTATION } = {}) {
  // `UX-316`: annotation grade by construction and by argument both -
  // a strip drawn beside a table *is* the §2a annotation case, and the
  // parameter exists so the guard reads one rule rather than two.
  const size = scaleFor(grade);
  const numbers = (values ?? []).filter(numeric).slice().sort((a, b) => a - b);
  const wrap = box(doc, "div", { class: "density density-self",
                                 "data-role": "density",
                                 "data-grade": grade });
  if (label) wrap.append(box(doc, "span", { class: "density-label" }, label));
  if (numbers.length < SERIES_MIN_POINTS) {
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence muted",
                                   "data-role": "density-sentence" },
                    `${numbers.length} row${numbers.length === 1 ? "" : "s"}`
                    + " — too few to have a shape."));
    return wrap;
  }
  // Nearest-rank, the same rule `store_aggregate.percentile` uses, so
  // a self-built tick sits where a published one would.
  const rank = (p) => numbers[Math.max(0, Math.ceil((p / 100) * numbers.length) - 1)];
  const marks = {
    n: numbers.length,
    min: numbers[0], max: numbers[numbers.length - 1],
    p50: rank(50), p95: rank(95),
  };
  wrap.setAttribute("data-drawn", "true");
  wrap.setAttribute("data-n", String(marks.n));
  wrap.append(stripSvg(doc, marks, { printed: "rows", size }));
  // Actual row values and a count. Nothing derived is spelled out.
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  `${format(marks.min)} → ${format(marks.max)} across `
                  + `${marks.n} rows.`));
  return wrap;
}
