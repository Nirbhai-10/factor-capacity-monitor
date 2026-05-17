"use strict";
// AEGIS-MESH replay COP. Static/Vercel: plays precomputed replay JSON.
// Optional live mode: append ?ws=wss://host/ws to stream from a backend.
const VIEW = 6800;
const cv = document.getElementById("cop"), cx = cv.getContext("2d");
const el = (id) => document.getElementById(id);
const CLS = { uas:"#ff4d5e", unknown:"#ffc24b", bird:"#5b7384",
  aircraft:"#7aa7c7", clutter:"#3f5260" };
const EFFC = { soft_kill_cyber:"#27e0c4", hpm:"#b07bff",
  laser:"#ff7a45", net_interceptor:"#54d98c" };
const LAYERS = { sensors:1, tracks:1, swarms:1, engage:1, leaders:1 };

let replay=null, frames=[], fi=0, playing=false, timer=null, seen=new Map();
let scale=1, cw=0, ch=0;

function resize(){
  cv.width=cv.clientWidth*devicePixelRatio;
  cv.height=cv.clientHeight*devicePixelRatio;
  scale=Math.min(cv.width,cv.height)/(2*VIEW);
  cw=cv.width/2; ch=cv.height/2;
}
addEventListener("resize",()=>{resize();if(frames[fi])draw(frames[fi]);});
const X=(m)=>cw+m*scale, Y=(m)=>ch-m*scale;

function grid(){
  cx.strokeStyle="#11202b"; cx.fillStyle="#2d4a59";
  cx.font=`${11*devicePixelRatio}px ui-monospace`;
  for(let r=1000;r<=6000;r+=1000){
    cx.beginPath();cx.arc(cw,ch,r*scale,0,7);cx.stroke();
    cx.fillText(`${r/1000}km`,cw+4,ch-r*scale+13);
  }
  cx.strokeStyle="#0f1922";
  cx.beginPath();cx.moveTo(cw,0);cx.lineTo(cw,cv.height);
  cx.moveTo(0,ch);cx.lineTo(cv.width,ch);cx.stroke();
}
function asset(ko){
  cx.save();cx.strokeStyle="#ff7a45";cx.setLineDash([5,5]);
  cx.beginPath();cx.arc(cw,ch,ko*scale,0,7);cx.stroke();cx.setLineDash([]);
  cx.fillStyle="#27e0c4";cx.beginPath();
  for(let k=0;k<4;k++){const a=k*Math.PI/2;
    cx[k?"lineTo":"moveTo"](cw+Math.cos(a)*9*devicePixelRatio,
      ch+Math.sin(a)*9*devicePixelRatio);}
  cx.closePath();cx.fill();
  cx.fillStyle="#7fe9da";cx.fillText("ASSET",cw+12,ch+4);cx.restore();
}
function site(s){
  const sx=X(s.x),sy=Y(s.y),on=s.active;
  if(LAYERS.sensors){
    cx.globalAlpha=on?0.09:0.03;
    cx.strokeStyle=on?"#1f6f7a":"#3a2030";
    cx.beginPath();cx.arc(sx,sy,s.range*scale,0,7);cx.stroke();
    cx.globalAlpha=1;
  }
  cx.fillStyle=on?"#3fb6c2":"#5a2734";cx.fillRect(sx-4,sy-4,8,8);
  if(!on){cx.strokeStyle="#ff4d5e";cx.beginPath();
    cx.moveTo(sx-6,sy-6);cx.lineTo(sx+6,sy+6);
    cx.moveTo(sx+6,sy-6);cx.lineTo(sx-6,sy+6);cx.stroke();}
  cx.fillStyle=on?"#46647a":"#7a3a4a";cx.fillText(s.id,sx+7,sy+3);
}
function swarm(s){
  if(!LAYERS.swarms||!s.hull.length)return;
  const t=s.threat;
  cx.beginPath();
  s.hull.forEach((p,i)=>cx[i?"lineTo":"moveTo"](X(p[0]),Y(p[1])));
  cx.closePath();
  cx.fillStyle=`rgba(255,77,94,${0.04+0.2*t})`;
  cx.strokeStyle=`rgba(255,120,90,${0.35+0.5*t})`;
  cx.lineWidth=1.4;cx.fill();cx.stroke();
  const c=s.hull[0];cx.fillStyle="#ffd9a0";
  cx.fillText(`S${s.id} n=${s.n} T=${t.toFixed(2)}`+
    (s.tti!=null?` TTI=${s.tti}s`:"")+
    (s.mothership?" ⚑MOTHERSHIP":""),X(c[0])+6,Y(c[1])-6);
}
function order(o){
  if(!LAYERS.engage||o.state==="aborted")return;
  const ex=X(o.xy[0]),ey=Y(o.xy[1]),col=EFFC[o.kind]||"#888";
  cx.strokeStyle=col;cx.lineWidth=o.state==="executing"?2:1;
  cx.globalAlpha=o.state==="pending_approval"?0.4:0.85;
  if(o.state==="pending_approval")cx.setLineDash([3,4]);
  cx.beginPath();cx.moveTo(cw,ch);cx.lineTo(ex,ey);cx.stroke();
  cx.setLineDash([]);cx.globalAlpha=1;
  if(o.state==="neutralized"){cx.strokeStyle="#fff";
    cx.beginPath();cx.arc(ex,ey,9*devicePixelRatio,0,7);cx.stroke();}
}
function track(t){
  if(!LAYERS.tracks)return;
  const px=X(t.x),py=Y(t.y),c=CLS[t.cls]||"#888";
  if(LAYERS.leaders&&(t.vx||t.vy)){
    cx.strokeStyle=c;cx.globalAlpha=0.45;cx.beginPath();
    cx.moveTo(px,py);cx.lineTo(X(t.x+t.vx*6),Y(t.y+t.vy*6));
    cx.stroke();cx.globalAlpha=1;
  }
  cx.fillStyle=c;cx.strokeStyle=c;cx.lineWidth=1.3;
  const r=4*devicePixelRatio;
  if(t.cls==="uas"){
    cx.beginPath();cx.moveTo(px,py-r);cx.lineTo(px+r,py);
    cx.lineTo(px,py+r);cx.lineTo(px-r,py);cx.closePath();
    t.status==="coasting"?cx.stroke():cx.fill();
  }else{cx.beginPath();cx.arc(px,py,r*0.8,0,7);
    t.cls==="unknown"?cx.stroke():cx.fill();}
}
function draw(f){
  cx.clearRect(0,0,cv.width,cv.height);
  grid();
  (f.sites||[]).forEach(site);
  asset((f.asset&&f.asset.keepout)||250);
  (f.swarms||[]).forEach(swarm);
  (f.orders||[]).forEach(order);
  (f.tracks||[]).forEach(track);
  kpis(f); pipe(f); effectors(f); logDelta(f);
  el("clock").textContent=`t ${(f.t??0).toFixed(1)}s`;
}
const pct=(x)=>((x??0)*100).toFixed(0)+"%";
function kpis(f){
  const m=f.metrics||{};
  const card=(v,lbl,cls="")=>`<div class="kpi ${cls}"><b>${v}</b>
    <i>${lbl}</i></div>`;
  el("kpis").innerHTML=
    card(m.n_threats??0,"threats")+
    card(m.n_neutralized??0,"neutralized","good")+
    card(m.n_leaked??0,"leaked",(m.n_leaked>0)?"bad":"")+
    card(pct(m.detection_recall),"recall")+
    card(pct(m.uas_precision),"UAS prec")+
    card("$"+Math.round(m.sim_cost_per_kill??0),"$/kill")+
    card((m.mean_cycle_latency_ms??0).toFixed(0)+"ms","cycle")+
    card(m.audit_ok?"OK":"BROKEN","audit",m.audit_ok?"good":"bad");
}
function pipe(f){
  const m=f.metrics||{};
  const row=(k,v)=>`<div><span>${k}</span><b>${v}</b></div>`;
  el("pipe").innerHTML=
    row("tracker",(replay&&replay.tracker)||"gmphd")+
    row("active sensors",(m.active_sites??0)+"/7")+
    row("swarms",(f.swarms||[]).length)+
    row("tracks",(f.tracks||[]).length)+
    row("committed $",Math.round(m.committed_cost??0));
}
function effectors(f){
  el("effectors").innerHTML=(f.effectors||[]).map((e)=>{
    const cap=e.mag==null?"∞":e.mag;
    const w=e.mag==null?100:Math.max(3,Math.min(100,e.mag*4));
    const c=EFFC[e.kind]||"#888";
    return `<div class="eff"><span class="nm" style="color:${c}">${e.id}
     </span><div class="bar2"><i style="width:${w}%;background:${c}"></i>
     </div><span class="mg">${cap}</span></div>`;}).join("");
}
function logDelta(f){
  const L=el("log");
  (f.orders||[]).forEach((o)=>{
    if(seen.get(o.id)===o.state)return;
    seen.set(o.id,o.state);
    let cls="";
    if(o.state==="neutralized")cls="k";
    else if(o.state==="approved"||o.state==="executing")cls="a";
    else if(o.state==="missed")cls="m";
    const d=document.createElement("div");d.className=cls;
    d.textContent=`[${(f.t??0).toFixed(0)}s] #${o.id} ${o.kind}→trk`+
      `${o.tid} ${o.state}`;
    L.prepend(d);
  });
  while(L.childNodes.length>140)L.removeChild(L.lastChild);
}

// ---- replay control -------------------------------------------------------
function setFrame(i){
  fi=Math.max(0,Math.min(frames.length-1,i));
  el("scrub").value=frames.length>1?(fi/(frames.length-1)*100):0;
  if(frames[fi])draw(frames[fi]);
}
function tick(){
  if(!playing)return;
  if(fi>=frames.length-1){playing=false;el("play").textContent="↺ REPLAY";
    return;}
  setFrame(fi+1);
  const sp=parseFloat(el("speed").value)||1;
  timer=setTimeout(()=>requestAnimationFrame(tick),
    Math.max(((replay.dt||0.5)/sp)*1000/2,16));
}
el("play").onclick=()=>{
  if(fi>=frames.length-1){seen.clear();el("log").innerHTML="";setFrame(0);}
  playing=!playing;
  el("play").textContent=playing?"❚❚ PAUSE":"▶ PLAY";
  if(playing)tick();else clearTimeout(timer);
};
el("scrub").oninput=(e)=>{playing=false;el("play").textContent="▶ PLAY";
  setFrame(Math.round(e.target.value/100*(frames.length-1)));};

async function loadReplay(name){
  playing=false;clearTimeout(timer);seen.clear();el("log").innerHTML="";
  const r=await fetch(`/public/replays/${name}.json`);
  replay=await r.json();frames=replay.frames||[];
  el("desc").textContent=(window._idx&&window._idx[name])||replay.scenario;
  setFrame(0);
}
async function boot(){
  resize();
  el("layers").innerHTML=Object.keys(LAYERS).map((k)=>
    `<label><input type="checkbox" data-l="${k}" checked> ${k}</label>`)
    .join("");
  el("layers").querySelectorAll("input").forEach((c)=>c.onchange=()=>{
    LAYERS[c.dataset.l]=c.checked?1:0;if(frames[fi])draw(frames[fi]);});
  el("legend").innerHTML=[
    ["#ff4d5e","UAS / hostile"],["#ffc24b","unknown"],
    ["#5b7384","bird / decoy"],["#27e0c4","cyber take-over"],
    ["#b07bff","HPM area burst"],["#ff7a45","laser"],
    ["#54d98c","net interceptor"]].map(([c,t])=>
    `<div><span class="dot" style="background:${c}"></span>${t}</div>`)
    .join("");
  let idx=[];
  try{idx=await (await fetch("/public/replays/index.json")).json();}
  catch(e){idx=[];}
  window._idx={};idx.forEach((x)=>window._idx[x.scenario]=x.description);
  el("scenario").innerHTML=idx.map((x)=>
    `<option value="${x.scenario}">${x.scenario}</option>`).join("")||
    "<option>coordinated_formation</option>";
  el("scenario").onchange=()=>loadReplay(el("scenario").value);
  const ws=new URLSearchParams(location.search).get("ws");
  if(ws){liveMode(ws);return;}
  if(idx.length)await loadReplay(idx[0].scenario);
}
function liveMode(url){
  el("mode").textContent="live";el("src").textContent="live ws";
  const sc=el("scenario").value||"coordinated_formation";
  const s=new WebSocket(`${url}?scenario=${sc}`);
  s.onmessage=(e)=>{const f=JSON.parse(e.data);
    if(f.final||f.error)return;draw(f);};
}
boot();
