"""CLI: run Threat Library scenarios and print the §10 regression metrics."""

from __future__ import annotations

import argparse

from .pipeline import run
from .sim.scenarios import LIBRARY


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aegis-sim",
                                 description="Counter-swarm sim (defensive).")
    ap.add_argument("scenario", nargs="?", default="all",
                    choices=["all", *LIBRARY.keys()])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-mitigation", action="store_true",
                    help="commercial detect/track-only build (no effect)")
    args = ap.parse_args(argv)

    names = list(LIBRARY) if args.scenario == "all" else [args.scenario]
    for name in names:
        sc = LIBRARY[name](seed=args.seed)
        m = run(sc, mitigation_authorized=not args.no_mitigation,
                seed=args.seed)
        print(m.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
