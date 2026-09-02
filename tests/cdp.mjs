// UX-257: the whole CDP client. Node 22's built-in WebSocket and
// fetch, and nothing else - that is the argument for driving a browser
// directly rather than adding Playwright.
//
//   node cdp.mjs <port> <url> <width> <height> [--observe]  < expression
//
// Prints the JSON value the expression evaluated to. With `--observe`,
// prints `{value, console, csp, issues}` instead: everything the
// console was told, every security-policy violation the document
// reported, and every entry the Issues panel would show - all from
// this navigation onwards.
//
// `UX-334`: the console half exists because eleven CSP violations and
// four 404s per boot accumulated across ten rounds with nothing
// listening. `Runtime.consoleAPICalled` catches what the page says,
// `Runtime.exceptionThrown` what it throws, and `Log.entryAdded` what
// the *browser* says about the page - which is where a 404 on a
// subresource is reported, and nowhere else. The violation events are
// collected in-page instead: `securitypolicyviolation` fires on
// `document` with the directive on it, which is the name a reader
// needs, and `Log`'s rendering of the same event is a sentence.
const [, , port, url, width, height] = process.argv;
const observing = process.argv.includes("--observe");

let expression = "";
for await (const chunk of process.stdin) expression += chunk;

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);

let id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((resolve) => {
  const n = ++id;
  pending.set(n, resolve);
  ws.send(JSON.stringify({ id: n, method, params }));
});
const consoled = [];
const issues = [];
// Not until the navigation this run is about. `Log.enable` *replays*
// what the target has already logged and this browser is reused across
// loads, so without a gate the second page observed inherits the
// first's errors: measured, the served boot came back carrying three
// `file://` CORS errors from the exported boot before it, and
// `Log.clear` alone does not fix it - the replay is already in flight
// by the time the clear is acknowledged.
let recording = false;
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message.result);
    pending.delete(message.id);
    return;
  }
  if (!observing || !recording) return;
  const p = message.params ?? {};
  if (message.method === "Runtime.consoleAPICalled") {
    consoled.push({
      source: "console", level: p.type,
      text: (p.args ?? []).map(describe).join(" "),
      url: p.stackTrace?.callFrames?.[0]?.url ?? "",
    });
  } else if (message.method === "Runtime.exceptionThrown") {
    const d = p.exceptionDetails ?? {};
    consoled.push({
      source: "exception", level: "error",
      text: d.exception?.description ?? d.text ?? "",
      url: d.url ?? d.stackTrace?.callFrames?.[0]?.url ?? "",
    });
  } else if (message.method === "Audits.issueAdded") {
    // What the Issues panel shows. A different channel again: the
    // form-control complaints `UX-334` was filed over never reach the
    // console at all, so a guard that watched only `Log` would report
    // a clean page with two hundred issues in it.
    const detail = p.issue?.details ?? {};
    const [kind] = Object.keys(detail);
    const body = detail[kind] ?? {};
    issues.push({ code: p.issue?.code ?? "", kind: kind ?? "",
                  reason: body.errorType ?? body.reason ?? body.type ?? "" });
  } else if (message.method === "Log.entryAdded") {
    const e = p.entry ?? {};
    consoled.push({ source: e.source ?? "log", level: e.level,
                    text: e.text ?? "", url: e.url ?? "" });
  }
});

// A `RemoteObject` without `returnByValue`: the printable half, in the
// order Chrome itself would show it.
function describe(arg) {
  if (arg.type === "string") return arg.value;
  if ("value" in arg) return JSON.stringify(arg.value);
  return arg.description ?? arg.type;
}
await new Promise((resolve) => ws.addEventListener("open", resolve));

await send("Page.enable");
if (observing) {
  await send("Runtime.enable");
  await send("Log.enable");
  await send("Log.clear");
  await send("Audits.enable");
  // Before the document exists, so a violation from the first
  // stylesheet is caught. `Page.navigate` below is what runs it.
  await send("Page.addScriptToEvaluateOnNewDocument", {
    // UX-343: dev-mode strict hints, on for every observed boot. The
    // complaint `quantityFor` makes when it had to name-sniff a unit
    // is a console channel like any other, and this is the reader for
    // it - set here, before the document, because the page resolves
    // quantities during boot.
    source: `window.BGA_STRICT_HINTS = true;
      window.__bgaCsp = [];
      document.addEventListener("securitypolicyviolation", (event) => {
        window.__bgaCsp.push({
          directive: event.effectiveDirective || event.violatedDirective,
          disposition: event.disposition,
          blocked: event.blockedURI,
          source: event.sourceFile || "",
          line: event.lineNumber || 0,
        });
      });`,
  });
}
await send("Emulation.setDeviceMetricsOverride", {
  width: Number(width), height: Number(height),
  deviceScaleFactor: 1, mobile: false,
});
// The replay drains here, discarded, and the gate opens on the
// navigation this run is about.
if (observing) await new Promise((resolve) => setTimeout(resolve, 300));
recording = true;
await send("Page.navigate", { url });
// `UX-482`: this was a fixed 1,200ms settle, on the reasoning that the
// page is one file with inlined payloads and no network. That is a
// *duration* standing in for a *condition* - fixing guide s5 - and it
// lost on a loaded two-core runner: the first boot of a module observed
// a page mid-render and counted 40 of its 47 sections, while the second
// boot in the same module, with the browser already warm, counted all
// 47. The guard comparing the two then reported a difference the page
// does not have.
//
// So the wait is the condition it always meant: the rendered size of
// `#report` has stopped changing, with a ceiling so a page that never
// settles fails on its assertion rather than hanging here.
//
// `UX-523`: the 1,200ms floor `UX-482` kept beside the condition is
// gone. What it was standing in for is an **empty** `#report`, and
// emptiness is the thing to test: two zero-length samples are not a
// settled page. Measured on the two committed exports, drive 1.59s ->
// 0.56s with the same section counts (53 and 73); the suite was
// sleeping 1.2s per drive, ~430 drives a run.
//
// Removing it took two goes, and both misses are here because the
// second is the one that matters. Watching `#report || document.body`
// stop changing settles on a **served** page's static skeleton while
// the payload is still being fetched; watching `#report` alone settles
// on the sections while `boot()` is still wiring the controls after
// them, which is what three run-switching guards and two
// handoff-geometry guards then failed on. Both are the same mistake -
// a proxy for "the page has finished" - so `boot()` says it now
// (`data-bga-booted`), and this waits for the page's own word. A page
// with no `#report` has no `boot()` either, and settles on `body`.
const SETTLE_STEP_MS = 150;
const SETTLE_CEILING_MS = 20000;
{
  const state = async () => {
    const got = await send("Runtime.evaluate", {
      expression: `(() => {
        const report = document.getElementById("report");
        if (report) {
          return { booting: true,
                   done: document.documentElement.dataset.bgaBooted === "1" };
        }
        return { booting: false, n: document.body?.innerHTML.length ?? 0 };
      })()`,
      returnByValue: true,
    });
    return got.result?.value ?? { booting: false, n: 0 };
  };
  let previous = await state();
  for (let waited = 0; waited < SETTLE_CEILING_MS; waited += SETTLE_STEP_MS) {
    if (previous.booting && previous.done) break;
    await new Promise((resolve) => setTimeout(resolve, SETTLE_STEP_MS));
    const now = await state();
    if (!now.booting && !previous.booting && now.n === previous.n && now.n > 0) {
      break;
    }
    previous = now;
  }
}

const result = await send("Runtime.evaluate", {
  expression, returnByValue: true, awaitPromise: true,
});
if (result.exceptionDetails) {
  process.stderr.write(JSON.stringify(result.exceptionDetails, null, 1));
  process.exit(1);
}
const value = result.result.value ?? null;
let out = value;
if (observing) {
  const violations = await send("Runtime.evaluate", {
    expression: "window.__bgaCsp ?? []", returnByValue: true,
  });
  out = { value, console: consoled, csp: violations.result?.value ?? [],
          issues };
}
// `process.exit` is deliberately not called: stdout to a pipe is
// asynchronous, and exiting truncates a long report. Closing the
// socket is what lets the event loop drain and the process end.
process.stdout.write(JSON.stringify(out));
ws.close();
