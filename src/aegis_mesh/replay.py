"""Deterministic replay export — drives the hosted (Vercel) dashboard with
no backend. Each scenario is run once headless and serialised to JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import Engine
from .sim.scenarios import LIBRARY

DEFAULT_OUT = Path("web-app/public/replays")


def export(scenario: str, out: Path, *, seed: int = 0,
           tracker: str = "gmphd", stride: int = 1) -> Path:
    eng = Engine(LIBRARY[scenario](seed=seed), seed=seed, tracker=tracker,
                 mitigation_authorized=True, require_human=False)
    rep = eng.record_replay()
    rep["frames"] = rep["frames"][::stride]
    rep["tracker"] = tracker
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{scenario}.json"
    p.write_text(json.dumps(rep, separators=(",", ":")))
    return p


def export_all(out: Path = DEFAULT_OUT) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for name in LIBRARY:
        # the 1000-drone replay is large; thin it for the browser
        stride = 2 if "thousand" in name else 1
        p = export(name, out, stride=stride)
        meta = json.loads(p.read_text())["metrics"]
        index.append({"scenario": name,
                      "description": LIBRARY[name]().description,
                      "frames": len(json.loads(p.read_text())["frames"]),
                      "metrics": meta,
                      "bytes": p.stat().st_size})
        print(f"  {name:24s} {p.stat().st_size//1024:6d} KB")
    (out / "index.json").write_text(json.dumps(index, indent=2))
    return [i["scenario"] for i in index]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aegis-export")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--scenario", default="all")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.scenario == "all":
        export_all(out)
    else:
        export(a.scenario, out)
    print(f"replays -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
