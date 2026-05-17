# AEGIS-MESH — Counter-Swarm Defense (autonomy + data OS)

A sensor- and effector-agnostic real-time autonomy + data layer for
counter-swarm defense. The moat is the autonomy/data flywheel, not the
hardware (see `PLAN.md`).

> **Defensive only.** Read `SAFETY.md` first — a permanent, non-negotiable
> project boundary. Red-team and simulation target only our own synthetic
> range; no offensive weaponization.

## End-to-end system (implemented, runnable, tested)

```
SENSE ───────────► FUSE ──────────► SENSEMAKE ────► DECIDE ───────► EFFECT
multi-site mesh    EKF tracker      DBSCAN swarm    WTA + auth      authority-gated
radar / passiveRF  Cartesian +      intent, hull,   FSM, approval   simulated effect
/ EO-IR / acoustic bearing-only     axis, TTI,      queue, audit    + Pkill model
node-loss inject   KD-tree GNN      mothership      hash-chain      closed-loop
                   classifier
```

| Vertical | What's actually coded |
|---|---|
| **sim** | 7-site sensor mesh: radar (RCS/range Pd + clutter), passive-RF **bearing-only**, EO-IR, acoustic; signature-structured targets; mothership child-release; node-loss injection |
| **fusion** | 6-state **EKF** fusing Cartesian *and* bearing-only measurements; KD-tree gated GNN association (scales to 1000+); track lifecycle; softmax **classifier** trained on the signature model |
| **sensemaking** | **DBSCAN** swarm clustering, convex hull, heading coherence, axis-of-attack, time-to-impact distribution, mothership heuristic, class-weighted threat score |
| **orchestrator** | WTA: KD-tree **max-coverage** area bursts (HPM economics) + greedy optimal point assignment; **Pkill** model; keep-out; engagement-authority **FSM** with human-on-the-loop approval queue; tamper-evident **hash-chained audit** |
| **mesh** | decentralised pub/sub bus with fault isolation (node failure ≠ system failure) |
| **server** | FastAPI live COP over **WebSocket** + real approve/deny channel |
| **web** | zero-build canvas **operator dashboard** (dark ops UI) |
| **viz** | offline matplotlib COP renderer → PNG + animated GIF |

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q                                  # 23 regression tests
aegis-sim all                              # Threat Library + §10 metrics
aegis-sim coordinated_formation --kill-site radar-N@12   # resilience demo
aegis-sim single_drone --no-mitigation     # commercial detect/track build
aegis-serve                                # live COP at http://127.0.0.1:8000
aegis-render mixed_dark_saturation         # PNG + GIF in examples/
```

## Validated results (deterministic, seed 0)

| Scenario | Threats | Neutralized | Leak | Recall | UAS prec | $/kill | Cycle |
|---|--:|--:|--:|--:|--:|--:|--:|
| single_drone | 1 | 1 | 0 | 100% | 100% | $25 | 0.6 ms |
| coordinated_formation | 8 | 8 | 0 | 100% | 100% | $31 | 0.8 ms |
| mixed_dark_saturation (3-axis) | 30 | 30 | 0 | 100% | 100% | ~$140 | 2.4 ms |
| mothership_release (RF-silent) | 11 | 11 | 0 | 100% | 100% | ~$570 | 1.2 ms |
| **thousand_swarm** | **1000** | **1000** | 0 | 100% | 100% | **~$46** | ~95 ms |

RF-silent / dark targets cost more per kill (no cheap soft-kill) — an honest,
real-world economics insight, not hidden. `examples/` holds rendered COP
snapshots and animations.

## Layout

```
src/aegis_mesh/{sim,fusion,sensemaking,orchestrator,mesh}/   core verticals
src/aegis_mesh/{engine,pipeline,cli}.py                      closed loop
src/aegis_mesh/server/  web/                                 live COP
src/aegis_mesh/viz/     examples/                            offline render
tests/                                                       23 tests
legacy/factor-capacity-monitor/                              archived prior project
```

`PLAN.md` is the strategy/architecture source of truth; production migrates
the real-time path to Rust/C++ + ROS 2/DDS per `PLAN.md` §3.
