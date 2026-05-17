"""FastAPI app: serves the operator COP and streams a live engagement over
WebSocket, with a real human-on-the-loop approve/deny channel.

    uvicorn aegis_mesh.server.app:app   (or:  aegis-serve)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import logging
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from ..config import CONFIG
from ..engine import Engine
from ..sim.scenarios import LIBRARY

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"
REPLAYS = ROOT / "web-app" / "public" / "replays"

logging.basicConfig(level=CONFIG.log_level,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("aegis.server")

app = FastAPI(title="AEGIS-MESH COP", version="0.2.0")
app.mount("/static", StaticFiles(directory=str(WEB / "static")), name="static")

_STATS = {"ws_sessions": 0, "ws_active": 0, "started": time.time()}


@app.get("/")
def index():
    return FileResponse(str(WEB / "index.html"))


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": round(time.time() - _STATS["started"], 1),
            "tracker": CONFIG.default_tracker}


@app.get("/metrics")
def metrics():
    up = time.time() - _STATS["started"]
    body = (
        "# HELP aegis_uptime_seconds Process uptime.\n"
        "# TYPE aegis_uptime_seconds gauge\n"
        f"aegis_uptime_seconds {up:.1f}\n"
        "# HELP aegis_ws_sessions_total Total COP stream sessions.\n"
        "# TYPE aegis_ws_sessions_total counter\n"
        f"aegis_ws_sessions_total {_STATS['ws_sessions']}\n"
        "# HELP aegis_ws_active Active COP stream sessions.\n"
        "# TYPE aegis_ws_active gauge\n"
        f"aegis_ws_active {_STATS['ws_active']}\n")
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4")


@app.get("/api/replay/{scenario}")
def replay(scenario: str):
    p = REPLAYS / f"{scenario}.json"
    if not p.exists():
        return JSONResponse({"error": "no replay; run aegis-export"},
                            status_code=404)
    return FileResponse(str(p), media_type="application/json")


@app.get("/api/scenarios")
def scenarios():
    return JSONResponse([
        {"name": k, "description": LIBRARY[k]().description}
        for k in LIBRARY
    ])


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    q = sock.query_params
    name = q.get("scenario", "coordinated_formation")
    if name not in LIBRARY:
        await sock.close(code=4404)
        return
    seed = int(q.get("seed", "0"))
    mitigation = q.get("mitigation", "1") != "0"
    human = q.get("human", "0") == "1"
    node_loss = None
    if q.get("kill"):
        sid, ts = q["kill"].split("@")
        node_loss = {float(ts): sid}

    eng = Engine(LIBRARY[name](seed=seed), seed=seed,
                 tracker=q.get("tracker", CONFIG.default_tracker),
                 mitigation_authorized=mitigation, require_human=human,
                 node_loss=node_loss)
    speed = float(q.get("speed", str(CONFIG.playback_speed)))
    _STATS["ws_sessions"] += 1
    _STATS["ws_active"] += 1
    log.info("stream start scenario=%s tracker=%s", name, eng.tracker_kind)
    try:
        while not eng.done:
            # drain client approvals without blocking the sim clock
            try:
                while True:
                    raw = await asyncio.wait_for(sock.receive_text(),
                                                 timeout=1e-4)
                    msg = json.loads(raw)
                    if "approve" in msg:
                        eng.mgr.approve(int(msg["approve"]), eng.world.t)
                    elif "deny" in msg:
                        eng.mgr.deny(int(msg["deny"]), eng.world.t)
            except (asyncio.TimeoutError, ValueError):
                pass
            frame = eng.step()
            await sock.send_json(frame)
            await asyncio.sleep(max(eng.sc.dt / speed, 0.01))
        await sock.send_json({"t": eng.world.t, "final": eng.m.__dict__})
    except WebSocketDisconnect:
        pass
    except Exception as exc:                      # noqa: BLE001
        log.exception("stream error")
        try:
            await sock.send_json({"error": str(exc)})
        except Exception:
            pass
    finally:
        _STATS["ws_active"] -= 1


def main() -> int:
    import uvicorn
    uvicorn.run(app, host=CONFIG.host, port=CONFIG.port,
                log_level=CONFIG.log_level.lower())
    return 0
