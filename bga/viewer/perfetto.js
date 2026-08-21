// UX-194: hand the timeline to ui.perfetto.dev, wholesale.
//
// Direction 7's timeline rule: none of our own, ever. Perfetto's
// renderer and its SQL engine are better than anything this project
// would write, and they are one `postMessage` away.
//
// **This is not an upload.** The bytes go tab-to-tab through
// `postMessage` and are processed in the browser; ui.perfetto.dev is a
// static site with no server side to send a trace to. It looks like an
// upload - a public URL opens and your build data appears in it - so
// the page says so out loud, and so do the docs.
//
// The protocol is Perfetto's documented deep-link handshake: open the
// UI, ping it until it answers PONG (it cannot receive a trace before
// its worker is up), then post the buffer once.

export const PERFETTO_ORIGIN = "https://ui.perfetto.dev";

// Perfetto's own example uses 50ms. The cap exists because a blocked
// pop-up never answers, and a page that pings forever looks like it is
// working.
const PING_INTERVAL_MS = 50;
const TIMEOUT_MS = 20000;

/**
 * Post `buffer` to a freshly opened Perfetto tab.
 *
 * `deps` is injectable so this can be driven by a scripted window
 * double in a test - the handshake is the part worth guarding, and it
 * is unobservable through a real browser in CI.
 *
 * Resolves when Perfetto has the bytes. Rejects if the tab never
 * answers (a blocked pop-up is the usual cause, and the message says
 * so, because "nothing happened" is the worst possible failure here).
 */
export function openInPerfetto(buffer, title, deps = {}) {
  const {
    open = (url) => window.open(url),
    addEventListener = (...a) => window.addEventListener(...a),
    removeEventListener = (...a) => window.removeEventListener(...a),
    setInterval: setEvery = setInterval,
    clearInterval: clearEvery = clearInterval,
    setTimeout: setLater = setTimeout,
    clearTimeout: clearLater = clearTimeout,
    origin = PERFETTO_ORIGIN,
  } = deps;

  return new Promise((resolve, reject) => {
    const tab = open(origin);
    if (!tab) {
      reject(new Error(
        "The Perfetto tab did not open — your browser blocked the pop-up. " +
        "Allow pop-ups for this page, or open ui.perfetto.dev yourself and " +
        "drag the trace file in."));
      return;
    }

    let pinger = null, timer = null;
    const done = (fn, value) => {
      clearEvery(pinger);
      clearLater(timer);
      removeEventListener("message", onMessage);
      fn(value);
    };

    function onMessage(event) {
      // Only Perfetto's own origin may answer. Not for confidentiality
      // - `postMessage` below names `origin` as the target, so the
      // bytes cannot reach anywhere else regardless. It is so a stray
      // PONG from some other frame cannot make us fire *early*, before
      // Perfetto's worker is up, which loses the trace into a silent
      // empty tab.
      if (event.origin !== origin) return;
      if (event.data !== "PONG") return;
      tab.postMessage({ perfetto: { buffer, title } }, origin);
      done(resolve, { title, bytes: buffer.byteLength ?? buffer.length ?? 0 });
    }

    addEventListener("message", onMessage);
    pinger = setEvery(() => tab.postMessage("PING", origin), PING_INTERVAL_MS);
    timer = setLater(() => done(reject, new Error(
      `ui.perfetto.dev did not answer within ${TIMEOUT_MS / 1000}s. The tab ` +
      `may have been blocked, or opened without network access.`)), TIMEOUT_MS);
  });
}

/** Fetch the served trace and hand it over. */
export async function handOff(url = "timeline.json.gz", title = "bga timeline",
                              deps = {}) {
  const fetchIt = deps.fetch ?? ((u) => fetch(u));
  const response = await fetchIt(url);
  if (!response.ok) {
    throw new Error(
      `${url}: ${response.status}. This run has no timeline — it was ` +
      `captured with --no-keep-raw, or before UX-188.`);
  }
  // Perfetto sniffs gzip itself, so the compressed bytes go over as-is.
  // Measured on a real capture of examples/06: 272,964 B of merged
  // trace becomes 24,782 B, 9.1% - and that is what crosses the
  // postMessage boundary.
  const buffer = await response.arrayBuffer();
  return openInPerfetto(buffer, title, deps);
}
