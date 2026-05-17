"""CLI: run Threat Library scenarios and print §10 regression metrics."""

from __future__ import annotations

import argparse

from .engine import Engine
from .sim.scenarios import LIBRARY


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aegis-sim",
                                 description="Counter-swarm sim (defensive).")
    ap.add_argument("scenario", nargs="?", default="all",
                    choices=["all", *LIBRARY.keys()])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-mitigation", action="store_true",
                    help="commercial detect/track-only build (no effect)")
    ap.add_argument("--human", action="store_true",
                    help="require human-on-the-loop approval")
    ap.add_argument("--kill-site", default=None,
                    help="inject sensor node loss, e.g. radar-N@25")
    args = ap.parse_args(argv)

    node_loss = None
    if args.kill_site:
        sid, ts = args.kill_site.split("@")
        node_loss = {float(ts): sid}

    names = list(LIBRARY) if args.scenario == "all" else [args.scenario]
    for name in names:
        sc = LIBRARY[name](seed=args.seed)
        m = Engine(sc, seed=args.seed,
                   mitigation_authorized=not args.no_mitigation,
                   require_human=args.human, node_loss=node_loss).run()
        print(m.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
