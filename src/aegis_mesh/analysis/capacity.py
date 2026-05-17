"""Capacity & cost-exchange study — the value proposition, quantified.

Sweeps raid size against a multi-generation saturation attack and reports,
per raid size: leakage %, defended fraction, $/kill, and the
cost-exchange ratio (attacker spend : defender spend). The saturation
point is the largest raid the layered defence holds under the leakage
ceiling. Renders examples/value_proposition.png + a JSON summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..doctrine import Doctrine
from ..engine import Engine
from ..sim.scenarios import thousand_swarm

DEFAULT_SIZES = (25, 50, 100, 200, 400)
LEAK_CEIL = 0.05


def study(sizes=DEFAULT_SIZES, *, seed=0, tracker="gnn",
          attacker_unit_cost: float | None = None) -> dict:
    doc = Doctrine.load()
    auc = attacker_unit_cost or doc.attacker_unit_cost
    rows = []
    for n in sizes:
        eng = Engine(thousand_swarm(seed=seed, n=n), seed=seed,
                     tracker=tracker, doctrine=doc)
        m = eng.run()
        atk = n * auc
        deff = max(m.committed_cost, 1.0)
        rows.append({
            "raid": n,
            "leakage_pct": round(m.leakage_rate * 100, 2),
            "defended_pct": round(100 * m.n_neutralized /
                                  max(m.n_threats, 1), 1),
            "autonomous": m.n_autonomous,
            "auto_defeated": m.autonomous_neutralized,
            "escalations": m.escalations,
            "cost_per_kill": round(m.sim_cost_per_kill, 1),
            "defender_spend": round(m.committed_cost, 0),
            "attacker_spend": atk,
            "cost_exchange": round(atk / deff, 1),
            "ospa": m.ospa})
    held = [r["raid"] for r in rows if r["leakage_pct"] <= LEAK_CEIL * 100]
    return {"attacker_unit_cost": auc,
            "leak_ceiling_pct": LEAK_CEIL * 100,
            "saturation_point": max(held) if held else 0,
            "rows": rows}


def render(summary: dict, out: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r = summary["rows"]
    raids = [x["raid"] for x in r]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), facecolor="#070b10")
    for a in ax:
        a.set_facecolor("#0d141c")
        a.tick_params(colors="#6c8597")
        for s in a.spines.values():
            s.set_color("#1d2c39")
        a.grid(True, color="#16242f", lw=0.6)

    ax[0].plot(raids, [x["leakage_pct"] for x in r], "o-",
               color="#ff4d5e", lw=2)
    ax[0].axhline(summary["leak_ceiling_pct"], color="#ff7a45", ls="--",
                  label=f"{summary['leak_ceiling_pct']:.0f}% ceiling")
    ax[0].set_title("Leakage vs raid size", color="#eaf6ff")
    ax[0].set_xlabel("attacking drones", color="#6c8597")
    ax[0].set_ylabel("leakage %", color="#6c8597")
    ax[0].legend(facecolor="#0d141c", labelcolor="#cfe3ee")

    ax[1].plot(raids, [x["cost_exchange"] for x in r], "o-",
               color="#27e0c4", lw=2)
    ax[1].axhline(1.0, color="#6c8597", ls=":")
    ax[1].set_title("Cost-exchange ratio (attacker $ : our $)",
                    color="#eaf6ff")
    ax[1].set_xlabel("attacking drones", color="#6c8597")
    ax[1].set_ylabel("× in our favour", color="#6c8597")

    sp = summary["saturation_point"]
    fig.suptitle(
        f"AEGIS-MESH value proposition — holds {sp} drones under "
        f"{summary['leak_ceiling_pct']:.0f}% leakage; "
        f"cost-exchange ~{r[-1]['cost_exchange']:.0f}x in our favour",
        color="#eaf6ff", fontsize=13)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor="#070b10", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aegis-capacity")
    ap.add_argument("--sizes", default="25,50,100,200,400")
    ap.add_argument("--tracker", default="gnn")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="examples/value_proposition.png")
    a = ap.parse_args(argv)
    sizes = tuple(int(s) for s in a.sizes.split(","))
    s = study(sizes, seed=a.seed, tracker=a.tracker)
    Path("examples").mkdir(exist_ok=True)
    Path("examples/value_proposition.json").write_text(
        json.dumps(s, indent=2))
    render(s, Path(a.out))
    print(json.dumps(s, indent=2))
    print(f"saturation point: {s['saturation_point']} drones; "
          f"chart -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
