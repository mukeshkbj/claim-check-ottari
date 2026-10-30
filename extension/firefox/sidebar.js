// Runs a check against the Claim Check app and shows the verdicts in Firefox's sidebar.
// Extension pages may call the app directly thanks to host_permissions; nothing is sent until you pick the menu item.
const APP = "https://claim-check-tr4f.onrender.com";
const $ = (s) => document.querySelector(s);
let running = false, lastTs = 0;

function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function setStatus(msg, spin) { const s = $("#status"); s.textContent = ""; if (spin) s.append(el("span", "spin")); s.append(msg || ""); }

async function check(text) {
  if (running) return; running = true;
  $("#hint").hidden = true; $("#claims").textContent = ""; $("#foot").textContent = "";
  const inp = $("#input"); inp.hidden = false; inp.textContent = text.length > 300 ? text.slice(0, 300) + "…" : text;
  setStatus("Starting (the free server can take ~50 s to wake up)", true);
  const cards = {};
  try {
    const res = await fetch(`${APP}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ post: text }) });
    if (!res.ok) { let m = `Error ${res.status}`; try { const j = await res.json(); if (typeof j.detail === "string") m = j.detail; } catch {} throw new Error(m); }
    const reader = res.body.getReader(), dec = new TextDecoder(); let buf = "";
    for (;;) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i; while ((i = buf.indexOf("\n\n")) >= 0) {
        const line = buf.slice(0, i); buf = buf.slice(i + 2);
        if (line.startsWith("data: ")) handle(JSON.parse(line.slice(6)), cards);
      }
    }
  } catch (e) { $("#claims").append(el("p", "err", e.message)); setStatus(""); }
  running = false;
  takePending();  // something was picked while this check ran
}

function handle(ev, cards) {
  const card = ev.claim_id && cards[ev.claim_id];
  switch (ev.type) {
    case "status": setStatus(ev.message, true); break;
    case "page": $("#input").textContent = `Read from: ${ev.title || ev.url}`; break;
    case "claims": for (const c of ev.claims) {
      const d = el("div", "card"); d.append(el("div", "claim", c.text));
      const body = el("div", "body"); body.append(el("span", "kind", "Checking…")); d.append(body);
      $("#claims").append(d); cards[c.id] = body; } break;
    case "verdict": if (card) { const r = ev.result; card.textContent = "";
      card.append(el("span", `v v-${String(r.verdict || "").replace(/[^A-Za-z]/g, "")}`, r.verdict), " ",
                  el("span", "kind", `${r.confidence} confidence`), el("p", "expl", r.explanation || ""));
      const o = r.second_opinion;
      if (o) card.append(el("div", o.agree ? "second" : "second dis",
        o.agree ? `✓ Second judge (${String(o.model).split("/").pop()}) agrees` : `⚠ Judges disagree: ${String(o.model).split("/").pop()} says ${o.verdict}`));
    } break;
    case "error": (card || $("#claims")).append(el("p", "err", ev.message)); break;
    case "blocked": $("#claims").append(el("p", "err", `Blocked by a guardrail: ${ev.message}`)); setStatus("Blocked"); break;
    case "budget": (card || $("#claims")).append(el("p", "err", ev.message)); break;
    case "done": setStatus("Done"); break;
    case "report": { const a = el("a", null, "Open the full report with sources →"); a.href = `${APP}/r/${ev.id}`; a.target = "_blank";
      $("#foot").textContent = ""; $("#foot").append(a); break; }
  }
}

async function takePending() {
  const { pending } = await browser.storage.local.get("pending");
  if (running) return;
  if (pending && pending.ts > lastTs && Date.now() - pending.ts < 120000) {
    lastTs = pending.ts; await browser.storage.local.remove("pending"); check(pending.text);
  }
}
browser.storage.onChanged.addListener((ch, area) => { if (area === "local" && ch.pending?.newValue) takePending(); });
takePending();
