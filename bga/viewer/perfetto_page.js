// UX-266: this was an inline `<script type="module">` in
// `perfetto.html`, refused by the page's own `default-src 'self'`.
// The consequence is quieter than `sql.html`'s and worse: the page
// renders, the "Open in Perfetto" button is *there*, and nothing
// is listening to it - so `bga view --perfetto` lands on a button
// that does nothing at all.
import { handOff, deepLink } from "./perfetto.js";

const line = document.getElementById("line");
const deep = document.getElementById("deep");
deep.href = deepLink(new URL("timeline.json.gz", location.href).href);

// UX-198: no `go()` at script load. The previous version called it
// here, so there was never a user gesture and default-settings Chrome
// blocked the pop-up *every time* - the "Try again" button below it was
// the tell that nobody read as a bug report.
document.getElementById("open").addEventListener("click", async () => {
  line.textContent = "Opening ui.perfetto.dev…";
  try {
    const { bytes } = await handOff();
    line.textContent =
      `Sent ${(bytes / 1024).toFixed(1)} KiB to the Perfetto tab. ` +
      `You can close this one — and stop the server with Ctrl-C.`;
  } catch (error) {
    line.textContent = String(error.message ?? error);
  }
});
