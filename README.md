# AEGIS-MESH — Counter-Swarm Defense (autonomy + data OS)

A sensor- and effector-agnostic real-time autonomy + data layer for
counter-swarm defense. The moat is the autonomy/data flywheel, not the
hardware (see `PLAN.md`).

> **Defensive only.** Read `SAFETY.md` first — it is a permanent,
> non-negotiable project boundary. No offensive weaponization; red-team and
> simulation target only our own synthetic range.

## What's here (Phase 0/1 reference slice)

A runnable, tested `sense -> fuse -> sensemake -> decide -> audit` loop driven
by a synthetic multi-sensor swarm simulation:

- `sim/` — multi-sensor model (radar / passive-RF / EO-IR, missed detections,
  clutter) + **Threat Library v0** scenarios (single, formation, mixed-dark
  saturation, 1000-drone scaling).
- `fusion/` — multi-target tracker: constant-velocity Kalman + GNN association
  with Mahalanobis gating and M/N confirm/delete (MHT/JPDA stand-in).
- `sensemaking/` — swarm-intent estimation (clustering + coherence,
  axis-of-attack, time-to-impact, threat level).
- `orchestrator/` — weapon-target assignment (area-effector economics),
  human-on-the-loop authority FSM, tamper-evident hash-chained audit log.
- `pipeline.py` — wires it together and reports the §10 regression metrics.

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q
aegis-sim all                 # full Threat Library + metrics
aegis-sim single_drone --no-mitigation   # commercial detect/track-only build
```

Headline metrics: detection recall, leakage rate, decision latency, simulated
cost-per-kill, audit-chain integrity — enforced as regression tests in CI.

## Roadmap

`PLAN.md` is the source of truth (phased: detect/track → decide → effect →
scale). This slice is Phase 0 + the Phase 1 core; production migrates the
real-time path to Rust/C++ + ROS 2/DDS on edge compute per `PLAN.md` §3.

## Layout

```
src/aegis_mesh/{sim,fusion,sensemaking,orchestrator}/   core
tests/                                                  regression suite
redteam/                                                sim-only, safety-gated
legacy/factor-capacity-monitor/                          archived prior project
```
