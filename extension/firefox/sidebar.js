// Runs a check against the Claim Check app and shows the verdicts in Firefox's sidebar.
// Extension pages may call the app directly thanks to host_permissions; nothing is sent until you ask for a check.
const APP = "https://claim-check-tr4f.onrender.com";
const $ = (s) => document.querySelector(s);
let running = false, lastTs = 0;

function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function setStatus(msg, spin) { const s = $("#status"); s.textContent = ""; if (spin) s.append(el("span", "spin")); s.append(msg || ""); }
const shortModel = (m) => String(m || "").split("/").pop();
async function errorText(res) {
  try { const j = await res.json(); if (typeof j.detail === "string") return j.detail; } catch {}
  return `Error ${res.status}`;
}
function link(url, text) {
  const a = el("a", null, text || url);
  if (/^https?:\/\//i.test(url || "")) { a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer"; }
  return a;
}

async function check(text) {
  if (running) return; running = true;
  $("#go").disabled = true; $("#hint").hidden = true; $("#claims").textContent = ""; $("#foot").textContent = "";
  const inp = $("#input"); inp.hidden = false; inp.textContent = text.length > 300 ? text.slice(0, 300) + "…" : text;
  setStatus("Starting (the free server can take ~50 s to wake up)", true);
  const cards = {};
  try {
    const res = await fetch(`${APP}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ post: text }) });
    if (!res.ok) throw new Error(await errorText(res));
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
  running = false; $("#go").disabled = false;
  takePending();  // something was picked while this check ran
}

function handle(ev, cards) {
  const c = ev.claim_id && cards[ev.claim_id];
  switch (ev.type) {
    case "status": setStatus(ev.message, true); break;
    case "page": $("#input").textContent = `Read from: ${ev.title || ev.url}`; break;
    case "claims": for (const x of ev.claims) {
      const d = el("div", "card"); d.append(el("div", "claim", x.text));
      const body = el("div", "body"); body.append(el("span", "kind", "Checking…")); d.append(body);
      const srcs = el("ul", "srcs"); d.append(srcs);
      $("#claims").append(d); cards[x.id] = { body, srcs }; } break;
    case "evidence": if (c) { c.srcs.textContent = "";
      for (const e of (ev.research?.evidence || []).slice(0, 2)) { const li = el("li"); li.append(link(e.url, e.publisher || e.title || e.url)); c.srcs.append(li); } } break;
    case "verdict": if (c) { const r = ev.result; c.body.textContent = "";
      c.body.append(el("span", `v v-${String(r.verdict || "").replace(/[^A-Za-z]/g, "")}`, r.verdict), " ",
                    el("span", "kind", `${r.confidence} confidence`), el("p", "expl", r.explanation || ""));
      if (ev.cached) c.body.append(el("div", "second", "♻ Checked recently: verdict reused"));
      const j = r.jury;
      if (j) {
        const n = j.total + 1;
        c.body.append(el("div", j.unanimous ? "second" : "second dis", j.unanimous
          ? `Jury: unanimous across ${n} labs (OpenAI, ${j.votes.map(v => v.lab).join(", ")})`
          : `Jury: ${j.agree + 1} of ${n} labs agree. ` + j.votes.filter(v => !v.agree).map(v => `${v.lab} says ${v.verdict}`).join("; ")));
      }
    } break;
    case "error": (c ? c.body : $("#claims")).append(el("p", "err", ev.message)); break;
    case "blocked": $("#claims").append(el("p", "err", `Blocked by a guardrail: ${ev.message}`)); setStatus("Blocked"); break;
    case "budget": (c ? c.body : $("#claims")).append(el("p", "err", ev.message)); break;
    case "done": setStatus("Done"); break;
    case "report": showFoot(ev.id); break;
  }
}

function showFoot(id) {
  const foot = $("#foot"); foot.textContent = "";
  const row = el("div", "row");
  const btn = el("button", "ghost", "✍ Draft a calm reply"); btn.type = "button";
  row.append(btn, link(`${APP}/r/${id}`, "Full report with sources →"));
  const out = el("div"); foot.append(row, out);
  btn.onclick = async () => {
    btn.disabled = true; btn.textContent = "Drafting…";
    try {
      const res = await fetch(`${APP}/api/reply`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ report_id: id }) });
      if (!res.ok) throw new Error(await errorText(res));
      const j = await res.json();
      out.textContent = ""; out.append(el("div", "reply", j.reply));
      const copy = el("button", "ghost", "Copy reply"); copy.type = "button";
      copy.onclick = async () => { try { await navigator.clipboard.writeText(j.reply); copy.textContent = "Copied ✓"; } catch { copy.textContent = "Select and copy the text above"; } };
      const r2 = el("div", "row"); r2.append(copy, el("span", "kind", "read it before you post")); out.append(r2);
      btn.textContent = "✍ Reply drafted";
    } catch (e) { out.textContent = ""; out.append(el("p", "err", e.message)); btn.disabled = false; btn.textContent = "✍ Draft a calm reply"; }
  };
}

$("#ask").addEventListener("submit", (e) => {
  e.preventDefault();
  const text = $("#q").value.trim();
  if (text.length < 10) { setStatus("Paste a claim (10+ characters) or a link"); return; }
  check(text);
});

async function takePending() {
  if (running) return;
  const { pending } = await browser.storage.local.get("pending");
  if (!pending || pending.ts <= lastTs || Date.now() - pending.ts > 120000) return;
  lastTs = pending.ts; await browser.storage.local.remove("pending");
  if (pending.error) { $("#hint").hidden = true; $("#claims").textContent = ""; $("#claims").append(el("p", "err", pending.error)); return; }
  $("#q").value = pending.text;
  check(pending.text);
}
browser.storage.onChanged.addListener((ch, area) => { if (area === "local" && ch.pending?.newValue) takePending(); });
takePending();
