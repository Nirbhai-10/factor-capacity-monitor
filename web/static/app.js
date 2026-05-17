"use strict";
const VIEW = 6800;                       // metres half-extent
const cv = document.getElementById("cop"), cx = cv.getContext("2d");
const el = (id) => document.getElementById(id);
let ws = null, last = null, scale = 1, cxw = 0, cyh = 0;
const seenOrders = new Map();            // id -> state (for event log)

function resize() {
  cv.width = cv.clientWidth * devicePixelRatio;
  cv.height = cv.clientHeight * devicePixelRatio;
  scale = Math.min(cv.width, cv.height) / (2 * VIEW);
  cxw = cv.width / 2; cyh = cv.height / 2;
}
addEventListener("resize", resize);

const X = (mx) => cxw + mx * scale;       // world(m) -> screen
const Y = (my) => cyh - my * scale;

const CLS = { uas: "#ff4d5e", unknown: "#ffc24b", bird: "#5b7384",
  aircraft: "#7aa7c7", clutter: "#3f5260" };
const EFFC = { soft_kill_cyber: "#28e0c4", hpm: "#b07bff",
  laser: "#ff7a45", net_interceptor: "#54d98c" };

function grid() {
  cx.lineWidth = 1;
  cx.strokeStyle = "#12202b"; cx.fillStyle = "#33505f";
  cx.font = `${11 * devicePixelRatio}px ui-monospace`;
  for (let r = 1000; r <= 6000; r += 1000) {
    cx.beginPath(); cx.arc(cxw, cyh, r * scale, 0, 7); cx.stroke();
    cx.fillText(`${r / 1000}km`, cxw + 4, cyh - r * scale + 14);
  }
  cx.strokeStyle = "#101a22";
  cx.beginPath(); cx.moveTo(cxw, 0); cx.lineTo(cxw, cv.height);
  cx.moveTo(0, cyh); cx.lineTo(cv.width, cyh); cx.stroke();
  cx.fillStyle = "#4a6678"; cx.fillText("N", cxw + 6, 18 * devicePixelRatio);
}

function asset(keepout) {
  cx.save();
  cx.strokeStyle = "#ff7a45"; cx.setLineDash([5, 5]);
  cx.beginPath(); cx.arc(cxw, cyh, keepout * scale, 0, 7); cx.stroke();
  cx.setLineDash([]);
  cx.fillStyle = "#28e0c4";
  cx.beginPath();
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2;
    cx[k ? "lineTo" : "moveTo"](cxw + Math.cos(a) * 9 * devicePixelRatio,
      cyh + Math.sin(a) * 9 * devicePixelRatio);
  }
  cx.closePath(); cx.fill();
  cx.fillStyle = "#7fe9da";
  cx.fillText("ASSET", cxw + 12, cyh + 4);
  cx.restore();
}

function site(s) {
  const sx = X(s.x), sy = Y(s.y), on = s.active;
  cx.globalAlpha = on ? 0.10 : 0.03;
  cx.strokeStyle = on ? "#1f6f7a" : "#3a2030";
  cx.beginPath(); cx.arc(sx, sy, s.range * scale, 0, 7); cx.stroke();
  cx.globalAlpha = 1;
  cx.fillStyle = on ? "#3fb6c2" : "#5a2734";
  cx.fillRect(sx - 4, sy - 4, 8, 8);
  if (!on) {
    cx.strokeStyle = "#ff4d5e"; cx.beginPath();
    cx.moveTo(sx - 6, sy - 6); cx.lineTo(sx + 6, sy + 6);
    cx.moveTo(sx + 6, sy - 6); cx.lineTo(sx - 6, sy + 6); cx.stroke();
  }
  cx.fillStyle = on ? "#4a6678" : "#7a3a4a";
  cx.fillText(s.id, sx + 7, sy + 3);
}

function swarm(s) {
  if (!s.hull.length) return;
  const t = s.threat;
  cx.beginPath();
  s.hull.forEach((p, i) =>
    cx[i ? "lineTo" : "moveTo"](X(p[0]), Y(p[1])));
  cx.closePath();
  cx.fillStyle = `rgba(255,77,94,${0.05 + 0.18 * t})`;
  cx.strokeStyle = `rgba(255,120,90,${0.4 + 0.5 * t})`;
  cx.lineWidth = 1.5; cx.fill(); cx.stroke();
  const c = s.hull[0];
  cx.fillStyle = "#ffd9a0";
  cx.fillText(
    `S${s.id} n=${s.n} T=${t.toFixed(2)}` +
    (s.tti != null ? ` TTI=${s.tti}s` : "") +
    (s.mothership ? " ⚑MOTHERSHIP" : ""),
    X(c[0]) + 6, Y(c[1]) - 6);
}

function track(t) {
  const px = X(t.x), py = Y(t.y), c = CLS[t.cls] || "#888";
  if (t.vx || t.vy) {
    cx.strokeStyle = c; cx.globalAlpha = 0.5; cx.beginPath();
    cx.moveTo(px, py); cx.lineTo(X(t.x + t.vx * 6), Y(t.y + t.vy * 6));
    cx.stroke(); cx.globalAlpha = 1;
  }
  cx.fillStyle = c; cx.strokeStyle = c; cx.lineWidth = 1.4;
  const r = 4 * devicePixelRatio;
  if (t.cls === "uas") {
    cx.beginPath();
    cx.moveTo(px, py - r); cx.lineTo(px + r, py);
    cx.lineTo(px, py + r); cx.lineTo(px - r, py);
    cx.closePath();
    t.status === "coasting" ? cx.stroke() : cx.fill();
  } else {
    cx.beginPath(); cx.arc(px, py, r * 0.8, 0, 7);
    t.cls === "unknown" ? cx.stroke() : cx.fill();
  }
}

function order(o) {
  if (o.state === "aborted") return;
  const ex = X(o.xy[0]), ey = Y(o.xy[1]), col = EFFC[o.kind] || "#888";
  cx.strokeStyle = col;
  cx.lineWidth = o.state === "executing" ? 2 : 1;
  cx.globalAlpha = o.state === "pending_approval" ? 0.4 : 0.85;
  if (o.state === "pending_approval") cx.setLineDash([3, 4]);
  cx.beginPath(); cx.moveTo(cxw, cyh); cx.lineTo(ex, ey); cx.stroke();
  cx.setLineDash([]); cx.globalAlpha = 1;
  cx.fillStyle = col;
  cx.beginPath(); cx.arc(ex, ey, 7 * devicePixelRatio, 0,
    o.state === "neutralized" ? 7 : 0.0001); cx.stroke();
  if (o.state === "neutralized") {
    cx.strokeStyle = "#fff"; cx.beginPath();
    cx.arc(ex, ey, 9 * devicePixelRatio, 0, 7); cx.stroke();
  }
}

function draw(f) {
  resizeIfNeeded();
  cx.clearRect(0, 0, cv.width, cv.height);
  grid();
  (f.sites || []).forEach(site);
  asset((f.asset && f.asset.keepout) || 250);
  (f.swarms || []).forEach(swarm);
  (f.orders || []).forEach(order);
  (f.tracks || []).forEach(track);
  hud(f); effectors(f); approvals(f); logDelta(f);
}

let needResize = true;
function resizeIfNeeded() { if (needResize) { resize(); needResize = false; } }

function hud(f) {
  const m = f.metrics || {};
  const row = (k, v, cls) =>
    `<div><span>${k}</span><b class="${cls || ""}">${v}</b></div>`;
  el("hud").innerHTML =
    row("scenario", f.scenario || "-") +
    row("t", (m.t ?? 0) + "s") +
    row("threats", m.n_threats ?? 0) +
    row("neutralized", m.n_neutralized ?? 0) +
    row("leaked", m.n_leaked ?? 0,
      (m.n_leaked > 0 ? "" : "")) +
    row("leakage", pct(m.leakage_rate)) +
    row("recall", pct(m.detection_recall)) +
    row("UAS prec", pct(m.uas_precision)) +
    row("latency", (m.mean_cycle_latency_ms ?? 0).toFixed(1) + "ms") +
    row("$/kill", "$" + Math.round(m.sim_cost_per_kill ?? 0)) +
    row("sites up", (m.active_sites ?? 0)) +
    row("audit", m.audit_ok ? "OK" : "BROKEN");
}
const pct = (x) => ((x ?? 0) * 100).toFixed(0) + "%";

function effectors(f) {
  el("effectors").innerHTML = (f.effectors || []).map((e) => {
    const cap = e.mag == null ? "&#8734;" : e.mag;
    const w = e.mag == null ? 100 : Math.max(2, Math.min(100, e.mag * 5));
    return `<div class="eff"><span class="nm" style="color:${
      EFFC[e.kind] || "#888"}">${e.id}</span><div class="bar"><i style="width:${
      w}%;background:${EFFC[e.kind] || "#888"}"></i></div>
      <span class="mg">${cap}</span></div>`;
  }).join("");
}

function approvals(f) {
  const q = (f.orders || []).filter((o) => o.state === "pending_approval");
  el("approvalCard").hidden = q.length === 0;
  el("approvals").innerHTML = q.map((o) =>
    `<div class="appr"><span>#${o.id} ${o.kind} → trk ${o.tid}
     pK ${o.pk}</span><span><button class="y" onclick="act(${o.id},1)">
     APPROVE</button> <button class="n" onclick="act(${o.id},0)">DENY
     </button></span></div>`).join("");
}
window.act = (id, ok) => {
  if (ws && ws.readyState === 1)
    ws.send(JSON.stringify(ok ? { approve: id } : { deny: id }));
};

function logDelta(f) {
  const L = el("log");
  (f.orders || []).forEach((o) => {
    if (seenOrders.get(o.id) === o.state) return;
    seenOrders.set(o.id, o.state);
    let cls = "", txt = `#${o.id} ${o.kind}→trk${o.tid} ${o.state}`;
    if (o.state === "neutralized") cls = "k";
    else if (o.state === "approved" || o.state === "executing") cls = "a";
    else if (o.state === "missed") cls = "m";
    const d = document.createElement("div");
    d.className = cls;
    d.textContent = `[${(f.t ?? 0).toFixed(0)}s] ${txt}`;
    L.prepend(d);
  });
  while (L.childNodes.length > 120) L.removeChild(L.lastChild);
}

// ---- control --------------------------------------------------------------
async function loadScenarios() {
  try {
    const r = await fetch("/api/scenarios");
    const s = await r.json();
    el("scenario").innerHTML = s.map((x) =>
      `<option value="${x.name}">${x.name}</option>`).join("");
  } catch (e) {
    el("scenario").innerHTML = "<option>coordinated_formation</option>";
  }
}

el("start").onclick = () => {
  if (ws) ws.close();
  seenOrders.clear(); el("log").innerHTML = "";
  const p = new URLSearchParams({
    scenario: el("scenario").value,
    human: el("human").checked ? "1" : "0",
    mitigation: el("mitig").checked ? "1" : "0",
  });
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws?${p}`);
  ws.onopen = () => setConn(true);
  ws.onclose = () => setConn(false);
  ws.onmessage = (ev) => {
    const f = JSON.parse(ev.data);
    if (f.final) { el("conn").textContent = "complete"; return; }
    if (f.error) { alert(f.error); return; }
    last = f; requestAnimationFrame(() => draw(f));
  };
};
function setConn(on) {
  const c = el("conn");
  c.className = "pill " + (on ? "on" : "off");
  c.textContent = on ? "live" : "offline";
}

resize(); loadScenarios();
draw({ sites: [], tracks: [], swarms: [], orders: [],
  asset: { keepout: 250 }, metrics: {} });
