"""Render the COP offline to a PNG snapshot and an animated GIF, so the
operator picture is inspectable without running the server.

    python -m aegis_mesh.viz.render mixed_dark_saturation
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib import patches           # noqa: E402
from matplotlib.animation import PillowWriter  # noqa: E402

from ..engine import Engine              # noqa: E402
from ..sim.scenarios import LIBRARY      # noqa: E402

BG, INK, DIM = "#070b10", "#cfe3ee", "#6c8597"
CLS = {"uas": "#ff4d5e", "unknown": "#ffc24b", "bird": "#5b7384",
       "aircraft": "#7aa7c7", "clutter": "#3f5260"}
EFFC = {"soft_kill_cyber": "#28e0c4", "hpm": "#b07bff",
        "laser": "#ff7a45", "net_interceptor": "#54d98c"}
LIM = 6800


def _axes():
    fig = plt.figure(figsize=(13, 9), facecolor=BG)
    ax = fig.add_axes([0.0, 0.0, 0.74, 1.0]); ax.set_facecolor(BG)
    ax.set_xlim(-LIM, LIM); ax.set_ylim(-LIM, LIM)
    ax.set_aspect("equal"); ax.axis("off")
    tx = fig.add_axes([0.74, 0.0, 0.26, 1.0]); tx.set_facecolor("#0d141c")
    tx.axis("off")
    return fig, ax, tx


def _draw(ax, tx, f):
    ax.clear(); ax.set_xlim(-LIM, LIM); ax.set_ylim(-LIM, LIM)
    ax.set_aspect("equal"); ax.axis("off"); ax.set_facecolor(BG)
    for r in range(1000, 6001, 1000):
        ax.add_patch(patches.Circle((0, 0), r, fill=False,
                     ec="#16242f", lw=0.8))
        ax.text(60, r - 150, f"{r//1000}km", color="#33505f", fontsize=8)
    for s in f["sites"]:
        on = s["active"]
        ax.add_patch(patches.Circle((s["x"], s["y"]), s["range"], fill=False,
                     ec=("#1f6f7a" if on else "#3a2030"),
                     lw=0.5, alpha=0.5 if on else 0.25))
        ax.scatter([s["x"]], [s["y"]], marker="s", s=42,
                   c=("#3fb6c2" if on else "#5a2734"),
                   edgecolors="none", zorder=5)
        if not on:
            ax.scatter([s["x"]], [s["y"]], marker="x", s=70,
                       c="#ff4d5e", zorder=6)
        ax.text(s["x"] + 130, s["y"], s["id"], fontsize=7,
                color=("#4a6678" if on else "#7a3a4a"))
    ko = f["asset"]["keepout"]
    ax.add_patch(patches.Circle((0, 0), ko, fill=False, ec="#ff7a45",
                 ls="--", lw=1))
    ax.scatter([0], [0], marker="D", s=90, c="#28e0c4", zorder=8)
    ax.text(180, 0, "ASSET", color="#7fe9da", fontsize=9, va="center")

    for s in f["swarms"]:
        h = s["hull"]
        if len(h) >= 3:
            t = s["threat"]
            ax.add_patch(patches.Polygon(
                h, closed=True, fc=(1, 0.3, 0.36, 0.05 + 0.2 * t),
                ec=(1, 0.47, 0.35, 0.4 + 0.5 * t), lw=1.4))
        cx0, cy0 = h[0]
        lbl = f"S{s['id']} n={s['n']} T={s['threat']:.2f}"
        if s["tti"] is not None:
            lbl += f" TTI={s['tti']}s"
        if s["mothership"]:
            lbl += " MOTHERSHIP"
        ax.text(cx0 + 80, cy0 + 80, lbl, color="#ffd9a0", fontsize=8)

    for o in f["orders"]:
        if o["state"] in ("aborted",):
            continue
        col = EFFC.get(o["kind"], "#888")
        a = 0.35 if o["state"] == "pending_approval" else 0.8
        ax.plot([0, o["xy"][0]], [0, o["xy"][1]], color=col, lw=1.0,
                alpha=a, ls=":" if o["state"] == "pending_approval" else "-")
        if o["state"] == "neutralized":
            ax.scatter([o["xy"][0]], [o["xy"][1]], s=90,
                       facecolors="none", edgecolors="#ffffff", lw=1.2)

    for t in f["tracks"]:
        col = CLS.get(t["cls"], "#888")
        ax.plot([t["x"], t["x"] + t["vx"] * 6],
                [t["y"], t["y"] + t["vy"] * 6], color=col, lw=0.6, alpha=0.5)
        mk = "D" if t["cls"] == "uas" else "o"
        fc = "none" if t["status"] == "coasting" or t["cls"] == "unknown" \
            else col
        ax.scatter([t["x"]], [t["y"]], marker=mk, s=26, c=None,
                   facecolors=fc, edgecolors=col, lw=1.0, zorder=7)

    m = f["metrics"]
    tx.clear(); tx.axis("off"); tx.set_facecolor("#0d141c")
    tx.set_xlim(0, 1); tx.set_ylim(0, 1)
    tx.text(0.06, 0.97, "AEGIS-MESH", color="#eaf6ff", fontsize=15,
            weight="bold")
    tx.text(0.06, 0.945, "counter-swarm COP", color=DIM, fontsize=8)
    rows = [
        ("scenario", f["scenario"]),
        ("t", f"{m['t']}s"),
        ("threats", m["n_threats"]),
        ("neutralized", m["n_neutralized"]),
        ("leaked", m["n_leaked"]),
        ("leakage", f"{m['leakage_rate']*100:.0f}%"),
        ("recall", f"{m['detection_recall']*100:.0f}%"),
        ("UAS prec", f"{m['uas_precision']*100:.0f}%"),
        ("latency", f"{m['mean_cycle_latency_ms']:.1f}ms"),
        ("$/kill", f"${m['sim_cost_per_kill']:.0f}"),
        ("sites up", m["active_sites"]),
        ("audit", "OK" if m["audit_ok"] else "BROKEN"),
    ]
    y = 0.90
    for k, v in rows:
        tx.text(0.06, y, k, color=DIM, fontsize=9)
        tx.text(0.94, y, str(v), color="#eaf6ff", fontsize=9, ha="right")
        y -= 0.045
    y -= 0.02
    tx.text(0.06, y, "EFFECTORS", color=DIM, fontsize=9); y -= 0.04
    for e in f["effectors"]:
        cap = "inf" if e["mag"] is None else e["mag"]
        tx.text(0.06, y, e["id"], color=EFFC.get(e["kind"], "#888"),
                fontsize=8)
        tx.text(0.94, y, str(cap), color="#cfe3ee", fontsize=8, ha="right")
        y -= 0.036


def render(scenario: str, seed: int = 0, out: Path | None = None,
           gif: bool = True):
    out = out or Path("examples")
    out.mkdir(parents=True, exist_ok=True)
    eng = Engine(LIBRARY[scenario](seed=seed), seed=seed,
                 mitigation_authorized=True, require_human=False)
    rep = eng.record_replay()
    frames = rep["frames"]
    fig, ax, tx = _axes()

    # snapshot at peak engagement
    peak = max(frames, key=lambda fr: len(fr["orders"]))
    _draw(ax, tx, peak)
    png = out / f"cop_{scenario}.png"
    fig.savefig(png, facecolor=BG, dpi=130)
    print(f"wrote {png}")

    if gif:
        step = max(1, len(frames) // 90)
        sel = frames[::step]
        w = PillowWriter(fps=12)
        g = out / f"cop_{scenario}.gif"
        with w.saving(fig, str(g), dpi=80):
            for fr in sel:
                _draw(ax, tx, fr)
                w.grab_frame()
        print(f"wrote {g} ({len(sel)} frames)")
    plt.close(fig)
    print(eng.m.summary())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=list(LIBRARY))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-gif", action="store_true")
    a = ap.parse_args(argv)
    render(a.scenario, a.seed, gif=not a.no_gif)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
