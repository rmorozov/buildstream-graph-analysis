// UX-196: three views where a drawing says what sentences strain to.
//
// The discipline from UX-193 still holds: these render *published*
// payloads, and they draw only where the generic table genuinely cannot
// say it. That is exactly two SVGs - the band strip and the store trend
// - and no library behind either. Everything else here is layout.
//
// Nothing below recomputes anything. `compare/v1` already carries the
// band edges, the observed extent and the verdict; `store/v1` already
// carries the sizes and the incomplete reasons. A viewer that did its
// own arithmetic would be a second implementation of the analysis, and
// the first thing it would do is disagree with the first one.

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(name, String(value));
  }
  return node;
}


// Small local formatters rather than importing app.js's: app.js already
// imports *this* module, and a cycle between the two would work today
// (both export hoisted declarations) and break the first time either
// grows a top-level side effect. `UX-201` folds formatting into one
// schema-driven place, which is where this duplication goes to die.
function seconds(microseconds) {
  const s = microseconds / 1e6;
  return s < 90 ? `${s.toFixed(1)} s` : `${(s / 60).toFixed(1)} min`;
}

function mib(value) {
  const units = ["B", "KiB", "MiB", "GiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

// --------------------------------------------------------------- band
//
// `UX-170`'s disputed region is the case this drawing exists for: a
// candidate outside the noise band but inside the range the baseline
// runs actually spanned. In prose that took a paragraph and still read
// like a paradox. Drawn, the marker simply lands between the strip's
// edge and the dots' extent, and the question answers itself.

export function bandGeometry(compare) {
  const band = compare.baseline_band;
  if (!band) return null;

  const low = band.band_low_us ?? band.low_us ?? band.low;
  const high = band.band_high_us ?? band.high_us ?? band.high;
  const observedLow = band.observed_low_us ?? band.min_us ?? low;
  const observedHigh = band.observed_high_us ?? band.max_us ?? high;
  const candidate = compare.candidate?.total_duration_us;
  if ([low, high, candidate].some((v) => typeof v !== "number")) return null;

  // The axis spans whichever is wider - the band or what was observed -
  // with a margin so a candidate just outside is still on the canvas.
  const lo = Math.min(low, observedLow, candidate);
  const hi = Math.max(high, observedHigh, candidate);
  const pad = (hi - lo) * 0.1 || 1;
  const min = lo - pad, max = hi + pad;
  const at = (value) => ((value - min) / (max - min)) * 100;

  const inBand = candidate >= low && candidate <= high;
  const inObserved = candidate >= observedLow && candidate <= observedHigh;
  return {
    min, max, at,
    band: { low, high, x: at(low), width: at(high) - at(low) },
    observed: { low: observedLow, high: observedHigh,
                x: at(observedLow), width: at(observedHigh) - at(observedLow) },
    candidate: { value: candidate, x: at(candidate) },
    runs: (band.runs ?? band.baseline_runs ?? [])
      .map((r) => (typeof r === "number" ? r : r.total_duration_us))
      .filter((v) => typeof v === "number")
      .map((value) => ({ value, x: at(value) })),
    // The three-way answer, taken from the payload's own verdict where
    // it has one rather than re-derived from the numbers.
    where: inBand ? "inside the band"
      : inObserved ? "outside the band, inside the observed range"
      : "outside both",
    disputed: !inBand && inObserved,
  };
}

export function renderBand(compare) {
  const geometry = bandGeometry(compare);
  if (!geometry) return null;

  const H = 74;
  const figure = svg("svg", {
    viewBox: `0 0 100 ${H}`, class: "band", preserveAspectRatio: "none",
    role: "img", "data-where": geometry.where,
    "data-disputed": String(geometry.disputed),
    "data-candidate-x": geometry.candidate.x.toFixed(3),
    "data-band-x": geometry.band.x.toFixed(3),
    "data-band-width": geometry.band.width.toFixed(3),
    "data-observed-x": geometry.observed.x.toFixed(3),
    "data-observed-width": geometry.observed.width.toFixed(3),
  });
  figure.append(svg("rect", {
    x: geometry.observed.x, width: geometry.observed.width,
    y: 18, height: 26, class: "observed", "data-role": "observed",
  }));
  figure.append(svg("rect", {
    x: geometry.band.x, width: geometry.band.width,
    y: 24, height: 14, class: "band-strip", "data-role": "band",
  }));
  for (const run of geometry.runs) {
    figure.append(svg("circle", {
      cx: run.x, cy: 31, r: 1.4, class: "baseline-dot", "data-role": "run",
      "data-value": run.value,
    }));
  }
  figure.append(svg("line", {
    x1: geometry.candidate.x, x2: geometry.candidate.x, y1: 8, y2: 54,
    class: "candidate", "data-role": "candidate",
    "data-value": geometry.candidate.value,
  }));

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "band");
  const heading = document.createElement("h2");
  heading.textContent = "The band";
  const caption = document.createElement("p");
  caption.className = "muted";
  caption.textContent = geometry.disputed
    ? "The candidate is outside the noise band but inside the range the "
      + "baseline runs themselves spanned — the marker sits between the "
      + "strip and the dots' extent. UX-170 calls this the disputed "
      + "region, and it is why compare declines to call it a regression."
    : `The candidate is ${geometry.where}.`;
  wrapper.append(heading, figure, caption);
  return wrapper;
}

// -------------------------------------------------------------- trend
//
// `--list`, made visual. The question is "is this project drifting",
// and the answer is a shape.

export function renderTrend(store) {
  const rows = store?.snapshots ?? [];
  if (rows.length < 2) return null;

  const W = 100, H = 40;
  // UX-203: the axis is duration. It was `bytes`, so the trend
  // answered "is this project drifting" with disk usage.
  const sizes = rows.map((r) => r.total_duration_us ?? 0);
  const max = Math.max(...sizes, 1);
  const x = (i) => (rows.length === 1 ? W / 2 : (i / (rows.length - 1)) * W);
  const y = (v) => H - (v / max) * (H - 6) - 3;

  const figure = svg("svg", {
    viewBox: `0 0 ${W} ${H}`, class: "trend", preserveAspectRatio: "none",
    role: "img", "data-points": rows.length,
  });
  figure.append(svg("polyline", {
    points: rows.map((r, i) => `${x(i)},${y(r.total_duration_us ?? 0)}`).join(" "),
    class: "trend-line", fill: "none",
  }));
  for (const [index, row] of rows.entries()) {
    // Incomplete snapshots are *marked*, not hidden: they occupy the
    // disk, and a trend that quietly dropped them would answer the
    // drift question with a curated subset.
    const reason = row.incomplete_reason;
    // UX-203: the verdict colours the dot - the question the trend is
    // asked is whether this build is drifting, and the verdict is the
    // answer the rest of the tool already gives for one pair.
    const verdict = row.verdict_kind ?? "";
    const point = svg(reason ? "rect" : "circle", reason
      ? { x: x(index) - 1.3, y: y(row.total_duration_us ?? 0) - 1.3, width: 2.6,
          height: 2.6, class: "trend-point incomplete",
          "data-stamp": row.stamp, "data-incomplete": reason }
      : { cx: x(index), cy: y(row.total_duration_us ?? 0), r: 1.3,
          class: `trend-point${row.alias ? " aliased" : ""}`
                 + (verdict ? ` verdict-${verdict}` : ""),
          "data-stamp": row.stamp, "data-alias": row.alias ?? "",
          "data-verdict": verdict });
    // Size is still here, demoted to where it belongs: a detail you can
    // hover for, not the axis the question is answered on.
    const tip = svg("title");
    tip.textContent = [
      row.stamp,
      row.total_duration_us != null ? seconds(row.total_duration_us) : null,
      verdict ? verdict.replace(/_/g, " ") : null,
      row.cache_hit_rate != null
        ? `${(row.cache_hit_rate * 100).toFixed(0)}% cache hits` : null,
      row.bytes != null ? mib(row.bytes) : null,
    ].filter(Boolean).join(" · ");
    point.append(tip);
    figure.append(point);
  }

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "store-trend");
  const heading = document.createElement("h2");
  heading.textContent = `The store (${rows.length} snapshots)`;
  const caption = document.createElement("p");
  caption.className = "muted";
  const incomplete = rows.filter((r) => r.incomplete_reason);
  caption.textContent = incomplete.length
    ? `Squares are the ${incomplete.length} snapshot(s) that are not `
      + `measurements (${[...new Set(incomplete.map((r) => r.incomplete_reason))]
          .join(", ")}); they are on disk, so they are on the chart.`
    : "Every snapshot here finished.";
  wrapper.append(heading, figure, caption);
  return wrapper;
}

// ---------------------------------------------------------- blast box
//
// The search box is a *transport*: it hands the target to the server,
// which calls the same function `bga blast` calls. No resolution
// happens here, because a second resolver would be a second answer.

export function renderBlastSearch(onQuery) {
  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "blast");
  const heading = document.createElement("h2");
  heading.textContent = "What rebuilds if I touch this?";
  const form = document.createElement("form");
  form.setAttribute("data-role", "blast-form");
  const input = document.createElement("input");
  input.setAttribute("data-role", "blast-input");
  input.placeholder = "a git url, a path in the project, or an element name";
  input.size = 52;
  const button = document.createElement("button");
  button.textContent = "Ask";
  const answer = document.createElement("div");
  answer.setAttribute("data-role", "blast-answer");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    answer.textContent = "asking…";
    try {
      const result = await onQuery(input.value);
      answer.replaceChildren(renderBlastAnswer(result));
    } catch (error) {
      answer.textContent = String(error.message ?? error);
    }
  });
  form.append(input, button);
  wrapper.append(heading, form, answer);
  return wrapper;
}

export function renderBlastAnswer(result) {
  const list = document.createElement("dl");
  list.className = "pairs";
  list.setAttribute("data-role", "blast-result");
  // Straight from `blast/v1`; the sentence about keying is the payload's
  // own, so the page and `bga blast` cannot phrase it differently.
  const rows = [
    ["Resolved as", result.resolved_as],
    ["Keying", result.keying],
    ["Direct", result.direct_count],
    ["Rebuilds", result.blast_count],
    ["Of which build", result.building_count],
    ["…and assemble", result.assembling_count],
    ["Measured", result.measured
      ? `${result.measured_seconds?.toFixed?.(1) ?? result.measured_seconds}s `
        + `over ${result.measured_elements} element(s)`
      : "not measured (--no-cost, or no run)"],
  ];
  for (const [name, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = name;
    const dd = document.createElement("dd");
    dd.textContent = value === null || value === undefined ? "—" : String(value);
    dd.setAttribute("data-key", name.toLowerCase().replace(/\W+/g, "_"));
    list.append(dt, dd);
  }
  return list;
}
