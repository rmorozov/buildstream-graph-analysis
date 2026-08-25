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
//   - **fixed small geometry, no axes, no grid.** A sparkline is a
//     word-sized picture; the moment it needs a legend it is a chart,
//     and §6 says a chart owes its reader a sentence instead.
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

/** The drawing's box. Word-sized, and the same for every instance. */
export const SPARK_WIDTH = 100;
export const SPARK_HEIGHT = 20;
export const STRIP_HEIGHT = 8;

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

/**
 * An ordered numeric series as a sparkline plus its one sentence.
 *
 * `unit` is what one step along the order *is*, and it comes from the
 * schema's `bga:series` value - the sentence has to name it and a
 * viewer must not invent one.
 */
export function sparkline(values, {
  unit = "step", format = String, doc = document, label = null,
} = {}) {
  const points = (values ?? []).filter(numeric);
  const wrap = box(doc, "div", {
    class: "series", "data-role": "series",
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
  const x = (i) => (i / (points.length - 1)) * SPARK_WIDTH;
  // Flat series sit on the middle line rather than on the floor: a
  // series of identical values is not "all at zero".
  const y = (v) => span === 0
    ? SPARK_HEIGHT / 2
    : (SPARK_HEIGHT - 2) - ((v - low) / span) * (SPARK_HEIGHT - 4);

  const line = make(doc, "svg", {
    viewBox: `0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}`,
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
      cx: x(at).toFixed(2), cy: y(points[at]).toFixed(2), r: 1.6,
      class: "spark-point", "data-mark": role,
      "data-value": String(points[at]), "data-at": String(at),
    }));
  }
  wrap.append(line);
  wrap.append(box(doc, "span", { class: "series-sentence",
                                 "data-role": "series-sentence" },
                  `${points.length} ${unit}s, ${format(points[0])} → `
                  + `${format(points[points.length - 1])}`
                  + `, peak ${format(high)} at ${unit} ${peak + 1}.`));
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

function stripSvg(doc, marks, { printed }) {
  const span = marks.max - marks.min;
  const at = (v) => span === 0 ? 50 : ((v - marks.min) / span) * 100;
  const strip = make(doc, "svg", {
    viewBox: `0 0 100 ${STRIP_HEIGHT}`, class: "density-strip",
    preserveAspectRatio: "none", role: "img", "data-role": "density-strip",
    "data-min": String(marks.min), "data-max": String(marks.max),
    "data-p50": marks.p50 === null ? "" : String(marks.p50),
    "data-p95": marks.p95 === null ? "" : String(marks.p95),
    // Whether the numbers beside it were published or read off the
    // rows. A self-built strip prints no derived number, and this is
    // what lets a guard tell the two apart on the page.
    "data-printed": printed,
  });
  strip.append(make(doc, "rect", {
    class: "density-range", x: "0", y: String(STRIP_HEIGHT / 2 - 1),
    width: "100", height: "2",
  }));
  for (const [name, value] of [["p50", marks.p50], ["p95", marks.p95]]) {
    if (value === null) continue;
    strip.append(make(doc, "line", {
      class: `density-tick density-${name}`,
      x1: at(value).toFixed(2), x2: at(value).toFixed(2),
      y1: "0", y2: String(STRIP_HEIGHT),
      "data-mark": name, "data-value": String(value),
    }));
  }
  for (const [name, value] of [["min", marks.min], ["max", marks.max]]) {
    strip.append(make(doc, "line", {
      class: "density-end", x1: at(value).toFixed(2), x2: at(value).toFixed(2),
      y1: "1", y2: String(STRIP_HEIGHT - 1),
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
} = {}) {
  const marks = marksOf(distribution, countKey);
  const wrap = box(doc, "div", { class: "density", "data-role": "density" });
  if (label) wrap.append(box(doc, "span", { class: "density-label" }, label));
  if (!marks) {
    wrap.setAttribute("data-drawn", "false");
    wrap.append(box(doc, "span", { class: "density-sentence muted",
                                   "data-role": "density-sentence" },
                    "No distribution published for this population."));
    return wrap;
  }
  wrap.setAttribute("data-drawn", "true");
  wrap.setAttribute("data-n", marks.n === null ? "" : String(marks.n));
  wrap.append(stripSvg(doc, marks, { printed: "published" }));
  const parts = [`${format(marks.min)} → ${format(marks.max)}`];
  if (marks.p50 !== null) parts.push(`median ${format(marks.p50)}`);
  if (marks.p95 !== null) parts.push(`p95 ${format(marks.p95)}`);
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  `${parts.join(", ")}`
                  + (marks.n === null ? "." : ` — n=${marks.n}.`)));
  return wrap;
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
export function columnStrip(values, { format = String, doc = document,
                                      label = null } = {}) {
  const numbers = (values ?? []).filter(numeric).slice().sort((a, b) => a - b);
  const wrap = box(doc, "div", { class: "density density-self",
                                 "data-role": "density" });
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
  wrap.append(stripSvg(doc, marks, { printed: "rows" }));
  // Actual row values and a count. Nothing derived is spelled out.
  wrap.append(box(doc, "span", { class: "density-sentence",
                                 "data-role": "density-sentence" },
                  `${format(marks.min)} → ${format(marks.max)} across `
                  + `${marks.n} rows.`));
  return wrap;
}
