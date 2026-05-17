"""FastAPI app: serves the operator COP and streams a live engagement over
WebSocket, with a real human-on-the-loop approve/deny channel.

    uvicorn aegis_mesh.server.app:app   (or:  aegis-serve)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..engine import Engine
from ..sim.scenarios import LIBRARY

WEB = Path(__file__).resolve().parents[3] / "web"

app = FastAPI(title="AEGIS-MESH COP")
app.mount("/static", StaticFiles(directory=str(WEB / "static")), name="static")


@app.get("/")
def index():
    return FileResponse(str(WEB / "index.html"))


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
                 mitigation_authorized=mitigation, require_human=human,
                 node_loss=node_loss)
    speed = float(q.get("speed", "6"))           # playback x real-time
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
        return
    except Exception as exc:                      # noqa: BLE001
        await sock.send_json({"error": str(exc)})


def main() -> int:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    return 0
